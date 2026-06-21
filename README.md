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

### Option A — Docker Compose 🚀 (zero config)

**No `.env` file needed.** Just clone and run. Email/password auth works out of the box.

```bash
git clone https://github.com/vihaanvp/SnippetVault.git
cd SnippetVault
docker compose up -d
# → Open http://localhost:5001
```

Want OAuth or custom settings? Copy `.env.example` to `.env`, fill in your secrets, then restart:

```bash
cp .env.example .env
# Edit .env with your OAuth credentials
docker compose up -d
```

### Option B — From Release Tarball

Download from [GitHub Releases](https://github.com/vihaanvp/SnippetVault/releases):

```bash
tar xf snippetvault-v1.0.0.tar
cd snippetvault-v1.0.0
docker compose up -d
```

### Option C — Without Docker

```bash
pip install -r requirements.txt
python app.py
# → Open http://localhost:5001 (set WAITRESS=1 for production)
```

---

## Configuration (`data/config.json`)

All settings live in `data/config.json` (auto-created on first start, persists in bind mount):

```json
{
    "auth_mode": 3,
    "allow_registration": true
}
```

| Setting | Values | Default | Description |
|---------|--------|---------|-------------|
| `auth_mode` | `1`, `2`, `3` | `3` | 1=Email only, 2=OAuth only, 3=Both |
| `allow_registration` | `true`, `false` | `true` | Set `false` to disable new signups |

Change any value and restart: `docker compose up -d`

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

**None are required.** The app works with email/password auth straight away. Create a `.env` file only if you need OAuth or custom settings:

```bash
cp .env.example .env   # then edit
```

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(auto-generated & persisted)* | Flask session signing key |
| `GOOGLE_CLIENT_ID` | *(empty — disabled)* | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | *(empty — disabled)* | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | *(empty — disabled)* | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | *(empty — disabled)* | GitHub OAuth client secret |
| `PUBLIC_URL` | *(empty)* | Full public URL (e.g. `https://snippetvault.example.com`). Fixes OAuth redirects behind Cloudflare Tunnel / reverse proxies. |
| `PREFERRED_URL_SCHEME` | `https` | Set `http` for local dev without TLS |
| `DATABASE_DIR` | `/app/data` (Docker) | Custom directory for `snippets.db` |
| `PORT` | `5001` | Server port |
| `WAITRESS` | *(unset)* | Set `1` to use Waitress production server |

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
├── entrypoint.sh       # Auto-creates config files on container start
├── data/               # Persistent data — config.json, snippets.db, roles.json (bind mount)
│   └── .gitkeep
├── templates/          # Jinja2 templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── ...
├── static/             # Static assets (CSS, JS)
├── requirements.txt
├── Dockerfile          # Multi-stage build
├── docker-compose.yml  # Compose definition with bind mount
├── .env.example        # Env var template (optional — app runs without it)
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

- **Zero config**: Just `docker compose up -d`. No `.env` needed. Config files are auto-created in `data/`.
- **Database**: SQLite with WAL mode. Delete `data/snippets.db` to reset schema (no Alembic).
- **Port**: Default `5001`. Set `PORT=5000` to change.
- **Secret key**: Auto-generated and **persisted** to `data/.secret_key` on first start (Docker) or auto-generated in-memory (local dev). No session invalidation on restart.
- **Config file**: `data/config.json` is checked first, then project-root `config.json` for backward compatibility.
- **OAuth**: Only enabled when credentials are configured. Missing credentials = no OAuth buttons.

---

## License

[MIT](LICENSE)
