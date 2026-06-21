#!/bin/bash
# =============================================================================
# SnippetVault — Docker Entrypoint
#
# Runs as root, auto-creates config files, fixes bind-mount permissions,
# then drops privileges to the snippet user before starting the app.
# =============================================================================
set -e

# --- Ensure data directory exists ---
mkdir -p /app/data

# --- Auto-create config.json with defaults if missing ---
if [ ! -f /app/data/config.json ]; then
    cat > /app/data/config.json << 'EOF'
{
    "auth_mode": 3,
    "allow_registration": true,
    "_comment": [
        "Authentication mode (auth_mode):",
        "  1 = Email/password only (register + login forms)",
        "  2 = External OAuth only (Google + GitHub)",
        "  3 = Both email/password and OAuth (default)",
        "",
        "Registration toggle (allow_registration):",
        "  Set to false to disable new account signups.",
        "  Existing users can still log in."
    ]
}
EOF
    echo "[entrypoint] Created /app/data/config.json with auth_mode=3, allow_registration=true"
fi

# --- Auto-create roles.json if missing ---
if [ ! -f /app/data/roles.json ]; then
    echo "{}" > /app/data/roles.json
    echo "[entrypoint] Created /app/data/roles.json (empty — all users get role 'user')"
fi

# --- Persist SECRET_KEY across restarts (if not explicitly set via env) ---
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY_FILE=/app/data/.secret_key
    if [ -f "$SECRET_KEY_FILE" ]; then
        export SECRET_KEY=$(cat "$SECRET_KEY_FILE")
        echo "[entrypoint] Restored SECRET_KEY from $SECRET_KEY_FILE"
    else
        NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "$NEW_KEY" > "$SECRET_KEY_FILE"
        export SECRET_KEY="$NEW_KEY"
        echo "[entrypoint] Generated persistent SECRET_KEY saved to $SECRET_KEY_FILE"
    fi
fi

# --- Fix bind-mount permissions and drop privileges ---
# Docker creates bind-mount host directories as root:root. The snippet user
# (uid 1000) needs to write config.json, roles.json, snippets.db, etc.
# This also handles the case where data/ was pre-created by the user with
# root ownership.
if [ "$(id -u)" = "0" ]; then
    chown -R snippet:snippet /app/data
    echo "[entrypoint] Fixed /app/data ownership to snippet:snippet"
    # Drop privileges to snippet user, preserving CWD, environment, PATH.
    # setpriv is from util-linux and does NOT change the working directory
    # (unlike su or chroot, which both chdir to / or $HOME).
    exec setpriv --reuid=1000 --regid=1000 --init-groups "$@"
fi

# --- If already running as non-root (e.g. docker run --user 1000), just exec ---
exec "$@"
