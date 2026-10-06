from app import db, socketio
from app.models.notification import Notification
from app.services.notification_prefs import categorie_active

def envoyer_notification(user_id, type, titre, message, lien=None):
    """
    Cree une notification en base ET la pousse en temps reel si l'utilisateur est connecte.
    """
    if not categorie_active(user_id, type):
        return None

    notif = Notification(
        user_id=user_id,
        type=type,
        titre=titre,
        message=message,
        lien=lien
    )
    db.session.add(notif)
    db.session.commit()

    socketio.emit('notification', notif.to_dict(), room=f'user_{user_id}')

    try:
        from app.services.push import envoyer_push
        envoyer_push(user_id, titre, message, lien)
    except Exception:
        pass

    return notif
