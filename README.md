# Circkle

A small Instagram-style social network: register/login, profiles, follow, text + image posts, comments and reactions.
Built as a **modular monolith** (FastAPI + PostgreSQL + Redis, Next.js frontend) that can later be split into microservices.

| Part | Tech |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2 |
| Data | PostgreSQL 16, Redis 7 (rate limits + cache) |
| Media | Local disk or S3-compatible storage (Cloudflare R2, S3, MinIO) + CDN |
| Ops | Docker, nginx load balancer, GitHub Actions, Sentry, structured JSON logs |

Docs: [Architecture](docs/ARCHITECTURE.md) · [API](docs/API.md) · [Auth](docs/AUTH.md) · [Testing](docs/TESTING.md) · [Security](docs/SECURITY.md) · [Deployment](docs/DEPLOYMENT.md) · [Features](docs/FEATURES.md) · [Roadmap](docs/ROADMAP.md)

## Run it locally (Windows PowerShell; macOS/Linux are the same idea)

You need: Docker Desktop, Python 3.12, Node 20, Git.

```powershell
# 1. Infrastructure: Postgres, Redis, Mailpit (a fake inbox for emails)
docker compose up -d
docker compose exec db psql -U y -d y -c "CREATE DATABASE y_test;"   # once, for tests

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # paste the result as JWT_SECRET_KEY in .env
alembic upgrade head
python -m scripts.seed                      # 10 users + 10 posts
uvicorn app.main:app --reload --port 8001   # API docs: http://localhost:8001/docs

# 3. Frontend (new terminal)
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev                                 # http://localhost:3000
```

Log in with `ada@example.com` / `Circkle#Dev2026` (Ada is the admin; all 10 seed users share this DEV-ONLY password).
Emails (verification, password reset) appear in Mailpit at http://localhost:8025.

## Everyday commands

```powershell
cd backend
pytest                                  # all backend tests
pytest --cov                            # with coverage
ruff check .                            # lint
alembic revision --autogenerate -m "describe change"   # after editing a model; READ the generated file
alembic upgrade head
alembic check                           # fails if models and migrations disagree

cd ../frontend
npm run typecheck; npm run lint; npm test; npm run build
npm run test:e2e                        # needs backend + frontend running
```

## Project layout

```
backend/app/
  core/        config, security, errors, rate limit, cache, email, webhooks, middleware, pagination
  db/          engine/session, base, model registry
  modules/     auth, users, posts, comments, reactions, media, admin   (router -> service -> repository -> models)
  tests/       unit + integration tests (real PostgreSQL)
backend/alembic/   migrations        backend/scripts/   seed + admin tools
frontend/app/      pages (App Router)   frontend/components/   UI   frontend/lib/   API client + helpers
deploy/nginx/      load balancer + media cache config
docs/              the documentation
```

## Rules of the house

1. Never commit `.env` files or real secrets (only the `*.example` files).
2. Every schema change goes through an Alembic migration.
3. Every feature: branch -> code -> tests -> docs -> PR -> green CI -> merge.
4. Authorization is enforced on the **server**; frontend guards are only for user experience.

## Upgrading an existing Phase 0-2 checkout

This project replaces the earlier hand-built backend (same `backend/`, `frontend/`, CI layout) and ships one fresh initial migration.

1. Extract the zip over your repo folder (keep your `.git`). Keep your own `backend/.env`; add the new variables from `backend/.env.example` (`FRONTEND_URL`, `CORS_ORIGINS`, `EMAIL_BACKEND`, ...).
2. **Reset your local dev database** (the old migration history is replaced; dev data is disposable):
   ```powershell
   docker compose down -v
   docker compose up -d
   docker compose exec db psql -U y -d y -c "CREATE DATABASE y_test;"
   cd backend; alembic upgrade head; python -m scripts.seed
   ```
3. Frontend: delete `frontend/node_modules` and `frontend/package-lock.json` (it came from a different Next.js version), then `npm install` and commit the new `package-lock.json`.
4. `pip install -r requirements-dev.txt` in your venv.
