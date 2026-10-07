import json
from flask import request
from flask_login import current_user
from app import db
from app.models.audit_log import AuditLog


def _json(valeur):
    if valeur is None:
        return None
    try:
        return json.dumps(valeur, ensure_ascii=False, default=str)[:4000]
    except Exception:
        return str(valeur)[:4000]


def audit(action, cible_type=None, cible_id=None, avant=None, apres=None, admin=None):
    """Ajoute une ligne au journal d'audit, dans la transaction en cours (validée avec l'action)."""
    acteur = admin if admin is not None else current_user
    db.session.add(AuditLog(
        admin_id=getattr(acteur, 'id', None),
        admin_email=getattr(acteur, 'email', None),
        action=action[:60],
        cible_type=cible_type,
        cible_id=str(cible_id)[:64] if cible_id else None,
        ancienne_valeur=_json(avant),
        nouvelle_valeur=_json(apres),
        ip=(request.remote_addr or '')[:64],
        ip_chaine=(request.headers.get('X-Forwarded-For') or '')[:300],
    ))
