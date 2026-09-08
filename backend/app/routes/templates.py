import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.project import Project
from app.models.workspace import Workspace, WorkspaceMember
from app.models.template import Template

templates_bp = Blueprint('templates', __name__)

CATEGORIES = ('productivite', 'ecommerce', 'jeux', 'utilitaires', 'education', 'sante', 'finance', 'social', 'autre')


@templates_bp.route('', methods=['GET'])
def list_templates():
    templates = Template.query.order_by(Template.created_at.desc()).all()
    return jsonify([t.to_dict() for t in templates])


@templates_bp.route('/<template_id>', methods=['GET'])
def get_template(template_id):
    template = Template.query.get_or_404(template_id)
    return jsonify(template.to_dict())


@templates_bp.route('/from-project/<project_id>', methods=['POST'])
@login_required
def publish_template(project_id):
    from app.routes.project import _check_access
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    if project.statut != 'pret' or not project.code_genere:
        return jsonify({'error': 'Le projet doit etre genere avec succes'}), 400

    data = request.get_json() or {}
    nom = data.get('nom', '').strip() or project.nom
    description = data.get('description', '').strip() or project.prompt_initial[:200]
    categorie = data.get('categorie', 'autre')
    if categorie not in CATEGORIES:
        categorie = 'autre'

    template = Template(
        auteur_id=current_user.id,
        nom=nom,
        description=description,
        categorie=categorie,
        code_genere=project.code_genere
    )
    db.session.add(template)
    db.session.commit()

    return jsonify(template.to_dict()), 201


@templates_bp.route('/<template_id>/use', methods=['POST'])
@login_required
def use_template(template_id):
    template = Template.query.get_or_404(template_id)
    data = request.get_json() or {}
    workspace_id = data.get('workspace_id')
    nom = data.get('nom', '').strip() or template.nom

    if not workspace_id:
        return jsonify({'error': 'workspace_id requis'}), 400

    membership = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=current_user.id).first()
    if not membership:
        return jsonify({'error': 'Non autorisé sur cet espace de travail'}), 403

    project = Project(
        workspace_id=workspace_id,
        nom=nom,
        prompt_initial=f"Cree depuis le template: {template.nom}",
        provider='template',
        statut='pret',
        code_genere=template.code_genere
    )
    db.session.add(project)
    db.session.commit()

    return jsonify(project.to_dict()), 201
