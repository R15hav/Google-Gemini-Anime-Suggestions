"""Smoke test for the 429 error parser. Run directly: `python -m backend.services.test_gemini_quota`."""

import sys

from backend.services.gemini import _parse_quota_error, _parse_retry_delay


class _FakeClientError(Exception):
    def __init__(self, payload: dict):
        self.response_json = payload


SAMPLE_429 = {
    "error": {
        "code": 429,
        "status": "RESOURCE_EXHAUSTED",
        "message": "Quota exceeded for metric: generate_content_free_tier_requests, limit: 25, model: gemini-2.5-pro. Please retry in 6.343969865s.",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                "violations": [
                    {
                        "quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                        "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier",
                        "quotaDimensions": {"model": "gemini-2.5-pro", "location": "global"},
                        "quotaValue": "25",
                    }
                ],
            },
            {
                "@type": "type.googleapis.com/google.rpc.RetryInfo",
                "retryDelay": "6.343969865s",
            },
            {
                "@type": "type.googleapis.com/google.rpc.Help",
                "links": [{"description": "Docs", "url": "https://ai.google.dev/gemini-api/docs/rate-limits"}],
            },
        ],
    }
}


def main() -> int:
    err = _parse_quota_error(_FakeClientError(SAMPLE_429), "gemini-2.5-pro")
    failures: list[str] = []

    def check(name, got, expected):
        if got != expected:
            failures.append(f"{name}: got {got!r}, expected {expected!r}")

    check("model", err.model, "gemini-2.5-pro")
    check("model_from_api", err.model_from_api, "gemini-2.5-pro")
    check("metric", err.metric, "generativelanguage.googleapis.com/generate_content_free_tier_requests")
    check("limit", err.limit, 25)
    check("retry_after_seconds", err.retry_after_seconds, 6.343969865)
    assert err.message and "Quota exceeded" in err.message, "message should preserve Google's text"

    # Fallback: missing details
    empty = _parse_quota_error(_FakeClientError({}), "gemini-2.5-flash")
    check("empty.model", empty.model, "gemini-2.5-flash")
    check("empty.metric", empty.metric, None)
    check("empty.limit", empty.limit, None)
    check("empty.retry_after_seconds", empty.retry_after_seconds, None)

    # _parse_retry_delay edge cases
    check("retry_delay '3s'", _parse_retry_delay("3s"), 3.0)
    check("retry_delay '12.5s'", _parse_retry_delay("12.5s"), 12.5)
    check("retry_delay numeric", _parse_retry_delay(4.2), 4.2)
    check("retry_delay None", _parse_retry_delay(None), None)
    check("retry_delay garbage", _parse_retry_delay("not-a-duration"), None)

    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("OK: _parse_quota_error smoke checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
