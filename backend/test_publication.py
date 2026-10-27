import json
from app import db
from app.models.project import Project
from app.models.visite import Visite
from app.routes.project import _generer_slug


def creer_projet(nom='App', titre='E-Commerce - Accueil', deploye=True, **kw):
    code = json.dumps({
        'description': 'Une boutique en ligne. Phrase technique interne.',
        'fichiers': [
            {'chemin': 'index.html',
             'contenu': '<html><head><title>' + titre + '</title></head><body>Bonjour</body></html>'},
            {'chemin': 'style.css', 'contenu': ':root{--color-primary:#4a6bff;}'},
        ],
    })
    p = Project(workspace_id='ws-test', nom=nom, prompt_initial='prompt', statut='pret',
                code_genere=code, est_deploye=deploye, **kw)
    db.session.add(p)
    db.session.commit()
    if deploye:
        p.slug = _generer_slug(p)
        db.session.commit()
    return p


def test_slug_depuis_le_titre_sans_mot_generique(app):
    assert creer_projet().slug == 'e-commerce'


def test_slug_doublon_recoit_un_suffixe(app):
    a = creer_projet()
    b = creer_projet()
    assert a.slug == 'e-commerce'
    assert b.slug != a.slug and b.slug.startswith('e-commerce-')


def test_nom_app_prioritaire_sur_le_titre(app):
    p = creer_projet(nom_app='MonShop')
    assert p.slug == 'monshop'


def test_lien_court_et_balises(client):
    p = creer_projet()
    r = client.get(f'/a/{p.slug}/')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'rel="manifest"' in html
    assert 'name="theme-color"' in html
    assert 'property="og:title" content="E-Commerce"' in html
    assert 'og:image' in html
    assert 'Une boutique en ligne.' in html
    assert 'technique' not in html


def test_ancien_lien_uuid_fonctionne(client):
    p = creer_projet()
    assert client.get(f'/api/projects/{p.id}/live/').status_code == 200


def test_manifest_et_icone(client):
    p = creer_projet(nom_app='MonShop')
    m = client.get(f'/a/{p.slug}/manifest.json').get_json()
    assert m['name'] == 'MonShop' and m['short_name'] == 'MonShop'
    svg = client.get(f'/a/{p.slug}/icon.svg').get_data(as_text=True)
    assert '>M</text>' in svg


def test_image_de_partage(client):
    p = creer_projet()
    r = client.get(f'/a/{p.slug}/og.png')
    assert r.status_code == 200
    assert r.mimetype == 'image/png'
    assert r.data[:4] == b'\x89PNG'


def test_projet_depublie_ou_suspendu_renvoie_404(client):
    non_publie = creer_projet(deploye=False)
    assert client.get(f'/api/projects/{non_publie.id}/live/').status_code == 404
    p = creer_projet()
    p.modere_statut = 'suspendu'
    db.session.commit()
    assert client.get(f'/a/{p.slug}/').status_code == 404


def test_slug_inconnu_renvoie_404(client):
    assert client.get('/a/nexiste-pas/').status_code == 404


def test_visites_ignorent_les_robots(client):
    p = creer_projet()
    client.get(f'/a/{p.slug}/', headers={'User-Agent': 'Mozilla/5.0 Chrome'})
    client.get(f'/a/{p.slug}/', headers={'User-Agent': 'WhatsApp/2.23'})
    client.get(f'/a/{p.slug}/manifest.json', headers={'User-Agent': 'Mozilla/5.0 Chrome'})
    total = sum(v.nombre for v in Visite.query.filter_by(project_id=p.id).all())
    assert total == 1


def test_app_sans_couleur_dans_le_css(client):
    p = creer_projet()
    code = json.loads(p.code_genere)
    code['fichiers'] = [f for f in code['fichiers'] if not f['chemin'].endswith('.css')]
    p.code_genere = json.dumps(code)
    db.session.commit()
    assert client.get(f'/a/{p.slug}/').status_code == 200
    assert client.get(f'/a/{p.slug}/manifest.json').get_json()['theme_color'] == '#4361ee'
    assert client.get(f'/a/{p.slug}/icon.svg').status_code == 200
    assert client.get(f'/a/{p.slug}/og.png').status_code == 200


def test_projet_bloque_en_generation_passe_en_erreur(app):
    from datetime import datetime, timedelta
    from app.routes.project import _reparer_si_bloque
    p = creer_projet(deploye=False)
    p.statut = 'en_generation'
    p.updated_at = datetime.utcnow() - timedelta(minutes=30)
    db.session.commit()
    _reparer_si_bloque(p)
    assert p.statut == 'erreur'
    recent = creer_projet(deploye=False)
    recent.statut = 'en_generation'
    db.session.commit()
    _reparer_si_bloque(recent)
    assert recent.statut == 'en_generation'


def test_liste_repare_les_projets_bloques(app):
    from datetime import datetime, timedelta
    from app.routes.project import _reparer_si_bloque
    p = creer_projet(deploye=False)
    p.statut = 'en_generation'
    p.updated_at = datetime.utcnow() - timedelta(minutes=30)
    db.session.commit()
    projets = Project.query.filter_by(workspace_id=p.workspace_id).all()
    for x in projets:
        _reparer_si_bloque(x)
    assert Project.query.get(p.id).statut == 'erreur'


def test_service_worker_versionne_et_hors_ligne(client):
    p = creer_projet()
    r = client.get(f'/a/{p.slug}/sw.js')
    assert r.status_code == 200
    sw1 = r.get_data(as_text=True)
    assert "caches.match('./index.html')" in sw1
    code = json.loads(p.code_genere)
    code['fichiers'][0]['contenu'] += '<!-- v2 -->'
    p.code_genere = json.dumps(code)
    db.session.commit()
    sw2 = client.get(f'/a/{p.slug}/sw.js').get_data(as_text=True)
    assert sw1 != sw2
