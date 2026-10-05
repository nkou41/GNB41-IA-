import os

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app import db
from app.models.push_subscription import PushSubscription
from app.services.push import envoyer_push

push_bp = Blueprint('push', __name__)


@push_bp.route('/public-key', methods=['GET'])
def public_key():
    return jsonify({'public_key': os.environ.get('VAPID_PUBLIC_KEY', '')})


@push_bp.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    data = request.get_json(silent=True) or {}
    keys = data.get('keys') or {}
    endpoint, p256dh, auth = data.get('endpoint'), keys.get('p256dh'), keys.get('auth')
    if not (endpoint and p256dh and auth):
        return jsonify({'error': 'Abonnement invalide'}), 400
    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if sub:
        sub.user_id, sub.p256dh, sub.auth = current_user.id, p256dh, auth
    else:
        db.session.add(PushSubscription(
            user_id=current_user.id, endpoint=endpoint, p256dh=p256dh, auth=auth))
    db.session.commit()
    return jsonify({'success': True})


@push_bp.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.query.filter_by(endpoint=endpoint, user_id=current_user.id).delete()
        db.session.commit()
    return jsonify({'success': True})


@push_bp.route('/test', methods=['POST'])
@login_required
def test():
    n = envoyer_push(current_user.id, 'GNB41 IA', 'Les notifications fonctionnent.', '/')
    return jsonify({'sent': n})
