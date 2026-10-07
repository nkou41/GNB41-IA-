import os
from functools import wraps
from flask import jsonify
from flask_login import current_user

ROLES = {
    'superadmin': 'Super administrateur',
    'admin': 'Administrateur',
    'moderateur': 'Modérateur',
    'support': 'Support client',
    'finance': 'Responsable financier',
    'technique': 'Responsable technique',
    'marketing': 'Responsable marketing',
    'analyste': 'Analyste',
}

PERMISSIONS = (
    'moderation.voir', 'moderation.decider', 'utilisateurs.voir', 'utilisateurs.modifier',
    'finance.voir', 'finance.gerer', 'abonnements.gerer', 'ia.configurer', 'api.gerer',
    'notifications.envoyer', 'logs.voir', 'stats.voir', 'audit.voir',
    'systeme.configurer', 'roles.gerer',
)
_RESERVEES = {'roles.gerer', 'systeme.configurer'}

ROLE_PERMISSIONS = {
    'superadmin': set(PERMISSIONS),
    'admin': set(PERMISSIONS) - _RESERVEES,
    'moderateur': {'moderation.voir', 'moderation.decider', 'stats.voir'},
    'support': {'utilisateurs.voir', 'moderation.voir', 'notifications.envoyer'},
    'finance': {'finance.voir', 'finance.gerer', 'abonnements.gerer', 'stats.voir'},
    'technique': {'logs.voir', 'api.gerer', 'ia.configurer', 'stats.voir'},
    'marketing': {'notifications.envoyer', 'stats.voir'},
    'analyste': {'stats.voir'},
}


def est_proprietaire(user):
    """Accès de secours : le compte dont l'e-mail est ADMIN_EMAIL a toutes les permissions."""
    admin_email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
    return bool(admin_email) and (getattr(user, 'email', '') or '').strip().lower() == admin_email


def a_permission(permission, user=None):
    u = user if user is not None else current_user
    if not getattr(u, 'is_authenticated', False):
        return False
    if est_proprietaire(u):
        return True
    return permission in ROLE_PERMISSIONS.get(getattr(u, 'role', None) or 'user', ())


def permission_required(permission):
    def decorateur(f):
        @wraps(f)
        def decore(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Non authentifié'}), 401
            if not a_permission(permission):
                return jsonify({'error': 'Accès refusé'}), 403
            return f(*args, **kwargs)
        return decore
    return decorateur
