import os
import requests
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from flask_login import login_required, current_user
from app import db, limiter

billing_bp = Blueprint('billing', __name__)

PLAN_PRIX = {
    'pro': 12000,
}


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
    plan = data.get('plan')
    if plan not in PLAN_PRIX:
        return jsonify({'error': 'Plan invalide'}), 400

    base = _fedapay_base_url()
    headers = _fedapay_headers()

    try:
        payload = {
            'description': f'GNB41 IA - Plan {plan}',
            'amount': PLAN_PRIX[plan],
            'currency': {'iso': 'XOF'},
            'customer': {
                'firstname': current_user.username,
                'lastname': '.',
                'email': current_user.email,
            }
        }
        res = requests.post(f'{base}/transactions', json=payload, headers=headers, timeout=15)
        res.raise_for_status()
        transaction = res.json()['v1/transaction']
        transaction_id = transaction['id']

        token_res = requests.post(f'{base}/transactions/{transaction_id}/token', headers=headers, timeout=15)
        token_res.raise_for_status()
        token_data = token_res.json()['token']

        return jsonify({'payment_url': token_data['url'], 'transaction_id': transaction_id})
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'Erreur creation paiement FedaPay: {str(e)}')
        return jsonify({'error': 'Erreur lors de la creation du paiement'}), 500


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
            current_user.plan = 'pro'
            current_user.plan_expiry = datetime.utcnow() + timedelta(days=30)
            db.session.commit()
            return jsonify({'status': 'approved', 'plan': current_user.plan, 'plan_expiry': current_user.plan_expiry.isoformat()})
        return jsonify({'status': status})
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'Erreur verification paiement FedaPay: {str(e)}')
        return jsonify({'error': 'Erreur lors de la verification'}), 500
