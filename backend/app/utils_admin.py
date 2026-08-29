from functools import wraps
from flask import jsonify
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Non authentifie'}), 401
        if current_user.role not in ('admin', 'superadmin'):
            return jsonify({'error': 'Acces reserve aux administrateurs'}), 403
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Non authentifie'}), 401
        if current_user.role != 'superadmin':
            return jsonify({'error': 'Acces reserve au super-administrateur'}), 403
        return f(*args, **kwargs)
    return decorated
