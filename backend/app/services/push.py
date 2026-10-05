import json
import logging
import os

from app import db
from app.models.push_subscription import PushSubscription

log = logging.getLogger(__name__)


def envoyer_push(user_id, titre, message, lien=None):
    """Envoie une notification push a tous les appareils de l'utilisateur.
    Retourne le nombre d'envois reussis. Ne leve jamais d'exception."""
    private_key = os.environ.get('VAPID_PRIVATE_KEY')
    subject = os.environ.get('VAPID_SUBJECT', 'mailto:contact@example.com')
    if not private_key:
        return 0
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        log.warning('pywebpush non installe')
        return 0

    payload = json.dumps({'title': titre, 'body': message, 'url': lien or '/'})
    envoyes = 0
    try:
        subs = PushSubscription.query.filter_by(user_id=user_id).all()
        for s in subs:
            try:
                webpush(
                    subscription_info={
                        'endpoint': s.endpoint,
                        'keys': {'p256dh': s.p256dh, 'auth': s.auth},
                    },
                    data=payload,
                    vapid_private_key=private_key,
                    vapid_claims={'sub': subject},
                    ttl=86400,
                    timeout=10,
                )
                envoyes += 1
            except WebPushException as e:
                code = getattr(getattr(e, 'response', None), 'status_code', None)
                if code in (404, 410):
                    db.session.delete(s)  # appareil desinscrit
                else:
                    log.warning('Echec push: %s', e)
            except Exception as e:
                log.warning('Echec push: %s', e)
        db.session.commit()
    except Exception as e:
        log.warning('Erreur push: %s', e)
        db.session.rollback()
    return envoyes
