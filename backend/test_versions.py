import sys, json, copy
from datetime import datetime, timedelta
from app import create_app, db
from app.models.project import Project
from app.models.project_version import ProjectVersion

action = sys.argv[1] if len(sys.argv) > 1 else ''
nom = sys.argv[2] if len(sys.argv) > 2 else ''
if action not in ('ajouter', 'nettoyer') or not nom:
    print('Usage : python test_versions.py ajouter|nettoyer "Nom du projet"')
    sys.exit(1)

app = create_app()
with app.app_context():
    url = db.engine.url
    print('Base :', url.drivername, url.host or '(fichier local)')
    projets = Project.query.filter_by(nom=nom).all()
    if len(projets) != 1:
        print(f'{len(projets)} projet(s) nommé(s) "{nom}" : il en faut exactement un.')
        sys.exit(1)
    p = projets[0]
    if p.est_deploye:
        print('Ce projet est publié : refus.')
        sys.exit(1)
    print('Projet :', p.nom, '| id', p.id)
    if input('Tapez OUI pour continuer : ').strip() != 'OUI':
        print('Annulé.')
        sys.exit(0)

    if action == 'nettoyer':
        n = ProjectVersion.query.filter(
            ProjectVersion.project_id == p.id,
            ProjectVersion.prompt.like('[TEST]%')
        ).delete(synchronize_session=False)
        db.session.commit()
        print(n, 'version(s) de test supprimée(s).')
        sys.exit(0)

    try:
        data = json.loads(p.code_genere)
        fichiers = data['fichiers']
    except Exception:
        print('Code du projet illisible : rien écrit.')
        sys.exit(1)

    def code(modif=None):
        d = copy.deepcopy(data)
        if modif:
            modif(d['fichiers'])
        return json.dumps(d, ensure_ascii=False, indent=2)

    def modif(fs):
        cible = next((f for f in fs if f['chemin'].endswith('.js')), fs[0])
        cible['contenu'] += '\n// ligne ajoutée pour le test'
        fs.append({'chemin': 'test.js', 'contenu': "console.log('test');"})

    maintenant = datetime.utcnow()
    versions = [
        dict(prompt='[TEST] Première version', statut='pret', code_genere=code(),
             duree_generation_ms=4200, created_at=maintenant - timedelta(hours=3)),
        dict(prompt='[TEST] Ajoute un fichier de test et une ligne au script', statut='pret',
             code_genere=code(modif), duree_generation_ms=6800, created_at=maintenant - timedelta(hours=2)),
        dict(prompt='[TEST] Essai qui a échoué', statut='erreur', code_genere=code(),
             erreur_message='Échec simulé pour le test', duree_generation_ms=1500,
             created_at=maintenant - timedelta(hours=1)),
    ]
    try:
        for v in versions:
            db.session.add(ProjectVersion(project_id=p.id, provider=p.provider,
                                          agent_type='creation', **v))
        db.session.commit()
        print('3 versions de test ajoutées.')
    except Exception as e:
        db.session.rollback()
        print('Échec, rien écrit :', e)
