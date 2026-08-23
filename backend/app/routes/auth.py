from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db, limiter, mail, csrf
from flask_wtf.csrf import generate_csrf
from app.models.user import User
import secrets
from flask_mail import Message

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/csrf-token', methods=['GET'])
def csrf_token():
    return jsonify({'csrf_token': generate_csrf()})


@auth_bp.route('/register', methods=['POST'])
@limiter.limit('5 per hour')
@csrf.exempt
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'username, email et password requis'}), 400

    if len(password) < 8:
        return jsonify({'error': 'Le mot de passe doit contenir au moins 8 caractères'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Nom d\'utilisateur déjà pris'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email déjà utilisé'}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    confirm_token = secrets.token_urlsafe(32)
    user.confirm_token = confirm_token
    db.session.add(user)
    db.session.commit()

    confirm_url = f"http://localhost:5173/confirm-email?token={confirm_token}"
    try:
        msg = Message("Confirmez votre email - Tableau IA", recipients=[email])
        msg.body = f"Bienvenue sur GNB41 IA ! Cliquez sur ce lien pour confirmer votre email : {confirm_url}"
        mail.send(msg)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Erreur envoi email confirmation: {str(e)}")

    login_user(user)
    return jsonify(user.to_dict()), 201


@auth_bp.route('/confirm-email', methods=['POST'])
@limiter.limit('10 per hour')
def confirm_email():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({'error': 'Token requis'}), 400
    user = User.query.filter_by(confirm_token=token).first()
    if not user:
        return jsonify({'error': 'Lien invalide'}), 400
    user.email_confirmed = True
    user.confirm_token = None
    db.session.commit()

    try:
        welcome_msg = Message('Bienvenue sur GNB41 IA !', recipients=[user.email])
        welcome_msg.body = f"Bonjour {user.username},\n\nVotre email est confirme et votre compte GNB41 IA est maintenant actif.\n\nVous pouvez commencer a creer vos applications des maintenant.\n\nA bientot,\nL'equipe GNB41 IA"
        mail.send(welcome_msg)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Erreur envoi email bienvenue: {str(e)}')

    return jsonify({'message': 'Email confirme avec succes'})


@auth_bp.route('/login', methods=['POST'])
@limiter.limit('10 per minute')
@csrf.exempt
def login():
    data = request.get_json()
    identifier = data.get('username') or data.get('email')
    password = data.get('password')

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Identifiants invalides'}), 401

    login_user(user)
    return jsonify(user.to_dict())


@auth_bp.route('/forgot-password', methods=['POST'])
@limiter.limit('3 per hour')
@csrf.exempt
def forgot_password():
    import secrets
    from datetime import datetime, timedelta
    from flask_mail import Message
    from app import mail
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()
        reset_url = f"http://localhost:5173/reset-password?token={token}"
        try:
            msg = Message('Reinitialisation de mot de passe - Tableau IA', recipients=[email])
            msg.body = f"Cliquez sur ce lien pour reinitialiser votre mot de passe (valable 1 heure) : {reset_url}"
            mail.send(msg)
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'Erreur envoi email: {str(e)}')
    return jsonify({'message': 'Si cet email existe, un lien de reinitialisation a ete envoye'})


@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit('5 per hour')
@csrf.exempt
def reset_password():
    from datetime import datetime
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')
    if not token or not new_password:
        return jsonify({'error': 'Token et mot de passe requis'}), 400
    if len(new_password) < 8:
        return jsonify({'error': 'Le mot de passe doit contenir au moins 8 caracteres'}), 400
    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        return jsonify({'error': 'Lien invalide ou expire'}), 400
    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()
    return jsonify({'message': 'Mot de passe reinitialise avec succes'})


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True})


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify(current_user.to_dict())


@auth_bp.route('/me', methods=['PUT'])
@login_required
def update_me():
    data = request.get_json()
    new_email = data.get('email')
    new_password = data.get('password')
    current_password = data.get('current_password')

    if not current_password or not current_user.check_password(current_password):
        return jsonify({'error': 'Mot de passe actuel incorrect'}), 401

    if new_email and new_email != current_user.email:
        if User.query.filter_by(email=new_email).first():
            return jsonify({'error': 'Email déjà utilisé'}), 409
        current_user.email = new_email

    if new_password:
        current_user.set_password(new_password)

    db.session.commit()
    return jsonify(current_user.to_dict())
