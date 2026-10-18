from src.agent_scope.find_leads.ask import scope as ask_find_leads
from src.agent_scope.find_leads.setup import scope as find_leads_setup

ACTIONS = {
    "find-leads-setup": find_leads_setup,
    "ask-find-leads": ask_find_leads,
}
