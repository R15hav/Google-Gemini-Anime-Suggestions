from pydantic import BaseModel


class Recommendation(BaseModel):
    title: str
    reason: str
    match_score: int


class RecommendationResponse(BaseModel):
    series: list[Recommendation]
    movies: list[Recommendation]
    notes: str
    thinking: str
