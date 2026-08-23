from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.notification import Notification

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('', methods=['GET'])
@login_required
def get_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(50).all()
    non_lues = Notification.query.filter_by(user_id=current_user.id, lu=False).count()
    return jsonify({
        'notifications': [n.to_dict() for n in notifs],
        'non_lues': non_lues
    })

@notifications_bp.route('/<int:notif_id>/lu', methods=['POST'])
@login_required
def marquer_lu(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if not notif:
        return jsonify({'error': 'Notification introuvable'}), 404
    notif.lu = True
    db.session.commit()
    return jsonify(notif.to_dict())

@notifications_bp.route('/tout-lire', methods=['POST'])
@login_required
def tout_marquer_lu():
    Notification.query.filter_by(user_id=current_user.id, lu=False).update({'lu': True})
    db.session.commit()
    return jsonify({'success': True})
