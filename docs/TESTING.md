# Testing Strategy & Quality Assurance

## 1. Strategy and goals

Goals: ship changes safely, catch regressions in CI within minutes, and prove the security rules. We follow the test pyramid: many fast unit tests, a solid layer of API/integration tests against a real database, a few end-to-end browser flows, plus targeted performance and security checks.

| Layer | What it proves | Tool | Where |
|---|---|---|---|
| Unit | Pure logic: hashing, JWT, cursors, signatures, image processing, formatters | pytest, Vitest | `test_security_unit.py`, `frontend/lib/*.test.ts` |
| API / integration | Endpoint + validation + auth + database together | pytest + httpx + real PostgreSQL | `app/tests/test_*.py` |
| E2E | Real browser user journeys | Playwright | `frontend/e2e` |
| Performance | p95 latency and error rate under load | k6 | `loadtests/k6` |
| Security | OWASP issues | pytest rules + ZAP + pip-audit/npm audit | see section 10 |
| Database | Migrations, constraints, backups | Alembic in CI, restore drill | section 11 |

## 2. Environments

| Env | Purpose | Data | Notes |
|---|---|---|---|
| Local | Development | Seed data | Docker infra + venv + npm; `y_test` database for pytest |
| CI | Every push | Throwaway Postgres service | Fresh DB each run |
| Staging | Pre-release smoke/UAT/load | Seed or anonymised data | Same Docker images as production; real SMTP sandbox |
| Production | Real users | Real | Only read-only smoke checks (`/health/ready`, login with a test account) |

Never run tests that truncate tables against a database whose name does not end with `_test` (the test config refuses to start otherwise).

## 3. Tools

pytest + pytest-asyncio + pytest-cov (backend) · httpx `AsyncClient` with ASGI transport (no network needed) · Vitest (frontend units) · Playwright (E2E, Chromium) · k6 (load) · ruff (lint) · `alembic check` (schema drift) · OWASP ZAP, pip-audit, npm audit (security) · Postman optional: import `http://localhost:8001/openapi.json`.

## 4. Unit testing guide

Pure functions, no database, no network. Example (`test_security_unit.py`):

```python
def test_password_hash_roundtrip_and_is_salted() -> None:
    first, second = hash_password("s3cret-password"), hash_password("s3cret-password")
    assert first != second and verify_password("s3cret-password", first)
```
Naming: `test_<behaviour>_<condition>`. One behaviour per test. Arrange / act / assert.

## 5. API testing guide

Every endpoint test checks: **happy path, validation failure, unauthenticated (401), forbidden (403), not found (404)** and that responses never leak secrets. Example:

| Request | Expected |
|---|---|
| `POST /auth/register` valid | 201, no `password`/`password_hash` in body |
| same again | 409 `EMAIL_OR_USERNAME_TAKEN` |
| `POST /auth/register` with `role: "admin"` | 422 (unknown field) |
| `GET /users/me` no cookie | 401 `UNAUTHENTICATED` |
| `PATCH /posts/{id}` as other user | 403 |
| `GET /posts/explore?limit=500` | 422 |

Manual with curl/Postman: see API.md section 13.

## 6. Integration testing guide

Tests run the real FastAPI app in-process against PostgreSQL (`y_test`). Tables are created from the models once per session and truncated after each test; Redis is replaced by the in-memory fallback; email goes to an in-memory outbox (`OUTBOX`) so tests can read verification links. Several "browsers" = several `AsyncClient`s via the `make_client` fixture, each with its own cookie jar. Helpers: `signup()`, `create_post()`, `token_from_outbox()` in `app/tests/helpers.py`.

## 7. End-to-end (E2E) guide

```powershell
# terminal 1: docker compose up -d ; backend with RATE_LIMIT_ENABLED=false ; terminal 2: npm run dev
cd frontend
npx playwright install chromium     # once
npm run test:e2e
```
Key flows covered in `e2e/auth-and-posts.spec.ts`:
1. Guest opening `/` is redirected to `/login`.
2. Register -> log in -> create post -> react -> comment -> log out.
3. Wrong password shows a generic error.
4. Unknown profile shows the 404 page.

Add next: follow/unfollow, image upload, password reset (read the link from Mailpit's API at `http://localhost:8025/api/v1/messages`), admin ban.

## 8. UI/UX checklist (manual before each release)

- [ ] **Browsers:** latest Chrome, Firefox, Safari (macOS/iOS), Edge; Android Chrome
- [ ] **Responsive:** 360 px phone, 768 px tablet, 1280 px+ desktop; bottom nav on mobile, sidebar on desktop; no horizontal scroll
- [ ] **Accessibility:** everything reachable and usable by keyboard (Tab order, visible focus); form fields have labels; images have alt text; errors use `role="alert"`; colour contrast >= 4.5:1; screen reader pass with NVDA/VoiceOver on login and post flows; `prefers-reduced-motion` respected; run Lighthouse (accessibility >= 90)
- [ ] **States:** loading spinners, empty lists, error messages, disabled buttons while saving
- [ ] **Forms:** validation messages are clear; double-click does not double-submit
- [ ] **Slow network:** throttle to "Slow 3G" in DevTools; app stays usable
- [ ] **Session expiry:** wait 16 min idle, then act: the app should silently refresh

## 9. Performance testing

Targets (non-functional): API p95 < 200 ms for reads, error rate < 1%, uptime 99.9%.
```powershell
python -m scripts.seed
# run the API with RATE_LIMIT_ENABLED=false
docker run --rm -i --network host -e BASE_URL=http://localhost:8001 grafana/k6 run - < loadtests/k6/smoke.js
```
The script ramps to 50 virtual users and fails if p95 > 200 ms or errors > 1%. Scale up (200, 1000 VUs) against **staging** only. Watch DB connections, CPU, and Redis. Save results in `docs/perf/` with the date and commit. Login is excluded from the p95 goal on purpose: Argon2 is deliberately slow (~50-100 ms of CPU).

## 10. Security testing

| Check | How |
|---|---|
| Access control, CSRF origin, CORS, rate limits, injection escapes, upload validation | Automated pytest (see SECURITY.md table) |
| Dependency vulnerabilities | `pip-audit -r backend/requirements.txt`, `npm audit` |
| Web scan | `docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://staging.example.com` |
| SQL injection | Try `' OR 1=1--` in search, login, usernames: expect 422/empty, never 500 |
| XSS | Post `<img src=x onerror=alert(1)>`: must show as plain text |
| Auth | Reuse an old refresh token (expect session revoked); tamper JWT; use another user's UUIDs |
| Secrets | `git log -p | findstr /i "password secret key"` sanity check; enable GitHub secret scanning |

## 11. Database testing

- **Constraints:** lowercase email/username, role/reaction type checks, one reaction per user (PK), no self-follow, post needs text or image: covered indirectly by API tests; add direct tests when you add constraints.
- **Migrations:** CI runs `alembic upgrade head`, `downgrade base`, `upgrade head`, then `alembic check` (fails if models and migrations drift).
- **Integrity:** deleting a user cascades (see `test_delete_account_removes_user_and_their_content`).
- **Backups:** monthly restore drill (DEPLOYMENT.md section 9): restore the latest dump into a scratch database and run `/health/ready` + a row count comparison.

## 12. Test data

| Need | How |
|---|---|
| Dev/demo data | `python -m scripts.seed` -> 10 users (`ada` is admin), 10 posts, follows. Password `Circkle#Dev2026` (DEV ONLY, refuses to run in production) |
| Automated tests | Created per test through the API with `signup()`; DB truncated after each test |
| More volume | Copy `seed.py`, loop with Faker (add to dev requirements) for load tests on staging |

## 13. Test scenarios per feature (from FEATURES.md)

| Feature | Scenarios | Test file |
|---|---|---|
| Register/Login/Logout | success, duplicates, reserved names, bad input, generic failures, cookie flags, logout idempotent | `test_auth.py` |
| Refresh | rotation, reuse detection, grace window | `test_auth.py` |
| Email verify / reset | single use, expiry path, no enumeration | `test_auth.py` |
| Google login | disabled, state cookie, mismatch, linking | `test_auth.py` |
| Profile | update, forbidden fields, public view hides email, cache invalidation, avatar | `test_users.py` |
| Follow | idempotent, self-follow, lists, counts | `test_users.py` |
| Posts | create/validate, image attach, foreign media, edit/delete permissions, hidden when deactivated | `test_posts.py` |
| Feed | only followed + own, order, cursor pagination without gaps, invalid cursor | `test_posts.py` |
| Comments | create/validate, order, pagination, delete permissions | `test_comments_reactions.py` |
| Reactions | set/change/remove, one per user, counts, validation | `test_comments_reactions.py` |
| Media | webp re-encode, EXIF stripped, type/size limits, traversal | `test_media.py` |
| Admin/RBAC | guest/user blocked, ban logs out, no self-change, delete any post | `test_admin_rbac.py` |
| Platform | headers, request id, error format, CSRF, CORS, rate limits, health | `test_platform.py` |

## 14. Bug report template and severity

Use `.github/ISSUE_TEMPLATE/bug_report.md`.

| Severity | Definition | Response |
|---|---|---|
| S1 Critical | Security hole, data loss, outage | Fix now, hotfix release |
| S2 Major | Core feature broken, no workaround | Fix in current iteration |
| S3 Minor | Workaround exists | Backlog, next release |
| S4 Trivial | Cosmetic | When convenient |

Always include the `X-Request-ID` from the failing response: it finds the exact log lines.

## 15. Continuous testing (GitHub Actions)

`.github/workflows/ci.yml` on every push/PR: ruff -> migrations up/down/up -> `alembic check` -> pytest with coverage (fails under 60%) -> frontend typecheck, lint, Vitest, build -> Docker image builds. `.github/workflows/e2e.yml` (manual + weekly) runs Playwright against the real stack. In GitHub: Settings -> Branches -> require the CI checks before merging.

## 16. Run everything locally

```powershell
docker compose up -d
cd backend; .venv\Scripts\Activate.ps1
ruff check .
pytest --cov
alembic upgrade head; alembic check
cd ..\frontend
npm run typecheck; npm run lint; npm test; npm run build
npm run test:e2e        # with backend (RATE_LIMIT_ENABLED=false) + frontend running
```

## 17. Coverage goals

Backend: CI gate 60% today, **goal 80%+**, 90%+ for `core/` and `modules/auth`. Report: `pytest --cov --cov-report=html` then open `backend/htmlcov/index.html`; CI uploads `coverage.xml`. Raise `--cov-fail-under` in `ci.yml` as the suite grows. Frontend: unit-test pure helpers; cover behaviour with E2E rather than chasing a percentage.

## 18. Known limitations / watch list

- Rate-limit and cache fall back to in-process memory without Redis (tests only; never in production).
- Webhook delivery has no retries yet.
- E2E covers the main journey only; image upload, password reset and admin flows need specs.
- Search is prefix `LIKE` without a trigram index: re-measure beyond ~100k users.
- Feed counts are computed per query: re-measure p95 beyond ~100k posts.
- Local media storage is per-server; multi-server needs the shared volume (compose does this) or S3/R2.
- Google login and S3 storage code paths are only unit-tested at the boundary (they need real credentials): do a manual check in staging.
