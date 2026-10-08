from fastapi import APIRouter

from app.agents.orchestrator import MRIOrchestrator
from app.schemas.agent import AgentChatRequest, AgentChatResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
def chat(payload: AgentChatRequest) -> AgentChatResponse:
    return MRIOrchestrator().chat(payload.message, payload.study_id)
