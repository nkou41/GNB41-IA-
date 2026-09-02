from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app import db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.project import Project
from app.utils_admin import admin_required, superadmin_required
from app.services.reqres_client import get_users as reqres_get_users, TEST_MODE
from app.models.evaluation_run import EvaluationRun
from app.services.generator import generate_project_code
import time
import uuid as uuid_lib

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def list_users():
    if TEST_MODE:
        data = reqres_get_users()
        return jsonify({'users': data.get('data', []), 'total': data.get('total', 0), 'test_mode': True})

    search = request.args.get('q', '').strip()
    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    users = query.order_by(User.created_at.desc()).all()
    return jsonify({'users': [u.to_dict() for u in users], 'total': len(users)})


@admin_bp.route('/users/<user_id>/role', methods=['PATCH'])
@login_required
@superadmin_required
def update_user_role(user_id):
    data = request.get_json() or {}
    new_role = data.get('role')
    if new_role not in ('user', 'admin', 'superadmin'):
        return jsonify({'error': 'Role invalide'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    user.role = new_role
    db.session.commit()
    return jsonify({'user': user.to_dict()})


@admin_bp.route('/workspaces', methods=['GET'])
@login_required
@admin_required
def list_workspaces():
    workspaces = Workspace.query.order_by(Workspace.created_at.desc()).all()
    result = []
    for w in workspaces:
        owner = User.query.get(w.owner_id)
        d = w.to_dict()
        d['owner_email'] = owner.email if owner else None
        d['owner_username'] = owner.username if owner else None
        d['member_count'] = len(w.members)
        result.append(d)
    return jsonify({'workspaces': result, 'total': len(result)})


@admin_bp.route('/workspaces/<workspace_id>', methods=['DELETE'])
@login_required
@superadmin_required
def delete_workspace(workspace_id):
    workspace = Workspace.query.get(workspace_id)
    if not workspace:
        return jsonify({'error': 'Workspace introuvable'}), 404
    db.session.delete(workspace)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
def admin_stats():
    return jsonify({
        'total_users': User.query.count(),
        'total_workspaces': Workspace.query.count(),
        'total_projects': Project.query.count(),
        'users_by_plan': {
            plan: User.query.filter_by(plan=plan).count()
            for plan in ['gratuit', 'pro']
        }
    })


# Axe 14 (evaluation) : suite de prompts fixes rejoues periodiquement pour
# mesurer la qualite du moteur IA dans le temps (comprehension, plan,
# avertissements, duree), independamment de l'observabilite (Axe 14 duree seule).
EVALUATION_PROMPTS = [
    "Cree une landing page pour un cafe avec un formulaire de contact",
    "Ajoute une todo list avec ajout et suppression de taches en JavaScript",
    "Cree un portfolio personnel simple avec une section projets",
]


@admin_bp.route('/evaluation/run', methods=['POST'])
@login_required
@admin_required
def run_evaluation():
    data = request.get_json() or {}
    provider = data.get('provider', 'claude')
    suite_id = str(uuid_lib.uuid4())
    resultats = []

    for prompt in EVALUATION_PROMPTS:
        debut = time.time()
        try:
            result = generate_project_code(prompt, provider=provider)
            duree_ms = int((time.time() - debut) * 1000)
            run = EvaluationRun(
                suite_id=suite_id,
                prompt=prompt,
                provider=provider,
                statut=result.get('statut'),
                a_comprehension=bool(result.get('comprehension')),
                a_plan=bool(result.get('plan')),
                nb_fichiers=len(result.get('fichiers') or []),
                nb_avertissements=len(result.get('avertissements') or []),
                duree_ms=duree_ms,
                erreur=result.get('message') if result.get('statut') == 'erreur' else None,
            )
        except Exception as e:
            duree_ms = int((time.time() - debut) * 1000)
            run = EvaluationRun(
                suite_id=suite_id,
                prompt=prompt,
                provider=provider,
                statut='exception',
                duree_ms=duree_ms,
                erreur=str(e),
            )
        db.session.add(run)
        resultats.append(run)

    db.session.commit()
    return jsonify({'suite_id': suite_id, 'resultats': [r.to_dict() for r in resultats]})


@admin_bp.route('/evaluation/history', methods=['GET'])
@login_required
@admin_required
def evaluation_history():
    runs = EvaluationRun.query.order_by(EvaluationRun.created_at.desc()).limit(300).all()
    suites = {}
    ordre = []
    for r in runs:
        if r.suite_id not in suites:
            suites[r.suite_id] = []
            ordre.append(r.suite_id)
        suites[r.suite_id].append(r.to_dict())
    resultat = [
        {'suite_id': sid, 'created_at': suites[sid][-1]['created_at'], 'runs': suites[sid]}
        for sid in ordre
    ]
    return jsonify({'suites': resultat})
