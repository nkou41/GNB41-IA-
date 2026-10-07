import re
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlparse


def _norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode('ascii').lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


_MOTS_CONNEXION = [_norm(m) for m in [
    'sign in', 'signin', 'log in', 'login', 'logon', 'password', 'mot de passe',
    'identifiants', 'verify your account', 'verification de compte',
    'verifier votre compte', 'compte suspendu', 'account suspended',
    'code de verification',
]]

_RACCOURCIS = {'bit.ly', 'tinyurl.com', 'cutt.ly', 't.co', 'goo.gl', 'ow.ly',
               'is.gd', 'rb.gy', 'shorturl.at', 'tiny.cc', 't.ly', 's.id'}

_HOTE_SUSPECT = re.compile(r'(login|signin|sign-in|verify|password|connexion|webmail|secure|account)')


def _hote(lien):
    url = (lien or '').strip()
    if '://' not in url:
        url = '//' + url
    try:
        return (urlparse(url).hostname or '').lower()
    except Exception:
        return ''


def _raison_lien(hote):
    if not hote:
        return None
    if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', hote):
        return "adresse IP au lieu d'un nom de domaine"
    if hote in _RACCOURCIS:
        return 'lien raccourci'
    if 'xn--' in hote:
        return 'nom de domaine déguisé (punycode)'
    if _HOTE_SUSPECT.search(hote):
        return 'nom de domaine évoquant une connexion'
    return None


def signaux_suspects(titre, description, tags, lien, source_type, compte_cree_le, nb_ventes):
    # Retourne les signaux qui justifient un examen manuel avant publication.
    signaux = []
    texte = ' ' + _norm(' '.join([titre or '', description or '', tags or '', lien or ''])) + ' '
    mots = [m for m in _MOTS_CONNEXION if ' ' + m + ' ' in texte]
    try:
        recent = (compte_cree_le is not None and nb_ventes == 0
                  and datetime.utcnow() - compte_cree_le < timedelta(days=14))
    except Exception:
        recent = False
    if mots and (source_type != 'gnb41' or recent):
        signaux.append('vocabulaire de page de connexion (' + ', '.join(mots[:3]) + ')')
    if lien:
        raison = _raison_lien(_hote(lien))
        if raison:
            signaux.append('lien suspect : ' + raison)
    return signaux
