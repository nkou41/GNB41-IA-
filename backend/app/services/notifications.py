from app import db, socketio
from app.models.notification import Notification

def envoyer_notification(user_id, type, titre, message, lien=None):
    """
    Cree une notification en base ET la pousse en temps reel si l'utilisateur est connecte.
    """
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

    return notif
