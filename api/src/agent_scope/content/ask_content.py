from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.content.models.content_piece_issues import ContentPieceIssue
from src.content.models.content_pieces import ContentPiece
from src.content.models.post_media import PostMedia
from src.content.models.site_channels import SiteChannel
from src.content.tools import content_create_piece, content_update_piece
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
    SitePage,
    SiteChunk,
    SiteSearchDaily,
)
GUIDES = desk_guides("workflow", "pages", "content")

ASK = AskDesk(
    title="Content",
    produces="pieces, each written for one channel",
    pen="""Write and revise pieces. A piece is one text for ONE channel, with its own status. Use content_create_piece for a new one and content_update_piece to change one. Everything lands as a draft for the user to review.""",
    extra=[
        "**Nothing here sends.** Meelu holds the text; the user posts it themselves wherever it goes.",
        "Read the site's own copy of each channel's rules in the site_channels table. The user's version beats any assumption about the platform. A disabled channel cannot take a piece.",
        "The same idea for two channels is two pieces. Clone the first with cloneFromPieceId and rewrite it for the second channel's rules.",
    ],
    elsewhere=[
        "Whether a piece brought anything → **Analytics**.",
        "Finding the people a piece should reach → **Lead Management**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[content_create_piece, content_update_piece],
    limits={"maxTurns": 40, "maxBudgetUsd": 2},
    system_prompt=ask_prompt(ASK),
)
