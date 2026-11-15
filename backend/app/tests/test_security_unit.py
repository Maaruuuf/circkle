"""Unit tests: no database, no HTTP."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings
from app.core.pagination import decode_cursor, encode_cursor
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.webhooks import sign_payload
from app.modules.media.images import process_image
from app.tests.helpers import make_png


def test_password_hash_roundtrip_and_is_salted() -> None:
    first = hash_password("s3cret-password")
    second = hash_password("s3cret-password")

    assert first != second  # random salt
    assert verify_password("s3cret-password", first)
    assert not verify_password("wrong", first)
    assert not verify_password("anything", "not-a-valid-hash")


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()

    assert decode_access_token(create_access_token(user_id)) == user_id


def test_access_token_rejects_tampering_expiry_and_wrong_type() -> None:
    settings = get_settings()
    secret = settings.jwt_secret_key.get_secret_value()
    user_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    expired = jwt.encode(
        {"sub": user_id, "type": "access", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        secret,
        algorithm="HS256",
    )
    wrong_type = jwt.encode(
        {"sub": user_id, "type": "refresh", "iat": now, "exp": now + timedelta(minutes=5)},
        secret,
        algorithm="HS256",
    )
    wrong_key = jwt.encode(
        {"sub": user_id, "type": "access", "iat": now, "exp": now + timedelta(minutes=5)},
        "another-secret-key-that-is-long-enough-123",
        algorithm="HS256",
    )

    assert decode_access_token(expired) is None
    assert decode_access_token(wrong_type) is None
    assert decode_access_token(wrong_key) is None
    assert decode_access_token("garbage") is None


def test_token_hash_is_stable_and_not_the_token() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != "abc"


def test_cursor_roundtrip_and_rejects_garbage() -> None:
    created_at = datetime.now(UTC)
    row_id = uuid.uuid4()

    cursor = decode_cursor(encode_cursor(created_at, row_id))

    assert cursor is not None
    assert cursor.created_at == created_at and cursor.id == row_id
    assert decode_cursor(None) is None


def test_invalid_cursor_raises_bad_request() -> None:
    from app.core.errors import BadRequestError

    for bad in ("not-base64!!", "aGVsbG8", encode_cursor(datetime.now(UTC), uuid.uuid4())[:-5]):
        try:
            decode_cursor(bad)
        except BadRequestError as error:
            assert error.code == "INVALID_CURSOR"
        else:  # pragma: no cover
            raise AssertionError(f"cursor {bad!r} should be rejected")


def test_webhook_signature_depends_on_secret_timestamp_and_body() -> None:
    base = sign_payload("secret", "100", b"{}")

    assert base == sign_payload("secret", "100", b"{}")
    assert base != sign_payload("other", "100", b"{}")
    assert base != sign_payload("secret", "101", b"{}")
    assert base != sign_payload("secret", "100", b"{ }")


def test_process_image_outputs_webp_and_limits_size() -> None:
    processed = process_image(make_png(4000, 3000))

    assert processed.content_type == "image/webp"
    assert max(processed.width, processed.height) <= 2048
    assert processed.data[:4] == b"RIFF"


def test_process_image_square_crop_for_avatars() -> None:
    processed = process_image(make_png(300, 100), square=100)

    assert (processed.width, processed.height) == (100, 100)
