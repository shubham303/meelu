from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.find_leads.setup import DESK, GUIDES, TABLES
from src.agent_scope.lib import AgentScope
from src.find_leads.tools import find_leads_save_briefs, find_leads_update_lead

ASK = AskDesk(
    title="Find Leads",
    produces="a short list of people worth a personal message, each with the reason and a link to reach them",
    pen="""Two writes on this desk. You can **change a lead's status** with find_leads_update_lead: new, contacted or discarded. Move a lead the user says they messaged to contacted and one they wave off to discarded; a discarded person never comes back in a later run. You can **add or reword briefs** with find_leads_save_briefs.

You can also **write a note for later tasks**. Use save_note when the user states a standing rule: a kind of person to skip, a region to stay in, a competitor's customers to leave alone. Notes are in the user's words.

Everything else here is a read. Meelu never sends a message and never stores one; the user opens the profile or email and writes their own.""",
    extra=[
        "**Answer analytical questions with SQL** over lead joined to lead_brief and lead_run: counts per status, per brief, per source. For anything heavier, load the Analytics desk; never walk leads to compute a number.",
        "**Runs happen only when the user presses Find leads** on the desk, on their machine. There is no tool for it here and no schedule. If the list looks stale, check lead_run and point at that button.",
        "**When the user asks what to say to someone, suggest the opening, not the message.** Base it on that lead's reason, evidence and angle; the user writes the message in their own words.",
        "**A brief that keeps finding nobody, or people the user keeps discarding, needs rewording.** Compare its leads by status and suggest a sharper sentence that names who they are and what shows they need the site.",
    ],
    elsewhere=[
        "Public posts worth replying to, rather than people to message → **Social Listening**.",
        "Charting or modelling the leads → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[find_leads_update_lead, find_leads_save_briefs],
    limits={"maxTurns": 60},
    system_prompt=ask_prompt(ASK),
)
