# Deployment, Operations, Scaling

## 1. Environments and configuration

All configuration is environment variables (12-factor). Templates: `backend/.env.example` (local), `.env.prod.example` (server), `frontend/.env.example`. Real values live only on your machine / the hosting dashboard / GitHub Secrets, never in git.

| Variable | Local | Production |
|---|---|---|
| `ENVIRONMENT` | development | production |
| `DEBUG` / `LOG_JSON` | true / false | false / true |
| `COOKIE_SECURE` | false (http) | true |
| `DATABASE_URL`, `REDIS_URL` | docker compose | managed or compose services |
| `JWT_SECRET_KEY` | random, in `.env` | random, secret store |
| `FRONTEND_URL`, `CORS_ORIGINS` | http://localhost:3000 | https://your-domain |
| `EMAIL_BACKEND` | smtp -> Mailpit | smtp -> real provider |
| `TRUSTED_PROXY` | false | true (only behind your nginx/platform proxy) |
| `BACKEND_URL` (frontend) | http://localhost:8001 | http://backend:8000 or your API URL |

## 2. Free staging (learn the flow, ~50-300 registered users)

| Part | Service | Notes |
|---|---|---|
| Frontend | Vercel | set `BACKEND_URL` to the API URL; auto-deploys from GitHub |
| Backend | Render / Fly.io / Railway (Docker, root `backend/`) | start command is in the Dockerfile; set env vars; free tiers sleep when idle |
| Database | Neon / Supabase | use the **pooled** URL, `postgresql+asyncpg://...` (replace `postgres://`) |
| Redis | Upstash | `rediss://...` URL; mind the monthly command cap |
| Images | Cloudflare R2 | `STORAGE_BACKEND=s3`, `S3_*`, `MEDIA_PUBLIC_BASE_URL` |

Run migrations once per deploy: `alembic upgrade head` (Render: pre-deploy command; Fly: release command). Free-tier limits change: re-check pricing pages.
Cookie rule: browser, frontend and `/api` must be **one site**. Vercel rewrites `/api` to the backend (already configured in `next.config.mjs`), so cookies stay first-party.

## 3. Production on one VPS (about 1,000 users)

A 2 vCPU / 4 GB VPS (Hetzner, DigitalOcean, ~$5-15/month) is enough.

```bash
# on the server (Ubuntu): install Docker, then
git clone https://github.com/<you>/circkle.git && cd circkle
cp .env.prod.example .env.prod && nano .env.prod       # fill every value
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml logs -f backend1
```
Stack: nginx -> backend1 + backend2 (+ frontend) -> Postgres + Redis, media on a shared volume. `migrate` runs first and exits. Update = `git pull` + the same `up -d --build`.
Optional demo data on staging only: `docker compose -f docker-compose.prod.yml run --rm backend1 python -m scripts.seed` is **refused in production**; set `ENVIRONMENT=staging` for a staging server.

## 4. Domain and HTTPS

1. Buy a domain; add an `A` record to the server IP.
2. Easiest HTTPS: put **Cloudflare** (free) in front, SSL mode "Full (strict)" with an origin certificate, or run **Caddy** in front of nginx (automatic Let's Encrypt). nginx here listens on :80 and expects TLS to be terminated before it.
3. Set `FRONTEND_URL`, `CORS_ORIGINS`, `GOOGLE_REDIRECT_URI` to the final `https://` URLs and keep `COOKIE_SECURE=true`.

## 5. CDN and caching

| Layer | What | How |
|---|---|---|
| Browser | images cached 1 year (immutable, random names) | `Cache-Control` from `/media` |
| nginx | `/media/*` proxy cache 7 days | `proxy_cache` in `deploy/nginx/nginx.conf` |
| Cloudflare (free CDN) | caches `/media/*` and `/_next/static/*` at the edge | Cache Rules: "URI path starts with /media/ -> Eligible for cache, Edge TTL 1 month". Never cache `/api/*` |
| Object storage + CDN | best for scale | `STORAGE_BACKEND=s3`, R2 bucket with a custom domain, `MEDIA_PUBLIC_BASE_URL=https://media.example.com` |
| Redis | public profile cache 60 s, rate limit counters | `core/cache.py`, `core/rate_limit.py` |
| HTTP | API responses are `no-store` (personalised, cookie-based) | middleware |

Cache invalidation rule: data that changes -> delete its key (profiles on update/follow/post). Media never needs invalidation because files are immutable.

## 6. CI/CD (step by step, for beginners)

**CI** = GitHub runs your tests on every push. Already set up in `.github/workflows/ci.yml`.
**CD** = after CI passes on `main`, deploy automatically.

1. Repo Settings -> Branches -> add rule for `main`: require PR and status checks "backend", "frontend", "docker".
2. Staging (free): connect the repo to Vercel and Render. Each merge to `main` redeploys. Nothing else to script.
3. VPS deploy (optional workflow, add `.github/workflows/deploy.yml`):
```yaml
name: Deploy
on:
  workflow_run:
    workflows: [CI]
    branches: [main]
    types: [completed]
jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd ~/circkle && git pull
            docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```
Add `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` in Settings -> Secrets and variables -> Actions. Use a dedicated deploy key, not your personal one.
4. Rollback: `git revert <bad commit>` + push (redeploys). For a bad migration, restore the backup (section 9) or write a reverse migration.

## 7. Load balancing and scaling

- Backends are **stateless** (sessions in cookies/DB, limits and cache in Redis, files on a shared volume/object storage), so you can add instances.
- nginx `least_conn` over `backend1`, `backend2` with passive health checks (`max_fails`). Add `backend3` by copying the service and the `upstream` line.
- Per instance: uvicorn workers. For more CPU use `--workers N` (N = cores) in the Dockerfile `CMD`, or more containers.
- DB connections: `DB_POOL_SIZE` x instances must stay below Postgres `max_connections` (default 100). With many instances add PgBouncer.
- 100k users: managed Postgres + read replica, object storage/CDN for media, queue + workers, autoscaling platform. See ROADMAP.md.

## 8. Logs, monitoring, error tracking

- **Logs:** JSON lines on stdout (`LOG_JSON=true`): `timestamp, level, logger, message, request_id, method, path, status, duration_ms`. Read: `docker compose logs -f backend1`. Find one failing request: grep its `request_id` (returned in every error body and the `X-Request-ID` header). Ship to Loki/Better Stack/Grafana Cloud later.
- **Sentry:** create a project, set `SENTRY_DSN`. PII sending is off.
- **Uptime:** free UptimeRobot/Better Stack hitting `https://your-domain/health/ready` every minute; alert by email.
- **Health:** `/health` (process alive, Docker HEALTHCHECK) vs `/health/ready` (database reachable). Load balancers use readiness.
- **Metrics (later):** Prometheus + Grafana, see ROADMAP.md.

## 9. Backups and disaster recovery

| Asset | Backup | Frequency | Keep |
|---|---|---|---|
| PostgreSQL | `pg_dump` to compressed file, copied off the server (R2/S3/another host) | daily | 14 daily + 3 monthly |
| Media | provider versioning, or `rsync`/`rclone` of the volume | daily | 14 days |
| Secrets | password manager | on change | - |

```bash
# /etc/cron.d/circkle-backup  (daily 02:30)
30 2 * * * root cd /home/deploy/circkle && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U circkle -Fc circkle > /backups/circkle-$(date +\%F).dump

# restore drill (do it monthly, on a scratch database)
docker compose -f docker-compose.prod.yml exec -T db createdb -U circkle restore_test
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U circkle -d restore_test --no-owner < /backups/circkle-2026-01-01.dump
```
Managed Postgres (Neon/Supabase/RDS) gives point-in-time recovery: turn it on.
**Targets:** RPO (max data loss) 24 h with daily dumps (minutes with PITR); RTO (time to be back) under 1 h. **Runbook for a dead server:** new VPS -> install Docker -> clone repo -> restore `.env.prod` from the password manager -> start `db` only -> `pg_restore` -> start the rest -> copy media backup into the `media_data` volume -> point DNS/Cloudflare -> verify `/health/ready` and log in.
**Failover:** two backends already survive one crashing (nginx retries the other). Database failover needs a managed HA Postgres (or a replica you promote): not included on a single VPS.

## 10. Release checklist

- [ ] CI green on `main`; migrations reviewed (`alembic upgrade head` on a staging copy first)
- [ ] Staging smoke test: register, login, post, image upload, comment, react, reset password email, logout
- [ ] Security checklist in SECURITY.md
- [ ] Backup taken right before the release
- [ ] Deploy, watch logs + Sentry for 15 minutes, check `/health/ready`
- [ ] Tag the release: `git tag v1.0.0 && git push --tags`

## 11. Dependency locking

`requirements.txt` uses compatible ranges. After your first successful install, freeze exact versions for reproducible builds: `pip freeze | Out-File -Encoding utf8 requirements.lock.txt` and install from it in the Dockerfile. Commit `frontend/package-lock.json` too (then CI/Docker use `npm ci`).
