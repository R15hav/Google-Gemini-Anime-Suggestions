import os
from pathlib import Path

import requests as http_requests
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.models import Recommendation, RecommendationResponse, UserProfile
from backend.services.anilist import fetch_candidates, fetch_user_watchlist, validate_user
from backend.services.gemini import QuotaExceededError, finalize_recommendations, get_search_params

DEFAULT_MODEL = "gemini-2.5-flash-lite"
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Anime Sensei API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/game-cover")
async def game_cover(title: str):
    """Return a RAWG cover image URL for a game title. Returns {url: null} if key not set."""
    if not RAWG_API_KEY:
        return {"url": None}
    try:
        resp = http_requests.get(
            "https://api.rawg.io/api/games",
            params={"search": title, "page_size": 1, "key": RAWG_API_KEY},
            timeout=6,
        )
        results = resp.json().get("results", [])
        url = results[0].get("background_image") if results else None
        return {"url": url}
    except Exception:
        return {"url": None}


@app.get("/validate/{username}")
async def validate(username: str):
    result = validate_user(username)
    if result["error"]:
        code = 404 if not result["exists"] else 403
        raise HTTPException(status_code=code, detail=result["error"])
    if result["completed_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No completed anime found. Mark some anime as completed on AniList first.",
        )
    return {"username": username, "completed_count": result["completed_count"]}


@app.get("/recommend/{username}", response_model=RecommendationResponse)
@limiter.limit("30/minute")
async def get_recs(
    request: Request,
    username: str,
    model_choice: str = DEFAULT_MODEL,
    x_gemini_api_key: str = Header(None),
):
    if not x_gemini_api_key:
        raise HTTPException(status_code=401, detail="A Gemini API key is required. Get your free key at aistudio.google.com.")

    # 1. Validate user before spending any Gemini quota
    validation = validate_user(username)
    if validation["error"]:
        code = 404 if not validation["exists"] else 403
        raise HTTPException(status_code=code, detail=validation["error"])
    if validation["completed_count"] == 0:
        raise HTTPException(
            status_code=400,
            detail="No completed anime found. Mark some anime as completed on AniList first.",
        )

    # 2. Fetch user history and profile stats
    try:
        completed, dropped, planning, profile_stats = fetch_user_watchlist(username)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to reach AniList. Try again in a moment.")

    # 3. Ask Gemini for search vectors based on full profile
    try:
        search_queries = get_search_params(completed, dropped, planning, model_choice, x_gemini_api_key)
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=429,
            detail=f"Gemini quota exceeded for {e.model}. Try again after midnight UTC or switch to a different model.",
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Gemini is unavailable right now. Please try again in a moment.")

    # 4. Gather candidate pool from AniList
    try:
        candidate_pool: list = []
        for q in search_queries:
            candidate_pool.extend(fetch_candidates(genre=q.get("genre"), tag=q.get("tag")))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to reach AniList while fetching candidates. Try again in a moment.")

    # 5. Let Gemini pick the best series, movies, and games
    try:
        result = finalize_recommendations(candidate_pool, completed, dropped, planning, model_choice, x_gemini_api_key)
    except QuotaExceededError as e:
        raise HTTPException(
            status_code=429,
            detail=f"Gemini quota exceeded for {e.model}. Try again after midnight UTC or switch to a different model.",
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Gemini is unavailable right now. Please try again in a moment.")

    return RecommendationResponse(
        series=[Recommendation.model_validate(r) for r in result.get("series", [])],
        movies=[Recommendation.model_validate(r) for r in result.get("movies", [])],
        games=[Recommendation.model_validate(r) for r in result.get("games", [])],
        notes=result.get("notes", ""),
        thinking=result.get("thinking", ""),
        profile=UserProfile(
            username=username,
            watched=profile_stats.get("watched", 0),
            mean_score=profile_stats.get("mean_score", 0.0),
            top_genres=profile_stats.get("top_genres", []),
            recent_fav=profile_stats.get("recent_fav", ""),
        ),
    )


# ── Serve React SPA (only when dist/ exists; dev works without a build) ────────
_dist = Path("frontend/dist")
if _dist.exists():
    _assets = _dist / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        candidate = _dist / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_dist / "index.html"))
