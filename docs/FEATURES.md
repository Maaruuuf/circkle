# Features

Scope = the MVP list: Register, Login, profile update/delete, follow, status posts (text, image), comments, reactions. Everything else is an extra needed for a production-grade app.

| # | Feature | Details | Status |
|---|---|---|---|
| F1 | Register | email + username + password, Argon2, reserved names, verification email | done |
| F2 | Login / logout / refresh | HttpOnly cookies, rotation, logout-all | done |
| F3 | Email verification | single-use link, resend; optional enforcement | done |
| F4 | Password reset / change | emailed link; change needs current password | done |
| F5 | Google login | server-side OAuth, safe account linking | done (needs credentials) |
| F6 | Profile | display name, bio, avatar, public page (SSR), counts | done |
| F7 | Deactivate / delete account | reversible hide / permanent cascade | done |
| F8 | Follow / unfollow | idempotent, followers/following lists | done |
| F9 | Posts | text and/or image, edit text, delete | done |
| F10 | Feed / explore | cursor pagination, image filter | done |
| F11 | Comments | create, list (asc/desc), delete (author, post owner, admin) | done |
| F12 | Reactions | like/love/haha/wow/sad, one per user, optimistic UI | done |
| F13 | Search | users by username/name prefix | done |
| F14 | Admin | stats, ban/unban, roles, remove posts | done |
| F15 | Media | validated upload, WebP re-encode, CDN-ready URLs | done |
| F16 | Platform | rate limits, cache, logs, Sentry, health, webhooks, CI | done |
| F17 | Not in scope yet | chat, notifications, stories, hashtags, 2FA | see ROADMAP.md |
