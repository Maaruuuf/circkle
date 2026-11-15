# Roadmap and "advanced topics for later"

Not built yet on purpose. Each item has the signal that tells you it is time.

| Topic | Add it when | Sketch |
|---|---|---|
| Background jobs + queue (RabbitMQ or Redis/ARQ) | Emails slow down requests, webhooks need retries, or counters need async sync | Producer in the service layer, worker container, idempotent handlers, dead-letter queue |
| Denormalised counters | Feed queries exceed the p95 budget | `reaction_count`/`comment_count` columns updated in the same transaction (or by a worker), Redis for hot posts |
| Read replica | Primary CPU > ~60% from reads | Second async engine for read-only endpoints (feed, explore, profiles) |
| Chat microservice (WeChat-style) | You start building messaging | Separate service + WebSockets, own database, Redis pub/sub for fan-out, auth by verifying the same JWT (share the public verification key: switch to RS256/EdDSA first) |
| Notifications service | Likes/comments/follows should alert users | Consume domain events (`post.created`, `reaction.set`) from the queue |
| Search service | `LIKE` search gets slow (> ~100k users) | PostgreSQL trigram index first, then OpenSearch/Meilisearch |
| Postgres Row Level Security | You have several services touching one database | See `backend/sql/rls_posts.sql` and docs/SECURITY.md |
| Prometheus + Grafana | You need dashboards beyond Sentry + logs | `/metrics` endpoint, node/postgres/redis exporters |
| Kubernetes | You run many services and need autoscaling | Not before the compose setup stops being enough |
| 2FA (TOTP) / passkeys | Real users with valuable accounts | New `auth` endpoints + recovery codes |

Webhooks today: best-effort POST with HMAC signature (`backend/app/core/webhooks.py`). Move to the queue for retries.
