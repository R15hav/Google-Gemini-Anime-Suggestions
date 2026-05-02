from pydantic import BaseModel, ConfigDict


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str
    reason: str
    match_score: int
    similar: str = ""
    year: int | None = None
    studio: str = ""
    genres: list[str] = []


class UserProfile(BaseModel):
    username: str
    watched: int
    mean_score: float
    top_genres: list[str]
    recent_fav: str


class RecommendationResponse(BaseModel):
    series: list[Recommendation]
    movies: list[Recommendation]
    games: list[Recommendation]
    notes: str
    thinking: str
    profile: UserProfile
