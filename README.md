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


