# Use the same Python version as your local environment
FROM python:3.12-slim

# 1. Install system dependencies (curl needed for health checks/debugging)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 2. Install 'uv' directly from their official image (Fastest/Safest method)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# 3. Copy dependency files first to leverage Docker caching
COPY pyproject.toml uv.lock ./

# 4. Install dependencies into SYSTEM python
# We use --system so we don't have to activate a .venv in our start script
RUN uv sync --frozen --system

# 5. Copy the rest of your code
COPY . .

# 6. Copy the start script and make it executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Render sets the PORT variable (e.g., 10000). 
# We don't expose 8000 because FastAPI stays internal.
ENV PORT=10000

# 7. Run the start script
CMD ["/app/start.sh"]