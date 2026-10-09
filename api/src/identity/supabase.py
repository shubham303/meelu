from dataclasses import dataclass

import httpx

from src.settings import settings


class SupabaseAuthError(Exception):
    pass


@dataclass(frozen=True)
class SupabaseUser:
    id: str
    email: str
    name: str
    image: str | None
    email_confirmed: bool


def _parse(body: dict) -> SupabaseUser:
    meta = body.get("user_metadata") or {}
    email = (body.get("email") or "").strip().lower()
    if not body.get("id") or not email:
        raise SupabaseAuthError("Supabase returned a user without an id or email.")
    return SupabaseUser(
        id=body["id"],
        email=email,
        name=meta.get("full_name") or meta.get("name") or "",
        image=meta.get("avatar_url") or meta.get("picture"),
        email_confirmed=bool(body.get("email_confirmed_at")),
    )


async def fetch_user(access_token: str) -> SupabaseUser:
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise SupabaseAuthError("Supabase auth is not configured on the server.")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {access_token}",
            },
        )
    if response.status_code != 200:
        raise SupabaseAuthError("The sign-in token is invalid or expired.")
    return _parse(response.json())
