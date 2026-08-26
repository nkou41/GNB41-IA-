import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.project import Project
from app.models.app_table import AppTable
from app.models.app_row import AppRow
from app.models.api_key import ApiKey

appdb_bp = Blueprint('appdb', __name__)

ALLOWED_TYPES = ('texte', 'nombre', 'booleen', 'date')


def _check_project_access(project_id):
    from app.routes.project import _check_access
    project = Project.query.get_or_404(project_id)
    if not _check_access(project.workspace_id):
        return None
    return project


def _validate_row(colonnes, data):
    for col in colonnes:
        nom = col['nom']
        type_ = col.get('type', 'texte')
        requis = col.get('requis', False)

        if requis and nom not in data:
            return f"Le champ '{nom}' est requis"

        if nom in data and data[nom] is not None:
            valeur = data[nom]
            if type_ == 'nombre' and not isinstance(valeur, (int, float)):
                return f"Le champ '{nom}' doit etre un nombre"
            if type_ == 'booleen' and not isinstance(valeur, bool):
                return f"Le champ '{nom}' doit etre un booleen"
    return None


@appdb_bp.route('/<project_id>/tables', methods=['GET'])
@login_required
def list_tables(project_id):
    if not _check_project_access(project_id):
        return jsonify({'error': 'Non autorisé'}), 403
    tables = AppTable.query.filter_by(project_id=project_id).all()
    return jsonify([t.to_dict() for t in tables])


@appdb_bp.route('/<project_id>/tables', methods=['POST'])
@login_required
def create_table(project_id):
    if not _check_project_access(project_id):
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json() or {}
    nom = data.get('nom', '').strip()
    colonnes = data.get('colonnes', [])

    if not nom:
        return jsonify({'error': 'nom requis'}), 400
    if not colonnes or not isinstance(colonnes, list):
        return jsonify({'error': 'colonnes requis (liste non vide)'}), 400

    for col in colonnes:
        if 'nom' not in col or col.get('type', 'texte') not in ALLOWED_TYPES:
            return jsonify({'error': f"colonne invalide: {col}"}), 400

    table = AppTable(project_id=project_id, nom=nom, colonnes=json.dumps(colonnes))
    db.session.add(table)
    db.session.commit()

    return jsonify(table.to_dict()), 201


@appdb_bp.route('/tables/<table_id>', methods=['DELETE'])
@login_required
def delete_table(table_id):
    table = AppTable.query.get_or_404(table_id)
    if not _check_project_access(table.project_id):
        return jsonify({'error': 'Non autorisé'}), 403

    AppRow.query.filter_by(table_id=table_id).delete()
    db.session.delete(table)
    db.session.commit()
    return jsonify({'success': True})


@appdb_bp.route('/<project_id>/keys', methods=['GET'])
@login_required
def list_keys(project_id):
    if not _check_project_access(project_id):
        return jsonify({'error': 'Non autorisé'}), 403
    keys = ApiKey.query.filter_by(project_id=project_id).all()
    return jsonify([k.to_dict() for k in keys])


@appdb_bp.route('/<project_id>/keys', methods=['POST'])
@login_required
def create_key(project_id):
    if not _check_project_access(project_id):
        return jsonify({'error': 'Non autorisé'}), 403

    raw, prefix, key_hash = ApiKey.generate_key()
    key = ApiKey(project_id=project_id, key_prefix=prefix, key_hash=key_hash)
    db.session.add(key)
    db.session.commit()

    result = key.to_dict()
    result['key'] = raw
    return jsonify(result), 201


@appdb_bp.route('/keys/<key_id>', methods=['DELETE'])
@login_required
def revoke_key(key_id):
    key = ApiKey.query.get_or_404(key_id)
    if not _check_project_access(key.project_id):
        return jsonify({'error': 'Non autorisé'}), 403
    key.revoked = True
    db.session.commit()
    return jsonify({'success': True})


def _get_api_key_from_request():
    import hashlib
    header = request.headers.get('X-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
    if not header:
        return None
    key_hash = hashlib.sha256(header.encode()).hexdigest()
    key = ApiKey.query.filter_by(key_hash=key_hash, revoked=False).first()
    if key:
        key.last_used_at = datetime.utcnow()
        db.session.commit()
    return key


@appdb_bp.route('/v1/tables/<table_id>/rows', methods=['GET'])
def public_list_rows(table_id):
    key = _get_api_key_from_request()
    if not key:
        return jsonify({'error': 'Cle API invalide ou manquante'}), 401
    table = AppTable.query.get_or_404(table_id)
    if table.project_id != key.project_id:
        return jsonify({'error': 'Cle API non autorisee pour cette table'}), 403

    rows = AppRow.query.filter_by(table_id=table_id).all()
    return jsonify([r.to_dict() for r in rows])


@appdb_bp.route('/v1/tables/<table_id>/rows', methods=['POST'])
def public_create_row(table_id):
    key = _get_api_key_from_request()
    if not key:
        return jsonify({'error': 'Cle API invalide ou manquante'}), 401
    table = AppTable.query.get_or_404(table_id)
    if table.project_id != key.project_id:
        return jsonify({'error': 'Cle API non autorisee pour cette table'}), 403

    data = request.get_json() or {}
    colonnes = json.loads(table.colonnes)
    erreur = _validate_row(colonnes, data)
    if erreur:
        return jsonify({'error': erreur}), 400

    row = AppRow(table_id=table_id, data=json.dumps(data))
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@appdb_bp.route('/v1/tables/<table_id>/rows/<row_id>', methods=['PUT'])
def public_update_row(table_id, row_id):
    key = _get_api_key_from_request()
    if not key:
        return jsonify({'error': 'Cle API invalide ou manquante'}), 401
    table = AppTable.query.get_or_404(table_id)
    if table.project_id != key.project_id:
        return jsonify({'error': 'Cle API non autorisee pour cette table'}), 403

    row = AppRow.query.get_or_404(row_id)
    if row.table_id != table_id:
        return jsonify({'error': 'Ligne introuvable dans cette table'}), 404

    data = request.get_json() or {}
    colonnes = json.loads(table.colonnes)
    erreur = _validate_row(colonnes, data)
    if erreur:
        return jsonify({'error': erreur}), 400

    row.data = json.dumps(data)
    db.session.commit()
    return jsonify(row.to_dict())


@appdb_bp.route('/v1/tables/<table_id>/rows/<row_id>', methods=['DELETE'])
def public_delete_row(table_id, row_id):
    key = _get_api_key_from_request()
    if not key:
        return jsonify({'error': 'Cle API invalide ou manquante'}), 401
    table = AppTable.query.get_or_404(table_id)
    if table.project_id != key.project_id:
        return jsonify({'error': 'Cle API non autorisee pour cette table'}), 403

    row = AppRow.query.get_or_404(row_id)
    if row.table_id != table_id:
        return jsonify({'error': 'Ligne introuvable dans cette table'}), 404

    db.session.delete(row)
    db.session.commit()
    return jsonify({'success': True})
