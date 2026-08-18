from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User

workspace_bp = Blueprint('workspace', __name__)


def _get_role(workspace_id, user_id):
    member = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first()
    return member.role if member else None


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
    if not _get_role(workspace_id, current_user.id):
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
    if not _get_role(workspace_id, current_user.id):
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
    role = _get_role(workspace_id, current_user.id)
    if role != 'owner':
        return jsonify({'error': 'Seul le propriétaire peut inviter des membres'}), 403

    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'error': 'email requis'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Utilisateur introuvable avec cet email'}), 404

    existing = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user.id).first()
    if existing:
        return jsonify({'error': 'Cet utilisateur est déjà membre'}), 409

    member = WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role='member')
    db.session.add(member)
    db.session.commit()

    return jsonify({
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'role': 'member'
    }), 201


@workspace_bp.route('/<workspace_id>/members/<user_id>', methods=['DELETE'])
@login_required
def remove_member(workspace_id, user_id):
    role = _get_role(workspace_id, current_user.id)
    if role != 'owner':
        return jsonify({'error': 'Seul le propriétaire peut retirer des membres'}), 403

    if user_id == current_user.id:
        return jsonify({'error': 'Le propriétaire ne peut pas se retirer lui-même'}), 400

    member = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member:
        return jsonify({'error': 'Membre introuvable'}), 404

    db.session.delete(member)
    db.session.commit()
    return jsonify({'success': True})
