import logging
from application.ports.llm_port import LLMPort
from domain.entities.agent_state import AgentState
from domain.entities.agent_task import AgentTask
from prompts.content_prompt import CONTENT_SYSTEM_PROMPT, build_content_prompt

logger = logging.getLogger(__name__)


class ContentService:
    """Service that handles section content generation using context from previous tasks."""

    def __init__(self, llm_port: LLMPort) -> None:
        self.llm_port = llm_port

    async def generate_content(
        self,
        task: AgentTask,
        task_index: int,
        state: AgentState,
    ) -> str:
        """Calls the LLM to generate the text content for a single section."""
        logger.info("ContentService: Generating section content for task %s...", task.id)

        # Retrieve a preview summary of previous sections to maintain document flow
        previous_summary = state.get_previous_sections_summary(task_index)

        user_prompt = build_content_prompt(
            user_request=state.request,
            document_type=state.document_type or "Business Document",
            task_description=task.description,
            previous_sections=previous_summary,
            assumptions=state.assumptions,
        )

        try:
            # High temperature for rich content synthesis
            content = await self.llm_port.generate(
                system_prompt=CONTENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.7,
            )
        except Exception as e:
            logger.error("ContentService: LLM generation failed for task %s: %s", task.id, str(e))
            raise

        final_content = content.strip()
        if not final_content:
            logger.error("ContentService: LLM returned empty content for task %s", task.id)
            raise ValueError(f"LLM generated empty content for task '{task.description}'")

        logger.debug("ContentService: Successfully generated content for task %s (%d chars)", task.id, len(final_content))
        return final_content
