from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app import db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.project import Project
from app.utils_admin import admin_required, superadmin_required
from app.services.reqres_client import get_users as reqres_get_users, TEST_MODE

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def list_users():
    if TEST_MODE:
        data = reqres_get_users()
        return jsonify({'users': data.get('data', []), 'total': data.get('total', 0), 'test_mode': True})

    search = request.args.get('q', '').strip()
    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    users = query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [u.to_dict() for u in users], 'total': len(users)})


@admin_bp.route('/users/<user_id>/role', methods=['PATCH'])
@login_required
@superadmin_required
def update_user_role(user_id):
    data = request.get_json() or {}
    new_role = data.get('role')
    if new_role not in ('user', 'admin', 'superadmin'):
        return jsonify({'error': 'Role invalide'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    user.role = new_role
    db.session.commit()
    return jsonify({'user': user.to_dict()})


@admin_bp.route('/workspaces', methods=['GET'])
@login_required
@admin_required
def list_workspaces():
    workspaces = Workspace.query.order_by(Workspace.created_at.desc()).all()
    result = []
    for w in workspaces:
        owner = User.query.get(w.owner_id)
        d = w.to_dict()
        d['owner_email'] = owner.email if owner else None
        d['owner_username'] = owner.username if owner else None
        d['member_count'] = len(w.members)
        result.append(d)
    return jsonify({'workspaces': result, 'total': len(result)})


@admin_bp.route('/workspaces/<workspace_id>', methods=['DELETE'])
@login_required
@superadmin_required
def delete_workspace(workspace_id):
    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return jsonify({'error': 'Workspace introuvable'}), 404
    db.session.delete(workspace)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
def admin_stats():
    return jsonify({
        'total_users': User.query.count(),
        'total_workspaces': Workspace.query.count(),
        'total_projects': Project.query.count(),
        'users_by_plan': {
            plan: User.query.filter_by(plan=plan).count()
            for plan in ['gratuit', 'pro']
        }
    })
