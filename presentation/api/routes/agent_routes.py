import logging
from fastapi import APIRouter, Depends
from presentation.api.schemas.agent_request import AgentRequest
from presentation.api.schemas.agent_response import AgentResponse
from application.use_cases.run_autonomous_agent import RunAutonomousAgentUseCase
from app.dependencies import get_agent_use_case

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/agent", response_model=AgentResponse)
async def run_agent(
    payload: AgentRequest,
    use_case: RunAutonomousAgentUseCase = Depends(get_agent_use_case),
) -> AgentResponse:
    """
    Submits a natural language document generation request to the autonomous agent.
    Runs planning, sequentially writes sections, checks quality, and returns a docx file download link.
    """
    logger.info("Presentation: POST /agent request received.")
    state = await use_case.execute(payload.request)

    # Convert reflection domain dataclass to response schema representation
    reflection_resp = {
        "quality_score": state.reflection.quality_score if state.reflection else 0,
        "passed": state.reflection.passed if state.reflection else False,
        "issues": state.reflection.issues if state.reflection else [],
        "improvement_instructions": state.reflection.improvement_instructions if state.reflection else "",
    }

    # Format response trace JSON
    return AgentResponse(
        request=state.request,
        document_type=state.document_type or "Business Document",
        execution_plan=[task.description for task in state.tasks],
        tasks=[
            {
                "id": task.id,
                "description": task.description,
                "status": task.status,
                "result": task.result,
                "error": task.error,
            }
            for task in state.tasks
        ],
        assumptions=state.assumptions,
        reflection=reflection_resp,
        document_path=state.document_path or "",
        download_url=f"/documents/{state.document_filename}" if state.document_filename else "",
    )


@router.get("/health")
async def health_check():
    """Liveness check returning health status."""
    return {"status": "healthy"}
