from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope
from src.agent_scope.social_listening.setup import DESK, GUIDES, TABLES
from src.social_listening.tools import (
    social_listening_save_queries,
    social_listening_update_post,
)

ASK = AskDesk(
    title="Social Listening",
    produces="a triage of the found posts and a reply angle for each one worth answering",
    pen="""Two families of writes on this desk. You can **set a post's angle and status** with social_listening_update_post: a suggestedAngle is two or three sentences on how a reply from this site would belong in that thread (the stance, what to lead with, what not to pitch), never the reply itself; the user writes every reply in their own words. Statuses are to_reply, drafted, replied, skipped and rejected; move a post the user waves off to skipped, one they call a wrong match to rejected, and back to to_reply if they change their mind. You can **grow the list of lines** with social_listening_save_queries, only after the user agrees to the wording. A brand or competitor is watched by a line like any other.

You can also **write a note for later tasks**. Use save_note when the user states a standing rule: a subreddit to avoid, a tone to keep, a competitor never to name. Notes are in the user's words and saved once they agree to the wording.

Everything else here is a read. Posting a reply happens on the platform itself; the user copies their finished text from this desk.""",
    extra=[
        "**Answer analytical questions with SQL** over social_listening_post: counts, drop reasons, per-platform and per-line splits. For anything heavier, social_listening_download_posts exports a CSV for the Analytics desk; never walk posts to compute a number.",
        "**Runs happen only when the user presses Run now** on the desk, on their machine. There is no tool for it here and no schedule. If the posts look stale, check social_listening_run and point at that button.",
        "**A line that finds many posts but keeps none needs rewording.** Compare its found and kept counts and suggest a sharper sentence that says who is posting and what they want.",
    ],
    elsewhere=[
        "Writing a post or article from what you learn here → **Content**.",
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
    ],
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    system_prompt=ask_prompt(ASK),
)
