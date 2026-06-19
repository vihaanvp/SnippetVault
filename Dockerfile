# =============================================================================
# SnippetVault — Dockerfile
# Multi-stage build for a small, secure production image.
# =============================================================================

# ---- Build stage (install dependencies) ----
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Runtime stage ----
FROM python:3.12-slim

# Link this image to the GitHub repository for package listings
LABEL org.opencontainers.image.source=https://github.com/vihaanvp/SnippetVault
LABEL org.opencontainers.image.description="SnippetVault — self-hostable code snippet manager"
LABEL org.opencontainers.image.licenses=MIT

# Create a non-root user
RUN groupadd --gid 1000 snippet && \
    useradd --uid 1000 --gid snippet --create-home --shell /bin/bash snippet

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/snippet/.local
ENV PATH=/home/snippet/.local/bin:$PATH

# Copy application code
COPY --chown=snippet:snippet . .

# Data directory (mount a volume here for persistence)
RUN mkdir -p /app/data && chown snippet:snippet /app/data

# Switch to non-root user
USER snippet

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/health')" || exit 1

EXPOSE 5001

# Run with Waitress in production by default
ENV WAITRESS=1
CMD ["python", "app.py"]
