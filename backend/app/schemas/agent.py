from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    study_id: str | None = None


class AgentChatResponse(BaseModel):
    answer: str
    actions: list[str] = []
    safety_notes: list[str] = []
