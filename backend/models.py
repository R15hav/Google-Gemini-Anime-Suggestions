from pydantic import BaseModel


class Recommendation(BaseModel):
    title: str
    reason: str
    match_score: int
