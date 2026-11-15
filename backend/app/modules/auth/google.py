"""Google OAuth 2.0 (authorization code flow, server side, client secret kept on the server)."""

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    name: str | None


def build_authorization_url(state: str) -> str:
    settings = get_settings()
    query = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{GOOGLE_AUTH_URL}?{query}"


async def fetch_profile(code: str) -> GoogleProfile:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret.get_secret_value(),
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_response.status_code != 200:
                raise GoogleAuthError("token exchange failed")
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise GoogleAuthError("no access token")

            info_response = await client.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            if info_response.status_code != 200:
                raise GoogleAuthError("userinfo failed")
            info = info_response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GoogleAuthError("google request failed") from exc

    # Only trust an email address Google itself has verified.
    if not info.get("sub") or not info.get("email") or info.get("email_verified") is not True:
        raise GoogleAuthError("unverified google account")
    return GoogleProfile(
        sub=str(info["sub"]), email=str(info["email"]).lower(), name=info.get("name")
    )
