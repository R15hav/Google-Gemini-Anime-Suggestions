#!/bin/bash

echo "🚀 Starting Deployment..."

# 1. Start FastAPI in the background (&)
# We bind to 127.0.0.1 because only Streamlit (running in the same container) needs to reach it.
# We explicitly call 'python -m uvicorn' since we installed to system python.
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

# Capture the Process ID (PID) of FastAPI
FASTAPI_PID=$!

# 2. Wait for FastAPI to wake up
echo "⏳ Waiting for Backend to start..."
sleep 5

# 3. Start Streamlit in the foreground
# Streamlit listens on the public $PORT assigned by Render
echo "🎨 Starting Streamlit Frontend on port $PORT..."
python -m streamlit run frontend/app.py --server.port $PORT --server.address 0.0.0.0

# (Optional) If Streamlit crashes, kill FastAPI too so the container restarts cleanly
kill $FASTAPI_PID