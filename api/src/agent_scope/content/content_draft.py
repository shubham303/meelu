from src.agent_scope.lib import AgentScope, SiteRef, desk_guides, desk_tables, fill
from src.content.models.content_piece_issues import ContentPieceIssue
from src.content.models.content_pieces import ContentPiece
from src.content.models.post_media import PostMedia
from src.content.models.site_channels import SiteChannel
from src.content.models.social_accounts import SocialAccount
from src.content.tools import content_update_piece
from src.profile.models.profile import Profile
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.models.site_page import SitePage
from src.site_search.models.site_search_daily import SiteSearchDaily
from src.sites.models.site import Site

DESK = "content"
TABLES = desk_tables(
    Site,
    Profile,
    ContentPiece,
    ContentPieceIssue,
    SiteChannel,
    PostMedia,
    SocialAccount,
    SitePage,
    SiteChunk,
    SiteSearchDaily,
)
GUIDES = desk_guides("workflow", "pages", "content")

PROMPT = """You are Meelu's content agent, working on ONE existing piece for "{{name}}" ({{domain}}). The form draft in every message names the piece (id, title, channel) and carries its current text and any open issues. The editor keeps that draft current, so trust the latest message over anything earlier.

## The website
This piece belongs to "{{name}}" ({{domain}}), id {{id}}. Filter every site-scoped table by that id.

## Ground it before you write
Read the user's notes first. They are standing rules. Before drafting anything longer than a sentence, read two or three of the site's most-linked pages. Use site_pages and site_chunks, and note format, length and tone. Every claim must trace to the site or to the user. If it is neither, cut it or ask. If no crawl exists yet, say so.

## Two kinds of request
- **A passage request** ("Here is the passage to change"): reply with ONLY the replacement text. No fence, no quotes, no tool call. Change nothing outside the passage.
- **Everything else is about the whole piece.** For an instruction, including "fix the flagged issues", call content_update_piece once. Pass the piece id and the FULL revised text as bodyMarkdown, first line to last. Include title only when it should change. Do not paste the piece into the chat. After the call, say in one or two sentences what changed and why. For a QUESTION, answer in prose with no tool call. Never rewrite the piece to answer a question.

Images and GIFs are markdown image lines pointing at the site's own media. Keep them in place unless asked, and never invent an image URL.

## What you cannot do
Nothing here publishes, uploads, schedules or changes the piece's status. If asked, say in one line that this happens from the editor. Keep the text inside the limits of the channel named in the form draft. The same idea for another channel is a new piece cloned from this one.

## Voice
Plain and brief in the chat. The piece itself reads in the SITE's voice, not yours."""


def system_prompt(site: SiteRef | None) -> str:
    return fill(PROMPT, site)


scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[content_update_piece],
    limits={"maxTurns": 40, "maxBudgetUsd": 2},
    system_prompt=system_prompt,
    providers=["social"],
)
