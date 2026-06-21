# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-06-21

### Added
- `entrypoint.sh` — auto-creates `data/config.json`, `data/roles.json`, persists `SECRET_KEY` on first container start.
- Auto-fix for bind-mount permissions — entrypoint runs as root, fixes ownership, then drops privileges via `setpriv`.
- OAuth credential checking — each provider registered only if credentials are configured; missing creds = no buttons, no crash.
- Safety fallback — `auth_mode: 2` with no OAuth credentials falls back to mode 3 (email + OAuth) instead of showing a blank login page.

### Changed
- `config.json` moved from project root to `data/` (bind mount) — persistent and editable on the host.
- Registration toggle moved from `.env` to `data/config.json` (`allow_registration` key).
- All docker-compose env vars now have `${VAR:-}` defaults — `.env` is completely optional.
- Config file resolution: checks `DATABASE_DIR` first, then project root for backward compat.

### Removed
- `ALLOW_REGISTRATION` env var — now exclusively in `data/config.json`.
- `USER snippet` from Dockerfile — entrypoint handles privilege dropping.

## [1.1.0] - 2026-06-21

### Added
- `role` column on the User model (default `"user"`).
- `data/roles.json` — maps email → role, synced on login and at startup.
- Registration toggle via `ALLOW_REGISTRATION` env var.
- Database migration for role column in `init_db()`.
- `PUBLIC_URL` env var — forces correct OAuth redirect URIs behind reverse proxies.
- `ProxyFix` middleware for Cloudflare Tunnel / reverse proxy compatibility.

### Changed
- Docker volume switched from named volume to bind mount (`./data:/app/data`) — persistent data directly accessible in project folder.
- `docker-compose.yml` updated to use bind mount and pass `PUBLIC_URL`, `ALLOW_REGISTRATION`.

### Fixed
- Missing `requests`, `email-validator` dependencies in `requirements.txt`.
- Invisible code on dark background (Pygments CSS styles in `snippet.html`).
- Attestation manifests removed from Docker builds (`--provenance=false --sbom=false`).

## [1.0.0] - 2026-06-19

### Added
- Initial release of SnippetVault.
- CRUD operations for code snippets with syntax highlighting (Pygments).
- Tag-based categorization and search.
- User authentication with three configurable modes:
  - **Mode 1**: Email/password only.
  - **Mode 2**: OAuth-only (Google + GitHub).
  - **Mode 3**: Both email/password and OAuth.
- Auth mode toggled via `config.json` (no code changes needed).
- OAuth integration via Authlib for Google and GitHub.
- Docker support: multi-stage `Dockerfile` with non-root user, healthcheck, and `docker-compose.yml` with persistent volume.
- Waitress production server (cross-platform) via `WAITRESS=1` env var.
- SQLite with WAL mode for concurrent access.
- `init_db()` with automatic `password_hash` column migration for existing databases.
- `AGENTS.md` – compact developer reference file.
- `.env.example` for all configuration secrets.
