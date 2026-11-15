# Security

## OWASP Top 10 (2021) mapping

| Risk | What Circkle does | Where |
|---|---|---|
| A01 Broken access control | Server-side checks in every service; roles from DB; UUID ids; admin self-modify blocked; tests per rule | `modules/*/service.py`, `test_admin_rbac.py`, `test_posts.py` |
| A02 Cryptographic failures | Argon2; HTTPS + HSTS in production; tokens hashed at rest; secrets only in env | `core/security.py`, `core/middleware.py` |
| A03 Injection | SQLAlchemy parameterised queries only; LIKE wildcards escaped; Pydantic validation; React escapes output (no `dangerouslySetInnerHTML`) | `users/repository.py` |
| A04 Insecure design | Rate limits, refresh rotation + reuse detection, pre-hijack defence, single-use tokens | `core/rate_limit.py`, `auth/service.py` |
| A05 Security misconfiguration | Production refuses unsafe settings; docs hidden; security headers; CSP on the frontend; non-root containers | `core/config.py`, `next.config.mjs` |
| A06 Vulnerable components | Dependabot/`pip-audit`/`npm audit` (see below); small dependency list | CI |
| A07 Auth failures | Generic errors, brute-force limits, strong hashing, session revocation | `auth/*` |
| A08 Integrity failures | Signed webhooks (HMAC), pinned lockfiles, CI builds | `core/webhooks.py` |
| A09 Logging/monitoring | JSON logs with request ids, Sentry, health checks; no secrets logged | `core/logging.py` |
| A10 SSRF | Server only calls fixed Google/webhook/S3 URLs from config, never user-supplied URLs | `auth/google.py` |

## CSRF
Cookies are `SameSite=Lax`; additionally any POST/PUT/PATCH/DELETE carrying an `Origin` that is not ours gets 403. All state changes use non-GET methods.

## CORS
Explicit allow-list (`CORS_ORIGINS`), credentials allowed only for those origins, never `*`. In normal use the proxy makes everything same-origin so CORS is rarely exercised.

## SQL injection
No string-built SQL anywhere. Search escapes `%` `_` `\`. Test: `test_search_users_by_prefix_and_escapes_wildcards`.

## XSS
No HTML is rendered from user data (React escapes text). Cookies are HttpOnly so XSS cannot steal sessions. Frontend CSP restricts script/connect sources (production build).

## Uploads
Size capped while streaming, decoded with Pillow, pixel-bomb limit, re-encoded to WebP (EXIF and hidden payloads removed), random server-side file names, served with `nosniff`, path traversal blocked by regex + resolved-path check.

## Secrets
Only `*.example` files are committed. `.env`, `.env.prod` are git-ignored. Rotating a leaked secret: generate a new one, redeploy, (for `JWT_SECRET_KEY` everyone is logged out, which is the intent). If a secret was ever pushed, deleting the commit is not enough: rotate it. Enable GitHub secret scanning + push protection on the repo.

## Dependency hygiene
Run regularly: `pip install pip-audit && pip-audit -r backend/requirements.txt` and `npm audit` in `frontend/`. Turn on Dependabot (Settings -> Code security).

## Row Level Security (RLS)
Authorization lives in the application. RLS adds a second lock inside PostgreSQL. A ready-to-review example is in `backend/sql/rls_posts.sql`. It is **not enabled** because it only helps when (1) the app connects as a non-owner role, and (2) every transaction sets `app.current_user_id`. Adopt it when several services share one database. Test in staging first: cascades and background jobs need a privileged role.

## Reporting
Create a private GitHub security advisory on the repo, or email the maintainer. Never post exploits in public issues.

## Pre-release security checklist
- [ ] `ENVIRONMENT=production`, `DEBUG=false`, `COOKIE_SECURE=true`, strong `JWT_SECRET_KEY`
- [ ] HTTPS everywhere (HSTS on)
- [ ] `/docs` not reachable; `/health/ready` not leaking details beyond ok/unavailable
- [ ] Rate limits on with Redis (`REDIS_URL` set), `TRUSTED_PROXY=true` only behind your own nginx
- [ ] Database not exposed to the internet; backups tested
- [ ] `pip-audit` and `npm audit` clean (or accepted)
- [ ] OWASP ZAP baseline scan against staging (see TESTING.md)
