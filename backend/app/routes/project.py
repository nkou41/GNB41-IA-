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
from app.utils.permissions import get_role, can_edit, log_activity, get_plan_limits
from app.services.generator import generate_project_code

project_bp = Blueprint('project', __name__)

VALID_PROVIDERS = ('claude', 'openai', 'gemini', 'mistral')


def _check_access(workspace_id):
    member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id, user_id=current_user.id
    ).first()
    return member is not None

def _check_edit_access(workspace_id):
    role = get_role(workspace_id, current_user.id)
    return can_edit(role)


def _provision_database(project, tables):
    import json as json_lib
    from app.models.app_table import AppTable
    from app.models.api_key import ApiKey

    if not tables:
        return None

    for t in tables:
        existing = AppTable.query.filter_by(project_id=project.id, nom=t.get('nom')).first()
        if not existing:
            new_table = AppTable(project_id=project.id, nom=t.get('nom'), colonnes=json_lib.dumps(t.get('colonnes', [])))
            db.session.add(new_table)
    db.session.commit()

    ApiKey.query.filter_by(project_id=project.id, revoked=False).update({'revoked': True})
    raw, prefix, key_hash = ApiKey.generate_key()
    key = ApiKey(project_id=project.id, key_prefix=prefix, key_hash=key_hash)
    db.session.add(key)
    db.session.commit()

    return raw


def _substitute_placeholders(code_genere_json, project, api_key_raw):
    import json as json_lib
    from app.models.app_table import AppTable

    parsed = json_lib.loads(code_genere_json)
    fichiers = parsed.get('fichiers', [])
    tables = AppTable.query.filter_by(project_id=project.id).all()
    table_map = {t.nom: t.id for t in tables}

    api_base = os.environ.get('API_PUBLIC_URL', 'http://localhost:5001/api')

    for f in fichiers:
        contenu = f.get('contenu', '')
        contenu = contenu.replace('{{API_BASE}}', api_base)
        if api_key_raw:
            contenu = contenu.replace('{{API_KEY}}', api_key_raw)
        for nom_table, table_id in table_map.items():
            contenu = contenu.replace('{{TABLE_ID:' + nom_table + '}}', table_id)
        f['contenu'] = contenu

    return json_lib.dumps(parsed, ensure_ascii=False, indent=2)


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

        tables = result.get('tables', [])
        if tables:
            api_key_raw = _provision_database(project, tables)
            project.code_genere = _substitute_placeholders(project.code_genere, project, api_key_raw)

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
    if not _check_edit_access(workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json()
    nom = data.get('nom')
    prompt_initial = data.get('prompt_initial')
    provider = data.get('provider', 'claude')
    if not nom or not prompt_initial:
        return jsonify({'error': 'nom et prompt_initial requis'}), 400

    workspace = Workspace.query.get(workspace_id)
    owner = User.query.get(workspace.owner_id) if workspace else None
    if owner:
        limits = get_plan_limits(owner.plan)
        if limits['max_projects_per_workspace'] is not None:
            current_count = Project.query.filter_by(workspace_id=workspace_id).count()
            if current_count >= limits['max_projects_per_workspace']:
                return jsonify({'error': f"Limite atteinte pour le plan {owner.plan} ({limits['max_projects_per_workspace']} projets max par espace). Passez au plan Pro pour en creer davantage."}), 403

    project = Project(workspace_id=workspace_id, nom=nom, prompt_initial=prompt_initial, statut='en_generation')
    db.session.add(project)
    db.session.commit()

    project = _run_generation(project, prompt_initial, provider)
    log_activity(workspace_id, current_user.id, 'project_created', nom)
    db.session.commit()
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
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    log_activity(project.workspace_id, current_user.id, 'project_deleted', project.nom)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'success': True})


@project_bp.route('/<project_id>/regenerate', methods=['POST'])
@login_required
def regenerate_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
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
    if not _check_edit_access(project.workspace_id):
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
    if not _check_edit_access(project.workspace_id):
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


@project_bp.route('/<project_id>/files', methods=['PUT'])
@login_required
def update_file(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json() or {}
    chemin = data.get('chemin')
    contenu = data.get('contenu')

    if not chemin or contenu is None:
        return jsonify({'error': 'chemin et contenu requis'}), 400

    if not project.code_genere:
        return jsonify({'error': "Aucun code genere pour ce projet"}), 400

    try:
        parsed = json.loads(project.code_genere)
    except json.JSONDecodeError:
        return jsonify({'error': 'Code genere illisible'}), 500

    fichiers = parsed.get('fichiers', [])
    found = False
    for f in fichiers:
        if f.get('chemin') == chemin:
            f['contenu'] = contenu
            found = True
            break

    if not found:
        return jsonify({'error': 'Fichier introuvable dans ce projet'}), 404

    project.code_genere = json.dumps(parsed, ensure_ascii=False, indent=2)
    db.session.commit()

    return jsonify(project.to_dict())
