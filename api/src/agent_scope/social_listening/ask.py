from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope
from src.agent_scope.social_listening.setup import DESK, GUIDES, TABLES
from src.social_listening.tools import (
    social_listening_save_queries,
    social_listening_save_targets,
    social_listening_update_post,
)

ASK = AskDesk(
    title="Social Listening",
    produces="a triage of the found posts and a reply angle for each one worth answering",
    pen="""Three families of writes on this desk. You can **set a post's angle and status** with social_listening_update_post: a suggestedAngle is two or three sentences on how a reply from this site would belong in that thread — the stance, what to lead with, what not to pitch — never the reply itself; the user writes every reply in their own words. Move a post the user waves off to skipped, and back to needs_reply if they change their mind. You can **grow the query list** with social_listening_save_queries and **grow the brand and competitor lists** with social_listening_save_targets, both only after the user agrees to the additions.

You can also **write a note for later tasks**. Use save_note when the user states a standing rule — a subreddit to avoid, a tone to keep, a competitor never to name. Notes are in the user's words and saved once they agree to the wording.

Everything else here is a read. Posting a reply happens on the platform itself; the user copies their finished text from this desk.""",
    extra=[
        "**Answer analytical questions with SQL** over social_listening_post — counts, class breakdowns, per-platform splits. For anything heavier, social_listening_download_posts exports a CSV for the Analytics desk; never walk posts to compute a number.",
        "**Runs happen on the user's machine.** The desk's Run button fetches and classifies; there is no tool for it here. If the posts look stale, check social_listening_run and point at that button.",
        "**A praise thread for a competitor is signal, not an invitation.** Recommend no reply where jumping in would read as brand-jacking; suggest a note for the Content desk instead.",
    ],
    elsewhere=[
        "Writing a post or article from what you learn here → **Content**.",
        "Adding a person you found here to the lead list → **Lead Management**.",
        "Charting or modelling the exported CSV → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[
        social_listening_update_post,
        social_listening_save_queries,
        social_listening_save_targets,
    ],
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    system_prompt=ask_prompt(ASK),
)
