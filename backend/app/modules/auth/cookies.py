from fastapi import Response

from app.core.config import get_settings
from app.modules.auth.service import TokenPair

ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
# The refresh cookie is only sent to auth endpoints, never to normal API calls.
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _common() -> dict[str, object]:
    settings = get_settings()
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "domain": settings.cookie_domain or None,
    }


def set_auth_cookies(response: Response, tokens: TokenPair) -> None:
    settings = get_settings()
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        tokens.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        **_common(),  # type: ignore[arg-type]
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        tokens.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        **_common(),  # type: ignore[arg-type]
    )


def clear_auth_cookies(response: Response) -> None:
    common = _common()
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/", **common)  # type: ignore[arg-type]
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH, **common)  # type: ignore[arg-type]
