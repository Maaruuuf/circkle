import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings

_password_hasher = PasswordHasher()

# Verified against when an account does not exist, so a missing account takes
# as long as a wrong password (prevents user enumeration by response time).
DUMMY_PASSWORD_HASH = _password_hasher.hash("timing-attack-protection")

ACCESS_TOKEN_TYPE = "access"


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> uuid.UUID | None:
    """Return the user id for a valid access token, otherwise None."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],  # never trust the token's own header
            options={"require": ["exp", "iat", "sub"]},
        )
        if payload.get("type") != ACCESS_TOKEN_TYPE:
            return None
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None


def generate_token() -> str:
    """Long random URL-safe token (refresh tokens, email links, OAuth state)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Only this hash is stored, so a DB leak does not expose usable tokens.
    SHA-256 is enough because the tokens are long and random (not passwords)."""
    return hashlib.sha256(token.encode()).hexdigest()
