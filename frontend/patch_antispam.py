with open('app/routes/marketplace.py', 'r') as f:
    content = f.read()

old_import = "from app.models.project import Project"
new_import = "from app.models.project import Project\nfrom datetime import datetime, timedelta"

if old_import in content:
    content = content.replace(old_import, new_import)
    print("1/2 OK: import datetime ajoute")
else:
    print("1/2 ERREUR: import Project non trouve")

old_check = """@marketplace_bp.route('', methods=['POST'])
@login_required
def create_listing():
    titre = request.form.get('titre')"""

new_check = """@marketplace_bp.route('', methods=['POST'])
@login_required
def create_listing():
    depuis_24h = datetime.utcnow() - timedelta(hours=24)
    recent_count = Listing.query.filter(
        Listing.vendeur_id == current_user.id,
        Listing.created_at >= depuis_24h
    ).count()
    if recent_count >= 5:
        return jsonify({'error': 'Limite de 5 publications par 24h atteinte. Reessayez plus tard.'}), 429

    titre = request.form.get('titre')"""

if old_check in content:
    content = content.replace(old_check, new_check)
    print("2/2 OK: limite anti-spam ajoutee")
else:
    print("2/2 ERREUR: route create_listing non trouvee")

with open('app/routes/marketplace.py', 'w') as f:
    f.write(content)
