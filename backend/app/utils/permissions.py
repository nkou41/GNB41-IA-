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


PLAN_LIMITS = {
    'gratuit': {'max_workspaces': 1, 'max_projects_per_workspace': 3},
    'pro': {'max_workspaces': None, 'max_projects_per_workspace': None},
}

def get_plan_limits(plan):
    return PLAN_LIMITS.get(plan, PLAN_LIMITS['gratuit'])


def check_and_downgrade_plan(user):
    from app import db
    from datetime import datetime
    if user.plan == 'pro' and user.plan_expiry and user.plan_expiry < datetime.utcnow():
        user.plan = 'gratuit'
        user.plan_expiry = None
        db.session.commit()
