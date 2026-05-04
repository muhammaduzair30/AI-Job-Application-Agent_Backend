import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    cv_id: uuid.UUID
    jd_text: str
    job_id: uuid.UUID | None = None


class ContentBlock(BaseModel):
    """A single content block for structured CV/cover letter output."""
    type: str  # heading, subheading, paragraph, list, contact, divider
    content: str | list[str]


class AnalysisResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    cv_id: uuid.UUID
    job_id: uuid.UUID | None
    match_score: int
    matched_skills: list[str]
    missing_critical: list[str]
    missing_optional: list[str]
    recommendation_summary: str
    optimised_cv: list[dict[str, Any]]
    cover_letter: list[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}
