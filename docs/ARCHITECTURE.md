# Architecture

## Shape: modular monolith

One deployable backend, split into modules with strict one-way layering:

```
router (HTTP, validation, rate limit)  ->  service (business rules)  ->  repository (SQL)  ->  models
```

Modules: `auth`, `users`, `posts`, `comments`, `reactions`, `media`, `admin`.
Rules that keep a later split into microservices cheap:

- A module talks to another module only through its **service/repository functions**, never by reaching into its tables in random places.
- IDs are UUIDs (safe to share across services). No auto-increment ids leak.
- Cross-module side effects are isolated (cache invalidation helpers, `dispatch_event` webhooks), so they can become events later.
- Stateless app servers: all state is in PostgreSQL, Redis or object storage.

## Request path (production-like)

```
Browser -> (CDN) -> nginx (load balancer, cache) -> backend1 / backend2 (FastAPI)  -> PostgreSQL
                                   |                                              -> Redis (limits, cache)
                                   +-> frontend (Next.js)                         -> media storage
```

The browser only talks to **one origin**. Next.js (dev) and nginx (prod) forward `/api/*` and `/media/*` to FastAPI, so cookies are first-party and CORS is not needed.

## Data model

```
users 1-* refresh_tokens          users 1-* auth_tokens (email verify / password reset)
users 1-* media                   users 1-* posts *-0..1 media
posts 1-* comments *-1 users      posts 1-* reactions *-1 users   (PK post_id+user_id: one reaction per user)
users *-* users via follows (follower_id, followee_id)
```

Indexes follow the queries: `(author_id, created_at, id)` for profile timelines, `(created_at, id)` for explore, `(post_id, created_at, id)` for comments, `(followee_id, created_at)` for follower lists. Deleting a user cascades to everything they own (database `ON DELETE CASCADE`).

## Key design decisions

| Decision | Why |
|---|---|
| Cursor (keyset) pagination | Stable while data changes, constant cost on deep pages |
| Counts via correlated subqueries | One query per page, no N+1; fine to ~100k posts. Next step: denormalised counters |
| Cache-aside for public profiles (60 s TTL) | Cheap win; invalidated on profile/follow/post change |
| Rate limit in Redis | Shared by all instances; in-memory fallback only for dev/tests |
| Images re-encoded to WebP on upload | Strips EXIF/GPS, kills polyglot files, smaller downloads |
| Refresh-token rotation with reuse detection | Stolen refresh tokens are detected and the session killed |
| Migrations run as a one-shot job | Several backend replicas must never race to migrate |

## Scaling path

| Users | What changes |
|---|---|
| ~1,000 | One VPS, `docker-compose.prod.yml` (2 backends + nginx), Redis, local/R2 media |
| ~10,000 | Managed Postgres + backups, object storage + CDN for all media, Sentry, uptime checks |
| ~100,000 | Read replica for feeds, denormalised counters, background workers + queue, autoscaling backends |
| Beyond | Split chat/notifications/media into services (see ROADMAP.md) |
