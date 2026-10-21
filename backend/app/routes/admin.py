from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app import db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.project import Project
from app.utils_admin import admin_required, superadmin_required
from app.utils.rbac import permission_required, ROLES, a_permission, est_proprietaire
from app.services.notifications import envoyer_notification
from datetime import datetime, timedelta
from app.services.audit import audit
from app.models.audit_log import AuditLog
from app.services.reqres_client import get_users as reqres_get_users, TEST_MODE
from app.models.evaluation_run import EvaluationRun
from app.services.generator import generate_project_code
import time
import uuid as uuid_lib

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@login_required
@permission_required('utilisateurs.voir')
def list_users():
    if TEST_MODE:
        data = reqres_get_users()
        return jsonify({'users': data.get('data', []), 'total': data.get('total', 0), 'test_mode': True})

    voir_email = a_permission('utilisateurs.voir_email')
    search = request.args.get('q', '').strip()[:100]
    query = User.query
    if search:
        if voir_email:
            motif = db.or_(User.username.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        else:
            # Sans droit sur les e-mails : adresse exacte uniquement (pas de sondage lettre par lettre).
            motif = db.or_(User.username.ilike(f'%{search}%'), db.func.lower(User.email) == search.lower())
        query = query.filter(motif)
    users = query.order_by(User.created_at.desc()).limit(200).all()
    return jsonify({'users': [_vue_utilisateur(u, voir_email) for u in users], 'total': len(users)})


@admin_bp.route('/users/<user_id>/role', methods=['PATCH'])
@login_required
@permission_required('roles.gerer')
def update_user_role(user_id):
    data = request.get_json(silent=True) or {}
    new_role = data.get('role')
    if new_role != 'user' and new_role not in ROLES:
        return jsonify({'error': 'Role invalide'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    if user.id == current_user.id:
        return jsonify({'error': 'Vous ne pouvez pas modifier votre propre rôle'}), 403
    ancien = user.role or 'user'
    if ancien == new_role:
        return jsonify({'user': user.to_dict()})
    try:
        user.role = new_role
        audit('utilisateur.role_modifie', 'utilisateur', user.id,
              avant={'role': ancien, 'email': user.email}, apres={'role': new_role})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Modification impossible. Réessayez.'}), 500
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
    provider = data.get('provider', 'mistral')
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


@admin_bp.route('/plans', methods=['GET'])
@login_required
@admin_required
def admin_list_plans():
    from app.models.plan import Plan
    plans = Plan.query.order_by(Plan.ordre.asc()).all()
    return jsonify({'plans': [p.to_dict() for p in plans]})


@admin_bp.route('/plans/<plan_id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_plan(plan_id):
    from app.models.plan import Plan
    import json
    plan = Plan.query.get(plan_id)
    if not plan:
        return jsonify({'error': 'Plan introuvable'}), 404
    data = request.get_json() or {}
    for field in ['nom', 'prix_usd', 'prix_xof', 'credits', 'description', 'ordre', 'populaire', 'actif', 'sur_devis']:
        if field in data:
            setattr(plan, field, data[field])
    if 'features' in data:
        plan.features = json.dumps(data['features'])
    db.session.commit()
    return jsonify({'plan': plan.to_dict()})


@admin_bp.route('/plans', methods=['POST'])
@login_required
@admin_required
def admin_create_plan():
    from app.models.plan import Plan
    import json
    data = request.get_json() or {}
    if not data.get('slug') or not data.get('nom'):
        return jsonify({'error': 'slug et nom requis'}), 400
    if Plan.query.filter_by(slug=data['slug']).first():
        return jsonify({'error': 'Ce slug existe deja'}), 400
    plan = Plan(
        slug=data['slug'],
        nom=data['nom'],
        prix_usd=data.get('prix_usd', 0),
        prix_xof=data.get('prix_xof', 0),
        credits=data.get('credits'),
        description=data.get('description'),
        features=json.dumps(data.get('features', [])),
        ordre=data.get('ordre', 0),
        populaire=data.get('populaire', False),
        actif=data.get('actif', True),
        sur_devis=data.get('sur_devis', False),
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify({'plan': plan.to_dict()}), 201


@admin_bp.route('/audit', methods=['GET'])
@login_required
@permission_required('audit.voir')
def list_audit():
    prefix = request.args.get('prefix', '')
    requete = AuditLog.query
    if prefix in ('moderation.', 'annonce.', 'utilisateur.'):
        requete = requete.filter(AuditLog.action.like(prefix + '%'))
    lignes = requete.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify({'entries': [dict(l.to_dict(), ip_chaine=l.ip_chaine) for l in lignes]})


STATUTS_COMPTE = ('actif', 'suspendu', 'bloque')


def _avec_statut(u):
    d = u.to_dict()
    d['compte_statut'] = u.compte_statut or 'actif'
    d['suspendu_jusqua'] = u.suspendu_jusqua.isoformat() if u.suspendu_jusqua else None
    d['motif_suspension'] = u.motif_suspension
    return d


def _notifier_compte(user, titre, message):
    try:
        envoyer_notification(user.id, 'compte', titre[:200], message)
    except Exception:
        db.session.rollback()


@admin_bp.route('/users/<user_id>/statut', methods=['PATCH'])
@login_required
@permission_required('utilisateurs.modifier')
def update_user_statut(user_id):
    data = request.get_json(silent=True) or {}
    statut = data.get('statut')
    motif = (data.get('motif') or '').strip()[:300]
    if statut not in STATUTS_COMPTE:
        return jsonify({'error': 'Statut invalide'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    if user.id == current_user.id:
        return jsonify({'error': 'Vous ne pouvez pas modifier le statut de votre propre compte'}), 403
    if est_proprietaire(user):
        return jsonify({'error': 'Ce compte ne peut pas être suspendu'}), 403
    if (user.role or 'user') in ('admin', 'superadmin') and not a_permission('roles.gerer'):
        return jsonify({'error': 'Seul un super administrateur peut agir sur ce compte'}), 403
    if statut != 'actif' and len(motif) < 5:
        return jsonify({'error': 'Un motif de 5 caractères minimum est requis'}), 400
    jours = None
    if statut == 'suspendu' and data.get('jours') not in (None, ''):
        try:
            jours = int(data.get('jours'))
        except (ValueError, TypeError):
            return jsonify({'error': 'Durée invalide'}), 400
        if jours < 1 or jours > 365:
            return jsonify({'error': 'La durée doit être comprise entre 1 et 365 jours'}), 400

    avant = {'statut': user.compte_statut or 'actif',
             'jusqua': user.suspendu_jusqua.isoformat() if user.suspendu_jusqua else None}
    try:
        user.compte_statut = statut
        user.suspendu_jusqua = datetime.utcnow() + timedelta(days=jours) if jours else None
        user.motif_suspension = motif if statut != 'actif' else None
        audit('utilisateur.statut_modifie', 'utilisateur', user.id, avant=avant,
              apres={'statut': statut, 'jours': jours, 'motif': motif or None, 'email': user.email})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Modification impossible. Réessayez.'}), 500

    if statut == 'actif':
        _notifier_compte(user, 'Compte réactivé', 'Votre compte est de nouveau actif.')
    elif statut == 'suspendu':
        _notifier_compte(user, 'Compte suspendu', f'Votre compte a été suspendu. Motif : {motif}')
    else:
        _notifier_compte(user, 'Compte bloqué', f'Votre compte a été bloqué. Motif : {motif}')
    return jsonify({'user': _avec_statut(user)})


@admin_bp.route('/users/<user_id>/credits', methods=['POST'])
@login_required
@permission_required('utilisateurs.modifier')
def add_user_credits(user_id):
    data = request.get_json(silent=True) or {}
    motif = (data.get('motif') or '').strip()[:300]
    try:
        n = int(data.get('credits'))
    except (ValueError, TypeError):
        return jsonify({'error': 'Nombre de crédits invalide'}), 400
    if n < 1 or n > 1000:
        return jsonify({'error': 'Le nombre de crédits doit être compris entre 1 et 1000'}), 400
    if len(motif) < 5:
        return jsonify({'error': 'Un motif de 5 caractères minimum est requis'}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    if user.id == current_user.id and not est_proprietaire(current_user):
        return jsonify({'error': 'Vous ne pouvez pas vous ajouter des crédits à vous-même'}), 403
    avant = user.credits if user.credits is not None else 1
    try:
        user.credits = avant + n
        audit('utilisateur.credits_ajoutes', 'utilisateur', user.id,
              avant={'credits': avant}, apres={'credits': avant + n, 'motif': motif, 'email': user.email})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Ajout impossible. Réessayez.'}), 500
    _notifier_compte(user, 'Crédits ajoutés', f'{n} crédit(s) ont été ajoutés à votre compte.')
    return jsonify({'user': _avec_statut(user)})


def _masquer_email(email):
    if not email or '@' not in email:
        return ''
    local, domaine = email.split('@', 1)
    return (local[:1] or '*') + '***@' + domaine


def _vue_utilisateur(u, voir_email):
    return {
        'id': u.id,
        'username': u.username,
        'email': u.email if voir_email else _masquer_email(u.email),
        'created_at': u.created_at.isoformat() if u.created_at else None,
        'plan': u.plan or 'gratuit',
        'credits': u.credits if u.credits is not None else 1,
        'role': u.role or 'user',
        'compte_statut': u.compte_statut or 'actif',
        'suspendu_jusqua': u.suspendu_jusqua.isoformat() if u.suspendu_jusqua else None,
        'motif_suspension': u.motif_suspension,
    }


@admin_bp.route('/users/<user_id>/reveler-email', methods=['POST'])
@login_required
@permission_required('utilisateurs.voir')
def reveler_email(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utilisateur introuvable'}), 404
    if (est_proprietaire(user) or (user.role or 'user') in ('admin', 'superadmin')) and not a_permission('roles.gerer'):
        return jsonify({'error': 'Seul un super administrateur peut voir cette adresse'}), 403
    try:
        audit('utilisateur.email_revele', 'utilisateur', user.id, apres={'champ': 'email'})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Action impossible. Réessayez.'}), 500
    return jsonify({'email': user.email})


def _compter_par(colonne, id_col, defaut):
    resultat = {}
    for cle, n in db.session.query(colonne, db.func.count(id_col)).group_by(colonne).all():
        nom = str(cle) if cle else defaut
        resultat[nom] = resultat.get(nom, 0) + n
    return resultat


def _serie_par_jour(colonne, id_col, jours):
    debut = (datetime.utcnow() - timedelta(days=jours - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    lignes = (db.session.query(db.func.date(colonne), db.func.count(id_col))
              .filter(colonne >= debut).group_by(db.func.date(colonne)).all())
    comptes = {str(j)[:10]: n for j, n in lignes}
    serie = []
    for i in range(jours):
        jour = (debut + timedelta(days=i)).strftime('%Y-%m-%d')
        serie.append({'jour': jour, 'n': comptes.get(jour, 0)})
    return serie


@admin_bp.route('/overview', methods=['GET'])
@login_required
@permission_required('stats.voir')
def admin_overview():
    from app.models.listing import Listing
    from app.models.purchase import Purchase
    from app.models.payment import Payment
    from app.models.listing_review import ListingReview
    from app.models.listing_report import ListingReport
    from app.models.studio_usage_log import StudioUsageLog

    try:
        jours = int(request.args.get('jours', 14))
    except (ValueError, TypeError):
        jours = 14
    if jours not in (7, 14, 30, 90):
        jours = 14
    maintenant = datetime.utcnow()
    depuis = lambda n: maintenant - timedelta(days=n)

    suspendus = User.query.filter(db.or_(
        User.compte_statut == 'bloque',
        db.and_(User.compte_statut == 'suspendu',
                db.or_(User.suspendu_jusqua.is_(None), User.suspendu_jusqua > maintenant)))).count()
    donnees = {
        'jours': jours,
        'utilisateurs': {
            'total': User.query.count(),
            'nouveaux_7j': User.query.filter(User.created_at >= depuis(7)).count(),
            'nouveaux_30j': User.query.filter(User.created_at >= depuis(30)).count(),
            'suspendus': suspendus,
            'par_plan': _compter_par(User.plan, User.id, 'gratuit'),
        },
        'projets': {
            'total': Project.query.count(),
            'nouveaux_7j': Project.query.filter(Project.created_at >= depuis(7)).count(),
            'nouveaux_30j': Project.query.filter(Project.created_at >= depuis(30)).count(),
            'deployes': Project.query.filter_by(est_deploye=True).count(),
            'par_statut': _compter_par(Project.statut, Project.id, 'inconnu'),
            'par_modele': _compter_par(Project.provider, Project.id, 'inconnu'),
        },
        'moderation': {
            'a_examiner': ListingReview.query.filter_by(statut='en_attente').count(),
            'signalements': ListingReport.query.filter_by(statut='nouveau').count(),
        },
        'studio': {
            'appels_7j': StudioUsageLog.query.filter(StudioUsageLog.created_at >= depuis(7)).count(),
            'erreurs_7j': StudioUsageLog.query.filter(StudioUsageLog.created_at >= depuis(7),
                                                      StudioUsageLog.statut_http >= 400).count(),
        },
        'boutique': {
            'annonces': _compter_par(Listing.statut, Listing.id, 'inconnu'),
            'ventes': Purchase.query.filter_by(statut='complete').count(),
        },
        'series': {
            'inscriptions': _serie_par_jour(User.created_at, User.id, jours),
            'projets': _serie_par_jour(Project.created_at, Project.id, jours),
        },
    }
    if a_permission('finance.voir'):
        ca, commission = db.session.query(
            db.func.coalesce(db.func.sum(Purchase.prix_paye_centimes), 0),
            db.func.coalesce(db.func.sum(Purchase.commission_centimes), 0)
        ).filter(Purchase.statut == 'complete').one()
        donnees['finance'] = {
            'ca_centimes': int(ca),
            'commission_centimes': int(commission),
            'paiements': _compter_par(Payment.status, Payment.id, 'inconnu'),
        }
    return jsonify(donnees)


FILTRES_PROJETS = ('tous', 'publies', 'suspendus', 'echecs')


@admin_bp.route('/projects', methods=['GET'])
@login_required
@permission_required('projets.voir')
def admin_list_projects():
    voir_email = a_permission('utilisateurs.voir_email')
    filtre = request.args.get('filtre', 'tous')
    if filtre not in FILTRES_PROJETS:
        filtre = 'tous'
    search = request.args.get('q', '').strip()[:100]
    requete = (db.session.query(
        Project.id.label('pid'), Project.nom.label('nom'), Project.statut.label('statut'),
        Project.provider.label('provider'), Project.est_deploye.label('deploye'),
        Project.modere_statut.label('modere'), Project.modere_motif.label('motif'),
        Project.created_at.label('cree'), Project.updated_at.label('maj'),
        User.id.label('uid'), User.username.label('uname'), User.email.label('umail'))
        .select_from(Project)
        .join(Workspace, Project.workspace_id == Workspace.id)
        .join(User, Workspace.owner_id == User.id))
    if filtre == 'publies':
        requete = requete.filter(Project.est_deploye.is_(True))
    elif filtre == 'suspendus':
        requete = requete.filter(Project.modere_statut == 'suspendu')
    elif filtre == 'echecs':
        requete = requete.filter(Project.statut == 'erreur')
    if search:
        criteres = [Project.nom.ilike(f'%{search}%'), User.username.ilike(f'%{search}%')]
        criteres.append(User.email.ilike(f'%{search}%') if voir_email else db.func.lower(User.email) == search.lower())
        requete = requete.filter(db.or_(*criteres))
    lignes = requete.order_by(Project.created_at.desc()).limit(100).all()
    projets = [{
        'id': l.pid, 'nom': l.nom, 'statut': l.statut, 'modele': l.provider,
        'est_deploye': bool(l.deploye), 'modere_statut': l.modere or 'actif', 'modere_motif': l.motif,
        'created_at': l.cree.isoformat() if l.cree else None,
        'updated_at': l.maj.isoformat() if l.maj else None,
        'proprietaire_id': l.uid, 'proprietaire': l.uname,
        'proprietaire_email': l.umail if voir_email else _masquer_email(l.umail),
    } for l in lignes]
    return jsonify({'projects': projets, 'total': len(projets)})


@admin_bp.route('/projects/<project_id>/moderation', methods=['PATCH'])
@login_required
@permission_required('projets.moderer')
def moderer_projet(project_id):
    from app.models.listing import Listing
    from app.models.listing_review import ListingReview
    data = request.get_json(silent=True) or {}
    action = data.get('action')
    motif = (data.get('motif') or '').strip()[:300]
    if action not in ('suspendre', 'reactiver'):
        return jsonify({'error': 'Action invalide'}), 400
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'error': 'Projet introuvable'}), 404
    workspace = Workspace.query.get(project.workspace_id)
    proprietaire = User.query.get(workspace.owner_id) if workspace else None
    if proprietaire is not None:
        if proprietaire.id == current_user.id:
            return jsonify({'error': 'Vous ne pouvez pas modérer votre propre projet'}), 403
        if est_proprietaire(proprietaire):
            return jsonify({'error': 'Ce projet ne peut pas être suspendu'}), 403
        if (proprietaire.role or 'user') in ('admin', 'superadmin') and not a_permission('roles.gerer'):
            return jsonify({'error': 'Seul un super administrateur peut agir sur ce projet'}), 403
    actuel = project.modere_statut or 'actif'
    if action == 'suspendre':
        if actuel == 'suspendu':
            return jsonify({'error': 'Ce projet est déjà suspendu'}), 409
        if len(motif) < 5:
            return jsonify({'error': 'Un motif de 5 caractères minimum est requis'}), 400
    elif actuel != 'suspendu':
        return jsonify({'error': "Ce projet n'est pas suspendu"}), 409

    retirees = 0
    try:
        avant = {'modere_statut': actuel, 'est_deploye': bool(project.est_deploye)}
        if action == 'suspendre':
            maintenant = datetime.utcnow()
            project.modere_statut = 'suspendu'
            project.modere_motif = motif
            project.est_deploye = False
            for l in Listing.query.filter_by(project_id=project.id).all():
                if l.statut in ('publie', 'en_revue', 'suspendu'):
                    for rv in ListingReview.query.filter_by(listing_id=l.id, statut='en_attente').all():
                        rv.statut = 'retire'
                        rv.decide_par = current_user.id
                        rv.decision_motif = motif
                        rv.decided_at = maintenant
                    l.statut = 'retire'
                    retirees += 1
            audit('projet.suspendu', 'projet', project.id, avant=avant,
                  apres={'modere_statut': 'suspendu', 'motif': motif, 'annonces_retirees': retirees,
                         'proprietaire': proprietaire.username if proprietaire else None})
        else:
            project.modere_statut = 'actif'
            project.modere_motif = None
            audit('projet.reactive', 'projet', project.id, avant=avant,
                  apres={'modere_statut': 'actif', 'proprietaire': proprietaire.username if proprietaire else None})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Modification impossible. Réessayez.'}), 500

    if proprietaire is not None:
        if action == 'suspendre':
            _notifier_compte(proprietaire, 'Projet suspendu', f"Votre projet « {project.nom} » a été suspendu. Motif : {motif}")
        else:
            _notifier_compte(proprietaire, 'Projet réactivé', f"Votre projet « {project.nom} » a été réactivé. Vous pouvez le republier.")
    return jsonify({'project': {'id': project.id, 'modere_statut': project.modere_statut, 'annonces_retirees': retirees}})
