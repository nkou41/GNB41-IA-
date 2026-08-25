from app.models.workspace import WorkspaceMember

ROLE_OWNER = 'owner'
ROLE_EDITOR = 'editeur'
ROLE_VIEWER = 'lecteur'
VALID_ROLES = (ROLE_OWNER, ROLE_EDITOR, ROLE_VIEWER)

def get_role(workspace_id, user_id):
    member = WorkspaceMember.query.filter_by(workspace_id=workspace_id, user_id=user_id).first()
    return member.role if member else None

def can_edit(role):
    return role in (ROLE_OWNER, ROLE_EDITOR)

def can_manage_members(role):
    return role == ROLE_OWNER


def log_activity(workspace_id, user_id, action, details=None):
    from app import db
    from app.models.activity_log import ActivityLog
    entry = ActivityLog(workspace_id=workspace_id, user_id=user_id, action=action, details=details)
    db.session.add(entry)
