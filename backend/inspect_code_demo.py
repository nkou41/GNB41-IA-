import json
from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.models.project_version import ProjectVersion

app = create_app()
with app.app_context():
    v = ProjectVersion.query.order_by(ProjectVersion.created_at.desc()).first()
    code = json.loads(v.code_genere) if v.code_genere else {}
    fichiers = [f.get('chemin') for f in code.get('fichiers', [])]
    print("Fichiers:", fichiers)
    print("Stack:", code.get('stack'))
