from app import db
from app.models.notification_preference import NotificationPreference

CATEGORIES = [
    {'id': 'boutique', 'label': 'Boutique',
     'description': 'Annonces publiées, refusées ou retirées, ventes et achats',
     'types': ['moderation', 'vente', 'achat']},
    {'id': 'abonnement', 'label': 'Abonnement et crédits',
     'description': 'Paiements, expiration de l’abonnement et alertes de crédits',
     'types': ['abonnement', 'credits']},
    {'id': 'workspace', 'label': 'Espaces de travail',
     'description': 'Ajouts et retraits de membres',
     'types': ['workspace']},
]

TYPE_TO_CATEGORIE = {t: c['id'] for c in CATEGORIES for t in c['types']}
IDS = {c['id'] for c in CATEGORIES}


def get_preferences(user_id):
    etat = {c['id']: True for c in CATEGORIES}
    for r in NotificationPreference.query.filter_by(user_id=user_id).all():
        if r.categorie in etat:
            etat[r.categorie] = bool(r.active)
    return etat


def categorie_active(user_id, type_):
    """Vrai si la notification doit être envoyée. En cas de doute, on envoie."""
    cat = TYPE_TO_CATEGORIE.get(type_)
    if not cat:
        return True
    try:
        row = NotificationPreference.query.filter_by(user_id=user_id, categorie=cat).first()
        return True if row is None else bool(row.active)
    except Exception:
        db.session.rollback()
        return True


def set_preference(user_id, categorie, active):
    row = NotificationPreference.query.filter_by(user_id=user_id, categorie=categorie).first()
    if row:
        row.active = bool(active)
    else:
        db.session.add(NotificationPreference(
            user_id=user_id, categorie=categorie, active=bool(active)))
    db.session.commit()
