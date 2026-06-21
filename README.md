# SnippetVault

> A self-hostable code snippet manager with syntax highlighting, tagging, and configurable authentication.

![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![Docker](https://img.shields.io/badge/docker-ready-2496ED?logo=docker)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Create, edit, delete, and browse** code snippets with syntax highlighting (Pygments).
- **Tag & search** – organize snippets by language and tags, full-text search.
- **Configurable authentication** – switch between email/password, OAuth (Google + GitHub), or both — no code changes needed.
- **Self-hosted** – single container, SQLite-backed (WAL mode), no external services required.
- **Dockerized** – multi-stage build, non-root user, healthcheck, compose-ready.

---

## Quick Start

### Option A — Docker Compose (recommended)

Pulls the pre-built multi-arch image (amd64 + arm64) from GitHub Container Registry:

```bash
# 1. Clone the repository
git clone https://github.com/vihaanvp/SnippetVault.git
cd SnippetVault

# 2. Configure environment
cp .env.example .env
# Edit .env with your SECRET_KEY and OAuth credentials (if using OAuth)

# 3. Configure auth mode
# Edit config.json – set auth_mode to 1 (email), 2 (OAuth), or 3 (both)

# 4. Run
docker compose up -d
# → Open http://localhost:5001
```

### Option B — From Release Tarball

No git clone needed — download the source from [GitHub Releases](https://github.com/vihaanvp/SnippetVault/releases):

```bash
# 1. Download the tarball
#    https://github.com/vihaanvp/SnippetVault/releases/download/v1.0.0/snippetvault-v1.0.0.tar

# 2. Extract
tar xf snippetvault-v1.0.0.tar
cd snippetvault-v1.0.0

# 3. Configure
cp .env.example .env
# Edit .env with your SECRET_KEY and OAuth credentials (if using OAuth)
# Edit config.json – set auth_mode (default 3)

# 4. Run with Docker
docker compose up -d
# → Open http://localhost:5001
```

### Option C — Without Docker

```bash
pip install -r requirements.txt
python app.py
# → Open http://localhost:5001 (set WAITRESS=1 for production)
```

---

## Authentication Modes

| Mode | `config.json` | Description |
|------|---------------|-------------|
| 1    | `"auth_mode": 1` | Email/password only (register + login) |
| 2    | `"auth_mode": 2` | OAuth only (Google + GitHub) – no password forms |
| 3    | `"auth_mode": 3` | Both email/password and OAuth |

Change `auth_mode` in `config.json` and restart the app.

### Registration Toggle

Add `ALLOW_REGISTRATION=false` to your `.env` file and restart. Existing users can still log in. Default is `true`.

```bash
# In .env:
ALLOW_REGISTRATION=false

# Then restart:
docker compose up -d
```

### User Roles

Create a `roles.json` file in the `data/` directory to assign roles by email:

```json
{
    "admin@example.com": "admin",
    "moderator@example.com": "moderator"
}
```

- Emails not in the file get the default role of **"user"**.
- Roles are synced at startup and on every login.
- The `data/` folder is a bind mount — `roles.json` lives right in your project and persists across restarts.
- The `role` is available on the `User` model as `user.role`.

---

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | *(auto-generated)* | Flask session signing key |
| `GOOGLE_CLIENT_ID` | OAuth only | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth only | — | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | OAuth only | — | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | OAuth only | — | GitHub OAuth client secret |
| `PUBLIC_URL` | Behind proxy | — | Full public URL (e.g. `https://snippetvault.example.com`). Fixes OAuth redirects behind Cloudflare Tunnel / reverse proxies. |
| `ALLOW_REGISTRATION` | No | `true` | Set to `false` to disable new signups. |
| `PREFERRED_URL_SCHEME` | No | `https` | Use `http` for local dev without TLS |
| `DATABASE_DIR` | No | *(app root)* | Custom directory for `snippets.db` |
| `PORT` | No | `5001` | Server port (outside Docker) |
| `WAITRESS` | No | *(unset)* | Set to `1` to use Waitress production server |

### OAuth Callback URLs

Register these in your OAuth provider's console:

- **Google**: `https://<your-domain>/login/google/authorize`
- **GitHub**: `https://<your-domain>/login/github/authorize`

For local development use `http://localhost:5001/...` and set `PREFERRED_URL_SCHEME=http`.

> **Behind a reverse proxy (Cloudflare Tunnel, nginx, etc.)?** Set `PUBLIC_URL=https://<your-domain>` in `.env` to ensure OAuth redirects use the correct scheme and host regardless of internal forwarding headers.

---

## Project Structure

```
SnippetVault/
├── app.py              # Flask application (models, routes, OAuth, forms)
├── config.json         # Runtime configuration (auth mode, registration toggle)
├── data/               # Persistent data — snippets.db, roles.json (bind mount)
│   └── .gitkeep
├── roles.json          # User role assignments by email (created manually in data/)
├── templates/          # Jinja2 templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── ...
├── static/             # Static assets (CSS, JS)
├── requirements.txt
├── Dockerfile          # Multi-stage build
├── docker-compose.yml  # Compose definition with volume
├── .env.example        # Env var template
├── AGENTS.md           # Developer reference
├── builds/             # Docker build artifacts (gitignored)
└── .gitignore
```

---

## API Routes

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/` | Optional | Home – public snippets |
| GET/POST | `/login` | No | Login |
| GET/POST | `/register` | No | Register (modes 1, 3) |
| GET | `/logout` | Yes | Logout |
| GET/POST | `/new` | Yes | Create snippet |
| GET/POST | `/edit/<id>` | Yes | Edit snippet |
| POST | `/delete/<id>` | Yes | Delete snippet |
| GET | `/snippet/<id>` | Optional | View snippet |
| GET | `/tag/<tag>` | Optional | Filter by tag |
| GET | `/search` | Optional | Search snippets |
| GET | `/health` | No | Healthcheck endpoint |
| GET | `/login/google` | No | Google OAuth initiate |
| GET | `/login/github` | No | GitHub OAuth initiate |
| GET | `/login/google/authorize` | No | Google OAuth callback |
| GET | `/login/github/authorize` | No | GitHub OAuth callback |

---

## Building a Docker Image

Pre-built multi-arch images are available at `ghcr.io/vihaanvp/snippetvault` — see the [Releases](https://github.com/vihaanvp/SnippetVault/releases) page for tagged versions.

To build locally:

```bash
# From the project directory
docker build -t snippetvault:latest .
```

Or from the release tarball:

```bash
tar xf snippetvault-v1.0.0.tar
cd snippetvault-v1.0.0
docker build -t snippetvault:latest .
```

Build artifacts are stored in `builds/` (gitignored) for your own releases.

---

## Development Notes

- **Database**: SQLite with WAL mode. Delete `snippets.db` to reset schema (no Alembic).
- **Port**: Default `5001`. Set `PORT=5000` to change.
- **Secret key**: Auto-generated on first run if `SECRET_KEY` is not set. **Always set it in production** — sessions will invalidate on restart otherwise.
- **First run**: If `config.json` is missing, it is auto-created with `auth_mode: 3` (both email + OAuth).

---

## License

[MIT](LICENSE)
