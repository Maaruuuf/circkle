import asyncio
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.exceptions import (
    AccountDisabledError,
    ConfirmationMismatchError,
    EmailNotVerifiedError,
    EmailOrUsernameTakenError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    PasswordNotSetError,
)
from app.modules.auth.google import GoogleProfile
from app.modules.auth.models import EMAIL_VERIFY, PASSWORD_RESET, AuthToken, RefreshToken
from app.modules.auth.repository import AuthTokenRepository, RefreshTokenRepository
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.media.models import Media
from app.modules.media.storage import get_storage
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.service import invalidate_profile_cache

# Usernames nobody may register (impersonation / routing clashes).
RESERVED_USERNAMES = frozenset(
    {
        "admin", "administrator", "root", "support", "help", "circkle", "system",
        "moderator", "api", "media", "settings", "login", "register", "explore",
        "search", "null", "undefined", "staff", "security", "abuse",
    }
)


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class LoginResult:
    user: User
    tokens: TokenPair


@dataclass(frozen=True)
class EmailTokenResult:
    user: User
    token: str


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._auth_tokens = AuthTokenRepository(session)

    # --- registration & email verification -----------------------------------------
    async def register(self, data: RegisterRequest) -> EmailTokenResult:
        if data.username in RESERVED_USERNAMES or await self._users.email_or_username_exists(
            data.email, data.username
        ):
            raise EmailOrUsernameTakenError()

        # Argon2 is CPU-heavy on purpose; keep it off the event loop.
        password_hash = await asyncio.to_thread(hash_password, data.password)
        user = User(
            id=uuid.uuid4(),
            email=data.email,
            username=data.username,
            display_name=data.username,
            password_hash=password_hash,
        )
        try:
            await self._users.add(user)
            token = self._add_email_token(user.id, EMAIL_VERIFY, self._verify_ttl())
            await self._session.commit()
        except IntegrityError:
            # Lost a race with a parallel registration of the same email/username.
            await self._session.rollback()
            raise EmailOrUsernameTakenError() from None
        await self._session.refresh(user)
        return EmailTokenResult(user=user, token=token)

    async def verify_email(self, raw_token: str) -> None:
        now = datetime.now(UTC)
        token = await self._get_valid_token(raw_token, EMAIL_VERIFY, now)
        user = await self._users.get_by_id(token.user_id)
        if user is None:
            raise InvalidTokenError()
        token.used_at = now
        user.is_email_verified = True
        await self._session.commit()

    async def resend_verification(self, email: str) -> EmailTokenResult | None:
        """Returns None (silently) for unknown/verified/disabled accounts: no enumeration."""
        user = await self._users.get_by_email(email)
        if user is None or user.is_email_verified or not user.is_active:
            return None
        await self._auth_tokens.invalidate_unused(user.id, EMAIL_VERIFY, datetime.now(UTC))
        token = self._add_email_token(user.id, EMAIL_VERIFY, self._verify_ttl())
        await self._session.commit()
        return EmailTokenResult(user=user, token=token)

    # --- login / sessions ------------------------------------------------------------
    async def login(self, data: LoginRequest) -> LoginResult:
        user = await self._users.get_by_email(data.email)

        # Always verify a hash, even for unknown emails (constant-ish timing).
        stored_hash = user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
        password_ok = await asyncio.to_thread(verify_password, data.password, stored_hash)
        if user is None or user.password_hash is None or not password_ok:
            raise InvalidCredentialsError()

        # Only after the password is proven do we reveal account state.
        if not user.is_active:
            raise AccountDisabledError()
        if get_settings().require_email_verification and not user.is_email_verified:
            raise EmailNotVerifiedError()

        return await self._start_session(user)

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        settings = get_settings()
        now = datetime.now(UTC)
        stored = await self._refresh_tokens.get_by_hash_for_update(hash_token(raw_refresh_token))
        if stored is None:
            raise InvalidRefreshTokenError()

        if stored.revoked_at is not None:
            grace = timedelta(seconds=settings.refresh_reuse_grace_seconds)
            if now - stored.revoked_at > grace:
                # An old, already-used token came back: assume theft, kill the session.
                await self._refresh_tokens.revoke_family(stored.family_id, now)
                await self._session.commit()
            # Inside the grace window it is most likely two browser tabs refreshing
            # at the same moment: refuse, but keep the session alive.
            raise InvalidRefreshTokenError()

        if stored.expires_at <= now:
            raise InvalidRefreshTokenError()

        user = await self._users.get_by_id(stored.user_id)
        if user is None or not user.is_active or user.deactivated_at is not None:
            raise InvalidRefreshTokenError()

        stored.revoked_at = now  # rotation: each refresh token works once
        return await self._issue_tokens(user.id, family_id=stored.family_id)

    async def logout(self, raw_refresh_token: str | None) -> None:
        """Idempotent: always succeeds, even with a missing or unknown token."""
        if raw_refresh_token is None:
            return
        stored = await self._refresh_tokens.get_by_hash_for_update(hash_token(raw_refresh_token))
        if stored is not None:
            await self._refresh_tokens.revoke_family(stored.family_id, datetime.now(UTC))
            await self._session.commit()

    async def logout_all(self, user: User) -> None:
        await self._refresh_tokens.revoke_all_for_user(user.id, datetime.now(UTC))
        await self._session.commit()

    # --- passwords -------------------------------------------------------------------
    async def forgot_password(self, email: str) -> EmailTokenResult | None:
        user = await self._users.get_by_email(email)
        if user is None or not user.is_active:
            return None
        now = datetime.now(UTC)
        await self._auth_tokens.invalidate_unused(user.id, PASSWORD_RESET, now)
        ttl = timedelta(minutes=get_settings().password_reset_expire_minutes)
        token = self._add_email_token(user.id, PASSWORD_RESET, ttl)
        await self._session.commit()
        return EmailTokenResult(user=user, token=token)

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        now = datetime.now(UTC)
        token = await self._get_valid_token(raw_token, PASSWORD_RESET, now)
        user = await self._users.get_by_id(token.user_id)
        if user is None:
            raise InvalidTokenError()
        user.password_hash = await asyncio.to_thread(hash_password, new_password)
        user.is_email_verified = True  # they just proved they control the mailbox
        token.used_at = now
        await self._refresh_tokens.revoke_all_for_user(user.id, now)  # log out everywhere
        await self._session.commit()

    async def change_password(self, user: User, current: str, new: str) -> TokenPair:
        if user.password_hash is None:
            raise PasswordNotSetError()
        if not await asyncio.to_thread(verify_password, current, user.password_hash):
            raise IncorrectPasswordError()
        user.password_hash = await asyncio.to_thread(hash_password, new)
        # Other devices are logged out; this device gets a fresh session.
        await self._refresh_tokens.revoke_all_for_user(user.id, datetime.now(UTC))
        return await self._issue_tokens(user.id, family_id=uuid.uuid4())

    # --- account lifecycle -------------------------------------------------------------
    async def deactivate(self, user: User, password: str | None) -> None:
        await self._require_password_if_set(user, password)
        now = datetime.now(UTC)
        user.deactivated_at = now
        await self._refresh_tokens.revoke_all_for_user(user.id, now)
        await self._session.commit()
        await invalidate_profile_cache(user.username)

    async def delete_account(
        self, user: User, password: str | None, confirm_username: str
    ) -> None:
        if confirm_username != user.username:
            raise ConfirmationMismatchError()
        await self._require_password_if_set(user, password)

        media_keys = (
            await self._session.execute(select(Media.key).where(Media.owner_id == user.id))
        ).scalars().all()
        username = user.username
        await self._users.delete(user)  # DB cascades remove posts, comments, tokens, ...
        await self._session.commit()
        await invalidate_profile_cache(username)

        storage = get_storage()
        for key in media_keys:  # best effort: orphaned files are only wasted space
            try:
                await storage.delete(key)
            except Exception:  # noqa: BLE001
                continue

    # --- Google login ----------------------------------------------------------------------
    async def login_with_google(self, profile: GoogleProfile) -> LoginResult:
        user = await self._users.get_by_google_sub(profile.sub)
        if user is None:
            user = await self._users.get_by_email(profile.email)
            if user is not None:
                if not user.is_email_verified:
                    # Pre-hijacking defence: someone may have registered this address
                    # with a password they know before the real owner signed in.
                    user.password_hash = None
                    await self._refresh_tokens.revoke_all_for_user(user.id, datetime.now(UTC))
                user.is_email_verified = True
                user.google_sub = profile.sub
            else:
                username = await self._free_username(profile.email)
                user = User(
                    id=uuid.uuid4(),
                    email=profile.email,
                    username=username,
                    display_name=(profile.name or username)[:50],
                    google_sub=profile.sub,
                    is_email_verified=True,
                )
                await self._users.add(user)

        if not user.is_active:
            raise AccountDisabledError()
        return await self._start_session(user)

    # --- helpers -------------------------------------------------------------------------------
    async def _start_session(self, user: User) -> LoginResult:
        reactivated = user.deactivated_at is not None
        user.last_login_at = datetime.now(UTC)
        user.deactivated_at = None  # logging in again reactivates a deactivated account
        tokens = await self._issue_tokens(user.id, family_id=uuid.uuid4())
        if reactivated:
            await invalidate_profile_cache(user.username)
        return LoginResult(user=user, tokens=tokens)

    async def _issue_tokens(self, user_id: uuid.UUID, family_id: uuid.UUID) -> TokenPair:
        settings = get_settings()
        raw_refresh_token = generate_token()
        self._refresh_tokens.add(
            RefreshToken(
                user_id=user_id,
                family_id=family_id,
                token_hash=hash_token(raw_refresh_token),
                expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        await self._session.commit()
        return TokenPair(
            access_token=create_access_token(user_id), refresh_token=raw_refresh_token
        )

    def _verify_ttl(self) -> timedelta:
        return timedelta(hours=get_settings().email_verify_expire_hours)

    def _add_email_token(self, user_id: uuid.UUID, purpose: str, ttl: timedelta) -> str:
        raw = generate_token()
        self._auth_tokens.add(
            AuthToken(
                user_id=user_id,
                purpose=purpose,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) + ttl,
            )
        )
        return raw

    async def _get_valid_token(self, raw: str, purpose: str, now: datetime) -> AuthToken:
        token = await self._auth_tokens.get_by_hash_for_update(hash_token(raw))
        if (
            token is None
            or token.purpose != purpose
            or token.used_at is not None
            or token.expires_at <= now
        ):
            raise InvalidTokenError()
        return token

    async def _require_password_if_set(self, user: User, password: str | None) -> None:
        if user.password_hash is None:
            return  # Google-only account: the live session is the proof
        if password is None or not await asyncio.to_thread(
            verify_password, password, user.password_hash
        ):
            raise IncorrectPasswordError()

    async def _free_username(self, email: str) -> str:
        base = re.sub(r"[^a-z0-9_]", "", email.split("@", 1)[0].lower())[:20]
        if len(base) < 3:
            base = "user"
        candidate = base
        for _ in range(10):
            if candidate not in RESERVED_USERNAMES and not await self._users.username_exists(
                candidate
            ):
                return candidate
            candidate = f"{base}{secrets.randbelow(10_000):04d}"
        raise EmailOrUsernameTakenError()
