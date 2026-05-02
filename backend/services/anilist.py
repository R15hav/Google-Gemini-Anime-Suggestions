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


def fetch_user_watchlist(username: str) -> tuple[list, list, list]:
    """Returns (completed_titles, dropped_titles, planning_titles) as lists of romaji strings."""
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

    completed, dropped, planning = [], [], []
    for lst in lists:
        entries = [e["media"]["title"]["romaji"] for e in lst.get("entries", [])]
        if lst["status"] == "COMPLETED":
            completed = entries
        elif lst["status"] == "DROPPED":
            dropped = entries
        elif lst["status"] == "PLANNING":
            planning = entries

    return completed, dropped, planning


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
    # AniList may return 4xx with a JSON error body — always parse JSON first
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

    # AniList returns null data (not an error) for non-existent users
    if data.get("data") is None:
        return {"exists": False, "completed_count": 0, "error": "AniList user not found."}

    completed_count = sum(
        len(lst.get("entries", []))
        for lst in lists
        if lst.get("status") == "COMPLETED"
    )
    return {"exists": True, "completed_count": completed_count, "error": None}
