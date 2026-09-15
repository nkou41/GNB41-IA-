from app import create_app, db
from app.models.plan import Plan
import json

app = create_app()

PLANS = [
    dict(slug='gratuit', nom='Gratuit', prix_usd=0, prix_xof=0, credits=1,
         description='Pour decouvrir la plateforme.',
         features=['3 projets maximum', '1 espace de travail', 'Generation IA standard'],
         ordre=1, populaire=False, actif=True, sur_devis=False),
    dict(slug='starter', nom='Starter', prix_usd=16, prix_xof=9600, credits=80,
         description='Pour demarrer serieusement.',
         features=['Projets illimites', '1 espace de travail', 'Collaborateurs illimites avec credits partages'],
         ordre=2, populaire=False, actif=True, sur_devis=False),
    dict(slug='builder', nom='Builder', prix_usd=40, prix_xof=24000, credits=200,
         description='Le plus populaire.',
         features=['Tout Starter inclus', 'Espaces de travail illimites', 'Deploiement en un clic', 'Domaine personnalise'],
         ordre=3, populaire=True, actif=True, sur_devis=False),
    dict(slug='pro', nom='Pro', prix_usd=80, prix_xof=48000, credits=406,
         description='Pour les equipes exigeantes.',
         features=['Tout Builder inclus', 'Integrations incluses', 'Flux de travail avance', 'Choisissez votre modele IA'],
         ordre=4, populaire=False, actif=True, sur_devis=False),
    dict(slug='elite', nom='Elite', prix_usd=160, prix_xof=96000, credits=812,
         description='Le plus complet.',
         features=['Tout Pro inclus', 'Support prioritaire', 'Acces anticipe aux nouvelles fonctionnalites', 'Historique des versions'],
         ordre=5, populaire=False, actif=True, sur_devis=False),
    dict(slug='entreprise', nom='Entreprise', prix_usd=0, prix_xof=0, credits=None,
         description='Gouvernance et securite a grande echelle.',
         features=['SSO', 'Integrations dediees', 'Support dedie', 'Contrat sur mesure'],
         ordre=6, populaire=False, actif=True, sur_devis=True),
]

with app.app_context():
    for p in PLANS:
        existing = Plan.query.filter_by(slug=p['slug']).first()
        features_json = json.dumps(p.pop('features'))
        if existing:
            for k, v in p.items():
                setattr(existing, k, v)
            existing.features = features_json
            print(f"MAJ: {p['slug']}")
        else:
            plan = Plan(features=features_json, **p)
            db.session.add(plan)
            print(f"CREE: {p['slug']}")
    db.session.commit()
    print("OK: plans initialises")
