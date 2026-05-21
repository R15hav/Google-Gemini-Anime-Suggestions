import json
import random
import re
import time
from typing import Iterator
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
    """Raised on Gemini 429s. Carries the structured fields Google ships in
    ``error.details`` so the caller can surface a precise retry-after time
    and the exact quota dimension that was exhausted."""

    def __init__(
        self,
        model: str,
        *,
        metric: str | None = None,
        limit: int | None = None,
        model_from_api: str | None = None,
        retry_after_seconds: float | None = None,
        message: str | None = None,
    ):
        self.model = model
        self.metric = metric
        self.limit = limit
        self.model_from_api = model_from_api or model
        self.retry_after_seconds = retry_after_seconds
        self.message = message or f"Quota exceeded for model {model}"
        super().__init__(self.message)


_RETRY_DELAY_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*s\s*$")


def _parse_retry_delay(raw) -> float | None:
    """Accepts the protobuf Duration string form (e.g. ``"6.343969865s"``)
    or a plain numeric. Returns float seconds or None."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        m = _RETRY_DELAY_RE.match(raw)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


def _client_error_payload(e: ClientError) -> dict:
    """Best-effort extraction of the JSON body from a ClientError across
    SDK versions. Returns ``{}`` if nothing usable is attached."""
    for attr in ("response_json", "_response_json", "details"):
        val = getattr(e, attr, None)
        if isinstance(val, dict):
            return val
        if isinstance(val, list):
            return {"error": {"details": val}}
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            return resp.json()
        except Exception:
            pass
    return {}


def _parse_quota_error(e: ClientError, requested_model: str) -> "QuotaExceededError":
    """Walks the documented ``google.rpc.QuotaFailure`` + ``RetryInfo``
    details on a 429 response and packs them into a QuotaExceededError."""
    payload = _client_error_payload(e)
    err = payload.get("error", payload) if isinstance(payload, dict) else {}
    details = err.get("details", []) if isinstance(err, dict) else []

    metric: str | None = None
    limit: int | None = None
    model_from_api: str | None = None
    retry_after: float | None = None

    for d in details if isinstance(details, list) else []:
        if not isinstance(d, dict):
            continue
        type_url = str(d.get("@type", ""))
        if type_url.endswith("QuotaFailure"):
            violations = d.get("violations") or []
            if violations and isinstance(violations[0], dict):
                v = violations[0]
                metric = v.get("quotaMetric") or v.get("quota_metric") or metric
                raw_limit = v.get("quotaValue") or v.get("quota_value")
                if raw_limit is not None:
                    try:
                        limit = int(raw_limit)
                    except (TypeError, ValueError):
                        pass
                dims = v.get("quotaDimensions") or v.get("quota_dimensions") or {}
                if isinstance(dims, dict):
                    model_from_api = dims.get("model") or model_from_api
        elif type_url.endswith("RetryInfo"):
            retry_after = _parse_retry_delay(d.get("retryDelay") or d.get("retry_delay")) or retry_after

    message = err.get("message") if isinstance(err, dict) else None
    return QuotaExceededError(
        requested_model,
        metric=metric,
        limit=limit,
        model_from_api=model_from_api,
        retry_after_seconds=retry_after,
        message=message,
    )


def get_best_available_model(requested: str, usage_today: dict[str, int]) -> str:
    candidates = [requested] + [m for m in MODEL_FALLBACK_ORDER if m != requested]
    for model in candidates:
        limit = FREE_TIER_RPD.get(model, 1500)
        if usage_today.get(model, 0) < limit:
            return model
    raise QuotaExceededError(requested)


_SHORT_RETRY_THRESHOLD_S = 10.0


def _is_429(e: ClientError) -> bool:
    code = getattr(e, "status_code", None) or getattr(e, "code", None)
    return code == 429


def call_gemini(prompt: str, model: str = "gemini-2.5-flash-lite", api_key: str = None) -> str:
    if not api_key:
        raise ValueError("A Gemini API key must be provided.")
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text
    except ClientError as e:
        if _is_429(e):
            raise _parse_quota_error(e, model)
        raise


def call_gemini_stream(prompt: str, model: str, api_key: str) -> Iterator[str]:
    if not api_key:
        raise ValueError("A Gemini API key must be provided.")
    client = genai.Client(api_key=api_key)

    def _one_attempt():
        for chunk in client.models.generate_content_stream(model=model, contents=prompt):
            text = getattr(chunk, "text", None)
            if text:
                yield text

    try:
        yield from _one_attempt()
        return
    except ClientError as e:
        if not _is_429(e):
            raise
        quota_err = _parse_quota_error(e, model)
        # Short, bounded retry only when the server tells us to wait briefly.
        # RPM hits typically clear in single-digit seconds; RPD hits return
        # large values (seconds-until-midnight-PT) which we surface immediately.
        wait = quota_err.retry_after_seconds
        if wait is None or wait > _SHORT_RETRY_THRESHOLD_S:
            raise quota_err
        time.sleep(wait + random.uniform(0.1, 0.3))

    # Second attempt — propagate richer error on failure, no further retries.
    try:
        yield from _one_attempt()
    except ClientError as e:
        if _is_429(e):
            raise _parse_quota_error(e, model)
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


def _build_recommendation_prompt(
    candidates: list,
    user_completed: list,
    user_dropped: list,
    user_planning: list,
) -> str:
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

    return f"""
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


def finalize_recommendations(
    candidates: list,
    user_completed: list,
    user_dropped: list,
    user_planning: list,
    model: str,
    api_key: str,
) -> dict:
    prompt = _build_recommendation_prompt(candidates, user_completed, user_dropped, user_planning)
    response = call_gemini(prompt, model, api_key)
    return safe_json_parse(response)


def finalize_recommendations_stream(
    candidates: list,
    user_completed: list,
    user_dropped: list,
    user_planning: list,
    model: str,
    api_key: str,
) -> Iterator:
    """Yield text chunks from Gemini as they arrive. The final yielded value is
    a dict of shape {"__result__": <parsed JSON>} containing the parsed output."""
    prompt = _build_recommendation_prompt(candidates, user_completed, user_dropped, user_planning)
    buffer_parts: list[str] = []
    for chunk in call_gemini_stream(prompt, model, api_key):
        buffer_parts.append(chunk)
        yield chunk
    yield {"__result__": safe_json_parse("".join(buffer_parts))}
