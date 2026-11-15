"""Cross-cutting behaviour: error format, security headers, CSRF origin check, rate limits, health."""

from httpx import AsyncClient

from app.core.cache import cache_get_json, cache_set_json
from app.core.webhooks import dispatch_event
from app.tests.helpers import API, PASSWORD, email_for


async def test_liveness_and_readiness(client: AsyncClient) -> None:
    live = await client.get("/health")
    ready = await client.get("/health/ready")

    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"
    assert ready.json()["checks"]["redis"] == "not_configured"


async def test_security_headers_and_request_id(client: AsyncClient) -> None:
    response = await client.get(f"{API}/posts/explore", headers={"X-Request-ID": "my-trace-id-123"})

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"] == "my-trace-id-123"


async def test_invalid_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "bad id with spaces"})

    assert response.headers["x-request-id"] != "bad id with spaces"


async def test_unknown_route_uses_standard_error_format(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert (await client.put("/health")).status_code == 405


async def test_cross_origin_state_changing_request_is_rejected(client: AsyncClient) -> None:
    evil = await client.post(
        f"{API}/auth/login",
        json={"email": email_for("x"), "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    own = await client.post(
        f"{API}/auth/login",
        json={"email": email_for("x"), "password": PASSWORD},
        headers={"Origin": "http://localhost:3000"},
    )
    safe_get = await client.get("/health", headers={"Origin": "https://evil.example"})

    assert evil.status_code == 403 and evil.json()["error"]["code"] == "CSRF_ORIGIN_REJECTED"
    assert own.status_code == 401  # reached the endpoint (wrong credentials), not blocked
    assert safe_get.status_code == 200


async def test_cors_preflight_only_allows_configured_origins(client: AsyncClient) -> None:
    allowed = await client.options(
        f"{API}/posts",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    blocked = await client.options(
        f"{API}/posts",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert allowed.headers.get("access-control-allow-credentials") == "true"
    assert "access-control-allow-origin" not in blocked.headers


async def test_login_rate_limit_returns_429_with_retry_after(client: AsyncClient, monkeypatch, settings) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    payload = {"email": email_for("ghost"), "password": PASSWORD}

    statuses = [(await client.post(f"{API}/auth/login", json=payload)).status_code for _ in range(11)]

    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
    blocked = await client.post(f"{API}/auth/login", json=payload)
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["retry-after"]) > 0


async def test_register_rate_limit(client: AsyncClient, monkeypatch, settings) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "rate_limit_enabled", True)

    statuses = []
    for number in range(6):
        response = await client.post(
            f"{API}/auth/register",
            json={"email": f"user{number}@example.com", "username": f"user{number}", "password": PASSWORD},
        )
        statuses.append(response.status_code)

    assert statuses == [201] * 5 + [429]


async def test_cache_roundtrip_and_ttl_miss() -> None:
    await cache_set_json("test:key", {"a": 1}, ttl_seconds=60)

    assert await cache_get_json("test:key") == {"a": 1}
    assert await cache_get_json("test:missing") is None


async def test_webhook_dispatch_is_a_noop_without_url() -> None:
    await dispatch_event("post.created", {"id": "1"})  # must not raise or make requests
