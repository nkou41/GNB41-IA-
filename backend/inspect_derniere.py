from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.models.project_version import ProjectVersion

app = create_app()
with app.app_context():
    v = ProjectVersion.query.order_by(ProjectVersion.created_at.desc()).first()
    print("Statut:", v.statut, "- agent_type:", v.agent_type, "- provider:", v.provider)
    print("Comprehension:", repr(v.comprehension))
    print("Plan:", repr(v.plan))
    print("Suggestions:", repr(v.suggestions))
    print("Erreur:", v.erreur_message)
