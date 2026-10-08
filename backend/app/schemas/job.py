from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    scale: int = Field(default=2, ge=2, le=4)
    method: str = Field(default="baseline", pattern="^(baseline|model)$")


class Job(BaseModel):
    id: str
    study_id: str
    status: str
    scale: int
    method: str
    output_path: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
