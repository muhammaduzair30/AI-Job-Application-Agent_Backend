import uuid
from datetime import datetime

from pydantic import BaseModel


class JobCreate(BaseModel):
    raw_text: str
    job_title: str | None = None
    source_url: str | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_title: str | None
    raw_text: str
    source_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobScrapeResponse(BaseModel):
    job_description: str
