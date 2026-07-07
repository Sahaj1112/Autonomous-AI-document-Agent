import os
import asyncio
import logging
import uuid
from domain.entities.agent_state import AgentState
from application.ports.planner_port import PlannerPort
from application.ports.reflection_port import ReflectionPort
from application.ports.document_port import DocumentPort
from application.ports.storage_port import StoragePort
from application.services.executor_service import ExecutorService
from domain.exceptions.domain_exceptions import DomainError

logger = logging.getLogger(__name__)


class RunAutonomousAgentUseCase:
    """Core orchestrator executing the autonomous document agent workflow."""

    def __init__(
        self,
        planner_port: PlannerPort,
        executor_service: ExecutorService,
        reflection_port: ReflectionPort,
        document_port: DocumentPort,
        storage_port: StoragePort,
        max_reflection_retries: int = 1,
    ) -> None:
        self.planner_port = planner_port
        self.executor_service = executor_service
        self.reflection_port = reflection_port
        self.document_port = document_port
        self.storage_port = storage_port
        self.max_reflection_retries = max_reflection_retries

    async def execute(self, request_text: str) -> AgentState:
        """
        Runs the complete autonomous generation workflow:
        Plan -> Sequential content generation -> Self-check reflection -> Optional Improvement -> Word compilation.
        """
        request_text = request_text.strip()
        if not request_text or len(request_text) < 10:
            logger.warning("Agent workflow rejected due to invalid request length.", extra={"request_length": len(request_text)})
            raise DomainError("Request text must be at least 10 characters long.")

        logger.info(
            "RunAutonomousAgentUseCase: Launching agent workflow.",
            extra={"request_length": len(request_text), "action": "start_workflow"}
        )
        state = AgentState(request=request_text)

        try:
            # 1. Planning phase
            state = await self.planner_port.plan(state)

            # 2. Sequential execution phase
            state = await self.executor_service.execute_tasks(state)

            # 3. Reflection / self-check phase
            state = await self.reflection_port.reflect(state)

            # 4. Content improvement loop (configurable max retries)
            retry_count = 0
            while state.reflection and not state.reflection.passed and retry_count < self.max_reflection_retries:
                logger.info(
                    "Document score %d failed threshold. Running improvement pass %d/%d...",
                    state.reflection.quality_score,
                    retry_count + 1,
                    self.max_reflection_retries,
                    extra={
                        "quality_score": state.reflection.quality_score,
                        "retry_count": retry_count + 1,
                        "max_retries": self.max_reflection_retries,
                        "action": "improve_content"
                    }
                )
                state = await self.reflection_port.improve(state)
                # Recheck document quality score
                state = await self.reflection_port.reflect(state)
                retry_count += 1
                logger.info(
                    "Improved document score: %d/100 (Passed: %s) after retry %d",
                    state.reflection.quality_score,
                    str(state.reflection.passed),
                    retry_count,
                    extra={
                        "quality_score": state.reflection.quality_score,
                        "passed": state.reflection.passed,
                        "retry_count": retry_count,
                    }
                )
            
            if state.reflection and not state.reflection.passed:
                logger.warning("Document failed quality checks after %d retries. Proceeding with best effort.", retry_count)
            else:
                logger.info("Quality verification checks passed.")

            # 5. Document compiling phase (wrapped in to_thread to keep FastAPI non-blocking)
            logger.info("RunAutonomousAgentUseCase: Rending polished Word document...")
            full_text = state.get_full_content()
            doc_type = state.document_type or "Business Document"

            document_bytes = await asyncio.to_thread(
                self.document_port.generate_document,
                content=full_text,
                document_type=doc_type,
            )
            
            filename = f"agent_doc_{uuid.uuid4().hex[:8]}.docx"
            filepath = await self.storage_port.save_file(filename, document_bytes)

            state.document_path = filepath
            state.document_filename = os.path.basename(filepath)

            logger.info(
                "RunAutonomousAgentUseCase: Completed successfully.",
                extra={
                    "action": "complete_workflow",
                    "document_type": state.document_type,
                    "final_quality_score": state.reflection.quality_score if state.reflection else 0,
                    "filepath": filepath
                }
            )
            return state

        except DomainError:
            raise
        except Exception as e:
            logger.error("RunAutonomousAgentUseCase failed: %s", str(e), exc_info=True, extra={"action": "workflow_error"})
            raise DomainError(f"Workflow execution failure: {str(e)}") from e
