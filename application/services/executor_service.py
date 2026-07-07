import logging
from application.services.content_service import ContentService
from domain.entities.agent_state import AgentState
from domain.enums.task_status import TaskStatus
from domain.exceptions.domain_exceptions import ExecutionError

logger = logging.getLogger(__name__)


class ExecutorService:
    """Service coordinates sequential execution of planned tasks and updates execution state."""

    def __init__(self, content_service: ContentService) -> None:
        self.content_service = content_service

    async def execute_tasks(self, state: AgentState) -> AgentState:
        """Executes all tasks in the agent state task list sequentially."""
        logger.info("ExecutorService: Initiating sequential task execution...")

        completed_count = 0
        failed_count = 0

        for index, task in enumerate(state.tasks):
            task.mark_in_progress()
            logger.info("Task %s: %s | Status: IN_PROGRESS", task.id, task.description)

            try:
                result = await self.content_service.generate_content(
                    task=task,
                    task_index=index,
                    state=state,
                )

                task.mark_completed(result)
                state.generated_content[task.id] = result
                completed_count += 1
                logger.info("Task %s completed successfully.", task.id)

            except Exception as e:
                logger.error("Task %s failed: %s", task.id, str(e))
                task.mark_failed(str(e))
                failed_count += 1

        logger.info(
            "ExecutorService finished. Total Tasks: %d | Completed: %d | Failed: %d",
            len(state.tasks),
            completed_count,
            failed_count,
        )

        if completed_count == 0:
            raise ExecutionError("Every planned task execution failed.")

        return state
