from collections import Counter

import requests

ANILIST_URL = "https://graphql.anilist.co"

SEARCH_QUERY = """
query ($genre: String, $tag: String, $page: Int) {
  Page (page: $page, perPage: 20) {
    media (genre: $genre, tag: $tag, sort: SCORE_DESC, type: ANIME, isAdult: false) {
      title { english romaji }
      genres
      format
      description
      averageScore
    }
  }
}
"""

_WATCHLIST_QUERY = """
query ($name: String) {
  MediaListCollection(userName: $name, type: ANIME, status_in: [COMPLETED, DROPPED, PLANNING]) {
    lists {
      status
      entries {
        score(format: POINT_10)
        media {
          title { english romaji }
          genres
          tags { name }
          description
        }
      }
    }
  }
}
"""

_VALIDATE_QUERY = """
query ($name: String) {
  MediaListCollection(userName: $name, type: ANIME, status_in: [COMPLETED]) {
    lists {
      status
      entries { media { title { romaji } } }
    }
  }
}
"""


def fetch_candidates(genre: str = None, tag: str = None):
    import random
    page = random.randint(1, 5)

    variables = {"page": page}
    if genre:
        variables["genre"] = genre
    if tag:
        variables["tag"] = tag

    response = requests.post(ANILIST_URL, json={"query": SEARCH_QUERY, "variables": variables}, timeout=10)
    data = response.json()
    if data.get("errors"):
        raise ValueError(data["errors"][0].get("message", "AniList error"))
    return data.get("data", {}).get("Page", {}).get("media", [])


def _compute_profile_stats(completed_entries: list) -> dict:
    if not completed_entries:
        return {"watched": 0, "mean_score": 0.0, "top_genres": [], "recent_fav": ""}

    scores = [e["score"] for e in completed_entries if e.get("score") and e["score"] > 0]
    mean_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    genre_counter: Counter = Counter()
    for e in completed_entries:
        for g in e["media"].get("genres", []):
            genre_counter[g] += 1
    top_genres = [g for g, _ in genre_counter.most_common(3)]

    best = max(completed_entries, key=lambda e: e.get("score") or 0, default=None)
    recent_fav = ""
    if best:
        title = best["media"]["title"]
        recent_fav = title.get("english") or title.get("romaji") or ""

    return {
        "watched": len(completed_entries),
        "mean_score": mean_score,
        "top_genres": top_genres,
        "recent_fav": recent_fav,
    }


def fetch_user_watchlist(username: str) -> tuple[list, list, list, dict]:
    """Returns (completed_titles, dropped_titles, planning_titles, profile_stats)."""
    response = requests.post(
        ANILIST_URL,
        json={"query": _WATCHLIST_QUERY, "variables": {"name": username}},
        timeout=10,
    )
    data = response.json()

    errors = data.get("errors")
    if errors:
        msg = errors[0].get("message", "AniList error")
        raise ValueError(msg)

    lists = data.get("data", {}).get("MediaListCollection", {}).get("lists", [])

    completed_entries: list = []
    dropped_entries: list = []
    planning_entries: list = []

    for lst in lists:
        entries = lst.get("entries", [])
        if lst["status"] == "COMPLETED":
            completed_entries = entries
        elif lst["status"] == "DROPPED":
            dropped_entries = entries
        elif lst["status"] == "PLANNING":
            planning_entries = entries

    completed = [e["media"]["title"]["romaji"] for e in completed_entries]
    dropped = [e["media"]["title"]["romaji"] for e in dropped_entries]
    planning = [e["media"]["title"]["romaji"] for e in planning_entries]

    profile_stats = _compute_profile_stats(completed_entries)

    return completed, dropped, planning, profile_stats


def validate_user(username: str) -> dict:
    """
    Returns {"exists": bool, "completed_count": int, "error": str | None}.
    AniList returns HTTP 200 with a GraphQL errors array for not-found / private profiles.
    """
    response = requests.post(
        ANILIST_URL,
        json={"query": _VALIDATE_QUERY, "variables": {"name": username}},
        timeout=10,
    )
    try:
        data = response.json()
    except Exception:
        return {"exists": False, "completed_count": 0, "error": "AniList is unreachable. Try again in a moment."}

    errors = data.get("errors")
    if errors:
        msg = errors[0].get("message", "").lower()
        if "private" in msg:
            return {"exists": True, "completed_count": 0, "error": "Profile is private — set your AniList profile to public."}
        if any(w in msg for w in ("disabled", "stability", "unavailable", "maintenance")):
            return {"exists": False, "completed_count": 0, "error": "AniList is currently experiencing issues. Please try again later."}
        return {"exists": False, "completed_count": 0, "error": "AniList user not found."}

    lists = (data.get("data") or {}).get("MediaListCollection", {}).get("lists", [])

    if data.get("data") is None:
        return {"exists": False, "completed_count": 0, "error": "AniList user not found."}

    completed_count = sum(
        len(lst.get("entries", []))
        for lst in lists
        if lst.get("status") == "COMPLETED"
    )
    return {"exists": True, "completed_count": completed_count, "error": None}
