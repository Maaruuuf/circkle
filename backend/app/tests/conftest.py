import os
import tempfile
from collections.abc import AsyncIterator, Awaitable, Callable

# --- Environment must be prepared BEFORE the app is imported -----------------------------
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://y:y_dev_pass@localhost:5432/y_test"
)
# Safety guard: tests wipe tables, so they may only touch a *_test database.
if not TEST_DATABASE_URL.rsplit("/", 1)[-1].endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must point to a database ending in _test")

os.environ.update(
    {
        "DATABASE_URL": TEST_DATABASE_URL,
        "ENVIRONMENT": "development",
        "COOKIE_SECURE": "true",
        "EMAIL_BACKEND": "memory",
        "RATE_LIMIT_ENABLED": "false",
        "REDIS_URL": "",
        "STORAGE_BACKEND": "local",
        "MEDIA_ROOT": tempfile.mkdtemp(prefix="circkle_test_media_"),
        "REQUIRE_EMAIL_VERIFICATION": "false",
        "GOOGLE_CLIENT_ID": "",
        "WEBHOOK_URL": "",
        "SENTRY_DSN": "",
    }
)
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-at-least-32-characters-long")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.cache import reset_memory_cache  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.email import OUTBOX  # noqa: E402
from app.core.rate_limit import reset_memory_limits  # noqa: E402
from app.db import registry  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_state() -> AsyncIterator[None]:
    yield
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE reactions, comments, posts, media, follows, "
                "refresh_tokens, auth_tokens, users CASCADE"
            )
        )
    reset_memory_cache()
    reset_memory_limits()
    OUTBOX.clear()


@pytest.fixture
def settings():  # type: ignore[no-untyped-def]
    """The live settings object. Tests may change fields (monkeypatch) per test."""
    return get_settings()


@pytest_asyncio.fixture
async def make_client() -> AsyncIterator[Callable[[], Awaitable[AsyncClient]]]:
    """Factory for independent HTTP clients, each with its own cookie jar (= one browser)."""
    clients: list[AsyncClient] = []

    async def _make() -> AsyncClient:
        # https because the auth cookies are marked Secure.
        http_client = AsyncClient(transport=ASGITransport(app=app), base_url="https://test")
        clients.append(http_client)
        return http_client

    yield _make
    for http_client in clients:
        await http_client.aclose()


@pytest_asyncio.fixture
async def client(make_client: Callable[[], Awaitable[AsyncClient]]) -> AsyncClient:
    return await make_client()
