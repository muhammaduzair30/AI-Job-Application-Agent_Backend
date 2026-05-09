import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


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

    @field_validator("matched_skills", "missing_critical", "missing_optional", mode="before")
    @classmethod
    def sanitize_skills(cls, v: Any) -> list[str]:
        if not v:
            return []
            
        if not isinstance(v, list):
            v = [v]
            
        sanitized = []
        for item in v:
            if isinstance(item, str):
                sanitized.append(item)
            elif isinstance(item, dict) and "skills" in item:
                # Extract skills from dict like {'job': '...', 'skills': ['...']}
                skills = item["skills"]
                if isinstance(skills, list):
                    sanitized.extend([str(s) for s in skills])
            elif isinstance(item, list):
                sanitized.extend([str(s) for s in item])
            else:
                sanitized.append(str(item))
                
        # Remove duplicates while preserving order
        seen = set()
        return [x for x in sanitized if not (x in seen or seen.add(x))]

    model_config = {"from_attributes": True}
