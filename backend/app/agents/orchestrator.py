from app.schemas.agent import AgentChatResponse


class MRIOrchestrator:
    """Rule-based first agent; LLM/RAG can be injected without changing the API."""

    def chat(self, message: str, study_id: str | None = None) -> AgentChatResponse:
        lowered = message.lower()
        actions: list[str] = []
        if any(word in lowered for word in ("超分", "super", "分辨率")):
            actions.append("建议创建 2x 超分辨率任务")
        if study_id:
            actions.append(f"关联影像研究 {study_id}")
        return AgentChatResponse(
            answer="我可以帮助你检查影像、规划超分辨率处理流程，并解释任务状态。当前使用的是演示 Agent，不能替代影像科医生或临床诊断。",
            actions=actions,
            safety_notes=["请先完成患者信息脱敏。", "超分辨率结果仅供研究和质控，不应作为独立诊断依据。"],
        )
