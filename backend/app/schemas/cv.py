import uuid
from datetime import datetime

from pydantic import BaseModel


class CVResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CVTextResponse(BaseModel):
    id: uuid.UUID
    extracted_text: str
    created_at: datetime

    model_config = {"from_attributes": True}
