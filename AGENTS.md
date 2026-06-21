# SnippetVault — Agent Guide

Single-file Flask app (`app.py`). Email + OAuth auth (Google + GitHub). SQLite. Docker.

Zero-config startup: `git clone && cd SnippetVault && docker compose up -d` — works out of the box
with email/password auth. No `.env` file needed.

## Quick start

```bash
# Docker (zero config — no .env needed)
docker compose up -d   # → http://localhost:5001

# Local development
pip install -r requirements.txt
cp .env.example .env   # optional — app works without it
python app.py          # → http://127.0.0.1:5001
```

## Auth modes (data/config.json)

Edit `data/config.json` (auto-created on first start, persistent via bind mount):

```json
{ "auth_mode": 3 }
```

| Mode | Behavior |
|------|----------|
| `1` | **Email/password only** — register + login forms. OAuth routes not defined. |
| `2` | **OAuth only** (Google + GitHub) — no register route, no password fields. |
| `3` | **Both** — email/password AND OAuth side by side. |

The `auth_mode` value is read once at startup. Restart the app after changing it. If `config.json` is missing, it's auto-created with mode 3.

### Registration toggle

Set `"allow_registration": false` in `data/config.json` to disable new account creation (existing users can still log in). This applies to both email/password and OAuth registration.

## User Roles

Roles are assigned via `roles.json`, which lives in the same directory as the database (`DATABASE_DIR`). Auto-created if missing. Format:

```json
{
    "admin@example.com": "admin",
    "moderator@example.com": "moderator"
}
```

- Any email not in the file gets the default role of `"user"`.
- Roles are synced on login and at startup (in `init_db()`).
- The `roles.json` file persists across container restarts (bind mount).
- The `User` model has a `role` column (string, default `"user"`).

Templates receive `allow_registration` via the context processor — use it to conditionally render the registration link.

## Server modes

| Mode | Env | Server |
|------|-----|--------|
| Dev | `WAITRESS=0` or unset | `app.run(debug=True)` |
| Prod | `WAITRESS=1` | `waitress.serve(app)` (default inside Docker) |

Port: `PORT` env (default `5001`). Host: `HOST` env (default `0.0.0.0`).

## OAuth

OAuth is **only enabled if credentials are configured**. If `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`
are empty (no `.env` file), Google login buttons and routes are simply absent. Same for GitHub.

- `/login/google` → redirects to Google consent → `/login/google/authorize`
- `/login/github` → redirects to GitHub → `/login/github/authorize`
- `_find_or_create_user` deduplicates by **email** (same email across providers → same account).
- Callback URLs must be registered in each OAuth provider's console.
- `PREFERRED_URL_SCHEME` env (default `https`) controls whether callbacks use `http` or `https` — **must be set correctly behind a reverse proxy**.

## Database

- SQLite at `DATABASE_DIR/snippets.db` (in Docker: `/app/data/snippets.db`).
- Created and migrated via `init_db()` (runs at startup). **No Alembic / migration tool.** Schema changes require deleting the old `.db` file.
- WAL mode enabled on every startup (`PRAGMA journal_mode=WAL`).
- Docker: bind mount at `./data:/app/data`.

## Env vars (all via `.env` or environment)

**None are required.** The app works with email/password auth straight out of the box.

| Var | Notes |
|-----|-------|
| `SECRET_KEY` | Auto-generated & persisted on first start |
| `GOOGLE_CLIENT_ID` | Leave empty to disable Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Leave empty to disable Google OAuth |
| `GITHUB_CLIENT_ID` | Leave empty to disable GitHub OAuth |
| `GITHUB_CLIENT_SECRET` | Leave empty to disable GitHub OAuth |
| `PUBLIC_URL` | Full public URL (e.g. `https://snippetvault.example.com`). Fixes OAuth redirects behind reverse proxies |
| `PREFERRED_URL_SCHEME` | Default `https`. Set `http` for local dev without TLS |
| `DATABASE_DIR` | Default `/app/data` (Docker) or `data/` (local) |
| `PORT` | Default `5001` |
| `HOST` | Default `0.0.0.0` |
| `WAITRESS` | Set `1` for production (default in Docker) |

## Docker

```bash
# Zero config — just run it:
docker compose up -d   # → http://localhost:5001

# With custom settings:
cp .env.example .env   # fill in secrets
docker compose up -d
```

- Multi-stage build (`python:3.12-slim`), non-root user `snippet` (uid 1000).
- Entrypoint auto-creates `data/config.json`, `data/roles.json`, and persists `SECRET_KEY`.
- Healthcheck at `GET /health` → `{"status": "ok"}`.
- Persistent data at `./data/` (bind mount) — contains `config.json`, `snippets.db`, `roles.json`.
- `WAITRESS=1` set by default in the image.

## Project structure

```
├── app.py              # Flask app, models, routes, forms
├── requirements.txt
├── Dockerfile
├── entrypoint.sh       # Auto-creates config files on container start
├── docker-compose.yml
├── .env.example        # Template for custom settings (optional)
├── data/               # Persistent data (bind mount into /app/data)
│   ├── config.json     #   auth_mode setting (auto-created)
│   ├── snippets.db     #   SQLite database
│   ├── roles.json      #   Role overrides (auto-created)
│   └── .secret_key     #   Persisted SECRET_KEY (auto-generated)
├── static/css/style.css
└── templates/           # Jinja2 + Bootstrap 5
    ├── base.html
    ├── login.html       # email form and/or OAuth buttons
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
| `/login` | No | Login page (email form in modes 1/3, OAuth buttons if configured) |
| `/register` | No | Register page (mode 1/3 only) |
| `/login/google` → `/login/google/authorize` | No | Google OAuth (only if configured) |
| `/login/github` → `/login/github/authorize` | No | GitHub OAuth (only if configured) |
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
- **Config precedence**: `data/config.json` takes priority, falls back to project-root `config.json` for backward compat.
