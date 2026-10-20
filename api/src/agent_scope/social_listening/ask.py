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
    pen="""Two families of writes on this desk. You can **set a post's angle and status** with social_listening_update_post: a suggestedAngle is two or three sentences on how a reply from this site would belong in that thread (the stance, what to lead with, what not to pitch), never the reply itself; the user writes every reply in their own words. Statuses are to_reply, drafted, replied, skipped and rejected; move a post the user waves off to skipped, one they call a wrong match to rejected, and back to to_reply if they change their mind. You can **grow the list of lines** with social_listening_save_queries. A brand or competitor is watched by a line like any other.

You can also **write a note for later tasks**. Use save_note when the user states a standing rule: a subreddit to avoid, a tone to keep, a competitor never to name. Notes are in the user's words.

Everything else here is a read. When the user asks you to post a finished reply, load the Social desk: it posts that exact text from their own Reddit, LinkedIn or GitHub account once they approve it, and you then mark the post replied. Never post text the user has not seen. For an X post, give the user a reply link instead, https://x.com/intent/post?in_reply_to=<the number after /status/ in the post url>&text=<the url-encoded reply>: it opens X with the reply filled in and they press Post. X refuses replies sent through its API to people who did not mention the user. Other platforms stay manual: the user copies their text from this desk.""",
    extra=[
        "**Answer analytical questions with SQL** over social_listening_post joined to social_post: counts, per-status, per-platform and per-line splits. For anything heavier, such as trends, clusters or models over the posts, load the Analytics desk; never walk posts to compute a number.",
        "**Runs happen only when the user presses Run now** on the desk, on their machine. There is no tool for it here and no schedule. If the posts look stale, check social_listening_run and point at that button.",
        "**A line whose posts the user keeps rejecting, or that surfaces nothing run after run, needs rewording.** Compare its posts by status and suggest a sharper sentence that says who is posting and what they want.",
    ],
    elsewhere=[
        "Writing a post or article from what you learn here → **Content**.",
        "Charting or modelling the posts → **Analytics**.",
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
    limits={"maxTurns": 60},
    system_prompt=ask_prompt(ASK),
)
