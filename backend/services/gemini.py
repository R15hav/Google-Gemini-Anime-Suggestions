import json
import re
from google import genai
from google.genai.errors import ClientError

# Free-tier daily request limits (2 Gemini calls per recommendation).
# Source: https://ai.google.dev/gemini-api/docs/pricing#free
FREE_TIER_RPD: dict[str, int] = {
    "gemini-2.5-pro":        25,
    "gemini-2.5-flash":     500,
    "gemini-2.5-flash-lite": 1500,
    "gemini-2.0-flash":      1500,
    "gemini-2.0-flash-lite": 1500,
}

# Preferred fallback order when the requested model's quota is exhausted (server key only)
MODEL_FALLBACK_ORDER = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]


class QuotaExceededError(Exception):
    def __init__(self, model: str):
        self.model = model
        super().__init__(f"Quota exceeded for model {model}")


def get_best_available_model(requested: str, usage_today: dict[str, int]) -> str:
    """
    Return `requested` if it still has quota, else fall back through MODEL_FALLBACK_ORDER.
    Raises QuotaExceededError if all models are exhausted.
    """
    candidates = [requested] + [m for m in MODEL_FALLBACK_ORDER if m != requested]
    for model in candidates:
        limit = FREE_TIER_RPD.get(model, 1500)
        if usage_today.get(model, 0) < limit:
            return model
    raise QuotaExceededError(requested)


def call_gemini(prompt: str, model: str = "gemini-2.5-flash-lite", api_key: str = None) -> str:
    if not api_key:
        raise ValueError("A Gemini API key must be provided.")
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except ClientError as e:
        if e.status_code == 429:
            raise QuotaExceededError(model)
        raise


def safe_json_parse(text: str) -> list:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in Gemini response:\n{text}")

    return json.loads(match.group(0))


def get_search_params(user_completed: list, user_dropped: list, model: str, api_key: str) -> list:
    prompt = f"""
Based on these completed anime: {user_completed}
And these dropped shows: {user_dropped}

Identify 3 distinct 'vibe' categories to search for on AniList.
Return ONLY a valid JSON array — no markdown, no explanation.
Output must start with [ and end with ].
Example: [{{"genre": "Action", "tag": "Cyberpunk"}}, ...]
"""
    response = call_gemini(prompt, model, api_key)
    return safe_json_parse(response)


def finalize_recommendations(
    candidates: list,
    user_history: list,
    model: str,
    api_key: str,
) -> list:
    # Truncate to first 60 candidates; include only title + description to stay within token limits
    slim = [
        {"title": c.get("title", {}).get("romaji") or c.get("title", {}).get("english", "Unknown"),
         "genres": c.get("genres", []),
         "score": c.get("averageScore"),
         "description": (c.get("description") or "")[:200]}
        for c in candidates[:60]
    ]

    prompt = f"""
You are an anime recommendation engine. From the candidate pool below, select exactly 5 anime to recommend.

Rules:
- Do NOT recommend anything from the user's history.
- Prefer variety across genres.
- Explain WHY each pick suits this user in 1-2 sentences.
- Assign a match_score (0-100) based on how well it fits the user's taste.

User history (completed + dropped — avoid these): {user_history}

Candidate pool ({len(slim)} titles):
{json.dumps(slim, ensure_ascii=False)}

Return ONLY a valid JSON array — no markdown, no explanation.
Format: [{{"title": "...", "reason": "...", "match_score": 85}}, ...]
"""
    response = call_gemini(prompt, model, api_key)
    return safe_json_parse(response)
