from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
import os
from logging.handlers import RotatingFileHandler
import logging

db = SQLAlchemy()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=['2000 per hour'])
mail = Mail()

def create_app(test_config=None):
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'tableau_ia.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 Mo max par requete

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login_manager.init_app(app)
    CORS(app, supports_credentials=True, origins=['http://localhost:5173'])
    limiter.init_app(app)
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
    mail.init_app(app)

    if not app.debug:
        os.makedirs(os.path.join(basedir, 'logs'), exist_ok=True)
        file_handler = RotatingFileHandler(
            os.path.join(basedir, 'logs', 'app.log'), maxBytes=1024*1024*5, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Demarrage de l application Tableau IA')

    from app.models.user import User
    from app.models.workspace import Workspace, WorkspaceMember
    from app.models.project import Project
    from app.models.project_version import ProjectVersion
    from app.models.project_message import ProjectMessage
    from app.models.listing import Listing
    from app.models.purchase import Purchase

    from app.routes.auth import auth_bp
    from app.routes.workspace import workspace_bp
    from app.routes.project import project_bp
    from app.routes.marketplace import marketplace_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(workspace_bp, url_prefix='/api/workspaces')
    app.register_blueprint(project_bp, url_prefix='/api/projects')
    app.register_blueprint(marketplace_bp, url_prefix='/api/marketplace')

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Ressource introuvable'}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Méthode non autorisée'}), 405

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({'error': 'Trop de requêtes, veuillez patienter avant de réessayer'}), 429

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Erreur serveur interne'}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return jsonify({'error': e.description}), e.code
        app.logger.error(f'Erreur non gérée: {str(e)}')
        return jsonify({'error': 'Une erreur inattendue est survenue'}), 500

    with app.app_context():
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        db.create_all()
        db.session.execute(db.text('PRAGMA journal_mode=WAL'))
        db.session.commit()

    return app
