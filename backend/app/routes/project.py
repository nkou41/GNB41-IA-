from flask import Blueprint, request, jsonify, send_file, Response
import json
import os
import io
import zipfile
from flask_login import login_required, current_user
import re
from app import db, limiter
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.project_message import ProjectMessage
from app.models.workspace import Workspace, WorkspaceMember
from app.models.user import User
from app.utils.permissions import get_role, can_edit, log_activity, get_plan_limits
from app.services.generator import generate_project_code, generate_project_name

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


def _masquer_secrets(texte):
    """Empeche toute cle API de fuiter dans un message d'erreur stocke ou affiche."""
    if not texte:
        return texte
    motifs = [r'sk-ant-[A-Za-z0-9\-_]{10,}', r'sk-[A-Za-z0-9]{20,}', r'AIza[A-Za-z0-9_\-]{20,}']
    for motif in motifs:
        texte = re.sub(motif, '[CLE_MASQUEE]', texte)
    return texte


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


def _run_generation(project, prompt, provider, history=None, image=None, mode=None):
    import json as json_lib_local
    if provider not in VALID_PROVIDERS:
        provider = 'mistral'

    workspace = Workspace.query.get(project.workspace_id)
    owner = User.query.get(workspace.owner_id) if workspace else None
    if owner and owner.credits is not None and owner.role not in ('admin', 'superadmin') and owner.credits <= 0:
        project.statut = 'erreur'
        project.erreur_message = "Credits insuffisants pour generer. Passez a un plan superieur pour continuer."
        db.session.commit()
        return project

    anciens_fichiers = set()
    if project.code_genere:
        try:
            ancien_parsed = json_lib_local.loads(project.code_genere)
            anciens_fichiers = {f.get('chemin') for f in ancien_parsed.get('fichiers', [])}
        except (ValueError, TypeError):
            pass

    import time as time_lib
    contexte_projet = _build_contexte_projet(project)
    debut_generation = time_lib.time()
    result = generate_project_code(prompt, provider, history=history, image=image, contexte_projet=contexte_projet, fichiers_connus=anciens_fichiers, mode=mode)
    duree_ms = int((time_lib.time() - debut_generation) * 1000)
    if result.get('message'):
        result['message'] = _masquer_secrets(result['message'])

    if result.get('statut') == 'pret' and result.get('decisions_a_retenir'):
        existantes = (project.memoire_projet or '')
        lignes_existantes = set(l.strip() for l in existantes.split(chr(10)) if l.strip())
        nouvelles = [d.strip() for d in result['decisions_a_retenir'] if d.strip() and d.strip() not in lignes_existantes]
        if nouvelles:
            project.memoire_projet = (existantes + chr(10) if existantes else '') + chr(10).join(nouvelles)

    import json as json_lib
    plan_json = json_lib.dumps(result.get('plan', []), ensure_ascii=False) if result.get('plan') else None
    avertissements_json = json_lib.dumps(result.get('avertissements', []), ensure_ascii=False) if result.get('avertissements') else None
    suggestions_json = json_lib.dumps(result.get('suggestions', []), ensure_ascii=False) if result.get('suggestions') else None

    version = ProjectVersion(
        project_id=project.id,
        prompt=prompt,
        provider=provider,
        statut=result['statut'],
        code_genere=result.get('code'),
        erreur_message=result.get('message'),
        comprehension=result.get('comprehension'),
        plan=plan_json,
        avertissements=avertissements_json,
        duree_generation_ms=duree_ms,
        agent_type=result.get('agent_type'),
        suggestions=suggestions_json
    )
    db.session.add(version)

    est_clarification = bool((result.get('comprehension') or '').startswith('CLARIFICATION_NECESSAIRE:'))

    project.statut = result['statut']
    project.provider = provider
    if not est_clarification:
        project.prompt_initial = prompt

    if result['statut'] == 'erreur':
        project.erreur_message = result.get('message')
        project.code_genere = None
    elif est_clarification:
        project.erreur_message = None
    else:
        project.code_genere = result.get('code')
        project.erreur_message = None

        tables = result.get('tables', [])
        if tables:
            api_key_raw = _provision_database(project, tables)
            project.code_genere = _substitute_placeholders(project.code_genere, project, api_key_raw)

    credit_utilise = False
    if owner and owner.credits is not None and result['statut'] != 'erreur' and not est_clarification:
        owner.credits = max(0, owner.credits - 1)
        credit_utilise = True

    db.session.commit()

    if credit_utilise and owner.role not in ('admin', 'superadmin') and owner.credits in (0, 1):
        try:
            from app.services.notifications import envoyer_notification
            if owner.credits == 0:
                envoyer_notification(
                    owner.id, 'credits', 'Crédits épuisés',
                    "Vous n'avez plus de crédits. Passez à un plan supérieur pour continuer à générer.")
            else:
                envoyer_notification(
                    owner.id, 'credits', 'Il vous reste 1 crédit',
                    "Votre dernier crédit sera bientôt utilisé. Pensez à mettre à niveau votre plan.")
        except Exception:
            db.session.rollback()

    return project


@project_bp.route('/workspace/<workspace_id>', methods=['GET'])
@login_required
def list_projects(workspace_id):
    if not _check_access(workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    projects = Project.query.filter_by(workspace_id=workspace_id).all()
    for p in projects:
        _reparer_si_bloque(p)
    return jsonify([p.to_dict() for p in projects])


@project_bp.route('/workspace/<workspace_id>', methods=['POST'])
@login_required
@limiter.limit('20 per hour')
def create_project(workspace_id):
    if not _check_edit_access(workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json()
    nom = data.get('nom')
    prompt_initial = data.get('prompt_initial')
    provider = data.get('provider', 'mistral')
    mode = data.get('mode')
    if not prompt_initial:
        return jsonify({'error': 'prompt_initial requis'}), 400
    if not nom:
        nom_result = generate_project_name(prompt_initial, provider)
        nom = nom_result.get('nom') if nom_result.get('statut') == 'pret' else prompt_initial[:40]

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

    project = _run_generation(project, prompt_initial, provider, mode=mode)
    log_activity(workspace_id, current_user.id, 'project_created', nom)
    db.session.commit()
    return jsonify(project.to_dict()), 201


def _reparer_si_bloque(project):
    from datetime import datetime, timedelta
    if (project.statut == 'en_generation' and project.updated_at
            and datetime.utcnow() - project.updated_at > timedelta(minutes=10)):
        project.statut = 'erreur'
        project.erreur_message = "La génération a été interrompue (connexion coupée ou serveur redémarré). Relancez-la."
        db.session.commit()


@project_bp.route('/<project_id>', methods=['GET'])
@login_required
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    _reparer_si_bloque(project)
    return jsonify(project.to_dict())


@project_bp.route('/<project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    from flask import current_app
    from app.models.listing import Listing
    from app.models.api_key import ApiKey
    from app.models.app_table import AppTable
    from app.models.app_row import AppRow

    if Listing.query.filter_by(project_id=project_id).first():
        return jsonify({'error': "Ce projet a une annonce sur le marketplace. Retirez d'abord l'annonce."}), 409

    workspace_id = project.workspace_id
    nom = project.nom
    try:
        table_ids = [t.id for t in AppTable.query.filter_by(project_id=project_id).all()]
        if table_ids:
            AppRow.query.filter(AppRow.table_id.in_(table_ids)).delete(synchronize_session=False)
        AppTable.query.filter_by(project_id=project_id).delete(synchronize_session=False)
        ApiKey.query.filter_by(project_id=project_id).delete(synchronize_session=False)
        ProjectMessage.query.filter_by(project_id=project_id).delete(synchronize_session=False)
        ProjectVersion.query.filter_by(project_id=project_id).delete(synchronize_session=False)
        db.session.delete(project)
        log_activity(workspace_id, current_user.id, 'project_deleted', nom)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Suppression du projet %s impossible: %s', project_id, e)
        return jsonify({'error': 'Suppression impossible. Réessayez ou contactez le support.'}), 500
    return jsonify({'success': True})


@project_bp.route('/<project_id>', methods=['PUT'])
@login_required
def rename_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    data = request.get_json(silent=True) or {}
    nom = (data.get('nom') or '').strip()
    if not nom:
        return jsonify({'error': 'Le nom ne peut pas être vide'}), 400
    if len(nom) > 120:
        return jsonify({'error': 'Le nom est trop long (120 caractères maximum)'}), 400
    from flask import current_app
    try:
        project.nom = nom
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Renommage du projet %s impossible: %s', project_id, e)
        return jsonify({'error': 'Renommage impossible. Réessayez.'}), 500
    log_activity(project.workspace_id, current_user.id, 'project_renamed', nom)
    return jsonify(project.to_dict())


@project_bp.route('/<project_id>/nom-app', methods=['PUT'])
@login_required
def set_nom_app(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    data = request.get_json(silent=True) or {}
    nom = (data.get('nom_app') or '').strip()
    if not nom:
        return jsonify({'error': "Le nom de l'app ne peut pas être vide"}), 400
    if len(nom) > 45:
        return jsonify({'error': 'Le nom est trop long (45 caractères maximum)'}), 400
    from flask import current_app
    try:
        project.nom_app = nom
        if project.est_deploye:
            project.slug = _generer_slug(project)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Nom app du projet %s impossible: %s', project_id, e)
        return jsonify({'error': 'Enregistrement impossible. Réessayez.'}), 500
    live_url = None
    if project.est_deploye and project.slug:
        racine = os.environ.get('API_PUBLIC_URL', 'http://localhost:5001/api').rstrip('/')
        if racine.endswith('/api'):
            racine = racine[:-4]
        live_url = f"{racine}/a/{project.slug}/"
    return jsonify({'project': project.to_dict(), 'live_url': live_url})


@project_bp.route('/<project_id>/stats', methods=['GET'])
@login_required
def stats_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    from datetime import date, timedelta
    from sqlalchemy import func
    auj = date.today()

    def total(jours):
        v = db.session.query(func.coalesce(func.sum(Visite.nombre), 0)).filter(
            Visite.project_id == project.id, Visite.jour > auj - timedelta(days=jours)).scalar()
        return int(v or 0)

    return jsonify({'visites_7j': total(7), 'visites_30j': total(30)})


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
@limiter.limit('20 per hour')
def regenerate_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json()
    new_prompt = data.get('prompt')
    provider = data.get('provider', project.provider or 'mistral')
    mode = data.get('mode')
    if not new_prompt:
        return jsonify({'error': 'prompt requis'}), 400

    project = _run_generation(project, new_prompt, provider, mode=mode)
    return jsonify(project.to_dict())


@project_bp.route('/<project_id>/versions', methods=['GET'])
@login_required
def list_versions(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    versions = ProjectVersion.query.filter_by(project_id=project_id).order_by(ProjectVersion.created_at.desc()).all()
    return jsonify([v.to_dict() for v in versions])


@project_bp.route('/<project_id>/versions/latest-warnings', methods=['GET'])
@login_required
def latest_warnings(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403
    derniere = (ProjectVersion.query
                .with_entities(ProjectVersion.avertissements)
                .filter_by(project_id=project_id)
                .order_by(ProjectVersion.created_at.desc())
                .first())
    return jsonify({'avertissements': derniere[0] if derniere else None})


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
@limiter.limit('30 per hour')
def chat_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _check_edit_access(project.workspace_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json()
    user_message = data.get('message')
    provider = data.get('provider', project.provider or 'mistral')
    image = data.get('image')
    mode = data.get('mode')
    if not user_message:
        return jsonify({'error': 'message requis'}), 400

    user_msg = ProjectMessage(project_id=project_id, role='user', content=user_message)
    db.session.add(user_msg)
    db.session.commit()

    past_messages = ProjectMessage.query.filter_by(project_id=project_id).order_by(ProjectMessage.created_at.asc()).all()
    history = [{'role': m.role, 'content': m.content} for m in past_messages[:-1]]

    project.statut = 'en_generation'
    db.session.commit()

    project = _run_generation(project, user_message, provider, history=history, image=image, mode=mode)

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
        suggestions_texte = ''
        if derniere_version and derniere_version.suggestions:
            try:
                suggestions_liste = json_lib.loads(derniere_version.suggestions)
                if suggestions_liste:
                    suggestions_texte = chr(10) + chr(10) + '💡 ' + chr(10).join(suggestions_liste)
            except (ValueError, TypeError):
                pass
        if comprehension and comprehension.startswith('CLARIFICATION_NECESSAIRE:'):
            assistant_content = '❓ ' + comprehension.replace('CLARIFICATION_NECESSAIRE:', '', 1).strip()
        else:
            assistant_content = (comprehension + plan_texte + avert_texte + suggestions_texte) if comprehension else f"J'ai généré l'application : {project.nom}."
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

    if (project.modere_statut or 'actif') == 'suspendu':
        return jsonify({'error': 'Ce projet est suspendu par la modération et ne peut pas être dupliqué.'}), 403

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
    if (project.modere_statut or 'actif') == 'suspendu':
        return jsonify({'error': 'Ce projet est suspendu par la modération. Contactez le support.'}), 403
    if project.statut != 'pret' or not project.code_genere:
        return jsonify({'error': "Le projet doit etre genere avec succes avant deploiement"}), 400

    project.est_deploye = True
    project.slug = _generer_slug(project)
    db.session.commit()

    base_url = os.environ.get('API_PUBLIC_URL', 'http://localhost:5001/api')
    racine = base_url.rstrip('/')
    if racine.endswith('/api'):
        racine = racine[:-4]
    live_url = f"{racine}/a/{project.slug}/"
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


def _extraire_couleur_primaire(fichiers):
    """Cherche une couleur hex dans le CSS genere pour theme_color/background_color du PWA."""
    for f in fichiers:
        if f.get('chemin', '').endswith('.css'):
            contenu = f.get('contenu', '')
            match = re.search(r'--color-primary\s*:\s*(#[0-9a-fA-F]{3,6})', contenu)
            if match:
                return match.group(1)
            match = re.search(r'#[0-9a-fA-F]{6}', contenu)
            if match:
                return match.group(0)
    return '#4361ee'


def _titre_app(project, parsed):
    import html as _html
    if getattr(project, 'nom_app', None):
        return project.nom_app.strip()[:45]
    for f in parsed.get('fichiers', []):
        if f.get('chemin', '').endswith('.html'):
            m = re.search(r'<title[^>]*>(.*?)</title>', f.get('contenu', ''), re.S | re.I)
            if m:
                titre = _html.unescape(m.group(1)).strip()
                parties = [x.strip() for x in re.split(r'\s[-\u2013\u2014|:]\s', titre) if x.strip()]
                if parties:
                    return _choisir_partie(parties)[:45]
                break
    return project.nom or 'Application'


def _generer_manifest_pwa(project, parsed):
    fichiers = parsed.get('fichiers', [])
    couleur = _extraire_couleur_primaire(fichiers)
    nom = _titre_app(project, parsed)
    est_jeu = any(('<canvas' in (f.get('contenu') or '')) or ('getContext(' in (f.get('contenu') or '')) for f in fichiers)
    description = _description_courte(parsed.get('description') or project.prompt_initial or nom)
    return {
        'name': nom,
        'short_name': nom[:12],
        'description': description[:200],
        'start_url': './index.html',
        'display': 'fullscreen' if est_jeu else 'standalone',
        'background_color': '#ffffff',
        'theme_color': couleur,
        'icons': [
            {'src': 'icon.svg', 'sizes': '192x192', 'type': 'image/svg+xml', 'purpose': 'any'},
            {'src': 'icon.svg', 'sizes': '512x512', 'type': 'image/svg+xml', 'purpose': 'any'}
        ]
    }


def _generer_icone_svg(project, parsed):
    fichiers = parsed.get('fichiers', [])
    couleur = _extraire_couleur_primaire(fichiers)
    import html as _html
    nom_app = _titre_app(project, parsed)
    lettre = next((c for c in nom_app if c.isalnum()), 'A').upper()
    lettre = _html.escape(lettre)
    lignes = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">',
        '<rect width="512" height="512" rx="96" fill="' + couleur + '"/>',
        '<text x="256" y="330" font-family="Arial, sans-serif" font-size="260" font-weight="bold" fill="#ffffff" text-anchor="middle">' + lettre + '</text>',
        '</svg>'
    ]
    return chr(10).join(lignes)


def _version_cache(project):
    import hashlib
    return hashlib.md5((project.code_genere or '').encode('utf-8')).hexdigest()[:8]


def _generer_service_worker(project_id, version='1'):
    lignes = [
        "const CACHE_NAME = 'gnb41-pwa-" + project_id + "-" + version + "';",
        "self.addEventListener('install', function(event) {",
        "  event.waitUntil(caches.open(CACHE_NAME).then(function(c) { return c.add('./index.html').catch(function() {}); }));",
        "  self.skipWaiting();",
        "});",
        "self.addEventListener('activate', function(event) {",
        "  event.waitUntil(caches.keys().then(function(noms) {",
        "    return Promise.all(noms.filter(function(n) { return n.indexOf('gnb41-pwa-" + project_id + "-') === 0 && n !== CACHE_NAME; })",
        "      .map(function(n) { return caches.delete(n); }));",
        "  }).then(function() { return self.clients.claim(); }));",
        "});",
        "self.addEventListener('fetch', function(event) {",
        "  if (event.request.method !== 'GET') return;",
        "  if (new URL(event.request.url).origin !== self.location.origin) return;",
        "  event.respondWith(",
        "    fetch(event.request).then(function(rep) {",
        "      if (rep && rep.ok) {",
        "        var copie = rep.clone();",
        "        caches.open(CACHE_NAME).then(function(c) { c.put(event.request, copie); }).catch(function() {});",
        "      }",
        "      return rep;",
        "    }).catch(function() {",
        "      return caches.match(event.request).then(function(r) {",
        "        return r || caches.match('./index.html') || Response.error();",
        "      });",
        "    })",
        "  );",
        "});"
    ]
    return chr(10).join(lignes)


def _description_courte(texte, limite=160):
    texte = ' '.join((texte or '').split())
    m = re.match(r'(.+?[.!?])(\s|$)', texte)
    court = m.group(1) if m else texte
    if len(court) > limite:
        court = court[:limite].rsplit(' ', 1)[0].rstrip(',;:') + '…'
    return court


def _generer_og_png(project, parsed):
    import io
    from PIL import Image, ImageDraw, ImageFont
    nom = _titre_app(project, parsed)
    couleur = _extraire_couleur_primaire(parsed.get('fichiers', [])) or '#4a6bff'
    img = Image.new('RGB', (1200, 630), couleur)
    d = ImageDraw.Draw(img)
    lettre = next((c for c in nom if c.isalnum()), 'A').upper()
    d.ellipse((450, 90, 750, 390), fill='#ffffff')
    police_l = ImageFont.load_default(size=200)
    d.text((600, 240), lettre, font=police_l, fill=couleur, anchor='mm')
    taille = 110
    police = ImageFont.load_default(size=taille)
    while taille > 40 and d.textlength(nom, font=police) > 1050:
        taille -= 6
        police = ImageFont.load_default(size=taille)
    d.text((600, 500), nom, font=police, fill='#ffffff', anchor='mm')
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def _balises_og(project, parsed):
    import html as _html
    nom = _titre_app(project, parsed)
    desc = _description_courte(parsed.get('description') or project.prompt_initial or nom)
    racine = os.environ.get('API_PUBLIC_URL', 'http://localhost:5001/api').rstrip('/')
    if racine.endswith('/api'):
        racine = racine[:-4]
    if project.slug:
        url = f"{racine}/a/{project.slug}/"
    else:
        url = f"{racine}/api/projects/{project.id}/live/"
    e = lambda v: _html.escape(v, quote=True)
    return (chr(10) + '<meta property="og:type" content="website">'
            + chr(10) + '<meta property="og:title" content="' + e(nom) + '">'
            + chr(10) + '<meta property="og:description" content="' + e(desc) + '">'
            + chr(10) + '<meta property="og:url" content="' + e(url) + '">'
            + chr(10) + '<meta property="og:image" content="' + e(url + 'og.png') + '">'
            + chr(10) + '<meta property="og:image:width" content="1200">'
            + chr(10) + '<meta property="og:image:height" content="630">'
            + chr(10) + '<meta name="twitter:card" content="summary_large_image">'
            + chr(10) + '<meta name="description" content="' + e(desc) + '">')


def _injecter_pwa_dans_html(html, couleur, extra=''):
    balises_pwa = (
        '<link rel="manifest" href="manifest.json">' + chr(10)
        + '<meta name="theme-color" content="' + couleur + '">' + chr(10)
        + '<link rel="icon" href="icon.svg" type="image/svg+xml">' + chr(10)
        + "<script>if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('sw.js').catch(function(){});});}</script>"
    )
    balises_pwa += extra
    if '<head>' in html:
        return html.replace('<head>', '<head>' + chr(10) + balises_pwa, 1)
    return balises_pwa + html


GENERIQUES_TITRE = {'accueil', 'home', 'bienvenue', 'index', 'welcome', 'tableau de bord',
                    'dashboard', 'catalogue', 'boutique', 'contact', 'a propos', 'page'}


def _choisir_partie(parties):
    import unicodedata
    def norm(x):
        return unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower().strip()
    for x in parties:
        if norm(x) not in GENERIQUES_TITRE:
            return x
    return parties[-1]


def _generer_slug(project):
    import unicodedata, uuid as _uuid
    import html as _html
    titre = ''
    try:
        for f in json.loads(project.code_genere or '{}').get('fichiers', []):
            if f.get('chemin', '').endswith('.html'):
                m = re.search(r'<title[^>]*>(.*?)</title>', f.get('contenu', ''), re.S | re.I)
                if m:
                    titre = _html.unescape(m.group(1)).strip()
                    break
    except Exception:
        titre = ''
    if titre:
        parties = [x.strip() for x in re.split(r'\s[-\u2013\u2014|:]\s', titre) if x.strip()]
        if len(parties) > 1:
            titre = _choisir_partie(parties)
    source = (getattr(project, 'nom_app', None) or '').strip() or titre or project.nom or ''
    base = unicodedata.normalize('NFKD', source).encode('ascii', 'ignore').decode().lower()
    base = re.sub(r'[^a-z0-9]+', '-', base).strip('-')[:30].strip('-') or 'app'
    if base in ('a', 'live'):
        base += '-app'
    slug = base
    while Project.query.filter(Project.slug == slug, Project.id != project.id).first():
        slug = f"{base}-{_uuid.uuid4().hex[:4]}"
    return slug


@project_bp.route('/a/<slug>/', defaults={'chemin': 'index.html'}, methods=['GET'])
@project_bp.route('/a/<slug>/<path:chemin>', methods=['GET'])
def serve_live_slug(slug, chemin):
    project = Project.query.filter_by(slug=slug).first_or_404()
    return _servir_projet(project, chemin)


@project_bp.route('/<project_id>/live/', defaults={'chemin': 'index.html'}, methods=['GET'])

@project_bp.route('/<project_id>/live/<path:chemin>', methods=['GET'])
def serve_live(project_id, chemin):
    project = Project.query.get_or_404(project_id)
    return _servir_projet(project, chemin)


from app.models.visite import Visite


def _compter_visite(project_id):
    ua = (request.headers.get('User-Agent') or '').lower()
    robots = ('bot', 'crawler', 'spider', 'whatsapp', 'facebookexternalhit', 'telegram',
              'preview', 'slack', 'curl', 'wget')
    if not ua or any(m in ua for m in robots):
        return
    from datetime import date
    from sqlalchemy.exc import IntegrityError
    jour = date.today()

    def incrementer():
        return Visite.query.filter_by(project_id=project_id, jour=jour).update({'nombre': Visite.nombre + 1})

    try:
        if not incrementer():
            db.session.add(Visite(project_id=project_id, jour=jour, nombre=1))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        try:
            incrementer()
            db.session.commit()
        except Exception:
            db.session.rollback()
    except Exception:
        db.session.rollback()


def _servir_projet(project, chemin):
    if not project.est_deploye or not project.code_genere or (project.modere_statut or 'actif') == 'suspendu':
        return jsonify({'error': "Cette application n'est pas deployee"}), 404

    if chemin == 'index.html':
        _compter_visite(project.id)

    try:
        parsed = json.loads(project.code_genere)
    except json.JSONDecodeError:
        return jsonify({'error': 'Code illisible'}), 500

    fichiers = parsed.get('fichiers', [])
    couleur = _extraire_couleur_primaire(fichiers)

    if chemin == 'manifest.json':
        return jsonify(_generer_manifest_pwa(project, parsed))

    if chemin == 'og.png':
        resp = Response(_generer_og_png(project, parsed), mimetype='image/png')
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp

    if chemin == 'icon.svg':
        return Response(_generer_icone_svg(project, parsed), mimetype='image/svg+xml')

    if chemin == 'sw.js':
        return Response(_generer_service_worker(project.id, _version_cache(project)), mimetype='application/javascript')

    fichier = next((f for f in fichiers if f['chemin'] == chemin), None)

    if not fichier and chemin == 'index.html':
        fichier = next((f for f in fichiers if f['chemin'].endswith('.html')), None)

    if not fichier:
        return jsonify({'error': 'Fichier introuvable'}), 404

    contenu = fichier['contenu']
    if chemin.endswith('.html') or (chemin == 'index.html'):
        contenu = _injecter_pwa_dans_html(contenu, couleur, _balises_og(project, parsed))

    return Response(contenu, mimetype=_get_file_mimetype(chemin))
