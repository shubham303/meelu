import time
from dataclasses import dataclass

import httpx
import jwt

from src.settings import settings

ALGORITHMS = ["EdDSA"]
REFRESH_INTERVAL_SECONDS = 30
INVALID = "The sign-in token is invalid or expired."
UNAVAILABLE = "Sign-in is unavailable right now. Try again."


class AuthTokenError(Exception):
    pass


class AuthUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class AuthIdentity:
    id: str
    email: str
    name: str
    image: str | None
    email_verified: bool


class JwksKeys:
    def __init__(self) -> None:
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at = 0.0

    async def download(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(settings.auth_jwks_url)
        except httpx.HTTPError as e:
            raise AuthUnavailableError(UNAVAILABLE) from e
        if response.status_code != 200:
            raise AuthUnavailableError(UNAVAILABLE)
        try:
            body = response.json()
        except ValueError as e:
            raise AuthUnavailableError(UNAVAILABLE) from e
        if not isinstance(body, dict):
            raise AuthUnavailableError(UNAVAILABLE)
        return body

    async def _refresh(self) -> None:
        body = await self.download()
        keys: dict[str, jwt.PyJWK] = {}
        for entry in body.get("keys") or []:
            if not isinstance(entry, dict) or not isinstance(entry.get("kid"), str):
                continue
            try:
                keys[entry["kid"]] = jwt.PyJWK(entry)
            except jwt.PyJWTError:
                continue
        self._keys = keys
        self._fetched_at = time.monotonic()

    async def get(self, kid: str) -> jwt.PyJWK:
        stale = time.monotonic() - self._fetched_at >= REFRESH_INTERVAL_SECONDS
        if kid not in self._keys and (not self._keys or stale):
            await self._refresh()
        key = self._keys.get(kid)
        if key is None:
            raise AuthTokenError(INVALID)
        return key


jwks = JwksKeys()


async def verify_token(token: str) -> AuthIdentity:
    if not settings.auth_jwks_url or not settings.auth_issuer or not settings.auth_audience:
        raise AuthUnavailableError("Sign-in is not configured on the server.")
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise AuthTokenError(INVALID) from e
    kid = header.get("kid")
    if not isinstance(kid, str) or header.get("alg") not in ALGORITHMS:
        raise AuthTokenError(INVALID)
    key = await jwks.get(kid)
    try:
        claims = jwt.decode(
            token,
            key.key,
            algorithms=ALGORITHMS,
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise AuthTokenError(INVALID) from e
    subject = claims.get("sub")
    email = claims.get("email")
    if (
        not isinstance(subject, str)
        or not subject
        or not isinstance(email, str)
        or not email.strip()
    ):
        raise AuthTokenError(INVALID)
    name = claims.get("name")
    return AuthIdentity(
        id=subject,
        email=email.strip().lower(),
        name=name if isinstance(name, str) else "",
        image=None,
        email_verified=claims.get("emailVerified") is True,
    )
