import secrets
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Response, status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.core.rate_limit import RateLimit
from app.core.security import generate_token
from app.core.webhooks import dispatch_event
from app.modules.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.modules.auth.dependencies import AuthServiceDep, CurrentUser
from app.modules.auth.emails import send_password_reset_email, send_verification_email
from app.modules.auth.exceptions import InvalidRefreshTokenError
from app.modules.auth.google import GoogleAuthError, build_authorization_url, fetch_profile
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    DeactivateRequest,
    DeleteAccountRequest,
    EmailRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenRequest,
)
from app.modules.users.schemas import UserMeResponse

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_EMAIL_LIMIT = RateLimit("login_email", limit=10, window_seconds=900)
OAUTH_STATE_COOKIE = "oauth_state"
OAUTH_COOKIE_PATH = "/api/v1/auth/google"


@router.post(
    "/register",
    response_model=UserMeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit("register", 5, 3600))],
)
async def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthServiceDep,
) -> UserMeResponse:
    result = await auth_service.register(payload)
    background_tasks.add_task(
        send_verification_email, result.user.email, result.user.username, result.token
    )
    background_tasks.add_task(
        dispatch_event,
        "user.registered",
        {"id": str(result.user.id), "username": result.user.username},
    )
    return UserMeResponse.model_validate(result.user)


@router.post("/verify-email", response_model=MessageResponse,
             dependencies=[Depends(RateLimit("verify_email", 20, 3600))])
async def verify_email(payload: TokenRequest, auth_service: AuthServiceDep) -> MessageResponse:
    await auth_service.verify_email(payload.token)
    return MessageResponse(message="Email verified")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimit("resend_verification", 5, 3600))],
)
async def resend_verification(
    payload: EmailRequest, background_tasks: BackgroundTasks, auth_service: AuthServiceDep
) -> MessageResponse:
    result = await auth_service.resend_verification(payload.email)
    if result is not None:
        background_tasks.add_task(
            send_verification_email, result.user.email, result.user.username, result.token
        )
    # Same answer whether or not the address exists.
    return MessageResponse(message="If the account exists, a verification email was sent")


@router.post("/login", response_model=UserMeResponse,
             dependencies=[Depends(RateLimit("login", 10, 60))])
async def login(
    payload: LoginRequest, response: Response, auth_service: AuthServiceDep
) -> UserMeResponse:
    await LOGIN_EMAIL_LIMIT.check(f"email:{payload.email}")
    result = await auth_service.login(payload)
    set_auth_cookies(response, result.tokens)
    return UserMeResponse.model_validate(result.user)


@router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimit("refresh", 60, 60))],
)
async def refresh(
    auth_service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if refresh_token is None:
        raise InvalidRefreshTokenError()
    tokens = await auth_service.refresh(refresh_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_auth_cookies(response, tokens)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth_service: AuthServiceDep,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    await auth_service.logout(refresh_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(current_user: CurrentUser, auth_service: AuthServiceDep) -> Response:
    await auth_service.logout_all(current_user)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimit("forgot_password", 5, 3600))],
)
async def forgot_password(
    payload: EmailRequest, background_tasks: BackgroundTasks, auth_service: AuthServiceDep
) -> MessageResponse:
    result = await auth_service.forgot_password(payload.email)
    if result is not None:
        background_tasks.add_task(
            send_password_reset_email, result.user.email, result.user.username, result.token
        )
    return MessageResponse(message="If the account exists, a reset email was sent")


@router.post("/reset-password", response_model=MessageResponse,
             dependencies=[Depends(RateLimit("reset_password", 10, 3600))])
async def reset_password(
    payload: ResetPasswordRequest, auth_service: AuthServiceDep
) -> MessageResponse:
    await auth_service.reset_password(payload.token, payload.new_password)
    return MessageResponse(message="Password updated. Please log in again")


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimit("change_password", 10, 3600, per="user"))],
)
async def change_password(
    payload: ChangePasswordRequest, current_user: CurrentUser, auth_service: AuthServiceDep
) -> Response:
    tokens = await auth_service.change_password(
        current_user, payload.current_password, payload.new_password
    )
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_auth_cookies(response, tokens)
    return response


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_account(
    payload: DeactivateRequest, current_user: CurrentUser, auth_service: AuthServiceDep
) -> Response:
    await auth_service.deactivate(current_user, payload.password)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    payload: DeleteAccountRequest, current_user: CurrentUser, auth_service: AuthServiceDep
) -> Response:
    await auth_service.delete_account(current_user, payload.password, payload.confirm_username)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(response)
    return response


# --- Google login -------------------------------------------------------------------------
@router.get("/google/login", status_code=status.HTTP_302_FOUND)
async def google_login() -> RedirectResponse:
    """Start Google login: redirects the browser to Google's consent screen."""
    settings = get_settings()
    if not settings.google_enabled:
        raise NotFoundError("Google login is not configured", code="FEATURE_DISABLED")
    state = generate_token()
    response = RedirectResponse(build_authorization_url(state), status_code=302)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=OAUTH_COOKIE_PATH,
    )
    return response


@router.get("/google/callback", status_code=status.HTTP_302_FOUND)
async def google_callback(
    auth_service: AuthServiceDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    """Google redirects here. We always end by redirecting back to the frontend."""
    settings = get_settings()
    frontend = settings.frontend_url.rstrip("/")

    def fail() -> RedirectResponse:
        failure = RedirectResponse(f"{frontend}/login?error=google_failed", status_code=302)
        failure.delete_cookie(OAUTH_STATE_COOKIE, path=OAUTH_COOKIE_PATH)
        return failure

    if not settings.google_enabled:
        raise NotFoundError("Google login is not configured", code="FEATURE_DISABLED")
    # `state` ties this callback to the browser that started the login (CSRF protection).
    if error or not code or not state or not oauth_state:
        return fail()
    if not secrets.compare_digest(state, oauth_state):
        return fail()
    try:
        profile = await fetch_profile(code)
        result = await auth_service.login_with_google(profile)
    except (GoogleAuthError, AppError):
        return fail()

    response = RedirectResponse(f"{frontend}/", status_code=302)
    set_auth_cookies(response, result.tokens)
    response.delete_cookie(OAUTH_STATE_COOKIE, path=OAUTH_COOKIE_PATH)
    return response

