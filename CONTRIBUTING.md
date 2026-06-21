# Contributing to SnippetVault

Thanks for your interest in contributing! This project is open-source and welcomes contributions of all kinds — bug reports, feature requests, documentation improvements, and code changes.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Guidelines](#coding-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

By participating, you agree to maintain a respectful and inclusive environment. Be constructive, be kind, and assume good faith.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/SnippetVault.git
   cd SnippetVault
   ```
3. Set up the development environment (see below).

## Development Setup

### Without Docker (recommended for development)

```bash
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Fill in at least SECRET_KEY and any OAuth credentials you need
python app.py
```

The app runs at `http://127.0.0.1:5001` by default. Set `WAITRESS=0` for hot-reloading.

### With Docker

```bash
docker compose up -d
```

### Testing OAuth locally

1. Create OAuth credentials in the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and [GitHub OAuth Apps](https://github.com/settings/developers).
2. Set redirect URIs to `http://127.0.0.1:5001/login/google/authorize` and `http://127.0.0.1:5001/login/github/authorize`.
3. Fill the credentials in `.env` and set `PREFERRED_URL_SCHEME=http`.

## Project Structure

```
├── app.py              # Flask application (models, routes, OAuth, forms)
├── entrypoint.sh       # Docker entrypoint (auto-creates config files)
├── data/               # Persistent data (bind mount into /app/data)
│   └── config.json     # Auth mode & registration settings
├── templates/          # Jinja2 + Bootstrap 5 templates
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   └── ...
├── static/css/         # Static assets
│   └── style.css
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Coding Guidelines

- **Language**: Python 3.11+ with type hints where practical.
- **Style**: Follow PEP 8. No strict formatter enforced — use common sense.
- **Single-file app**: All application logic lives in `app.py`. Keep it that way unless there's a strong reason to split.
- **Jinja2 templates**: Use Bootstrap 5 classes. Load CSS/JS from CDN. No build step.
- **No migrations**: Schema changes in `init_db()` only. Document breaking changes in the changelog.
- **No tests yet**: If you add tests, place them in a `tests/` directory at the project root.

## Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Make your changes, keeping commits small and descriptive.
3. Update the changelog in `CHANGELOG.md` if your change is user-facing.
4. Test manually — run the app and verify the feature works.
5. Push to your fork and open a pull request targeting `main`.
6. In the PR description, explain what changed and why.

### PR Checklist

- [ ] Code works locally (with and without Docker)
- [ ] No new warnings in console
- [ ] Updated `CHANGELOG.md` if user-facing
- [ ] Updated `AGENTS.md` if internals changed
- [ ] No personal secrets or URLs committed

## Reporting Issues

Open an issue on GitHub with:

- A clear, descriptive title.
- Steps to reproduce the problem.
- Expected vs actual behavior.
- Your environment (OS, Python version, Docker version if applicable).
- Logs or error messages (sanitize any personal data).

For security vulnerabilities, please **do not** open a public issue. Email the maintainer directly (see GitHub profile).
