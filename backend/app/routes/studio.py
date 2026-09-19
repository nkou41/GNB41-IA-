import hashlib
import io
import json
import zipfile
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db, limiter
from app.models.workspace import Workspace
from app.models.project import Project
from app.models.studio_api_key import StudioApiKey
from app.models.studio_usage_log import StudioUsageLog

studio_bp = Blueprint('studio', __name__)
studio_public_bp = Blueprint('studio_public', __name__)


# ===== Gestion des cles (interne, session utilisateur) =====

def _est_pro(user):
    return user.plan == 'pro'


@studio_bp.route('/keys', methods=['GET'])
@login_required
def list_keys():
    if not _est_pro(current_user):
        return jsonify({'error': "Le Studio et les cles API sont reserves au plan Pro."}), 403
    keys = StudioApiKey.query.filter_by(user_id=current_user.id).order_by(StudioApiKey.created_at.desc()).all()
    return jsonify([k.to_dict() for k in keys])


@studio_bp.route('/keys', methods=['POST'])
@login_required
def create_key():
    if not _est_pro(current_user):
        return jsonify({'error': "Le Studio et les cles API sont reserves au plan Pro."}), 403
    data = request.get_json() or {}
    nom = (data.get('nom') or '').strip()
    environnement = data.get('environnement', 'live')
    if not nom:
        return jsonify({'error': 'nom requis'}), 400
    if environnement not in ('test', 'live'):
        environnement = 'live'

    raw, prefix, key_hash = StudioApiKey.generate_key(environnement)
    key = StudioApiKey(user_id=current_user.id, nom=nom, environnement=environnement, key_prefix=prefix, key_hash=key_hash)
    db.session.add(key)
    db.session.commit()

    result = key.to_dict()
    result['key'] = raw
    return jsonify(result), 201


@studio_bp.route('/keys/<key_id>', methods=['DELETE'])
@login_required
def revoke_key(key_id):
    key = StudioApiKey.query.get_or_404(key_id)
    if key.user_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    key.revoked = True
    db.session.commit()
    return jsonify({'success': True})


@studio_bp.route('/keys/<key_id>/usage', methods=['GET'])
@login_required
def key_usage(key_id):
    key = StudioApiKey.query.get_or_404(key_id)
    if key.user_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    logs = StudioUsageLog.query.filter_by(api_key_id=key_id).order_by(StudioUsageLog.created_at.desc()).limit(50).all()
    return jsonify([l.to_dict() for l in logs])


@studio_bp.route('/overview', methods=['GET'])
@login_required
def overview():
    if not _est_pro(current_user):
        return jsonify({'error': "Le Studio et les cles API sont reserves au plan Pro."}), 403
    now = datetime.utcnow()
    key_ids = [k.id for k in StudioApiKey.query.filter_by(user_id=current_user.id).all()]
    appels_7j = StudioUsageLog.query.filter(
        StudioUsageLog.api_key_id.in_(key_ids), StudioUsageLog.created_at >= now - timedelta(days=7)
    ).count() if key_ids else 0
    appels_30j = StudioUsageLog.query.filter(
        StudioUsageLog.api_key_id.in_(key_ids), StudioUsageLog.created_at >= now - timedelta(days=30)
    ).count() if key_ids else 0
    return jsonify({
        'cles_actives': StudioApiKey.query.filter_by(user_id=current_user.id, revoked=False).count(),
        'appels_7j': appels_7j,
        'appels_30j': appels_30j,
    })


# ===== API publique /v1 (auth par cle API, pour developpeurs externes) =====

def _get_studio_key_from_request():
    header = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not header:
        return None
    key_hash = hashlib.sha256(header.encode()).hexdigest()
    key = StudioApiKey.query.filter_by(key_hash=key_hash, revoked=False).first()
    if key:
        key.last_used_at = datetime.utcnow()
        db.session.commit()
    return key


def _log_usage(key, endpoint, statut_http):
    if not key:
        return
    log = StudioUsageLog(api_key_id=key.id, user_id=key.user_id, endpoint=endpoint, statut_http=statut_http)
    db.session.add(log)
    db.session.commit()


def _erreur(type_, message, code):
    return jsonify({'error': {'type': type_, 'message': message}}), code


def _get_or_create_studio_workspace(user_id):
    ws = Workspace.query.filter_by(owner_id=user_id, nom='Studio API').first()
    if not ws:
        ws = Workspace(owner_id=user_id, nom='Studio API')
        db.session.add(ws)
        db.session.commit()
    return ws


@studio_public_bp.route('/projects/generate', methods=['POST'])
@limiter.limit('20 per hour')
def public_generate_project():
    from app.routes.project import _run_generation, VALID_PROVIDERS

    key = _get_studio_key_from_request()
    if not key:
        return _erreur('authentication_error', 'Cle API invalide ou manquante', 401)

    data = request.get_json() or {}
    nom = (data.get('nom') or '').strip()
    description = (data.get('description') or '').strip()
    provider = data.get('provider', 'mistral')
    if not nom or not description:
        _log_usage(key, '/v1/projects/generate', 400)
        return _erreur('invalid_request_error', 'nom et description requis', 400)
    if provider not in VALID_PROVIDERS:
        provider = 'mistral'

    workspace = _get_or_create_studio_workspace(key.user_id)
    project = Project(workspace_id=workspace.id, nom=nom, prompt_initial=description, statut='en_generation')
    db.session.add(project)
    db.session.commit()

    project = _run_generation(project, description, provider)
    db.session.commit()

    statut_http = 201 if project.statut != 'erreur' else 500
    _log_usage(key, '/v1/projects/generate', statut_http)

    return jsonify({
        'id': project.id,
        'statut': project.statut,
        'nom': project.nom,
        'download_url': f"/v1/projects/{project.id}/download",
    }), statut_http


@studio_public_bp.route('/projects/<project_id>/download', methods=['GET'])
def public_download_project(project_id):
    key = _get_studio_key_from_request()
    if not key:
        return _erreur('authentication_error', 'Cle API invalide ou manquante', 401)

    project = Project.query.get_or_404(project_id)
    workspace = Workspace.query.get(project.workspace_id)
    if not workspace or workspace.owner_id != key.user_id:
        _log_usage(key, f'/v1/projects/{project_id}/download', 403)
        return _erreur('permission_error', 'Cle API non autorisee pour ce projet', 403)
    if not project.code_genere:
        _log_usage(key, f'/v1/projects/{project_id}/download', 404)
        return _erreur('not_found', 'Aucun code genere pour ce projet', 404)

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

    _log_usage(key, f'/v1/projects/{project_id}/download', 200)
    filename = f"{project.nom.replace(' ', '_')}.zip"
    return send_file(buffer, mimetype='application/zip', as_attachment=True, download_name=filename)


@studio_public_bp.route('/usage', methods=['GET'])
def public_usage():
    key = _get_studio_key_from_request()
    if not key:
        return _erreur('authentication_error', 'Cle API invalide ou manquante', 401)

    now = datetime.utcnow()
    appels_7j = StudioUsageLog.query.filter(
        StudioUsageLog.api_key_id == key.id, StudioUsageLog.created_at >= now - timedelta(days=7)
    ).count()
    appels_30j = StudioUsageLog.query.filter(
        StudioUsageLog.api_key_id == key.id, StudioUsageLog.created_at >= now - timedelta(days=30)
    ).count()

    return jsonify({
        'appels_7j': appels_7j,
        'appels_30j': appels_30j,
        'environnement': key.environnement,
    })
