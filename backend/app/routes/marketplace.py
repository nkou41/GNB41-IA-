import os
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
        tags=tags
    )
    db.session.add(listing)
    db.session.commit()

    return jsonify(listing.to_dict()), 201


@marketplace_bp.route('/<listing_id>', methods=['PUT'])
@login_required
def update_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.vendeur_id != current_user.id:
        return jsonify({'error': 'Non autorisé'}), 403

    data = request.get_json() or {}

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
    db.session.delete(listing)
    db.session.commit()
    return jsonify({'success': True})

@marketplace_bp.route('/<listing_id>/preview', methods=['GET'])
def preview_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.statut != 'publie':
        return jsonify({'error': 'Annonce non disponible'}), 404

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
        return Response(html_file['contenu'], mimetype='text/html')
    except (json.JSONDecodeError, KeyError):
        return jsonify({'error': "Erreur lors de la lecture de l'apercu"}), 500

@marketplace_bp.route('/uploads/images/<filename>', methods=['GET'])
def serve_listing_image(filename):
    return send_from_directory(_images_dir(), filename)


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

    return jsonify(purchase.to_dict()), 201


@marketplace_bp.route('/mine-purchases', methods=['GET'])
@login_required
def my_purchases():
    purchases = Purchase.query.filter_by(acheteur_id=current_user.id).order_by(Purchase.created_at.desc()).all()
    return jsonify([p.to_dict() for p in purchases])


@marketplace_bp.route('/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    admin_email = os.environ.get('ADMIN_EMAIL', '')
    if not admin_email or current_user.email != admin_email:
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
