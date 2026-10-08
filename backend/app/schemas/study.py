from datetime import datetime

from pydantic import BaseModel, Field


class Study(BaseModel):
    id: str
    filename: str
    content_type: str | None = None
    size_bytes: int = Field(ge=0)
    status: str = "uploaded"
    created_at: datetime


class StudyList(BaseModel):
    items: list[Study]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
