#!/bin/bash
set -e

echo "📦 Building frontend..."
cd /app/frontend
npm ci
npm run build

echo "🚀 Starting server on port ${PORT:-10000}..."
cd /app
python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-10000}"
