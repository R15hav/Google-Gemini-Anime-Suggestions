import json
import re
from google import genai
from google.genai.errors import ClientError

FREE_TIER_RPD: dict[str, int] = {
    "gemini-2.5-pro":        25,
    "gemini-2.5-flash":     500,
    "gemini-2.5-flash-lite": 1500,
    "gemini-2.0-flash":      1500,
    "gemini-2.0-flash-lite": 1500,
}

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


def safe_json_parse(text: str) -> dict | list:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try object first, then array
    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue

    raise ValueError(f"No JSON found in Gemini response:\n{text}")


def get_search_params(
    user_completed: list,
    user_dropped: list,
    user_planning: list,
    model: str,
    api_key: str,
) -> list:
    prompt = f"""
Based on this user's anime lists:
- Completed: {user_completed}
- Dropped: {user_dropped}
- Plan to watch: {user_planning}

Identify 3 distinct 'vibe' categories to search for on AniList that suit this user's taste.
Return ONLY a valid JSON array — no markdown, no explanation.
Output must start with [ and end with ].
Example: [{{"genre": "Action", "tag": "Cyberpunk"}}, ...]
"""
    response = call_gemini(prompt, model, api_key)
    return safe_json_parse(response)


def finalize_recommendations(
    candidates: list,
    user_completed: list,
    user_dropped: list,
    user_planning: list,
    model: str,
    api_key: str,
) -> dict:
    all_seen = user_completed + user_dropped

    slim = [
        {
            "title": c.get("title", {}).get("romaji") or c.get("title", {}).get("english", "Unknown"),
            "format": c.get("format", "UNKNOWN"),
            "genres": c.get("genres", []),
            "score": c.get("averageScore"),
            "description": (c.get("description") or "")[:200],
        }
        for c in candidates[:60]
    ]

    prompt = f"""
You are an expert anime recommendation engine. Analyse the user's profile and recommend anime from the candidate pool.

USER PROFILE:
- Completed ({len(user_completed)} titles): {user_completed}
- Dropped ({len(user_dropped)} titles — avoid similar ones): {user_dropped}
- Plan to watch ({len(user_planning)} titles — consider these interests): {user_planning}

CANDIDATE POOL ({len(slim)} titles):
{json.dumps(slim, ensure_ascii=False)}

INSTRUCTIONS:
1. Study the user's taste from completed, dropped, and planning lists.
2. Never recommend anything in the user's completed or dropped list.
3. Select exactly 5 SERIES (format: TV, TV_SHORT, ONA, OVA, or SPECIAL) and up to 5 MOVIES (format: MOVIE). If fewer than 5 movies exist in the pool, return as many as available.
4. Prefer variety across genres and avoid picking similar titles.
5. For each pick, explain WHY it suits this specific user (1-2 sentences referencing their actual watching history).
6. Assign a match_score (0-100) based on fit with user taste.

Return a single JSON object in this exact format (no markdown, no explanation outside the JSON):
{{
  "thinking": "Your step-by-step reasoning: what you observed in the user's completed list, what their dropped titles reveal, what their planning list signals, and how you chose each recommendation.",
  "notes": "A concise summary (3-5 sentences) of the key patterns noticed in the user's profile — genres they love, themes they avoid, and what their plan-to-watch list reveals about their interests.",
  "series": [
    {{"title": "...", "reason": "...", "match_score": 85}},
    ...5 items...
  ],
  "movies": [
    {{"title": "...", "reason": "...", "match_score": 90}},
    ...up to 5 items...
  ]
}}
"""
    response = call_gemini(prompt, model, api_key)
    return safe_json_parse(response)
