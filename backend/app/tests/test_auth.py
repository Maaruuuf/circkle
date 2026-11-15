from httpx import AsyncClient

from app.core.email import OUTBOX
from app.tests.helpers import API, PASSWORD, cookie_value, email_for, signup, token_from_outbox

REGISTER = f"{API}/auth/register"
LOGIN = f"{API}/auth/login"
REFRESH = f"{API}/auth/refresh"
LOGOUT = f"{API}/auth/logout"
ME = f"{API}/users/me"


def body(username: str = "maruf_01", **overrides: str) -> dict[str, str]:
    return {"email": email_for(username), "username": username, "password": PASSWORD, **overrides}


# ---- registration -------------------------------------------------------------------------
async def test_register_returns_user_without_secrets(client: AsyncClient) -> None:
    response = await client.post(REGISTER, json=body())

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "maruf_01@example.com"
    assert data["role"] == "user"
    assert data["is_email_verified"] is False
    assert "password" not in data and "password_hash" not in data


async def test_register_normalizes_email_and_username(client: AsyncClient) -> None:
    response = await client.post(
        REGISTER, json={"email": "  Maruf@Example.COM ", "username": "Maruf_01", "password": PASSWORD}
    )

    assert response.status_code == 201
    assert response.json()["email"] == "maruf@example.com"
    assert response.json()["username"] == "maruf_01"


async def test_register_duplicate_returns_conflict_error_code(client: AsyncClient) -> None:
    await client.post(REGISTER, json=body())

    same_email = await client.post(REGISTER, json=body("other", email=email_for("maruf_01")))
    same_username = await client.post(REGISTER, json=body("maruf_01", email="new@example.com"))

    for response in (same_email, same_username):
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EMAIL_OR_USERNAME_TAKEN"


async def test_register_rejects_reserved_username(client: AsyncClient) -> None:
    response = await client.post(REGISTER, json=body("admin"))

    assert response.status_code == 409


async def test_register_validation_errors(client: AsyncClient) -> None:
    short = await client.post(REGISTER, json=body(password="short"))
    bad_username = await client.post(REGISTER, json=body("Has Space"))
    extra_field = await client.post(REGISTER, json={**body(), "role": "admin"})
    bad_email = await client.post(REGISTER, json=body(email="not-an-email"))

    for response in (short, bad_username, extra_field, bad_email):
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "request_id" in error
        assert PASSWORD not in response.text  # never echo submitted values


# ---- login --------------------------------------------------------------------------------
async def test_login_sets_httponly_secure_cookies(client: AsyncClient) -> None:
    await client.post(REGISTER, json=body())

    response = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})

    assert response.status_code == 200
    cookies = [c.lower() for c in response.headers.get_list("set-cookie")]
    assert len(cookies) == 2
    for cookie in cookies:
        assert "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
    assert any("path=/api/v1/auth" in c for c in cookies)  # refresh cookie is path-scoped


async def test_login_failures_are_indistinguishable(client: AsyncClient) -> None:
    await client.post(REGISTER, json=body())

    wrong_password = await client.post(
        LOGIN, json={"email": email_for("maruf_01"), "password": "wrong-password-1"}
    )
    unknown_email = await client.post(
        LOGIN, json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


async def test_login_requires_verified_email_when_enabled(client: AsyncClient, monkeypatch, settings) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "require_email_verification", True)
    await client.post(REGISTER, json=body())

    blocked = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"

    verified = await client.post(f"{API}/auth/verify-email", json={"token": token_from_outbox()})
    assert verified.status_code == 200
    allowed = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    assert allowed.status_code == 200


# ---- session / protected routes --------------------------------------------------------------
async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(ME)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_me_returns_current_user(client: AsyncClient) -> None:
    await signup(client, "maruf_01")

    response = await client.get(ME)

    assert response.status_code == 200
    assert response.json()["username"] == "maruf_01"


async def test_tampered_access_cookie_is_rejected(client: AsyncClient) -> None:
    response = await client.get(ME, headers={"Cookie": "access_token=not.a.jwt"})

    assert response.status_code == 401


async def test_refresh_rotates_and_detects_reuse(client: AsyncClient, monkeypatch, settings) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "refresh_reuse_grace_seconds", 0)
    await client.post(REGISTER, json=body())
    login = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    old_token = cookie_value(login, "refresh_token")
    assert old_token

    rotated = await client.post(REFRESH, headers={"Cookie": f"refresh_token={old_token}"})
    new_token = cookie_value(rotated, "refresh_token")
    assert rotated.status_code == 204
    assert new_token and new_token != old_token

    replay = await client.post(REFRESH, headers={"Cookie": f"refresh_token={old_token}"})
    assert replay.status_code == 401

    # Reuse = theft suspected: the whole session family is revoked, even the newest token.
    after_theft = await client.post(REFRESH, headers={"Cookie": f"refresh_token={new_token}"})
    assert after_theft.status_code == 401


async def test_refresh_reuse_inside_grace_window_keeps_session(client: AsyncClient) -> None:
    await client.post(REGISTER, json=body())
    login = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    old_token = cookie_value(login, "refresh_token")
    rotated = await client.post(REFRESH, headers={"Cookie": f"refresh_token={old_token}"})
    new_token = cookie_value(rotated, "refresh_token")

    # A second browser tab sends the old token a moment later: refused, session survives.
    racing = await client.post(REFRESH, headers={"Cookie": f"refresh_token={old_token}"})
    assert racing.status_code == 401
    still_valid = await client.post(REFRESH, headers={"Cookie": f"refresh_token={new_token}"})
    assert still_valid.status_code == 204


async def test_refresh_without_cookie_is_unauthorized(client: AsyncClient) -> None:
    assert (await client.post(REFRESH)).status_code == 401


async def test_logout_revokes_session_and_is_idempotent(client: AsyncClient) -> None:
    await client.post(REGISTER, json=body())
    login = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    refresh_token = cookie_value(login, "refresh_token")

    logout = await client.post(LOGOUT)

    assert logout.status_code == 204
    assert (await client.get(ME)).status_code == 401
    assert (
        await client.post(REFRESH, headers={"Cookie": f"refresh_token={refresh_token}"})
    ).status_code == 401
    assert (await client.post(LOGOUT)).status_code == 204


async def test_logout_all_revokes_every_device(make_client) -> None:  # type: ignore[no-untyped-def]
    phone, laptop = await make_client(), await make_client()
    await signup(phone, "maruf_01")
    login = await laptop.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    laptop_refresh = cookie_value(login, "refresh_token")

    assert (await phone.post(f"{API}/auth/logout-all")).status_code == 204

    revoked = await laptop.post(REFRESH, headers={"Cookie": f"refresh_token={laptop_refresh}"})
    assert revoked.status_code == 401


# ---- email verification -------------------------------------------------------------------------
async def test_verify_email_flow_and_single_use(client: AsyncClient) -> None:
    await client.post(REGISTER, json=body())
    assert len(OUTBOX) == 1 and OUTBOX[0].to == "maruf_01@example.com"
    token = token_from_outbox()

    first = await client.post(f"{API}/auth/verify-email", json={"token": token})
    second = await client.post(f"{API}/auth/verify-email", json={"token": token})

    assert first.status_code == 200
    assert second.status_code == 400 and second.json()["error"]["code"] == "INVALID_TOKEN"


async def test_verify_email_rejects_garbage_token(client: AsyncClient) -> None:
    response = await client.post(f"{API}/auth/verify-email", json={"token": "x" * 40})

    assert response.status_code == 400


async def test_resend_verification_is_silent_for_unknown_email(client: AsyncClient) -> None:
    unknown = await client.post(f"{API}/auth/resend-verification", json={"email": "no@example.com"})
    await client.post(REGISTER, json=body())
    known = await client.post(
        f"{API}/auth/resend-verification", json={"email": email_for("maruf_01")}
    )

    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert len(OUTBOX) == 2  # one registration email + one resend, none for the unknown address


# ---- password reset / change ------------------------------------------------------------------------
async def test_forgot_and_reset_password_flow(client: AsyncClient) -> None:
    await signup(client, "maruf_01")
    forgot = await client.post(f"{API}/auth/forgot-password", json={"email": email_for("maruf_01")})
    assert forgot.status_code == 202
    token = token_from_outbox()

    reset = await client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "brand-new-password"}
    )
    assert reset.status_code == 200
    assert (await client.get(ME)).status_code == 200  # access token lives until it expires...

    old = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    new = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": "brand-new-password"})
    assert old.status_code == 401 and new.status_code == 200

    reused = await client.post(
        f"{API}/auth/reset-password", json={"token": token, "new_password": "another-password-1"}
    )
    assert reused.status_code == 400


async def test_forgot_password_does_not_reveal_unknown_emails(client: AsyncClient) -> None:
    response = await client.post(f"{API}/auth/forgot-password", json={"email": "ghost@example.com"})

    assert response.status_code == 202
    assert OUTBOX == []


async def test_change_password_requires_current_password(client: AsyncClient) -> None:
    await signup(client, "maruf_01")

    wrong = await client.post(
        f"{API}/auth/change-password",
        json={"current_password": "not-my-password", "new_password": "brand-new-password"},
    )
    ok = await client.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "brand-new-password"},
    )

    assert wrong.status_code == 400 and wrong.json()["error"]["code"] == "INCORRECT_PASSWORD"
    assert ok.status_code == 204
    assert (await client.get(ME)).status_code == 200  # this device stays logged in
    login = await client.post(LOGIN, json={"email": email_for("maruf_01"), "password": "brand-new-password"})
    assert login.status_code == 200


# ---- account lifecycle -----------------------------------------------------------------------------
async def test_deactivate_hides_profile_and_login_reactivates(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    await signup(client, "maruf_01")
    visitor = await make_client()

    deactivate = await client.post(f"{API}/auth/deactivate", json={"password": PASSWORD})
    assert deactivate.status_code == 204
    assert (await client.get(ME)).status_code == 401
    assert (await visitor.get(f"{API}/users/maruf_01")).status_code == 404

    login = await visitor.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    assert login.status_code == 200
    assert (await visitor.get(f"{API}/users/maruf_01")).status_code == 200


async def test_deactivate_needs_correct_password(client: AsyncClient) -> None:
    await signup(client, "maruf_01")

    response = await client.post(f"{API}/auth/deactivate", json={"password": "wrong-password-1"})

    assert response.status_code == 400


async def test_delete_account_removes_user_and_their_content(client: AsyncClient, make_client) -> None:  # type: ignore[no-untyped-def]
    await signup(client, "maruf_01")
    await client.post(f"{API}/posts", json={"content": "bye"})
    visitor = await make_client()

    mismatch = await client.request(
        "DELETE", f"{API}/auth/account", json={"password": PASSWORD, "confirm_username": "someone"}
    )
    deleted = await client.request(
        "DELETE", f"{API}/auth/account", json={"password": PASSWORD, "confirm_username": "maruf_01"}
    )

    assert mismatch.status_code == 400 and mismatch.json()["error"]["code"] == "CONFIRMATION_MISMATCH"
    assert deleted.status_code == 204
    assert (await visitor.get(f"{API}/users/maruf_01")).status_code == 404
    explore = await visitor.get(f"{API}/posts/explore")
    assert explore.json()["items"] == []
    login = await visitor.post(LOGIN, json={"email": email_for("maruf_01"), "password": PASSWORD})
    assert login.status_code == 401


# ---- Google ------------------------------------------------------------------------------------------
async def test_google_login_disabled_when_not_configured(client: AsyncClient) -> None:
    response = await client.get(f"{API}/auth/google/login")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FEATURE_DISABLED"


async def test_google_login_redirects_with_state_cookie(client: AsyncClient, monkeypatch, settings) -> None:  # type: ignore[no-untyped-def]
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(settings, "google_client_secret", SecretStr("client-secret"))

    response = await client.get(f"{API}/auth/google/login", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/")
    state = cookie_value(response, "oauth_state")
    assert state and f"state={state}" in location


async def test_google_callback_rejects_state_mismatch(client: AsyncClient, monkeypatch, settings) -> None:  # type: ignore[no-untyped-def]
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "google_client_id", "client-id")
    monkeypatch.setattr(settings, "google_client_secret", SecretStr("client-secret"))

    response = await client.get(
        f"{API}/auth/google/callback?code=abc&state=forged",
        headers={"Cookie": "oauth_state=different"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "error=google_failed" in response.headers["location"]
    assert cookie_value(response, "access_token") is None


async def test_google_login_creates_account_and_links_by_email(client: AsyncClient) -> None:
    from app.db.session import SessionFactory
    from app.modules.auth.google import GoogleProfile
    from app.modules.auth.service import AuthService

    async with SessionFactory() as session:
        created = await AuthService(session).login_with_google(
            GoogleProfile(sub="g-123", email="new.person@example.com", name="New Person")
        )
    assert created.user.is_email_verified and created.user.password_hash is None
    assert created.user.username == "newperson"

    # An unverified password account for the same address is taken over safely:
    # its password is wiped so a pre-registering attacker cannot keep access.
    await client.post(REGISTER, json=body("victim"))
    async with SessionFactory() as session:
        linked = await AuthService(session).login_with_google(
            GoogleProfile(sub="g-456", email="victim@example.com", name="Victim")
        )
    assert linked.user.password_hash is None and linked.user.google_sub == "g-456"
    attacker_login = await client.post(LOGIN, json={"email": "victim@example.com", "password": PASSWORD})
    assert attacker_login.status_code == 401
