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

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/SnippetVault.git
cd SnippetVault

# 2. Configure environment
cp .env.example .env
# Edit .env with your SECRET_KEY and OAuth credentials (if using OAuth)

# 3. Configure auth mode
# Edit config.json – set auth_mode to 1 (email), 2 (OAuth), or 3 (both)

# 4. Run with Docker
docker compose up -d
# → Open http://localhost:5001
```

Or run without Docker:

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
| `PREFERRED_URL_SCHEME` | No | `https` | Use `http` for local dev without TLS |
| `DATABASE_DIR` | No | *(app root)* | Custom directory for `snippets.db` |
| `PORT` | No | `5001` | Server port (outside Docker) |
| `WAITRESS` | No | *(unset)* | Set to `1` to use Waitress production server |

### OAuth Callback URLs

Register these in your OAuth provider's console:

- **Google**: `https://<your-domain>/login/google/authorize`
- **GitHub**: `https://<your-domain>/login/github/authorize`

For local development use `http://localhost:5001/...` and set `PREFERRED_URL_SCHEME=http`.

---

## Project Structure

```
SnippetVault/
├── app.py              # Flask application (models, routes, OAuth, forms)
├── config.json         # Runtime configuration (auth mode)
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

```bash
docker build -t snippetvault:latest .
docker tag snippetvault:latest <your-registry>/snippetvault:latest
docker push <your-registry>/snippetvault:latest
```

Pre-built images can be placed in `builds/` (excluded from git).

---

## Development Notes

- **Database**: SQLite with WAL mode. Delete `snippets.db` to reset schema (no Alembic).
- **Port**: Default `5001`. Set `PORT=5000` to change.
- **Secret key**: Auto-generated on first run if `SECRET_KEY` is not set. **Always set it in production** — sessions will invalidate on restart otherwise.
- **First run**: If `config.json` is missing, it is auto-created with `auth_mode: 3` (both email + OAuth).

---

## License

[MIT](LICENSE)
