# Use the same Python version as your local environment
FROM python:3.12-slim

# 1. Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Install 'uv'
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# 3. Copy dependency files
COPY pyproject.toml uv.lock ./

# 4. Install dependencies (Corrected Step)
# We remove '--system'. uv will create a folder named .venv inside /app
RUN uv sync --frozen

# 5. CRITICAL FIX: Add the .venv to the global PATH
# This ensures that typing 'python' or 'uvicorn' automatically uses the installed version
ENV PATH="/app/.venv/bin:$PATH"

# 6. Copy the rest of your code
COPY . .

# 7. Copy and prepare the start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

ENV PORT=10000

CMD ["/app/start.sh"]