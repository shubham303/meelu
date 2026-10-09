from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, current_user_id, require_site
from src.content.media.service import post_media_service
from src.content.piece_issues.service import content_piece_issue_service
from src.content.pieces.service import content_piece_service
from src.content.schemas import (
    ContentPieceCreateRequest,
    ContentPieceDeleteResponse,
    ContentPieceIssueListItemResponse,
    ContentPieceIssueResponse,
    ContentPieceIssuesReplaceRequest,
    ContentPieceIssuesReplaceResponse,
    ContentPieceIssueUpdateRequest,
    ContentPieceListItemResponse,
    ContentPieceResponse,
    ContentPieceUpdateRequest,
    PostMediaResponse,
    UnsplashDownloadRequest,
    UnsplashDownloadResponse,
    UnsplashPhotoResponse,
    UnsplashSearchResponse,
)
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.integrations.base import IntegrationError
from src.integrations.unsplash import unsplash

router = APIRouter()


def actor_of(request: Request) -> str:
    if not request.headers.get("x-api-key"):
        return "user"
    return "user" if request.headers.get("x-meelu-actor") == "user" else "agent"


@router.get("/content/pieces")
async def list_pieces(
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[ContentPieceListItemResponse]:
    page = await content_piece_service.list(db, ctx.site_id, paging, search=search)
    return PaginatedApiResponse[ContentPieceListItemResponse](
        data=[ContentPieceListItemResponse.model_validate(p) for p in page.data],
        pagination=page.pagination,
    )


@router.post("/content/pieces", status_code=201)
async def create_piece(
    body: ContentPieceCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    actor: str = Depends(actor_of),
) -> ContentPieceResponse:
    piece = await content_piece_service.create(db, ctx.user_id, ctx.site_id, body, actor=actor)
    return ContentPieceResponse.model_validate(piece)


@router.get("/content/pieces/{piece_id}")
async def get_piece(
    piece_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ContentPieceResponse:
    return ContentPieceResponse.model_validate(
        await content_piece_service.get(db, ctx.site_id, piece_id)
    )


@router.get("/content/pieces/{piece_id}/markdown")
async def piece_markdown(
    piece_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> Response:
    piece = await content_piece_service.get(db, ctx.site_id, piece_id)
    export = content_piece_service.markdown_export(piece)
    return Response(export.markdown, media_type="text/markdown; charset=utf-8")


@router.patch("/content/pieces/{piece_id}")
async def update_piece(
    piece_id: str,
    body: ContentPieceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ContentPieceResponse:
    piece = await content_piece_service.update(db, ctx.user_id, ctx.site_id, piece_id, body)
    return ContentPieceResponse.model_validate(piece)


@router.delete("/content/pieces/{piece_id}")
async def delete_piece(
    piece_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ContentPieceDeleteResponse:
    piece = await content_piece_service.delete(db, ctx.site_id, piece_id)
    return ContentPieceDeleteResponse(id=piece.id)


@router.get("/content/pieces/{piece_id}/issues")
async def list_piece_issues(
    piece_id: str,
    state: str | None = Query(None),
    tool: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[ContentPieceIssueListItemResponse]:
    page = await content_piece_issue_service.list(
        db, ctx.site_id, piece_id, paging, state=state, tool=tool
    )
    return PaginatedApiResponse[ContentPieceIssueListItemResponse](
        data=[ContentPieceIssueListItemResponse.model_validate(i) for i in page.data],
        pagination=page.pagination,
    )


@router.post("/content/pieces/{piece_id}/issues", status_code=201)
async def replace_piece_issues(
    piece_id: str,
    body: ContentPieceIssuesReplaceRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ContentPieceIssuesReplaceResponse:
    result = await content_piece_issue_service.replace_for_tool(
        db, ctx.user_id, ctx.site_id, piece_id, body
    )
    return ContentPieceIssuesReplaceResponse(
        run_id=result.run_id,
        tool=result.tool,
        issues=[ContentPieceIssueResponse.model_validate(i) for i in result.issues],
    )


@router.patch("/content/pieces/{piece_id}/issues/{issue_id}")
async def update_piece_issue(
    piece_id: str,
    issue_id: str,
    body: ContentPieceIssueUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ContentPieceIssueResponse:
    issue = await content_piece_issue_service.update(db, ctx.site_id, piece_id, issue_id, body)
    return ContentPieceIssueResponse.model_validate(issue)


@router.post("/content/media", status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    width: str | None = Form(None),
    height: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> PostMediaResponse:
    media = await post_media_service.upload(
        db,
        user_id,
        await file.read(),
        file.content_type or "",
        file.filename,
        width=width,
        height=height,
    )
    return PostMediaResponse.model_validate(media)


@router.get("/content/media/{media_id}")
async def serve_media(
    media_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> Response:
    media = await post_media_service.read(db, user_id, media_id)
    return Response(
        content=media.data,
        headers={
            "content-type": media.content_type,
            "content-length": str(len(media.data)),
            "cache-control": "private, max-age=31536000, immutable",
            "x-content-type-options": "nosniff",
        },
    )


def _unsplash_error(e: IntegrationError) -> HTTPException:
    if e.status == 501:
        return HTTPException(501, e.message)
    if e.status is None:
        return HTTPException(502, "Could not reach Unsplash. Check the connection and try again.")
    if e.status == 429 or (e.status == 403 and "rate limit" in str(e.body).lower()):
        return HTTPException(
            429,
            "Unsplash's hourly search limit is used up. Try again later, or upload an "
            "image instead.",
        )
    if e.status == 403:
        return HTTPException(502, "Unsplash refused the request. Check the access key.")
    return HTTPException(502, f"Unsplash search failed ({e.status}).")


@router.get("/content/unsplash")
async def search_unsplash(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    orientation: str | None = Query(None),
    user_id: str = Depends(current_user_id),
) -> UnsplashSearchResponse:
    term = (q or "").strip()
    if not term:
        return UnsplashSearchResponse(configured=unsplash.configured)

    try:
        result = await unsplash.search_photos(term, page=page, orientation=orientation)
    except IntegrationError as e:
        raise _unsplash_error(e)

    return UnsplashSearchResponse(
        configured=True,
        photos=[UnsplashPhotoResponse.model_validate(p) for p in result.photos],
        total=result.total,
        total_pages=result.total_pages,
    )


@router.post("/content/unsplash")
async def unsplash_download(
    body: UnsplashDownloadRequest,
    user_id: str = Depends(current_user_id),
) -> UnsplashDownloadResponse:
    try:
        await unsplash.trigger_download(body.download_location)
    except IntegrationError as e:
        if e.status == 400:
            raise HTTPException(400, e.message)
        raise _unsplash_error(e)
    return UnsplashDownloadResponse()
