# SnippetVault — Agent Guide

Single-file Flask app (`app.py`). OAuth-only auth (Google + GitHub). SQLite. Docker.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in OAuth secrets
python app.py          # opens http://127.0.0.1:5001
```

## Auth modes (config.json)

Edit `config.json` in the project root:

```json
{ "auth_mode": 3, "allow_registration": true }
```

| Mode | Behavior |
|------|----------|
| `1` | **Email/password only** — register + login forms. OAuth routes return 404. |
| `2` | **OAuth only** (Google + GitHub) — no register route, no password fields. |
| `3` | **Both** — email/password AND OAuth side by side. |

The `auth_mode` value is read once at startup. Restart the app after changing it. If `config.json` is missing, it's auto-created with mode 3.

### Registration toggle

Set `ALLOW_REGISTRATION=false` in `.env` to disable new account creation (existing users can still log in). This applies to both email/password and OAuth registration. The env var takes precedence over `allow_registration` in `config.json`.

## User Roles

Roles are assigned via `roles.json`, which lives in the same directory as the database (`DATABASE_DIR`). Format:

```json
{
    "admin@example.com": "admin",
    "moderator@example.com": "moderator"
}
```

- Any email not in the file gets the default role of `"user"`.
- Roles are synced on login and at startup (in `init_db()`).
- The `roles.json` file persists across container restarts (Docker volume).
- The `User` model has a `role` column (string, default `"user"`).

Templates receive `allow_registration` via the context processor — use it to conditionally render the registration link.

## Server modes

| Mode | Env | Server |
|------|-----|--------|
| Dev | `WAITRESS=0` or unset | `app.run(debug=True)` |
| Prod | `WAITRESS=1` | `waitress.serve(app)` (default inside Docker) |

Port: `PORT` env (default `5001`). Host: `HOST` env (default `0.0.0.0`).

## Auth — OAuth only

**No password auth, no register route.** Users sign in exclusively via Google or GitHub.

- `/login/google` → redirects to Google consent → `/login/google/authorize`
- `/login/github` → redirects to GitHub → `/login/github/authorize`
- `_find_or_create_user` deduplicates by **email** (same email across providers → same account).
- Callback URLs must be registered in each OAuth provider's console.
- `PREFERRED_URL_SCHEME` env (default `https`) controls whether callbacks use `http` or `https` — **must be set correctly behind a reverse proxy**.

## Database

- SQLite at `DATABASE_DIR/snippets.db` (`DATABASE_DIR` defaults to `instance/`).
- Created and migrated via `init_db()` (runs at startup). **No Alembic / migration tool.** Schema changes require deleting the old `.db` file.
- WAL mode enabled on every startup (`PRAGMA journal_mode=WAL`).
- Docker: mount a volume at `/app/data` and set `DATABASE_DIR=/app/data`.

## Env vars (all via `.env` or environment)

| Var | Required | Notes |
|-----|----------|-------|
| `SECRET_KEY` | No | Auto-generated if missing (invalidates sessions on restart) |
| `GOOGLE_CLIENT_ID` | Yes | |
| `GOOGLE_CLIENT_SECRET` | Yes | |
| `GITHUB_CLIENT_ID` | Yes | |
| `GITHUB_CLIENT_SECRET` | Yes | |
| `PUBLIC_URL` | No | — | Full public URL (e.g. `https://snippetvault.example.com`). Fixes OAuth redirects behind reverse proxies |
| `ALLOW_REGISTRATION` | No | `true` | Set `false` to disable new signups |
| `PREFERRED_URL_SCHEME` | No | `https` | Set `http` for local dev without TLS |
| `DATABASE_DIR` | No | Defaults to `instance/` |
| `PORT` | No | Default `5001` |
| `HOST` | No | Default `0.0.0.0` |
| `WAITRESS` | No | Set `1` for production |

## Docker

```bash
cp .env.example .env   # fill secrets
docker compose up -d   # → http://localhost:5001
```

- Multi-stage build (`python:3.12-slim`), non-root user `snippet` (uid 1000).
- Healthcheck at `GET /health` → `{"status": "ok"}`.
- Persistent data at `./data/` (bind mount) — contains `snippets.db` and `roles.json`.
- `WAITRESS=1` set by default in the image.

## Project structure

```
├── config.json          # auth_mode: 1 (email), 2 (OAuth), 3 (both)
├── app.py              # entrypoint — Flask app, models, routes, forms
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── data/               # Persistent data (snippets.db, roles.json) — bind mount
│   └── .gitkeep
├── static/css/style.css
└── templates/           # Jinja2 + Bootstrap 5
    ├── base.html
    ├── login.html       # email form and/or OAuth buttons (depends on auth_mode)
    ├── register.html    # email/password registration (modes 1 & 3 only)
    ├── index.html
    ├── dashboard.html
    ├── create_snippet.html
    ├── snippet.html
    ├── explore.html
    ├── user_profile.html
    └── error.html
```

## Key routes

| Path | Auth | Purpose |
|------|------|---------|
| `/health` | No | Health check |
| `/login` | No | Login page (email form in modes 1/3, OAuth buttons in modes 2/3) |
| `/register` | No | Register page (mode 1/3 only; 404 in mode 2) |
| `/login/google` → `/login/google/authorize` | No | Google OAuth flow (mode 2/3 only; 404 in mode 1) |
| `/login/github` → `/login/github/authorize` | No | GitHub OAuth flow (mode 2/3 only; 404 in mode 1) |
| `/logout` | Yes | Log out |
| `/dashboard` | Yes | User's snippets, search, tag filter |
| `/snippet/new` | Yes | Create snippet |
| `/snippet/<uuid>` | Mixed | View (403 if private and not owner) |
| `/snippet/<uuid>/edit` | Yes | Edit (403 if not owner) |
| `/snippet/<uuid>/delete` | Yes | Delete (403 if not owner) |
| `/explore` | No | Browse public snippets |
| `/user/<username>` | No | User's public snippets |

## Conventions & quirks

- **Snippet visibility**: `is_public` boolean. Private snippets return 403 for non-owners.
- **Tags**: comma-separated string in `tags` column. Parsed by `tag_list()` method.
- **Syntax highlighting**: Pygments Monokai theme. Falls back to `guess_lexer`, then plain text.
- **Forms**: WTForms `SnippetForm` with 21 language choices (listed in `LANGUAGES`). No custom validators.
- **No frontend build step.** Bootstrap 5 + Bootstrap Icons loaded from CDN. Pygments CSS injected inline.
- **No tests exist.** No CI config. No linting/formatting config.
- **No migrations.** Schema changes = delete `snippets.db` and restart.
