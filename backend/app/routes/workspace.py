from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User
from app.utils.permissions import get_role, can_manage_members, VALID_ROLES, ROLE_EDITOR, log_activity, get_plan_limits

workspace_bp = Blueprint('workspace', __name__)




@workspace_bp.route('', methods=['GET'])
@login_required
def list_workspaces():
    memberships = WorkspaceMember.query.filter_by(user_id=current_user.id).all()
    workspaces = [m.workspace for m in memberships]
    return jsonify([w.to_dict() for w in workspaces])


@workspace_bp.route('', methods=['POST'])
@login_required
def create_workspace():
    data = request.get_json()
    nom = data.get('nom')
    if not nom:
        return jsonify({'error': 'nom requis'}), 400

    limits = get_plan_limits(current_user.plan)
    if limits['max_workspaces'] is not None:
        current_count = WorkspaceMember.query.filter_by(user_id=current_user.id, role='owner').count()
        if current_count >= limits['max_workspaces']:
            return jsonify({'error': f"Limite atteinte pour le plan {current_user.plan} ({limits['max_workspaces']} espace(s) de travail max). Passez au plan Pro pour en creer davantage."}), 403

    workspace = Workspace(nom=nom, owner_id=current_user.id)
    db.session.add(workspace)
    db.session.commit()

    member = WorkspaceMember(workspace_id=workspace.id, user_id=current_user.id, role='owner')
    db.session.add(member)
    db.session.commit()

    return jsonify(workspace.to_dict()), 201


@workspace_bp.route('/<workspace_id>', methods=['GET'])
@login_required
def get_workspace(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    if not get_role(workspace_id, current_user.id):
        return jsonify({'error': 'Non autorisé'}), 403
    return jsonify(workspace.to_dict())


@workspace_bp.route('/<workspace_id>', methods=['DELETE'])
@login_required
def delete_workspace(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    if workspace.owner_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    db.session.delete(workspace)
    db.session.commit()
    return jsonify({'success': True})


@workspace_bp.route('/<workspace_id>/members', methods=['GET'])
@login_required
def list_members(workspace_id):
    if not get_role(workspace_id, current_user.id):
        return jsonify({'error': 'Non autorisé'}), 403
    members = WorkspaceMember.query.filter_by(workspace_id=workspace_id).all()
    result = []
    for m in members:
        user = User.query.get(m.user_id)
        result.append({
            'user_id': m.user_id,
            'username': user.username if user else '?',
            'email': user.email if user else '?',
            'role': m.role
        })
    return jsonify(result)


@workspace_bp.route('/<workspace_id>/members', methods=['POST'])
@login_required
def add_member(workspace_id):
    role = get_role(workspace_id, current_user.id)
    if not can_manage_members(role):
        return jsonify({'error': 'Seul le propriétaire peut inviter des membres'}), 403

    data = request.get_json()
    email = data.get('email')
    new_role = data.get('role', ROLE_EDITOR)
    if new_role not in VALID_ROLES or new_role == 'owner':
        new_role = ROLE_EDITOR
    if not email:
        return jsonify({'error': 'email requis'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Utilisateur introuvable avec cet email'}), 404

    existing = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user.id).first()
    if existing:
        return jsonify({'error': 'Cet utilisateur est déjà membre'}), 409

    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role=new_role)
    db.session.add(member)
    log_activity(workspace_id, current_user.id, 'member_added', user.email)
    db.session.commit()

    return jsonify({
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'role': new_role
    }), 201


@workspace_bp.route('/<workspace_id>/members/<user_id>', methods=['DELETE'])
@login_required
def remove_member(workspace_id, user_id):
    role = get_role(workspace_id, current_user.id)
    if not can_manage_members(role):
        return jsonify({'error': 'Seul le propriétaire peut retirer des membres'}), 403

    if user_id == current_user.id:
        return jsonify({'error': 'Le propriétaire ne peut pas se retirer lui-même'}), 400

    member = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member:
        return jsonify({'error': 'Membre introuvable'}), 404

    removed_user = User.query.get(user_id)
    log_activity(workspace_id, current_user.id, 'member_removed', removed_user.email if removed_user else user_id)
    db.session.delete(member)
    db.session.commit()
    return jsonify({'success': True})


@workspace_bp.route('/<workspace_id>/activity', methods=['GET'])
@login_required
def list_activity(workspace_id):
    if not get_role(workspace_id, current_user.id):
        return jsonify({'error': 'Non autorisé'}), 403
    from app.models.activity_log import ActivityLog
    logs = ActivityLog.query.filter_by(workspace_id=workspace_id).order_by(ActivityLog.created_at.desc()).limit(50).all()
    return jsonify([l.to_dict() for l in logs])
