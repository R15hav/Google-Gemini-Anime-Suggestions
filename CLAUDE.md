# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Anime Sensei is a two-process web app that generates personalized anime recommendations by chaining AniList GraphQL queries with Google Gemini LLM calls.

- **Backend**: FastAPI app (`backend/main.py`) — the only public API surface
- **Frontend**: Streamlit app (`frontend/app.py`) — calls the backend at `http://127.0.0.1:8000`
- **Services**: `backend/services/anilist.py` (AniList GraphQL client) and `backend/services/gemini.py` (Gemini wrapper)

## Commands

```bash
# Install dependencies (uses uv)
uv sync

# Run backend (from project root)
uvicorn backend.main:app --reload

# Run frontend (separate terminal, from project root)
streamlit run frontend/app.py

# Run both together (Docker-style, single process)
bash start.sh
```

## Architecture

### Request flow

1. Frontend sends `GET /recommend/{username}?model_choice=<model>` with optional `x-gemini-api-key` header
2. `backend/main.py` fetches user's COMPLETED and DROPPED lists from AniList
3. `get_search_params()` (gemini.py) asks Gemini for 3 genre/tag search vectors based on watch history
4. `fetch_candidates()` (anilist.py) queries AniList for each vector (random page 1–5 for variety)
5. `finalize_recommendations()` (gemini.py) asks Gemini to pick 5 non-overlapping titles from the candidate pool
6. Returns a JSON list matching the `Recommendation` Pydantic model

### Rate limiting (tiered)

- **Free tier** (no API key): 1 request/hour per IP via `slowapi`
- **Premium tier** (provides own `x-gemini-api-key` header): 1000 requests/minute — effectively unlimited
- The frontend enforces a client-side 1-hour cooldown in session state as UX feedback

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes (for free tier) | Gemini API key loaded via `python-dotenv` from `.env` |
| `GEMINI_MODEL` | No | Not currently used in code; default is `gemini-2.5-flash-lite` |
| `PORT` | No (Docker) | Port Streamlit binds to in production (default `10000`) |

### Deployment

`start.sh` starts FastAPI on `127.0.0.1:8000` (background), then Streamlit on `0.0.0.0:$PORT` (foreground). Both run in the same Docker container. `Dockerfile` uses `uv sync --frozen` and adds `.venv/bin` to `PATH`.

## Key notes

- `backend/services/gemini.py::safe_json_parse` strips markdown fences and extracts a JSON array — Gemini sometimes wraps output in ` ```json ``` `; this handles it
- `fetch_user_watchlist` always expects `lists[0]` = COMPLETED and `lists[1]` = DROPPED — this is fragile if AniList returns lists in a different order
- The `models.py` Pydantic models (`Recommendation`, `RecommendationResponse`) are defined but not currently used in the route response — the route returns the raw parsed JSON list
