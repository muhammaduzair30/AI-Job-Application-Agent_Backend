import uuid
from datetime import datetime

from pydantic import BaseModel


class JobApplicationCreate(BaseModel):
    cv_id: uuid.UUID
    job_id: uuid.UUID
    analysis_id: uuid.UUID | None = None
    status: str = "saved"
    notes: str | None = None


class JobApplicationUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    applied_date: datetime | None = None


class JobApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    cv_id: uuid.UUID
    job_id: uuid.UUID
    analysis_id: uuid.UUID | None
    status: str
    applied_date: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
