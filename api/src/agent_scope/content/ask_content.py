from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.content.grounding import TABLES_NOTE
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.content.models.content_piece_issues import ContentPieceIssue
from src.content.models.content_pieces import ContentPiece
from src.content.models.post_media import PostMedia
from src.content.tools import content_create_piece, content_update_piece
from src.profile.models.profile import Profile
from src.sites.models.site import Site

DESK = "content"
TABLES = desk_tables(Site, Profile, ContentPiece, ContentPieceIssue, PostMedia)
GUIDES = desk_guides("workflow", "content")

ASK = AskDesk(
    title="Content",
    produces="web pages for this site, each with its title, H1, meta description, slug, target keyword and body",
    pen="""Write and revise pieces. A piece is one web page for this site. Use content_create_piece for a new one and content_update_piece to change one. Everything lands as a draft for the user to review.""",
    extra=[
        "**Nothing here publishes.** Meelu holds the text; the user puts it on the site themselves. There are no social posts on this desk.",
        f"**Write from the data.** {TABLES_NOTE} Choose the target keyword from the Search Console data and the internal links from the crawled pages; never invent a URL.",
    ],
    elsewhere=[
        "Whether a page brought anything → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[content_create_piece, content_update_piece],
    limits={"maxTurns": 60},
    system_prompt=ask_prompt(ASK),
)
