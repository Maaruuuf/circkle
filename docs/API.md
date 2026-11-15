# API Specification

Interactive docs while developing: `http://localhost:8001/docs` (disabled in production).

## 1. Base URL and versioning

| Environment | Base URL |
|---|---|
| Local | `http://localhost:8001/api/v1` (or `http://localhost:3000/api/v1` through Next.js) |
| Production | `https://<your-domain>/api/v1` |

The version is in the path (`/api/v1`). Breaking changes get `/api/v2`; additive changes (new fields/endpoints) stay in v1. Clients must ignore unknown response fields.
Non-versioned: `GET /health`, `GET /health/ready`, `GET /media/{file}.webp`.

## 2. Authentication and authorization

- Login sets two **HttpOnly, Secure, SameSite=Lax** cookies: `access_token` (JWT, 15 min, path `/`) and `refresh_token` (7 days, path `/api/v1/auth` only). Clients never read or send tokens by hand: use `credentials: "include"`.
- When an access token expires, call `POST /auth/refresh` (cookie rotates) and retry.
- Roles: `user`, `admin`. Column "Auth" below: **-** public, **opt** works for guests, personalised if logged in, **user** login required, **admin** admin role required. Ownership rules are in the Purpose column.

## 3. Endpoints

### Auth (`/auth`)
| Method & path | Auth | Purpose | Success |
|---|---|---|---|
| POST `/auth/register` | - | Create account, sends verification email | 201 User |
| POST `/auth/verify-email` | - | Confirm email with emailed token | 200 message |
| POST `/auth/resend-verification` | - | Send a new verification email (always 202) | 202 message |
| POST `/auth/login` | - | Log in, sets cookies | 200 User |
| POST `/auth/refresh` | cookie | Rotate refresh token, new access token | 204 |
| POST `/auth/logout` | - | Revoke this session, clear cookies | 204 |
| POST `/auth/logout-all` | user | Revoke every session of the user | 204 |
| POST `/auth/forgot-password` | - | Email a reset link (always 202) | 202 message |
| POST `/auth/reset-password` | - | Set a new password with emailed token | 200 message |
| POST `/auth/change-password` | user | Change password; other devices logged out | 204 |
| POST `/auth/deactivate` | user | Hide account (log in again to reactivate) | 204 |
| DELETE `/auth/account` | user | Permanently delete account and its content | 204 |
| GET `/auth/google/login` | - | Redirect to Google consent screen | 302 |
| GET `/auth/google/callback` | - | Google returns here; sets cookies; redirects to the app | 302 |

### Users (`/users`)
| Method & path | Auth | Purpose | Success |
|---|---|---|---|
| GET `/users/me` | user | Own account data | 200 User |
| PATCH `/users/me` | user | Update `display_name`, `bio` | 200 User |
| POST `/users/me/avatar` | user | Upload avatar (multipart `file`) | 200 User |
| GET `/users/search?q=&limit=` | - | Prefix search on username/display name (q 2-50 chars, limit 1-20) | 200 UserSummary[] |
| GET `/users/{username}` | opt | Public profile with counts | 200 PublicProfile |
| GET `/users/{username}/posts` | opt | Posts of a user (paginated, `has_image`) | 200 PostPage |
| POST `/users/{username}/follow` | user | Follow (idempotent) | 204 |
| DELETE `/users/{username}/follow` | user | Unfollow (idempotent) | 204 |
| GET `/users/{username}/followers` | - | Followers (paginated) | 200 UserPage |
| GET `/users/{username}/following` | - | Following (paginated) | 200 UserPage |

### Posts, comments, reactions
| Method & path | Auth | Purpose | Success |
|---|---|---|---|
| POST `/posts` | user | Create post (`content` and/or `media_id`) | 201 Post |
| GET `/posts/feed` | user | People you follow + you, newest first | 200 PostPage |
| GET `/posts/explore?has_image=` | opt | Everyone's newest posts | 200 PostPage |
| GET `/posts/{post_id}` | opt | One post | 200 Post |
| PATCH `/posts/{post_id}` | user (author only) | Edit text | 200 Post |
| DELETE `/posts/{post_id}` | user (author or admin) | Delete | 204 |
| GET `/posts/{post_id}/comments?order=asc\|desc` | - | Comments (paginated) | 200 CommentPage |
| POST `/posts/{post_id}/comments` | user | Add comment | 201 Comment |
| DELETE `/comments/{comment_id}` | user (comment author, post author, or admin) | Delete comment | 204 |
| GET `/posts/{post_id}/reactions` | opt | Reaction summary | 200 ReactionSummary |
| PUT `/posts/{post_id}/reaction` | user | Set/change your reaction | 200 ReactionSummary |
| DELETE `/posts/{post_id}/reaction` | user | Remove your reaction | 200 ReactionSummary |

### Media
| Method & path | Auth | Purpose | Success |
|---|---|---|---|
| POST `/media/images` | user | Upload an image (multipart `file`) | 201 `{id,url,width,height}` |
| GET `/media/{name}.webp` | - | Download (cached forever, immutable) | 200 image/webp |

### Admin (`/admin`, admin only)
| Method & path | Purpose |
|---|---|
| GET `/admin/users?is_active=&cursor=&limit=` | List users |
| PATCH `/admin/users/{id}` | `{is_active?, role?}`; ban revokes sessions; cannot modify yourself |
| DELETE `/admin/posts/{id}` | Remove any post |
| GET `/admin/stats` | Counters |

### Health
`GET /health` (liveness, no DB) · `GET /health/ready` (DB + optional Redis; 503 if the database is down).

## 4. Schemas (response shapes)

```jsonc
User          { "id": "uuid", "email": "...", "username": "ada", "display_name": "Ada", "bio": null,
                "avatar_url": "/media/<hex>.webp", "role": "user", "is_email_verified": true,
                "has_password": true, "created_at": "ISO-8601" }
UserSummary   { "id", "username", "display_name", "avatar_url", "bio" }
PublicProfile { "id", "username", "display_name", "bio", "avatar_url", "created_at",
                "followers_count": 0, "following_count": 0, "posts_count": 0,
                "is_following": false, "is_me": false }          // never contains email
Post          { "id", "content": "text|null", "image_url": "url|null", "created_at", "updated_at",
                "author": UserSummary, "reaction_count": 0, "comment_count": 0,
                "my_reaction": "like|love|haha|wow|sad|null" }
Comment       { "id", "post_id", "content", "created_at", "author": UserSummary }
ReactionSummary { "post_id", "reaction_count": 3, "my_reaction": "love", "by_type": {"love": 2, "like": 1} }
Page          { "items": [...], "next_cursor": "string|null" }
Error         { "error": { "code": "POST_NOT_FOUND", "message": "...", "details": [...], "request_id": "..." } }
```

## 5. Parameters and bodies

- **Path:** `{post_id}`, `{comment_id}`, `{id}` are UUIDs (invalid -> 422). `{username}` is case-insensitive.
- **Query (lists):** `limit` 1-50 (default 20), `cursor` opaque string from `next_cursor`, `has_image` true/false (posts), `order` asc/desc (comments).
- **Bodies** (JSON, unknown fields are **rejected** with 422):

| Endpoint | Body |
|---|---|
| register | `{email, username, password}` |
| login | `{email, password}` |
| verify-email | `{token}` |
| resend-verification / forgot-password | `{email}` |
| reset-password | `{token, new_password}` |
| change-password | `{current_password, new_password}` |
| deactivate | `{password}` (null for Google-only accounts) |
| delete account | `{password, confirm_username}` |
| PATCH users/me | `{display_name?, bio?}` |
| create post | `{content?, media_id?}` |
| edit post | `{content}` |
| comment | `{content}` |
| reaction | `{type}` |

## 6. Success and error responses

| Status | Meaning |
|---|---|
| 200 / 201 / 202 / 204 | OK / created / accepted (async effect, e.g. email) / no content |
| 302 | Redirect (Google flow) |
| 400 | Business rule violated (`INVALID_TOKEN`, `EMPTY_POST`, `CANNOT_FOLLOW_SELF`, `INVALID_CURSOR`...) |
| 401 | Not logged in / bad credentials / bad refresh token |
| 403 | Logged in but not allowed (`FORBIDDEN`, `EMAIL_NOT_VERIFIED`, `ACCOUNT_DISABLED`, `CSRF_ORIGIN_REJECTED`) |
| 404 | Not found (`USER_NOT_FOUND`, `POST_NOT_FOUND`, `COMMENT_NOT_FOUND`) |
| 409 | Conflict (`EMAIL_OR_USERNAME_TAKEN`) |
| 413 | Upload too large |
| 415 | Not a valid JPEG/PNG/WebP image |
| 422 | Validation failed (`details` lists field + message, never the submitted value) |
| 429 | Rate limited; read `Retry-After` (seconds) |
| 500 / 503 | Server error / dependency down. Quote the `request_id` when reporting |

## 7. Validation rules

| Field | Rule |
|---|---|
| email | valid address; trimmed + lowercased |
| username | `^[a-z0-9_]{3,30}$` after lowercasing; reserved names (admin, support, root...) refused |
| password | 8-128 characters, stored only as an Argon2 hash |
| display_name | 1-50 chars, trimmed |
| bio | 0-300 chars |
| post content | up to 2000 chars; a post needs text or an image |
| comment | 1-1000 chars, not blank |
| image | JPEG/PNG/WebP, max 5 MB, max ~20 MP; re-encoded to WebP, longest side 2048 px (avatars 400x400) |
| reaction type | `like`, `love`, `haha`, `wow`, `sad` |

## 8. Rate limiting

Fixed window counters in Redis, per IP (guests) or per user (logged in). Over the limit -> `429 RATE_LIMITED` + `Retry-After`.

| Route | Limit |
|---|---|
| everything (global, per IP) | 300 / min |
| login | 10 / min per IP **and** 10 / 15 min per email |
| register | 5 / hour per IP |
| forgot-password, resend-verification | 5 / hour per IP |
| reset-password, change-password | 10 / hour |
| refresh | 60 / min |
| create post | 30 / hour per user |
| create comment | 60 / hour per user |
| reaction | 120 / min per user |
| follow | 60 / hour per user |
| image / avatar upload | 30 / 20 per hour per user |

nginx adds a coarse 30 req/s per-IP limit in front. If Redis is down the limiter fails open (and logs a warning).

## 9. Pagination, filtering, sorting

Keyset (cursor) pagination: ordering is fixed (`created_at DESC, id DESC`; comments default ASC). Pass `next_cursor` as `cursor`; `null` means last page. Cursors are opaque: do not parse or build them. Filtering: `has_image`, `is_active` (admin), `q` (user search). Sorting is intentionally fixed so cursors stay valid.

## 10. Webhooks (outgoing)

Set `WEBHOOK_URL` and `WEBHOOK_SECRET`. Events: `user.registered`, `post.created`. Request:

```
POST <WEBHOOK_URL>
X-Circkle-Event: post.created
X-Circkle-Timestamp: 1767225600
X-Circkle-Signature: sha256=<hex>
{"event":"post.created","data":{"id":"...","author":"ada"}}
```
Verify: `HMAC_SHA256(secret, timestamp + "." + raw_body)` equals the signature (constant-time compare) and the timestamp is under 5 minutes old. Delivery is best-effort (5 s timeout, no retries yet).

## 11. File upload / download

Upload: `multipart/form-data` with field `file`. The server ignores the client filename and content type, decodes the image, strips metadata, re-encodes to WebP and stores it under a random name. Use the returned `id` as `media_id` when creating a post. Only your own uploads can be attached.
Download: `GET /media/<32 hex>.webp`, header `Cache-Control: public, max-age=31536000, immutable` (safe: names never repeat). With `MEDIA_PUBLIC_BASE_URL` set, URLs point straight at your CDN/bucket.

## 12. External integrations

| Service | Use | Notes |
|---|---|---|
| Google OAuth 2.0 / OpenID | "Continue with Google" | Server-side code flow, `state` cookie, only Google-verified emails accepted |
| SMTP provider | Verification and reset emails | Mailpit locally |
| S3-compatible storage / CDN | Images | Optional |
| Sentry | Error tracking | Optional, `send_default_pii=false` |

## 13. Examples

```http
POST /api/v1/auth/register
{"email":"ada@example.com","username":"ada","password":"correct-horse-battery"}
-> 201 {"id":"6f1c...","email":"ada@example.com","username":"ada","role":"user","is_email_verified":false,...}
```
```http
POST /api/v1/auth/login            {"email":"ada@example.com","password":"wrong"}
-> 401 {"error":{"code":"INVALID_CREDENTIALS","message":"Invalid email or password","request_id":"a1b2..."}}
```
```http
POST /api/v1/posts                 {"content":"Hello Circkle"}
-> 201 {"id":"...","content":"Hello Circkle","image_url":null,"author":{"username":"ada",...},"reaction_count":0,"comment_count":0,"my_reaction":null,...}

GET /api/v1/posts/feed?limit=2
-> 200 {"items":[{...},{...}],"next_cursor":"MjAyNi0wMS0wMVQ..."}

PUT /api/v1/posts/<id>/reaction    {"type":"love"}
-> 200 {"post_id":"...","reaction_count":1,"my_reaction":"love","by_type":{"love":1}}
```
```bash
curl -c jar.txt -H "Content-Type: application/json" -d '{"email":"ada@example.com","password":"Circkle#Dev2026"}' http://localhost:8001/api/v1/auth/login
curl -b jar.txt http://localhost:8001/api/v1/users/me
curl -b jar.txt -F "file=@photo.jpg" http://localhost:8001/api/v1/media/images
```

## 14. Error codes

`VALIDATION_ERROR` 422 · `UNAUTHENTICATED` 401 · `INVALID_CREDENTIALS` 401 · `INVALID_REFRESH_TOKEN` 401 · `FORBIDDEN` 403 · `EMAIL_NOT_VERIFIED` 403 · `ACCOUNT_DISABLED` 403 · `SELF_MODIFY` 403 · `CSRF_ORIGIN_REJECTED` 403 · `NOT_FOUND` / `USER_NOT_FOUND` / `POST_NOT_FOUND` / `COMMENT_NOT_FOUND` / `FEATURE_DISABLED` 404 · `METHOD_NOT_ALLOWED` 405 · `EMAIL_OR_USERNAME_TAKEN` 409 · `INVALID_TOKEN` · `INVALID_CURSOR` · `EMPTY_POST` · `INVALID_MEDIA` · `CANNOT_FOLLOW_SELF` · `INCORRECT_PASSWORD` · `PASSWORD_NOT_SET` · `CONFIRMATION_MISMATCH` 400 · `FILE_TOO_LARGE` 413 · `INVALID_IMAGE` 415 · `RATE_LIMITED` 429 · `INTERNAL_ERROR` 500.
Clients branch on `code`, never on `message` text.

## 15. Security considerations

HttpOnly cookies (no token in JavaScript) · SameSite=Lax + Origin check on state-changing requests (CSRF) · strict CORS allow-list · Argon2 hashing, constant-time-ish login · generic login/forgot/resend answers (no user enumeration) · refresh rotation + reuse detection · `extra="forbid"` on every body (no mass assignment) · UUID ids · ownership checked server-side in every service · parameterised SQL only (SQLAlchemy) · uploads re-encoded, size/pixel limited · security headers on every response · request ids for tracing · docs and OpenAPI hidden in production · no secrets in logs. Full list: [SECURITY.md](SECURITY.md).
