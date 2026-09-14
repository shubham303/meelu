from src.agent_scope.outreach.compose_reply import scope as compose_reply
from src.agent_scope.outreach.edit_project import scope as edit_project
from src.agent_scope.outreach.edit_prospect import scope as edit_prospect
from src.agent_scope.outreach.outreach_email import scope as outreach_email
from src.agent_scope.outreach.project import scope as project
from src.agent_scope.outreach.project_assist import scope as project_assist
from src.agent_scope.outreach.run_campaign import scope as run_campaign

ACTIONS = {
    "outreach-email": outreach_email,
    "project": project,
    "edit-project": edit_project,
    "project-assist": project_assist,
    "run-campaign": run_campaign,
    "edit-prospect": edit_prospect,
    "compose-reply": compose_reply,
}
