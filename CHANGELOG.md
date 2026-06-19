# Changelog

All notable changes to this project will be documented in this file.

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
