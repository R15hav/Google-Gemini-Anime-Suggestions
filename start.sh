#!/bin/bash
set -e

echo "🚀 Starting Anime Sensei..."

# Start FastAPI on localhost (only Streamlit needs to reach it)
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to be ready instead of sleeping a fixed amount
echo "⏳ Waiting for backend to be healthy..."
until curl -sf http://127.0.0.1:8000/health > /dev/null; do
  sleep 1
done
echo "✅ Backend is up."

# Start Streamlit on the public port assigned by the hosting platform
echo "🎨 Starting frontend on port ${PORT:-10000}..."
python -m streamlit run frontend/app.py \
  --server.port "${PORT:-10000}" \
  --server.address 0.0.0.0

# If Streamlit exits, bring down FastAPI so the container restarts cleanly
kill $FASTAPI_PID
