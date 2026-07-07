import logging
from fastapi import APIRouter, Depends
from presentation.api.schemas.agent_request import AgentRequest
from presentation.api.schemas.agent_response import AgentResponse
from infrastructure.config.settings import settings
from infrastructure.llm.groq_llm_adapter import GroqLLMAdapter
from infrastructure.document.docx_document_adapter import DocxDocumentAdapter
from application.services.planner_service import PlannerService
from application.services.content_service import ContentService
from application.services.executor_service import ExecutorService
from application.services.reflection_service import ReflectionService
from application.use_cases.run_autonomous_agent import RunAutonomousAgentUseCase

logger = logging.getLogger(__name__)

router = APIRouter()


def get_agent_use_case() -> RunAutonomousAgentUseCase:
    """Dependency injector setting up adapters, services, and use case orchestration."""
    llm_adapter = GroqLLMAdapter(api_key=settings.groq_api_key, model=settings.groq_model)
    document_adapter = DocxDocumentAdapter()
    from infrastructure.storage.local_storage_adapter import LocalDiskStorageAdapter
    storage_adapter = LocalDiskStorageAdapter(output_dir=settings.output_dir)

    planner_service = PlannerService(llm_port=llm_adapter)
    content_service = ContentService(llm_port=llm_adapter)
    executor_service = ExecutorService(content_service=content_service)
    reflection_service = ReflectionService(llm_port=llm_adapter, quality_threshold=settings.reflection_quality_threshold)

    return RunAutonomousAgentUseCase(
        planner_port=planner_service,
        executor_service=executor_service,
        reflection_port=reflection_service,
        document_port=document_adapter,
        storage_port=storage_adapter,
        max_reflection_retries=settings.max_reflection_retries,
    )


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
