FROM python:3.12-slim

# Install curl (needed by start.sh health-check loop)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Pin uv version for reproducible builds
COPY --from=ghcr.io/astral-sh/uv:0.7.3 /uv /bin/uv

WORKDIR /app

# Copy only dependency files first so this layer is cached unless deps change
COPY pyproject.toml uv.lock ./

# Install dependencies into .venv; use copy mode to avoid hardlink warnings
RUN UV_LINK_MODE=copy uv sync --frozen --no-dev

# Add the venv to PATH for all subsequent RUN / CMD steps
ENV PATH="/app/.venv/bin:$PATH"

# Keep Python output unbuffered so logs appear in real time
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code (.dockerignore excludes .venv, .env, .git, __pycache__)
COPY . .

RUN chmod +x /app/start.sh

ENV PORT=10000

CMD ["/app/start.sh"]
