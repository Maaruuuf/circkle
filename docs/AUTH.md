# Authentication & Authorization

## 1. Approach

Cookie-based sessions with JWT access tokens and rotating refresh tokens. Tokens live in **HttpOnly + Secure + SameSite=Lax** cookies, so JavaScript (and therefore XSS) can never read them; SameSite plus an Origin check stops cross-site request forgery.

## 2. Roles and permissions

| Capability | Guest | user | admin |
|---|:-:|:-:|:-:|
| Read profiles, explore, single posts, comments | yes | yes | yes |
| Feed, post, comment, react, follow, upload | - | yes | yes |
| Edit/delete own posts and comments | - | yes | yes |
| Delete a comment on your own post | - | yes | yes |
| Delete any post/comment | - | - | yes |
| Edit someone else's post | - | - | **no, nobody** |
| Ban/unban users, change roles, stats | - | - | yes (not on themselves) |

Roles are stored in the database (`users.role`, constrained to `user|admin`), **never** read from the token or from request bodies. Make the first admin with `python -m scripts.promote_admin you@example.com` (the seed's first user is an admin).

## 3. Registration flow

1. `POST /auth/register {email, username, password}` -> 201. Password is hashed with Argon2 (off the event loop). Email/username are lowercased. Duplicates and reserved names -> 409 `EMAIL_OR_USERNAME_TAKEN`.
2. A single-use verification token (24 h, only its SHA-256 hash stored) is emailed in the background.
3. User logs in. If `REQUIRE_EMAIL_VERIFICATION=true`, unverified users get 403 `EMAIL_NOT_VERIFIED`.

## 4. Email verification

Link: `<FRONTEND_URL>/verify-email?token=...` -> frontend calls `POST /auth/verify-email {token}`. Token is single use, expires, and a newer one invalidates older ones. `POST /auth/resend-verification {email}` always answers 202 (no account enumeration).

## 5. Login flow

```
POST /auth/login {email, password}
 200 {user}  + Set-Cookie: access_token (15 min, path /) + Set-Cookie: refresh_token (7 d, path /api/v1/auth)
 401 INVALID_CREDENTIALS     (same message for unknown email and wrong password; a dummy hash is verified so timing matches)
 403 ACCOUNT_DISABLED / EMAIL_NOT_VERIFIED   (only revealed AFTER the password was correct)
 429 RATE_LIMITED            (10/min per IP and 10/15 min per email)
```
Logging in to a self-deactivated account reactivates it.

## 6. Password reset (forgot password)

1. `POST /auth/forgot-password {email}` -> always 202. If the account exists, a 30-minute single-use link is emailed.
2. `POST /auth/reset-password {token, new_password}` -> sets the password, marks the email verified (they proved mailbox control), **revokes every session**. Old links stop working.

## 7. Social login (Google)

Enable by setting `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.
1. Google Cloud Console -> APIs & Services -> Credentials -> OAuth client (Web). Authorized redirect URI = `GOOGLE_REDIRECT_URI` (e.g. `http://localhost:3000/api/v1/auth/google/callback` locally).
2. Button -> `GET /auth/google/login`: random `state` stored in a short-lived HttpOnly cookie, redirect to Google.
3. `GET /auth/google/callback?code&state`: `state` must equal the cookie (CSRF), code is exchanged server-side (client secret never reaches the browser), only a **Google-verified** email is accepted.
4. Match by Google id, else by email, else create a new account (username derived from the email, no password: `has_password=false`).
5. **Pre-hijacking defence:** if an *unverified* password account already uses that email, its password is wiped before linking, so an attacker who pre-registered the victim's email cannot keep access.

## 8. Token management

| Token | Form | Lifetime | Storage |
|---|---|---|---|
| Access | JWT HS256 (`sub`, `type=access`, `iat`, `exp`) | 15 min | HttpOnly cookie, path `/` |
| Refresh | 48 random bytes, **opaque** | 7 days | HttpOnly cookie, path `/api/v1/auth`; DB stores only SHA-256 hash |
| Email / reset | 48 random bytes | 24 h / 30 min | DB hash only; single use |

- **Rotation:** every `POST /auth/refresh` revokes the used token and issues a new one in the same *family*.
- **Reuse detection:** presenting an already-used token (older than a 10 s grace window) revokes the whole family: a stolen token is detected the moment either party uses it. The grace window covers two browser tabs refreshing at once.
- Decoding pins the algorithm list, requires `exp/iat/sub`, checks `type`. Secret must be >= 32 chars (app refuses to start otherwise).
- Frontend: one shared in-flight refresh promise; a 401 triggers refresh then one retry.

## 9. Protected routes and middleware

**Backend (the real protection):** FastAPI dependencies `OptionalUser`, `CurrentUser` (401), `AdminUser` (403). Every protected route declares one; ownership is checked again inside the service. Middleware: request id + logging + security headers, Origin check (CSRF), CORS, rate limits.
**Frontend (UX only):** `RequireAuth` redirects guests to `/login?next=...` (the `next` value is validated by `safeNextPath` against open redirects); `AuthProvider` loads `/users/me` on start; admin pages use `<RequireAuth admin>`. A user who edits the JavaScript still hits the server checks.

## 10. RBAC implementation

`require_admin` dependency compares `user.role` (loaded fresh from the database on every request) with `UserRole.ADMIN`. Banned or deactivated users fail `get_optional_user` even with a still-valid access token, so bans take effect immediately. Admin endpoints refuse self-modification (no accidental lock-out or self-promotion path).

## 11. Profile management

`PATCH /users/me {display_name?, bio?}` and `POST /users/me/avatar`. Username and email are immutable in this version. `POST /auth/change-password {current_password, new_password}` requires the current password, logs out other devices and keeps this one signed in (new refresh family).

## 12. Account deletion / deactivation

- **Deactivate** `POST /auth/deactivate {password}`: profile and posts hidden, all sessions revoked; logging in again restores everything.
- **Delete** `DELETE /auth/account {password, confirm_username}`: needs the password (if set) and the typed username; the database cascades to posts, comments, reactions, follows, tokens; the user's image files are deleted from storage.

## 13. Security best practices in use

Argon2 hashing · password max length (no hash-DoS) · generic auth errors · per-IP **and** per-email login limits · HttpOnly/Secure/SameSite cookies · refresh path scoping · Origin check for CSRF · strict CORS · `extra="forbid"` request models · token hashes at rest · single-use email tokens · all sessions revoked on password reset/change · no secrets or tokens in logs · Sentry `send_default_pii=false`.

## 14. Environment variables

`JWT_SECRET_KEY` (required, >= 32 chars) · `ACCESS_TOKEN_EXPIRE_MINUTES` · `REFRESH_TOKEN_EXPIRE_DAYS` · `REFRESH_REUSE_GRACE_SECONDS` · `COOKIE_SECURE` (true except local http) · `COOKIE_DOMAIN` · `FRONTEND_URL` · `CORS_ORIGINS` · `REQUIRE_EMAIL_VERIFICATION` · `EMAIL_BACKEND`, `SMTP_*` · `GOOGLE_*` · `TRUSTED_PROXY` · `REDIS_URL` · `RATE_LIMIT_ENABLED`. In production the app **refuses to start** with `DEBUG=true`, `COOKIE_SECURE=false` or wildcard CORS.

## 15. Testing checklist (all automated in `backend/app/tests/test_auth.py` unless noted)

- [ ] Register: success, normalisation, duplicate, reserved name, bad input, no secrets in response
- [ ] Login: cookies flags, identical failure messages, unverified blocked when required
- [ ] Protected route without/with tampered cookie -> 401
- [ ] Refresh rotation, reuse detection, grace window, missing cookie
- [ ] Logout idempotent; logout-all revokes other devices
- [ ] Email verify single use; resend silent for unknown emails
- [ ] Forgot/reset flow; reset link single use; old password stops working
- [ ] Change password needs current one
- [ ] Deactivate hides profile, login reactivates; delete removes content
- [ ] Google: disabled by default, state cookie, state mismatch rejected, account linking + pre-hijack defence
- [ ] Rate limit on login/register (`test_platform.py`); RBAC (`test_admin_rbac.py`)
- [ ] Manual: expired access token silently refreshes in the browser; two tabs refreshing together stay logged in

## 16. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Logged in but next request is 401 | Cookie not stored: `COOKIE_SECURE=true` on plain http (use `false` locally), or frontend and API on different sites (use the Next.js proxy) |
| Cookie not sent to `/users/me` | Frontend must use `credentials: "include"`; same origin via the proxy |
| 403 `CSRF_ORIGIN_REJECTED` | Browser origin not in `CORS_ORIGINS` / `FRONTEND_URL` |
| Random logouts every 15 min | Refresh failing: check `/api/v1/auth/refresh` response and that the refresh cookie path matches the URL the browser uses |
| Logged out on one tab after another refreshed | Beyond the grace window; extend `REFRESH_REUSE_GRACE_SECONDS` slightly or check clock/latency |
| 429 while developing | Set `RATE_LIMIT_ENABLED=false` locally, or wait `Retry-After` seconds |
| Google: `redirect_uri_mismatch` | `GOOGLE_REDIRECT_URI` must equal the console value character for character |
| No emails | Local: open Mailpit http://localhost:8025 and use `EMAIL_BACKEND=smtp`; check `docker compose ps` |
| App exits on start | Read the first error: missing `JWT_SECRET_KEY`/`DATABASE_URL` or an unsafe production setting |
