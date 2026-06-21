#!/bin/bash
# =============================================================================
# SnippetVault — Docker Entrypoint
#
# Auto-creates persistent config files on first run so the user can simply
# `docker compose up -d` with zero manual setup.
# =============================================================================
set -e

# --- Ensure data directory exists ---
mkdir -p /app/data

# --- Auto-create config.json with defaults if missing ---
if [ ! -f /app/data/config.json ]; then
    cat > /app/data/config.json << 'EOF'
{
    "auth_mode": 3,
    "_comment": [
        "Authentication mode:",
        "  1 = Email/password only (register + login forms)",
        "  2 = External OAuth only (Google + GitHub)",
        "  3 = Both email/password and OAuth (default)"
    ]
}
EOF
    echo "[entrypoint] Created /app/data/config.json with default auth_mode=3"
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
        # Restore previously persisted key
        export SECRET_KEY=$(cat "$SECRET_KEY_FILE")
        echo "[entrypoint] Restored SECRET_KEY from $SECRET_KEY_FILE"
    else
        # Generate a permanent key
        NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        echo "$NEW_KEY" > "$SECRET_KEY_FILE"
        export SECRET_KEY="$NEW_KEY"
        echo "[entrypoint] Generated persistent SECRET_KEY saved to $SECRET_KEY_FILE"
    fi
fi

# --- Execute the main command (CMD from Dockerfile) ---
exec "$@"
