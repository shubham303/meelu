from src.agent.context import current
from src.agent.server import tool
from src.core.database import unit_of_work
from src.profile.service import profile_service
from src.profile.schemas import (
    ProfileCreateRequest,
    ProfileDeleteResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)

CLEARABLE = (
    "role",
    "company",
    "timezone",
    "signature",
    "bio",
    "writingVoice",
    "linkedinUrl",
    "xUrl",
    "websiteUrl",
)


@tool(writes=True, desk="profile")
async def save_profile(
    full_name: str | None = None,
    role: str | None = None,
    company: str | None = None,
    timezone: str | None = None,
    signature: str | None = None,
    bio: str | None = None,
    writing_voice: str | None = None,
    linkedin_url: str | None = None,
    x_url: str | None = None,
    website_url: str | None = None,
) -> ProfileResponse:
    """Set fields on the user's profile; omitted fields keep their value. Creates the
    profile when none exists (full_name required then). In the user's words;
    timezone is an IANA name like Europe/London."""
    given = {
        "full_name": full_name,
        "role": role,
        "company": company,
        "timezone": timezone,
        "signature": signature,
        "bio": bio,
        "writing_voice": writing_voice,
        "linkedin_url": linkedin_url,
        "x_url": x_url,
        "website_url": website_url,
    }
    fields = {key: value.strip() for key, value in given.items() if value is not None}
    if not fields:
        raise ValueError("Nothing to save: give at least one field.")
    if "full_name" in fields and not fields["full_name"]:
        raise ValueError("full_name cannot be blank.")
    ctx = current()
    async with unit_of_work() as db:
        record = await profile_service.upsert(db, ctx.user_id, ProfileCreateRequest(**fields))
    return ProfileResponse.model_validate(record)


@tool(writes=True, desk="profile")
async def clear_profile_fields(fields: list[str]) -> ProfileResponse:
    """Blank the named profile fields (any of role, company, timezone, signature,
    bio, writingVoice, linkedinUrl, xUrl, websiteUrl). Only when the user asks."""
    names = sorted({f.strip() for f in fields if f and f.strip()})
    if not names:
        raise ValueError("Give at least one field to clear.")
    unknown = [f for f in names if f not in CLEARABLE]
    if unknown:
        raise ValueError(f"Cannot clear {unknown}; allowed: {list(CLEARABLE)}.")
    ctx = current()
    async with unit_of_work() as db:
        record = await profile_service.update(
            db, ctx.user_id, ProfileUpdateRequest.model_validate(dict.fromkeys(names))
        )
    return ProfileResponse.model_validate(record)


@tool(writes=True, desk="profile")
async def delete_profile() -> ProfileDeleteResponse:
    """Delete the user's profile entirely. Only when the user explicitly asks."""
    ctx = current()
    async with unit_of_work() as db:
        record = await profile_service.delete(db, ctx.user_id)
    return ProfileDeleteResponse(id=record.id)
