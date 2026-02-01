from enum import Enum
from pydantic import BaseModel
from typing import List


class Recommendation(BaseModel):
    title: str
    reason: str
    match_score: int

class RecommendationResponse(BaseModel):
    username: str
    thematic_profile: str
    suggestions: List[Recommendation]