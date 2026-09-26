from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.media.repository import post_medias
from src.content.schemas.pieces import ContentPieceMediaRequest, PieceMediaResult


class PieceMediaService:
    async def resolve(
        self, db: AsyncSession, user_id: str, body: ContentPieceMediaRequest
    ) -> PieceMediaResult | None:
        if not body.has("media_source"):
            return None

        source = body.media_source
        if source == "none":
            return PieceMediaResult()

        if source == "upload":
            upload_id = body.media_upload_id or ""
            if not upload_id:
                raise HTTPException(400, "mediaUploadId is required when mediaSource is upload.")
            if await post_medias.get(db, user_id, upload_id) is None:
                raise HTTPException(400, "That upload doesn't exist. Upload the image first.")
            return PieceMediaResult(
                media_source="upload",
                media_upload_id=upload_id,
                media_url=f"/api/v1/content/media/{upload_id}",
                media_alt=body.media_alt,
                media_width=body.media_width,
                media_height=body.media_height,
            )

        url = body.media_url or ""
        if not url.startswith("https://images.unsplash.com/"):
            raise HTTPException(
                400,
                "An Unsplash image must be the hotlinked images.unsplash.com URL — their "
                "guidelines forbid re-hosting.",
            )
        if not body.media_credit_name or not body.media_credit_url:
            raise HTTPException(
                400,
                "An Unsplash image needs the photographer's name and profile link — "
                "attribution is required.",
            )
        return PieceMediaResult(
            media_source="unsplash",
            media_url=url,
            media_alt=body.media_alt,
            media_width=body.media_width,
            media_height=body.media_height,
            media_credit_name=body.media_credit_name,
            media_credit_url=body.media_credit_url,
        )


piece_media_service = PieceMediaService()
