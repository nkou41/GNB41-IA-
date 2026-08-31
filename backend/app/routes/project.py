from flask import Blueprint, request, jsonify, send_file, Response
import json
import os
import io
import zipfile
from flask_login import login_required, current_user
from app import db
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.project_message import ProjectMessage
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User
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


def _build_contexte_projet(project):
    import json as json_lib
    morceaux = []

    if project.memoire_projet and project.memoire_projet.strip():
        morceaux.append('Regles et decisions a respecter pour ce projet: ' + project.memoire_projet.strip())

    if project.code_genere:
        try:
            parsed = json_lib.loads(project.code_genere)
            fichiers = parsed.get('fichiers', [])
            if fichiers:
                liste = ', '.join(f.get('chemin', '?') for f in fichiers)
                morceaux.append(f"Stack: {parsed.get('stack', 'inconnue')}. Fichiers existants: {liste}.")

                MAX_CHARS_PAR_FICHIER = 6000
                blocs = []
                for f in fichiers:
                    chemin = f.get('chemin', '?')
                    contenu = f.get('contenu', '')
                    if len(contenu) > MAX_CHARS_PAR_FICHIER:
                        contenu = contenu[:MAX_CHARS_PAR_FICHIER] + "\n... (fichier tronque, trop volumineux)"
                    blocs.append(f"--- {chemin} ---\n{contenu}")
                morceaux.append("Contenu des fichiers existants:\n\n" + "\n\n".join(blocs))
        except (ValueError, TypeError):
            pass

    if not morceaux:
        return None
    return chr(10).join(morceaux)


def _run_generation(project, prompt, provider, history=None, image=None):
    import json as json_lib_local
    if provider not in VALID_PROVIDERS:
        provider = 'claude'

    anciens_fichiers = set()
    if project.code_genere:
        try:
            ancien_parsed = json_lib_local.loads(project.code_genere)
            anciens_fichiers = {f.get('chemin') for f in ancien_parsed.get('fichiers', [])}
        except (ValueError, TypeError):
            pass

    contexte_projet = _build_contexte_projet(project)
    result = generate_project_code(prompt, provider, history=history, image=image, contexte_projet=contexte_projet, fichiers_connus=anciens_fichiers)

    if result.get('statut') == 'pret' and anciens_fichiers:
        nouveaux_fichiers = {f.get('chemin') for f in result.get('fichiers', [])}
        supprimes = anciens_fichiers - nouveaux_fichiers
        if supprimes:
            avert = result.setdefault('avertissements', [])
            avert.append('Fichiers presents avant et absents apres generation: ' + ', '.join(sorted(supprimes)))

    if result.get('statut') == 'pret' and result.get('decisions_a_retenir'):
        existantes = (project.memoire_projet or '')
        lignes_existantes = set(l.strip() for l in existantes.split(chr(10)) if l.strip())
        nouvelles = [d.strip() for d in result['decisions_a_retenir'] if d.strip() and d.strip() not in lignes_existantes]
        if nouvelles:
            project.memoire_projet = (existantes + chr(10) if existantes else '') + chr(10).join(nouvelles)

    import json as json_lib
    plan_json = json_lib.dumps(result.get('plan', []), ensure_ascii=False) if result.get('plan') else None
    avertissements_json = json_lib.dumps(result.get('avertissements', []), ensure_ascii=False) if result.get('avertissements') else None

    version = ProjectVersion(
        project_id=project.id,
        prompt=prompt,
        provider=provider,
        statut=result['statut'],
        code_genere=result.get('code'),
        erreur_message=result.get('message'),
        comprehension=result.get('comprehension'),
        plan=plan_json,
        avertissements=avertissements_json
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


@project_bp.route('/<project_id>/memoire', methods=['PUT'])
@login_required
def update_memoire_projet(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    data = request.get_json()
    project.memoire_projet = (data.get('memoire_projet') or '').strip() or None
    db.session.commit()
    log_activity(project.workspace_id, current_user.id, 'memoire_projet_updated', project.nom)
    return jsonify(project.to_dict())


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


@project_bp.route('/<project_id>/versions/<version_id>/restore', methods=['POST'])
@login_required
def restore_version(project_id, version_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    version = ProjectVersion.query.filter_by(id=version_id, project_id=project_id).first_or_404()
    if version.statut != 'pret' or not version.code_genere:
        return jsonify({'error': 'Cette version ne peut pas etre restauree (pas de code valide)'}), 400

    version_restauree = ProjectVersion(
        project_id=project.id,
        prompt=f'[Restauration de la version du {version.created_at.strftime("%d/%m/%Y %H:%M")}]',
        provider=version.provider,
        statut='pret',
        code_genere=version.code_genere,
        comprehension=version.comprehension,
        plan=version.plan
    )
    db.session.add(version_restauree)

    project.code_genere = version.code_genere
    project.provider = version.provider
    project.statut = 'pret'
    project.erreur_message = None

    assistant_msg = ProjectMessage(
        project_id=project_id,
        role='assistant',
        content=f'Version du {version.created_at.strftime("%d/%m/%Y %H:%M")} restauree avec succes.'
    )
    db.session.add(assistant_msg)

    log_activity(project.workspace_id, current_user.id, 'version_restored', project.nom)
    db.session.commit()
    return jsonify(project.to_dict())


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
        import json as json_lib
        derniere_version = ProjectVersion.query.filter_by(project_id=project.id).order_by(ProjectVersion.created_at.desc()).first()
        comprehension = derniere_version.comprehension if derniere_version else None
        plan_texte = ''
        if derniere_version and derniere_version.plan:
            try:
                etapes = json_lib.loads(derniere_version.plan)
                if etapes:
                    plan_texte = chr(10) + chr(10).join(f'- {e}' for e in etapes)
            except (ValueError, TypeError):
                pass
        avert_texte = ''
        if derniere_version and derniere_version.avertissements:
            try:
                avert_liste = json_lib.loads(derniere_version.avertissements)
                if avert_liste:
                    avert_texte = chr(10) + chr(10) + 'A verifier :' + chr(10) + chr(10).join(f'- {a}' for a in avert_liste)
            except (ValueError, TypeError):
                pass
        assistant_content = (comprehension + plan_texte + avert_texte) if comprehension else f"J'ai généré l'application : {project.nom}."
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


def _get_file_mimetype(chemin):
    if chemin.endswith('.html'):
        return 'text/html'
    if chemin.endswith('.css'):
        return 'text/css'
    if chemin.endswith('.js'):
        return 'application/javascript'
    if chemin.endswith('.json'):
        return 'application/json'
    if chemin.endswith('.svg'):
        return 'image/svg+xml'
    if chemin.endswith('.png'):
        return 'image/png'
    return 'text/plain'


@project_bp.route('/<project_id>/deploy', methods=['POST'])
@login_required
def deploy_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    if project.statut != 'pret' or not project.code_genere:
        return jsonify({'error': "Le projet doit etre genere avec succes avant deploiement"}), 400

    project.est_deploye = True
    db.session.commit()

    base_url = os.environ.get('API_PUBLIC_URL', 'http://localhost:5001/api')
    live_url = f"{base_url}/projects/{project.id}/live/"
    return jsonify({'project': project.to_dict(), 'live_url': live_url})


@project_bp.route('/<project_id>/undeploy', methods=['POST'])
@login_required
def undeploy_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    project.est_deploye = False
    db.session.commit()
    return jsonify(project.to_dict())


@project_bp.route('/<project_id>/live/', defaults={'chemin': 'index.html'}, methods=['GET'])
@project_bp.route('/<project_id>/live/<path:chemin>', methods=['GET'])
def serve_live(project_id, chemin):
    project = Project.query.get_or_404(project_id)
    if not project.est_deploye or not project.code_genere:
        return jsonify({'error': "Cette application n'est pas deployee"}), 404

    try:
        parsed = json.loads(project.code_genere)
    except json.JSONDecodeError:
        return jsonify({'error': 'Code illisible'}), 500

    fichiers = parsed.get('fichiers', [])
    fichier = next((f for f in fichiers if f['chemin'] == chemin), None)

    if not fichier and chemin == 'index.html':
        fichier = next((f for f in fichiers if f['chemin'].endswith('.html')), None)

    if not fichier:
        return jsonify({'error': 'Fichier introuvable'}), 404

    return Response(fichier['contenu'], mimetype=_get_file_mimetype(chemin))
