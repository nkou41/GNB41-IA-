import os
import requests
from flask import Blueprint, request, jsonify, current_app
import hmac
import hashlib
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from app import db, limiter
from app.models.plan import Plan
from app.models.user import User
from app.models.payment import Payment
from app.services.email_service import send_email

billing_bp = Blueprint('billing', __name__)


def _fedapay_base_url():
    env = os.environ.get('FEDAPAY_ENVIRONMENT', 'sandbox').strip()
    return 'https://api.fedapay.com/v1' if env == 'live' else 'https://sandbox-api.fedapay.com/v1'


def _fedapay_headers():
    key = os.environ.get('FEDAPAY_SECRET_KEY', '').strip()
    return {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}


@billing_bp.route('/create-payment', methods=['POST'])
@login_required
@limiter.limit('10 per hour')
def create_payment():
    data = request.get_json()
    plan_slug = data.get('plan')
    plan = Plan.query.filter_by(slug=plan_slug, actif=True).first()
    if not plan:
        return jsonify({'error': 'Plan invalide'}), 400
    if plan.sur_devis or not plan.prix_xof:
        return jsonify({'error': 'Ce plan necessite de nous contacter directement'}), 400

    base = _fedapay_base_url()
    headers = _fedapay_headers()

    try:
        payload = {
            'description': f'GNB41 IA - Plan {plan.nom}',
            'amount': plan.prix_xof,
            'currency': {'iso': 'XOF'},
            'customer': {
                'firstname': current_user.username,
                'lastname': '.',
                'email': current_user.email,
            }
        }
        res = requests.post(f'{base}/transactions', json=payload, headers=headers, timeout=15)
        if not res.ok:
            current_app.logger.error(f'FedaPay create transaction {res.status_code}: {res.text}')
            return jsonify({'error': 'Erreur lors de la creation du paiement', 'detail': res.text}), 500
        transaction = res.json()['v1/transaction']
        transaction_id = transaction['id']

        token_res = requests.post(f'{base}/transactions/{transaction_id}/token', headers=headers, timeout=15)
        if not token_res.ok:
            current_app.logger.error(f'FedaPay token {token_res.status_code}: {token_res.text}')
            return jsonify({'error': 'Erreur lors de la creation du paiement', 'detail': token_res.text}), 500
        token_data = token_res.json()

        current_user.pending_plan = plan.slug
        current_user.pending_transaction_id = transaction_id
        db.session.add(Payment(
            user_id=current_user.id,
            transaction_id=str(transaction_id),
            plan_slug=plan.slug,
            amount=int(plan.prix_xof),
            status='pending',
        ))
        db.session.commit()

        return jsonify({'payment_url': token_data['url'], 'transaction_id': transaction_id})
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'Erreur creation paiement FedaPay: {str(e)}')
        return jsonify({'error': 'Erreur lors de la creation du paiement', 'detail': str(e)}), 500
    except Exception as e:
        current_app.logger.error(f'Erreur inattendue paiement: {str(e)}')
        return jsonify({'error': 'Erreur lors de la creation du paiement', 'detail': str(e)}), 500


def _activate_plan(transaction_id, tx):
    """Idempotent: renvoie (payment, erreur)."""
    p = Payment.query.filter_by(transaction_id=str(transaction_id)).first()
    if not p:
        return None, 'Transaction inconnue'
    if p.status == 'approved':
        return p, None
    plan = Plan.query.filter_by(slug=p.plan_slug, actif=True).first()
    if not plan or int(tx.get('amount') or 0) != int(plan.prix_xof or 0):
        return None, 'Montant ou plan invalide'
    now = datetime.utcnow()
    # prise de verrou atomique: un seul appel passe de pending a approved
    claimed = Payment.query.filter_by(id=p.id, status='pending').update(
        {'status': 'approved', 'processed_at': now}, synchronize_session=False)
    if claimed != 1:
        db.session.rollback()
        return p, None
    user = db.session.get(User, p.user_id)
    base = max(now, user.plan_expiry or now)
    user.plan = plan.slug
    user.plan_expiry = base + timedelta(days=30)
    if plan.credits is not None:
        user.credits = plan.credits
    user.pending_plan = None
    user.pending_transaction_id = None
    db.session.commit()
    try:
        from app.services.notifications import envoyer_notification
        envoyer_notification(
            user.id, 'abonnement', 'Paiement confirmé',
            f"Votre plan {plan.nom} est activé jusqu'au {user.plan_expiry.strftime('%d/%m/%Y')}.")
    except Exception:
        db.session.rollback()
    try:
        send_email(
            user.email,
            f"Paiement confirme - Plan {plan.nom}",
            f"Bonjour {user.username},\n\n"
            f"Votre paiement de {p.amount} XOF a bien ete recu.\n"
            f"Plan active : {plan.nom}\n"
            f"Valable jusqu'au : {user.plan_expiry.strftime('%d/%m/%Y')}\n\n"
            f"Merci de votre confiance,\nGNB41 IA",
        )
    except Exception as e:
        current_app.logger.error(f"Email confirmation paiement: {e}")
    return p, None


@billing_bp.route('/verify-payment/<int:transaction_id>', methods=['GET'])
@login_required
def verify_payment(transaction_id):
    try:
        res = requests.get(f'{_fedapay_base_url()}/transactions/{transaction_id}',
                           headers=_fedapay_headers(), timeout=15)
        res.raise_for_status()
        tx = res.json()['v1/transaction']
        status = tx.get('status')
        if status == 'approved':
            p, err = _activate_plan(transaction_id, tx)
            if err or p.user_id != current_user.id:
                return jsonify({'error': err or 'Transaction non reconnue pour cet utilisateur'}), 400
            return jsonify({'status': 'approved', 'plan': current_user.plan,
                            'plan_expiry': current_user.plan_expiry.isoformat()})
        return jsonify({'status': status})
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        current_app.logger.error(f'Erreur verification paiement FedaPay: {str(e)}')
        return jsonify({'error': 'Erreur lors de la verification'}), 500


@billing_bp.route('/webhook/fedapay', methods=['POST'])
def fedapay_webhook():
    secret = os.environ.get('FEDAPAY_WEBHOOK_SECRET', '').strip()
    if not secret:
        return '', 500
    raw = request.get_data()
    sig = request.headers.get('X-FEDAPAY-SIGNATURE', '')
    parts = dict(x.strip().split('=', 1) for x in sig.split(',') if '=' in x)
    expected = hmac.new(secret.encode(), f"{parts.get('t', '')}.{raw.decode()}".encode(),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, parts.get('s', '')):
        return '', 400
    try:
        tid = (request.get_json(silent=True) or {}).get('entity', {}).get('id')
        if not tid:
            return '', 200
        res = requests.get(f'{_fedapay_base_url()}/transactions/{tid}',
                           headers=_fedapay_headers(), timeout=15)
        res.raise_for_status()
        tx = res.json()['v1/transaction']
        if tx.get('status') == 'approved':
            _activate_plan(tid, tx)
    except Exception as e:
        current_app.logger.error(f'Webhook FedaPay: {str(e)}')
        return '', 500
    return '', 200


@billing_bp.route('/cron/daily', methods=['POST'])
def cron_daily():
    from sqlalchemy import or_
    secret = os.environ.get('CRON_SECRET', '').strip()
    given = request.headers.get('X-Cron-Secret', '')
    if not secret or not hmac.compare_digest(secret, given):
        return '', 403

    now = datetime.utcnow()
    free = Plan.query.filter_by(slug='gratuit').first()
    free_credits = free.credits if free and free.credits is not None else 1

    # 1. Expiration -> plan gratuit
    expired = User.query.filter(
        User.plan != 'gratuit',
        User.plan_expiry.isnot(None),
        User.plan_expiry < now).all()
    expired_info = [(u.email, u.username, u.plan) for u in expired]
    expired_ids = [u.id for u in expired]
    for u in expired:
        u.plan = 'gratuit'
        u.plan_expiry = None
        u.credits = free_credits
        u.reminder_sent_for = None
    db.session.commit()
    for uid, (_e, _n, _old) in zip(expired_ids, expired_info):
        try:
            from app.services.notifications import envoyer_notification
            envoyer_notification(
                uid, 'abonnement', 'Abonnement expiré',
                f"Votre plan {_old} a expiré. Votre compte est repassé au plan Gratuit.")
        except Exception:
            db.session.rollback()
    for email, name, old_plan in expired_info:
        try:
            send_email(email, "Votre abonnement a expire",
                f"Bonjour {name},\n\nVotre plan {old_plan} a expire. "
                f"Votre compte est repasse au plan Gratuit.\n"
                f"Vous pouvez vous reabonner a tout moment depuis votre espace.\n\nGNB41 IA")
        except Exception as e:
            current_app.logger.error(f"Email expiration: {e}")

    # 2. Rappel 3 jours avant l'echeance (une seule fois par echeance)
    soon = User.query.filter(
        User.plan != 'gratuit',
        User.plan_expiry >= now,
        User.plan_expiry <= now + timedelta(days=3),
        or_(User.reminder_sent_for.is_(None),
            User.reminder_sent_for != User.plan_expiry)).all()
    reminded = 0
    for u in soon:
        try:
            send_email(u.email, "Votre abonnement expire bientot",
                f"Bonjour {u.username},\n\nVotre plan {u.plan} expire le "
                f"{u.plan_expiry.strftime('%d/%m/%Y')}.\n"
                f"Renouvelez-le pour garder vos credits et vos avantages.\n\nGNB41 IA")
            u.reminder_sent_for = u.plan_expiry
            db.session.commit()
            reminded += 1
            try:
                from app.services.notifications import envoyer_notification
                envoyer_notification(
                    u.id, 'abonnement', 'Abonnement bientôt expiré',
                    f"Votre plan {u.plan} expire le {u.plan_expiry.strftime('%d/%m/%Y')}. Renouvelez-le pour garder vos crédits.")
            except Exception:
                db.session.rollback()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Email rappel: {e}")

    return jsonify({'downgraded': len(expired_info), 'reminded': reminded})
