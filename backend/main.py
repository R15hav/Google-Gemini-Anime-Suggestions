from fastapi import FastAPI, Header, Request, HTTPException
from services.anilist import fetch_user_watchlist, fetch_candidates
from services.gemini import finalize_recommendations, get_search_params
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def get_free_tier_ip(request: Request):
    """
    Returns the IP address ONLY if the user has NO API Key.
    If they have a key, returns None (skipping this 1/hour limit).
    """
    if request.headers.get("x-gemini-api-key"):
        return None  # User is premium, skip the "Free" limit
    return get_remote_address(request)  # User is free, bucket by IP

def get_premium_tier_id(request: Request):
    """
    Returns the IP (or Key) ONLY if the user HAS an API Key.
    If no key, returns None (skipping this 1000/minute limit).
    """
    if request.headers.get("x-gemini-api-key"):
        return get_remote_address(request)  # Apply high limit to this IP
    return None  # User is free, skip the "Premium" check

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Anime Sensei API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

MODEL = "gemini-2.5-flash-lite"

@app.get("/recommend/{username}")
# Rule 1: Free Users -> 1 Request per Hour
@limiter.limit("1/hour", key_func=get_free_tier_ip)
# Rule 2: Premium Users -> 1000 Requests per Minute (Effective Unlimited)
@limiter.limit("1000/minute", key_func=get_premium_tier_id)
async def get_recs(request: Request, username: str, model_choice: str = MODEL, x_gemini_api_key: str = Header(None)):
    # 1. Fetch user's history
    user_data = fetch_user_watchlist(username)
    completed = [e["media"]["title"]["romaji"] for e in user_data["data"]["MediaListCollection"]["lists"][0]["entries"]]
    dropped   = [e["media"]["title"]["romaji"] for e in user_data["data"]["MediaListCollection"]["lists"][1]["entries"]]


    # 2. Ask Gemini what we should look for today
    search_queries = get_search_params(completed, dropped, model_choice, x_gemini_api_key)

    # 3. Gather a pool of candidates from AniList
    candidate_pool = []
    for q in search_queries:
        candidate_pool.extend(fetch_candidates(genre=q.get('genre'), tag=q.get('tag')))

    # 4. Let Gemini pick the best 'randomized' winners
    final_recs = finalize_recommendations(candidate_pool, completed + dropped, model_choice, x_gemini_api_key)
    print(final_recs)
    return final_recs