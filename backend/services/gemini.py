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
You are an expert anime and video game recommendation engine.

USER PROFILE:
- Completed ({len(user_completed)} titles): {json.dumps(user_completed[:50], ensure_ascii=False)}
- Dropped ({len(user_dropped)} titles — avoid similar ones): {json.dumps(user_dropped[:20], ensure_ascii=False)}
- Plan to watch ({len(user_planning)} titles): {json.dumps(user_planning[:30], ensure_ascii=False)}

CANDIDATE POOL ({len(slim)} titles — pick series and movies only from here):
{json.dumps(slim, ensure_ascii=False)}

INSTRUCTIONS:
1. Never recommend anything in the completed or dropped lists.
2. Select exactly 5 SERIES (format TV, TV_SHORT, ONA, OVA, or SPECIAL) from the candidate pool.
3. Select up to 5 MOVIES (format MOVIE) from the candidate pool. If fewer than 5 movies exist, return as many as available.
4. Generate exactly 5 VIDEO GAME recommendations based on the user's anime taste — these do NOT come from the candidate pool; use your knowledge of real games.
5. For every pick include all these fields:
   - "title": the title
   - "reason": 1-2 sentences explaining why it suits this specific user, referencing their actual watch history
   - "match_score": integer 0-100 reflecting fit with user taste
   - "similar": ONE title from the user's completed list this resembles most closely
   - "year": release year as an integer (e.g. 2022)
   - "studio": studio name (anime) or developer name (games)
   - "genres": array of 2-3 genre strings

Return ONLY a valid JSON object — no markdown fences, no explanation outside the JSON:
{{
  "thinking": "your step-by-step reasoning about the user's taste and each pick",
  "notes": "3-5 sentence profile summary: key genres they love, themes they tend to drop, and what their plan-to-watch list signals",
  "series": [
    {{"title": "...", "reason": "...", "match_score": 85, "similar": "...", "year": 2019, "studio": "...", "genres": ["...", "..."]}},
    ...exactly 5 items
  ],
  "movies": [
    {{"title": "...", "reason": "...", "match_score": 90, "similar": "...", "year": 2021, "studio": "...", "genres": ["...", "..."]}},
    ...up to 5 items
  ],
  "games": [
    {{"title": "...", "reason": "...", "match_score": 88, "similar": "...", "year": 2022, "studio": "...", "genres": ["...", "..."]}},
    ...exactly 5 items
  ]
}}
"""
    response = call_gemini(prompt, model, api_key)
    return safe_json_parse(response)
