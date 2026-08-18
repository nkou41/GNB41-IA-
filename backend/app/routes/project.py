from flask import Blueprint, request, jsonify, send_file
import json
import io
import zipfile
from flask_login import login_required, current_user
from app import db
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.project_message import ProjectMessage
from app.models.workspace import Workspace, WorkspaceMember
from app.services.generator import generate_project_code

project_bp = Blueprint('project', __name__)

VALID_PROVIDERS = ('claude', 'openai', 'gemini', 'mistral')


def _check_access(workspace_id):
    member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id, user_id=current_user.id
    ).first()
    return member is not None


def _run_generation(project, prompt, provider, history=None, image=None):
    if provider not in VALID_PROVIDERS:
        provider = 'claude'

    result = generate_project_code(prompt, provider, history=history, image=image)

    version = ProjectVersion(
        project_id=project.id,
        prompt=prompt,
        provider=provider,
        statut=result['statut'],
        code_genere=result.get('code'),
        erreur_message=result.get('message')
    )
    db.session.add(version)

    project.statut = result['statut']
    project.prompt_initial = prompt
    project.provider = provider
    if result['statut'] == 'erreur':
        project.erreur_message = result.get('message')
        project.code_genere = None
    else:
        project.code_genere = result.get('code')
        project.erreur_message = None
    db.session.commit()
    return project


@project_bp.route('/workspace/<workspace_id>', methods=['GET'])
@login_required
def list_projects(workspace_id):
    if not _check_access(workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    projects = Project.query.filter_by(workspace_id=workspace_id).all()
    return jsonify([p.to_dict() for p in projects])


@project_bp.route('/workspace/<workspace_id>', methods=['POST'])
@login_required
def create_project(workspace_id):
    if not _check_access(workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json()
    nom = data.get('nom')
    prompt_initial = data.get('prompt_initial')
    provider = data.get('provider', 'claude')
    if not nom or not prompt_initial:
        return jsonify({'error': 'nom et prompt_initial requis'}), 400

    project = Project(workspace_id=workspace_id, nom=nom, prompt_initial=prompt_initial, statut='en_generation')
    db.session.add(project)
    db.session.commit()

    project = _run_generation(project, prompt_initial, provider)
    return jsonify(project.to_dict()), 201


@project_bp.route('/<project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    return jsonify(project.to_dict())


@project_bp.route('/<project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    db.session.delete(project)
    db.session.commit()
    return jsonify({'success': True})


@project_bp.route('/<project_id>/regenerate', methods=['POST'])
@login_required
def regenerate_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json()
    new_prompt = data.get('prompt')
    provider = data.get('provider', project.provider or 'claude')
    if not new_prompt:
        return jsonify({'error': 'prompt requis'}), 400

    project = _run_generation(project, new_prompt, provider)
    return jsonify(project.to_dict())


@project_bp.route('/<project_id>/versions', methods=['GET'])
@login_required
def list_versions(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    versions = ProjectVersion.query.filter_by(project_id=project_id).order_by(ProjectVersion.created_at.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@project_bp.route('/<project_id>/export', methods=['GET'])
@login_required
def export_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    if not project.code_genere:
        return jsonify({'error': 'Aucun code généré pour ce projet'}), 400

    try:
        data = json.loads(project.code_genere)
        fichiers = data.get('fichiers', [])
    except (json.JSONDecodeError, TypeError):
        fichiers = [{'chemin': 'code.txt', 'contenu': project.code_genere}]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fichier in fichiers:
            zf.writestr(fichier['chemin'], fichier['contenu'])
    buffer.seek(0)

    filename = f"{project.nom.replace(' ', '_')}.zip"
    return send_file(buffer, mimetype='application/zip', as_attachment=True, download_name=filename)


@project_bp.route('/<project_id>/messages', methods=['GET'])
@login_required
def list_messages(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    messages = ProjectMessage.query.filter_by(project_id=project_id).order_by(ProjectMessage.created_at.asc()).all()
    return jsonify([m.to_dict() for m in messages])


@project_bp.route('/<project_id>/chat', methods=['POST'])
@login_required
def chat_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json()
    user_message = data.get('message')
    provider = data.get('provider', project.provider or 'claude')
    image = data.get('image')
    if not user_message:
        return jsonify({'error': 'message requis'}), 400

    user_msg = ProjectMessage(project_id=project_id, role='user', content=user_message)
    db.session.add(user_msg)
    db.session.commit()

    past_messages = ProjectMessage.query.filter_by(project_id=project_id).order_by(ProjectMessage.created_at.asc()).all()
    history = [{'role': m.role, 'content': m.content} for m in past_messages[:-1]]

    project.statut = 'en_generation'
    db.session.commit()

    project = _run_generation(project, user_message, provider, history=history, image=image)

    if project.statut == 'pret':
        assistant_content = project.code_genere if project.code_genere else f"J'ai généré l'application : {project.nom}."
    else:
        assistant_content = f"Erreur lors de la génération : {project.erreur_message}"

    assistant_msg = ProjectMessage(project_id=project_id, role='assistant', content=assistant_content)
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify({
        'project': project.to_dict(),
        'assistant_message': assistant_msg.to_dict()
    })


@project_bp.route('/<project_id>/duplicate', methods=['POST'])
@login_required
def duplicate_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    copy = Project(
        workspace_id=project.workspace_id,
        nom=f"{project.nom} (copie)",
        prompt_initial=project.prompt_initial,
        provider=project.provider,
        statut=project.statut,
        code_genere=project.code_genere,
        erreur_message=project.erreur_message
    )
    db.session.add(copy)
    db.session.commit()

    return jsonify(copy.to_dict()), 201
