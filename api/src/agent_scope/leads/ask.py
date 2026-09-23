from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.leads.models.campaign import LeadCampaign
from src.leads.models.lead import Lead
from src.leads.models.run import LeadRun
from src.leads.tools import (
    leads_save_campaign,
    leads_update_lead,
)
from src.profile.models.profile import Profile
from src.sites.models.site import Site

DESK = "leads"
TABLES = desk_tables(
    Site,
    Profile,
    LeadCampaign,
    LeadRun,
    Lead,
)
GUIDES = desk_guides("leads")

ASK = AskDesk(
    title="Lead Management",
    produces="an honest, well-filtered lead list the user can act on outside Meelu",
    pen="""Two families of writes on this desk. You can **shape a campaign** with leads_save_campaign — the brief is the user's standing search in the user's words: audience, sources, schedule; propose, take corrections, save on a clear go-ahead. You can **keep a lead honest** with leads_update_lead: fields, evidence, fit, and stage. The stages are the funnel of filters — found is raw, qualified passed the fit check, shortlisted is the curated list; move a lead to shortlisted only when it clears the filters the user asked for.

You can also **write a note for later tasks** with save_note when the user states a standing rule, in their words, once they agree to the wording.

Everything else here is a read. **This desk ends at the list.** Meelu does not send email, track replies, or manage what happens after a lead is shortlisted; the user contacts leads with their own tools, from the exported list.""",
    extra=[
        "**Answer analytical questions with SQL** over the lead tables — stage counts, per-campaign splits, per-source yield. For anything heavier, leads_download_leads exports a CSV for the Analytics desk; never walk leads to compute a number.",
        "**Never invent contact details.** An email exists only if a fetched page showed it; a lead without one carries its platform handles instead.",
        "**Curation is filtering, not padding.** A shortlist earns its rows: fit score, evidence, and the user's own criteria — when in doubt, leave the lead at qualified and say why.",
    ],
    elsewhere=[
        "Finding people who are asking for what the site sells → **Social Listening**.",
        "Writing a page or post from what lead research surfaces → **Content**.",
        "Charting or modelling the exported CSV → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[leads_save_campaign, leads_update_lead],
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    system_prompt=ask_prompt(ASK),
)
