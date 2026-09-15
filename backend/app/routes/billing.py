import os
import requests
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from app import db, limiter
from app.models.plan import Plan

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
        db.session.commit()

        return jsonify({'payment_url': token_data['url'], 'transaction_id': transaction_id})
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'Erreur creation paiement FedaPay: {str(e)}')
        return jsonify({'error': 'Erreur lors de la creation du paiement', 'detail': str(e)}), 500
    except Exception as e:
        current_app.logger.error(f'Erreur inattendue paiement: {str(e)}')
        return jsonify({'error': 'Erreur lors de la creation du paiement', 'detail': str(e)}), 500


@billing_bp.route('/verify-payment/<int:transaction_id>', methods=['GET'])
@login_required
def verify_payment(transaction_id):
    base = _fedapay_base_url()
    headers = _fedapay_headers()
    try:
        res = requests.get(f'{base}/transactions/{transaction_id}', headers=headers, timeout=15)
        res.raise_for_status()
        transaction = res.json()['v1/transaction']
        status = transaction.get('status')
        if status == 'approved':
            if current_user.pending_transaction_id != transaction_id or not current_user.pending_plan:
                return jsonify({'error': 'Transaction non reconnue pour cet utilisateur'}), 400
            plan = Plan.query.filter_by(slug=current_user.pending_plan, actif=True).first()
            if not plan:
                return jsonify({'error': 'Plan introuvable'}), 400
            current_user.plan = plan.slug
            current_user.plan_expiry = datetime.utcnow() + timedelta(days=30)
            current_user.credits = plan.credits if plan.credits is not None else current_user.credits
            current_user.pending_plan = None
            current_user.pending_transaction_id = None
            db.session.commit()
            return jsonify({'status': 'approved', 'plan': current_user.plan, 'plan_expiry': current_user.plan_expiry.isoformat()})
        return jsonify({'status': status})
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'Erreur verification paiement FedaPay: {str(e)}')
        return jsonify({'error': 'Erreur lors de la verification'}), 500
