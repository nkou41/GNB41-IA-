import os
from app.services.notifications import envoyer_notification
import requests
import uuid
import json
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify, Response, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
from app import db
from app.models.listing import Listing
from app.models.purchase import Purchase
from app.models.listing_review import ListingReview
from app.models.listing_report import ListingReport
from app.models.user import User
from sqlalchemy import or_
from app import limiter
from app.utils.rbac import a_permission
from app.services.audit import audit
from app.models.project import Project
from datetime import datetime, timedelta

marketplace_bp = Blueprint('marketplace', __name__)

ALLOWED_EXTENSIONS = {'zip'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _upload_dir():
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    upload_path = os.path.join(basedir, 'instance', 'marketplace_uploads')
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


def _images_dir():
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    images_path = os.path.join(basedir, 'instance', 'marketplace_images')
    os.makedirs(images_path, exist_ok=True)
    return images_path


def _allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@marketplace_bp.route('', methods=['GET'])
def list_listings():
    query = Listing.query.filter_by(statut='publie')

    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(Listing.titre.ilike(f'%{search}%'))

    source_type = request.args.get('source_type', '').strip()
    if source_type in ('gnb41', 'externe_zip', 'externe_lien'):
        query = query.filter_by(source_type=source_type)

    categorie_filter = request.args.get('categorie', '').strip()
    if categorie_filter in ('productivite', 'ecommerce', 'jeux', 'utilitaires', 'education', 'sante', 'finance', 'social', 'autre'):
        query = query.filter_by(categorie=categorie_filter)

    prix_min = request.args.get('prix_min', type=int)
    if prix_min is not None:
        query = query.filter(Listing.prix_centimes >= prix_min)

    prix_max = request.args.get('prix_max', type=int)
    if prix_max is not None:
        query = query.filter(Listing.prix_centimes <= prix_max)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)

    pagination = query.order_by(Listing.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'listings': [l.to_dict() for l in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@marketplace_bp.route('/mine', methods=['GET'])
@login_required
def my_listings():
    listings = Listing.query.filter_by(vendeur_id=current_user.id).order_by(Listing.created_at.desc()).all()
    result = []
    for l in listings:
        d = l.to_dict()
        ventes = Purchase.query.filter_by(listing_id=l.id, statut='complete').all()
        d['nb_ventes'] = len(ventes)
        d['revenus_centimes'] = sum(p.montant_vendeur_centimes for p in ventes)
        result.append(d)
    return jsonify(result)


@marketplace_bp.route('/<listing_id>', methods=['GET'])
def get_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.statut != 'publie':
        visible = current_user.is_authenticated and (current_user.id == listing.vendeur_id or _est_moderateur())
        if not visible:
            return jsonify({'error': 'Annonce introuvable'}), 404
    return jsonify(listing.to_dict())


@marketplace_bp.route('', methods=['POST'])
@login_required
def create_listing():
    depuis_24h = datetime.utcnow() - timedelta(hours=24)
    recent_count = Listing.query.filter(
        Listing.vendeur_id == current_user.id,
        Listing.created_at >= depuis_24h
    ).count()
    if recent_count >= 5:
        return jsonify({'error': 'Limite de 5 publications par 24h atteinte. Reessayez plus tard.'}), 429

    titre = request.form.get('titre')
    description = request.form.get('description')
    prix = request.form.get('prix_centimes')
    source_type = request.form.get('source_type', 'gnb41')
    project_id = request.form.get('project_id')
    lien_externe = request.form.get('lien_externe')
    categorie = request.form.get('categorie', 'autre')
    if categorie not in ('productivite', 'ecommerce', 'jeux', 'utilitaires', 'education', 'sante', 'finance', 'social', 'autre'):
        categorie = 'autre'
    tags = request.form.get('tags', '').strip()[:300] or None

    if not titre or not description or not prix:
        return jsonify({'error': 'titre, description et prix_centimes requis'}), 400

    if request.form.get('droits_certifies') != '1':
        return jsonify({'error': 'Vous devez certifier détenir les droits sur cette application.'}), 400

    from app.services.marques import marques_detectees
    marques = marques_detectees(titre, description, request.form.get('tags', ''))
    justification = (request.form.get('justification') or '').strip()[:2000]
    statut_initial = 'publie'
    if marques:
        if len(justification) < 20:
            return jsonify({
                'error': f"« {marques[0]} » est une marque protégée. Pour publier cette application, joignez une justification (licence ou autorisation du titulaire des droits) : elle sera examinée avant sa mise en ligne.",
                'code': 'marque_detectee',
                'marques': marques
            }), 409
        statut_initial = 'en_revue'

    signaux = []
    try:
        from app.services.signaux_moderation import signaux_suspects
        nb_ventes = (Purchase.query.join(Listing, Purchase.listing_id == Listing.id)
                     .filter(Listing.vendeur_id == current_user.id, Purchase.statut == 'complete')
                     .count())
        signaux = signaux_suspects(
            titre, description, request.form.get('tags', ''),
            lien_externe if source_type == 'externe_lien' else None,
            source_type, getattr(current_user, 'created_at', None), nb_ventes)
    except Exception:
        db.session.rollback()
        signaux = []
    if signaux and statut_initial == 'publie':
        statut_initial = 'en_revue'

    try:
        prix_centimes = int(prix)
        if prix_centimes < 0:
            raise ValueError
    except ValueError:
        return jsonify({'error': 'prix_centimes doit etre un entier positif'}), 400

    if source_type not in ('gnb41', 'externe_zip', 'externe_lien'):
        return jsonify({'error': 'source_type invalide'}), 400

    fichier_zip_path = None
    favicon_url = None

    if source_type == 'gnb41':
        if not project_id:
            return jsonify({'error': 'project_id requis pour source_type=gnb41'}), 400
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'error': 'Projet introuvable'}), 404

    elif source_type == 'externe_zip':
        if 'fichier' not in request.files:
            return jsonify({'error': 'fichier zip requis pour source_type=externe_zip'}), 400
        file = request.files['fichier']
        if file.filename == '' or not _allowed_file(file.filename):
            return jsonify({'error': 'Fichier .zip valide requis'}), 400
        filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        filepath = os.path.join(_upload_dir(), filename)
        file.save(filepath)
        fichier_zip_path = filename
        project_id = None

    elif source_type == 'externe_lien':
        if not lien_externe:
            return jsonify({'error': 'lien_externe requis pour source_type=externe_lien'}), 400
        lien_externe = lien_externe.strip()
        if lien_externe and ':' not in lien_externe.split('/')[0]:
            lien_externe = 'https://' + lien_externe
        if not lien_externe.lower().startswith(('http://', 'https://')):
            return jsonify({'error': 'Le lien doit commencer par http:// ou https://'}), 400
        project_id = None
        try:
            domain = urlparse(lien_externe).netloc
            if domain:
                favicon_url = f'https://www.google.com/s2/favicons?domain={domain}&sz=128'
        except Exception:
            favicon_url = None

    image_url = None
    if 'image' in request.files and request.files['image'].filename != '':
        img_file = request.files['image']
        if _allowed_image(img_file.filename):
            img_filename = f"{uuid.uuid4()}_{secure_filename(img_file.filename)}"
            img_path = os.path.join(_images_dir(), img_filename)
            img_file.save(img_path)
            try:
                with Image.open(img_path) as pil_img:
                    pil_img = pil_img.convert('RGB') if pil_img.mode in ('RGBA', 'P') else pil_img
                    pil_img.thumbnail((1200, 1200))
                    pil_img.save(img_path, optimize=True, quality=80)
            except Exception:
                pass
            image_url = f'/api/marketplace/uploads/images/{img_filename}'

    if image_url is None and source_type == 'externe_lien' and lien_externe:
        image_url = f'https://api.microlink.io/?url={lien_externe}&screenshot=true&meta=false&embed=screenshot.url'

    listing = Listing(
        vendeur_id=current_user.id,
        project_id=project_id,
        titre=titre,
        description=description,
        prix_centimes=prix_centimes,
        source_type=source_type,
        fichier_zip_path=fichier_zip_path,
        lien_externe=lien_externe,
        favicon_url=favicon_url,
        image_url=image_url,
        categorie=categorie,
        tags=tags,
        statut=statut_initial,
        droits_certifies_at=datetime.utcnow()
    )
    db.session.add(listing)
    db.session.flush()
    if statut_initial == 'en_revue':
        from app.models.listing_review import ListingReview
        db.session.add(ListingReview(
            listing_id=listing.id, listing_titre=(listing.titre or '')[:120], vendeur_id=current_user.id,
            motif='marque_detectee' if marques else 'signal_auto',
            terme=(', '.join(marques) if marques else ' ; '.join(signaux))[:120],
            justification=justification or ('Détection automatique : ' + ' ; '.join(signaux))[:2000],
            statut='en_attente'))
    db.session.commit()

    if statut_initial == 'en_revue' and not marques:
        _notifier_vendeur(
            current_user.id, "Annonce en cours d'examen",
            f"Votre annonce « {listing.titre} » sera examinée avant sa mise en ligne.")
        _notifier_admins(
            'Annonce à examiner',
            f"« {listing.titre} » : {' ; '.join(signaux)}. Vérification manuelle requise.")
    elif statut_initial == 'en_revue':
        _notifier_moderation(listing, marques)
    else:
        _notifier_vendeur(
            current_user.id, 'Annonce publiée',
            f"Votre annonce « {listing.titre} » est maintenant en ligne.")

    return jsonify(listing.to_dict()), 201


@marketplace_bp.route('/<listing_id>', methods=['PUT'])
@login_required
def update_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.vendeur_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json() or {}

    if 'statut' in data and listing.statut not in ('publie', 'suspendu'):
        return jsonify({'error': "Cette annonce est en cours d'examen ou a été retirée : son statut ne peut pas être modifié."}), 403

    if 'titre' in data or 'description' in data:
        from app.services.marques import marques_detectees
        from app.models.listing_review import ListingReview
        nouvelles = marques_detectees(str(data.get('titre', listing.titre)), str(data.get('description', listing.description)), listing.tags or '')
        existantes = marques_detectees(listing.titre, listing.description, listing.tags or '')
        deja_ok = ' | '.join((x.terme or '') for x in ListingReview.query.filter_by(listing_id=listing.id, statut='approuve').all())
        interdites = [m for m in nouvelles if m not in existantes and m not in deja_ok]
        if interdites:
            return jsonify({'error': f"« {interdites[0]} » est une marque protégée : cette modification est refusée. Écrivez à contact@gnb41ia.com avec la preuve de vos droits.", 'code': 'marque_detectee'}), 409

    if 'titre' in data:
        if not data['titre'].strip():
            return jsonify({'error': 'Le titre ne peut pas etre vide'}), 400
        listing.titre = data['titre']

    if 'description' in data:
        if not data['description'].strip():
            return jsonify({'error': 'La description ne peut pas etre vide'}), 400
        listing.description = data['description']

    if 'prix_centimes' in data:
        try:
            prix = int(data['prix_centimes'])
            if prix < 0:
                raise ValueError
            listing.prix_centimes = prix
        except (ValueError, TypeError):
            return jsonify({'error': 'prix_centimes doit etre un entier positif'}), 400

    if 'statut' in data and data['statut'] in ('publie', 'suspendu'):
        listing.statut = data['statut']

    db.session.commit()
    return jsonify(listing.to_dict())


@marketplace_bp.route('/<listing_id>', methods=['DELETE'])
@login_required
def delete_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.vendeur_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403
    if Purchase.query.filter_by(listing_id=listing_id).first():
        # Des achats existent : on retire l'annonce sans effacer l'historique des ventes.
        listing.statut = 'retire'
        db.session.commit()
        return jsonify({'success': True, 'archived': True})
    db.session.delete(listing)
    db.session.commit()
    return jsonify({'success': True})

@marketplace_bp.route('/<listing_id>/preview', methods=['GET'])
def preview_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    moderation = False
    if listing.statut != 'publie':
        if not _est_moderateur():
            return jsonify({'error': 'Annonce non disponible'}), 404
        moderation = True

    if listing.source_type != 'gnb41' or not listing.project_id:
        return jsonify({'error': "Pas d'apercu disponible pour ce type d'annonce"}), 404

    project = Project.query.get(listing.project_id)
    if not project or not project.code_genere:
        return jsonify({'error': 'Apercu introuvable'}), 404

    try:
        parsed = json.loads(project.code_genere)
        fichiers = parsed.get('fichiers', [])
        html_file = next((f for f in fichiers if f['chemin'].endswith('.html')), None)
        if not html_file:
            return jsonify({'error': 'Aucun fichier HTML dans ce projet'}), 404
        reponse = Response(html_file['contenu'], mimetype='text/html')
        if moderation:
            # Contenu non vérifié : exécuté dans un bac à sable, sans accès à la session du modérateur.
            reponse.headers['Content-Security-Policy'] = 'sandbox allow-scripts'
            reponse.headers['Cache-Control'] = 'no-store'
            reponse.headers['X-Content-Type-Options'] = 'nosniff'
        return reponse
    except (json.JSONDecodeError, KeyError):
        return jsonify({'error': "Erreur lors de la lecture de l'apercu"}), 500

@marketplace_bp.route('/uploads/images/<filename>', methods=['GET'])
def serve_listing_image(filename):
    return send_from_directory(_images_dir(), filename)


def _fedapay_base_url():
    env = os.environ.get('FEDAPAY_ENVIRONMENT', 'sandbox').strip()
    return 'https://api.fedapay.com' if env == 'live' else 'https://sandbox-api.fedapay.com'


def _fedapay_headers():
    key = os.environ.get('FEDAPAY_SECRET_KEY', '').strip()
    return {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}


@marketplace_bp.route('/<listing_id>/purchase', methods=['POST'])
@login_required
def create_purchase(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    if listing.statut != 'publie':
        return jsonify({'error': "Cette annonce n'est plus disponible"}), 400

    if listing.vendeur_id == current_user.id:
        return jsonify({'error': 'Vous ne pouvez pas acheter votre propre application'}), 400

    existing = Purchase.query.filter_by(listing_id=listing_id, acheteur_id=current_user.id, statut='complete').first()
    if existing:
        return jsonify({'error': 'Vous avez deja achete cette application'}), 409

    commission = round(listing.prix_centimes * listing.commission_pourcentage / 100)
    montant_vendeur = listing.prix_centimes - commission

    purchase = Purchase(
        listing_id=listing_id,
        acheteur_id=current_user.id,
        prix_paye_centimes=listing.prix_centimes,
        commission_centimes=commission,
        montant_vendeur_centimes=montant_vendeur,
        statut='en_attente'
    )
    db.session.add(purchase)
    db.session.commit()

    try:
        montant_xof = max(round(listing.prix_centimes / 100 * 655), 100)
        response = requests.post(
            f'{_fedapay_base_url()}/v1/transactions',
            headers=_fedapay_headers(),
            json={
                'description': f'GNB41 IA - {listing.titre}',
                'amount': montant_xof,
                'currency': {'iso': 'XOF'},
                'callback_url': f'http://localhost:5173/marketplace-callback?purchase_id={purchase.id}',
                'customer': {
                    'email': current_user.email,
                    'firstname': current_user.username,
                    'lastname': '.'
                }
            },
            timeout=30
        )
        data = response.json()
        if 'v1/transaction' not in data:
            raise ValueError(data.get('message', 'Reponse FedaPay invalide'))

        transaction = data['v1/transaction']
        purchase.stripe_session_id = str(transaction['id'])
        db.session.commit()

        return jsonify({
            'purchase': purchase.to_dict(),
            'payment_url': transaction['payment_url'],
            'transaction_id': transaction['id']
        }), 201
    except Exception as e:
        purchase.statut = 'erreur'
        db.session.commit()
        return jsonify({'error': f'Erreur lors de la creation du paiement: {str(e)}'}), 500


@marketplace_bp.route('/purchase/<purchase_id>/verify', methods=['GET'])
@login_required
def verify_purchase(purchase_id):
    purchase = Purchase.query.get_or_404(purchase_id)
    if purchase.acheteur_id != current_user.id:
        return jsonify({'error': 'Non autorise'}), 403

    if purchase.statut == 'complete':
        return jsonify(purchase.to_dict())

    if not purchase.stripe_session_id:
        return jsonify({'error': 'Aucune transaction associee'}), 400

    try:
        response = requests.get(
            f'{_fedapay_base_url()}/v1/transactions/{purchase.stripe_session_id}',
            headers=_fedapay_headers(),
            timeout=30
        )
        data = response.json()
        transaction = data.get('v1/transaction', {})
        statut_fedapay = transaction.get('status')

        if statut_fedapay == 'approved':
            purchase.statut = 'complete'
            db.session.commit()
            listing_vendu = Listing.query.get(purchase.listing_id)
            if listing_vendu:
                envoyer_notification(
                    user_id=listing_vendu.vendeur_id,
                    type='vente',
                    titre='Nouvelle vente !',
                    message=f'Votre application "{listing_vendu.titre}" vient d\'etre achetee.',
                    lien=f'/marketplace/mes-ventes'
                )
                try:
                    envoyer_notification(
                        user_id=purchase.acheteur_id,
                        type='achat',
                        titre='Achat confirmé',
                        message=f'Votre achat de "{listing_vendu.titre}" est confirmé.',
                        lien='/marketplace'
                    )
                except Exception:
                    db.session.rollback()
        elif statut_fedapay in ('declined', 'canceled'):
            purchase.statut = 'echoue'
            db.session.commit()

        return jsonify(purchase.to_dict())
    except Exception as e:
        return jsonify({'error': f'Erreur lors de la verification: {str(e)}'}), 500


@marketplace_bp.route('/mine-purchases', methods=['GET'])
@login_required
def my_purchases():
    purchases = Purchase.query.filter_by(acheteur_id=current_user.id).order_by(Purchase.created_at.desc()).all()
    return jsonify([p.to_dict() for p in purchases])


@marketplace_bp.route('/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    if not a_permission('finance.voir'):
        return jsonify({'error': 'Non autorisé'}), 403

    total_listings = Listing.query.count()
    listings_publies = Listing.query.filter_by(statut='publie').count()

    ventes_completes = Purchase.query.filter_by(statut='complete').all()
    total_ventes = len(ventes_completes)
    total_commission = sum(p.commission_centimes for p in ventes_completes)
    total_ca = sum(p.prix_paye_centimes for p in ventes_completes)

    dernieres_ventes = Purchase.query.order_by(Purchase.created_at.desc()).limit(10).all()
    ventes_detail = []
    for p in dernieres_ventes:
        listing = Listing.query.get(p.listing_id)
        ventes_detail.append({
            'id': p.id,
            'titre': listing.titre if listing else 'Annonce supprimée',
            'prix_paye_centimes': p.prix_paye_centimes,
            'statut': p.statut,
            'created_at': p.created_at.isoformat()
        })

    return jsonify({
        'total_listings': total_listings,
        'listings_publies': listings_publies,
        'total_ventes': total_ventes,
        'total_commission_centimes': total_commission,
        'total_chiffre_affaires_centimes': total_ca,
        'dernieres_ventes': ventes_detail
    })


MOTIFS_SIGNALEMENT = ('contrefacon', 'contenu_illegal', 'autre')
SEUIL_SIGNALEMENTS = 3


def _est_moderateur():
    return a_permission('moderation.voir')


def _notifier_admins(titre, message):
    """Prévient les modérateurs. Ne doit jamais faire échouer l'action en cours."""
    try:
        cond = User.role.in_(['admin', 'superadmin', 'moderateur'])
        admin_email = os.environ.get('ADMIN_EMAIL', '')
        if admin_email:
            cond = or_(cond, User.email == admin_email)
        for admin in User.query.filter(cond).all():
            try:
                envoyer_notification(admin.id, 'moderation', titre[:200], message)
            except Exception:
                db.session.rollback()
    except Exception:
        db.session.rollback()


def _notifier_vendeur(user_id, titre, message):
    if not user_id:
        return
    try:
        envoyer_notification(user_id, 'moderation', titre[:200], message)
    except Exception:
        db.session.rollback()


def _notifier_moderation(listing, marques):
    """Une marque a été détectée à la publication."""
    _notifier_admins('Annonce à examiner', f"« {listing.titre} » mentionne : {', '.join(marques)}. Justification à vérifier.")
    _notifier_vendeur(listing.vendeur_id, "Annonce en cours d'examen", f"Votre annonce « {listing.titre} » sera examinée avant sa mise en ligne.")


@marketplace_bp.route('/<listing_id>/report', methods=['POST'])
@limiter.limit('10 per hour')
def report_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.statut != 'publie':
        return jsonify({'error': 'Annonce introuvable'}), 404
    data = request.get_json(silent=True) or {}
    motif = data.get('motif')
    if motif not in MOTIFS_SIGNALEMENT:
        return jsonify({'error': 'Motif invalide'}), 400
    details = (data.get('details') or '').strip()[:2000]
    if motif == 'autre' and len(details) < 10:
        return jsonify({'error': 'Précisez votre signalement (10 caractères minimum)'}), 400
    if current_user.is_authenticated:
        if current_user.id == listing.vendeur_id:
            return jsonify({'error': 'Vous ne pouvez pas signaler votre propre annonce'}), 400
        identite, reporter_id, email = current_user.id, current_user.id, None
    else:
        email = (data.get('contact_email') or '').strip().lower()[:255]
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'error': 'Une adresse e-mail valide est requise'}), 400
        identite, reporter_id = email, None

    passe_en_revue = False
    try:
        ouverts = ListingReport.query.filter_by(listing_id=listing.id, statut='nouveau').all()
        identites = {(x.reporter_id or (x.contact_email or '').lower()) for x in ouverts}
        if identite in identites:
            return jsonify({'success': True, 'deja': True}), 200
        db.session.add(ListingReport(
            listing_id=listing.id, listing_titre=(listing.titre or '')[:120],
            reporter_id=reporter_id, contact_email=email, motif=motif, details=details or None,
            statut='nouveau'))
        identites.add(identite)
        if len(identites) >= SEUIL_SIGNALEMENTS:
            passe_en_revue = True
            listing.statut = 'en_revue'
            if not ListingReview.query.filter_by(listing_id=listing.id, statut='en_attente').first():
                db.session.add(ListingReview(
                    listing_id=listing.id, listing_titre=(listing.titre or '')[:120],
                    vendeur_id=listing.vendeur_id, motif='signalement', statut='en_attente'))
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Signalement impossible. Réessayez.'}), 500

    if passe_en_revue:
        _notifier_admins('Annonce signalée', f"« {listing.titre} » a été signalée par {SEUIL_SIGNALEMENTS} personnes et passe en revue.")
        _notifier_vendeur(listing.vendeur_id, "Annonce en cours d'examen", f"Votre annonce « {listing.titre} » a été signalée et sera examinée.")
    return jsonify({'success': True}), 201


@marketplace_bp.route('/admin/reviews', methods=['GET'])
@login_required
def list_reviews():
    if not _est_moderateur():
        return jsonify({'error': 'Non autorisé'}), 403
    statut = request.args.get('statut', 'en_attente')
    if statut not in ('en_attente', 'approuve', 'refuse', 'retire'):
        statut = 'en_attente'
    reviews = ListingReview.query.filter_by(statut=statut).order_by(ListingReview.created_at.desc()).limit(100).all()
    items = []
    for rv in reviews:
        d = rv.to_dict()
        l = Listing.query.get(rv.listing_id)
        d['listing'] = {
            'statut': l.statut, 'description': (l.description or '')[:500], 'prix_centimes': l.prix_centimes,
            'devise': l.devise, 'source_type': l.source_type, 'categorie': l.categorie
        } if l else None
        v = User.query.get(rv.vendeur_id) if rv.vendeur_id else None
        d['vendeur_email'] = v.email if v else None
        reports = ListingReport.query.filter_by(listing_id=rv.listing_id).order_by(ListingReport.created_at.desc()).limit(10).all()
        d['signalements'] = [{'motif': x.motif, 'details': x.details,
                              'created_at': x.created_at.isoformat() if x.created_at else None} for x in reports]
        items.append(d)
    return jsonify({'reviews': items})


@marketplace_bp.route('/admin/reviews/<review_id>/decision', methods=['POST'])
@login_required
def decide_review(review_id):
    if not a_permission('moderation.decider'):
        return jsonify({'error': 'Non autorisé'}), 403
    review = ListingReview.query.get_or_404(review_id)
    if review.statut != 'en_attente':
        return jsonify({'error': 'Ce dossier a déjà été traité'}), 409
    data = request.get_json(silent=True) or {}
    decision = data.get('decision')
    motif = (data.get('motif') or '').strip()[:1000]
    if decision not in ('approuver', 'refuser', 'retirer'):
        return jsonify({'error': 'Décision invalide'}), 400
    if decision != 'approuver' and len(motif) < 5:
        return jsonify({'error': 'Un motif est requis pour refuser ou retirer une annonce'}), 400

    statut_review = {'approuver': 'approuve', 'refuser': 'refuse', 'retirer': 'retire'}[decision]
    statut_listing = {'approuver': 'publie', 'refuser': 'refuse', 'retirer': 'retire'}[decision]
    listing = Listing.query.get(review.listing_id)
    titre = (listing.titre if listing else review.listing_titre) or 'Annonce'
    ancien_statut = listing.statut if listing else None
    try:
        if listing:
            listing.statut = statut_listing
        review.statut = statut_review
        review.decide_par = current_user.id
        review.decision_motif = motif or None
        review.decided_at = datetime.utcnow()
        for rp in ListingReport.query.filter_by(listing_id=review.listing_id, statut='nouveau').all():
            rp.statut = 'traite'
            rp.traite_par = current_user.id
            rp.traite_at = datetime.utcnow()
        audit('moderation.' + decision, 'annonce', review.listing_id,
              avant={'statut': ancien_statut},
              apres={'statut': statut_listing, 'motif': motif or None, 'dossier': review.id})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Décision impossible. Réessayez.'}), 500

    if decision == 'approuver':
        _notifier_vendeur(review.vendeur_id, 'Annonce approuvée', f"Votre annonce « {titre} » est maintenant en ligne.")
    elif decision == 'refuser':
        _notifier_vendeur(review.vendeur_id, 'Annonce refusée', f"Votre annonce « {titre} » a été refusée : {motif}")
    else:
        _notifier_vendeur(review.vendeur_id, 'Annonce retirée', f"Votre annonce « {titre} » a été retirée : {motif}")
    return jsonify({'success': True, 'review': review.to_dict()})


@marketplace_bp.route('/admin/listings/<listing_id>/retirer', methods=['POST'])
@login_required
def retirer_annonce(listing_id):
    """Retrait d'office d'une annonce (réclamation d'un titulaire de droits, abus...)."""
    if not a_permission('moderation.decider'):
        return jsonify({'error': 'Non autorisé'}), 403
    listing = Listing.query.get_or_404(listing_id)
    if listing.statut in ('retire', 'refuse'):
        return jsonify({'error': 'Cette annonce est déjà retirée'}), 409
    data = request.get_json(silent=True) or {}
    motif = (data.get('motif') or '').strip()[:1000]
    if len(motif) < 5:
        return jsonify({'error': 'Un motif de 5 caractères minimum est requis'}), 400

    maintenant = datetime.utcnow()
    titre = listing.titre or 'Annonce'
    ancien_statut = listing.statut
    try:
        ouverts = ListingReview.query.filter_by(listing_id=listing.id, statut='en_attente').all()
        for rv in ouverts:
            rv.statut = 'retire'
            rv.decide_par = current_user.id
            rv.decision_motif = motif
            rv.decided_at = maintenant
        if not ouverts:
            db.session.add(ListingReview(
                listing_id=listing.id, listing_titre=titre[:120], vendeur_id=listing.vendeur_id,
                motif='retrait_office', statut='retire', decide_par=current_user.id,
                decision_motif=motif, decided_at=maintenant))
        for rp in ListingReport.query.filter_by(listing_id=listing.id, statut='nouveau').all():
            rp.statut = 'traite'
            rp.traite_par = current_user.id
            rp.traite_at = maintenant
        listing.statut = 'retire'
        audit('annonce.retrait_office', 'annonce', listing.id,
              avant={'statut': ancien_statut}, apres={'statut': 'retire', 'motif': motif})
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Retrait impossible. Réessayez.'}), 500

    _notifier_vendeur(listing.vendeur_id, 'Annonce retirée', f"Votre annonce « {titre} » a été retirée : {motif}")
    return jsonify({'success': True})


@marketplace_bp.route('/admin/suspects', methods=['GET'])
@login_required
def annonces_suspectes():
    # Annonces déjà publiées qui présentent les signaux de la modération automatique.
    if not _est_moderateur():
        return jsonify({'error': 'Non autorisé'}), 403
    from app.services.signaux_moderation import signaux_suspects
    resultats = []
    for l in Listing.query.filter(Listing.statut == 'publie').limit(500).all():
        try:
            source = getattr(l, 'source_type', None) or ('externe_lien' if l.lien_externe else 'gnb41')
            vendeur = User.query.get(l.vendeur_id)
            nb_ventes = (Purchase.query.join(Listing, Purchase.listing_id == Listing.id)
                         .filter(Listing.vendeur_id == l.vendeur_id, Purchase.statut == 'complete')
                         .count())
            signaux = signaux_suspects(
                l.titre, l.description, l.tags,
                l.lien_externe if source == 'externe_lien' else None,
                source, getattr(vendeur, 'created_at', None), nb_ventes)
            if signaux:
                resultats.append({
                    'id': l.id, 'titre': l.titre, 'vendeur': getattr(vendeur, 'username', None),
                    'lien': l.lien_externe, 'signaux': signaux})
        except Exception:
            db.session.rollback()
    return jsonify({'total': len(resultats), 'annonces': resultats})
