import re
import json
import logging
from application.ports.llm_port import LLMPort
from application.ports.reflection_port import ReflectionPort
from domain.entities.agent_state import AgentState
from domain.entities.reflection_result import ReflectionResult
from domain.enums.task_status import TaskStatus
from domain.exceptions.domain_exceptions import ReflectionError
from prompts.reflection_prompt import (
    REFLECTION_SYSTEM_PROMPT,
    IMPROVEMENT_SYSTEM_PROMPT,
    build_reflection_prompt,
    build_improvement_prompt,
)

logger = logging.getLogger(__name__)


class ReflectionService(ReflectionPort):
    """Service that handles draft document evaluation and self-check improvements using the LLM."""


    def __init__(self, llm_port: LLMPort, quality_threshold: int = 80) -> None:
        self.llm_port = llm_port
        self.quality_threshold = quality_threshold

    async def reflect(self, state: AgentState) -> AgentState:
        """Evaluates generated content completeness and quality score."""
        logger.info("ReflectionService: Starting self-check evaluation...")
        full_content = state.get_full_content()

        user_prompt = build_reflection_prompt(
            user_request=state.request,
            document_type=state.document_type or "Business Document",
            full_content=full_content,
        )

        try:
            # Low temperature for analytical validation checks
            raw_response = await self.llm_port.generate(
                system_prompt=REFLECTION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )

            result_dict = self._parse_json(raw_response)

            quality_score = result_dict.get("quality_score", 0)
            # Use the configurable threshold
            passed = quality_score >= self.quality_threshold

            state.reflection = ReflectionResult(
                quality_score=quality_score,
                passed=passed,
                issues=result_dict.get("issues", []),
                improvement_instructions=result_dict.get("improvement_instructions", ""),
            )

            logger.info(
                "Reflection complete. Score: %d/100 | Passed: %s",
                state.reflection.quality_score,
                str(state.reflection.passed),
                extra={
                    "quality_score": state.reflection.quality_score,
                    "passed": state.reflection.passed,
                    "issues_count": len(state.reflection.issues),
                }
            )
            return state

        except ReflectionError:
            raise
        except Exception as e:
            logger.error("ReflectionService encountered an error: %s", str(e))
            raise ReflectionError(f"Reflection self-check process failed: {str(e)}") from e

    async def improve(self, state: AgentState) -> AgentState:
        """Improves document draft text based on reflection feedback."""
        if not state.reflection:
            logger.warning("No reflection results found. Skipping improvement pass.")
            return state

        logger.info("ReflectionService: Launching content improvement iteration...")
        full_content = state.get_full_content()

        user_prompt = build_improvement_prompt(
            user_request=state.request,
            document_type=state.document_type or "Business Document",
            full_content=full_content,
            improvement_instructions=state.reflection.improvement_instructions,
        )

        try:
            improved_text = await self.llm_port.generate(
                system_prompt=IMPROVEMENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.7,
            )

            # Distribute improved text back into the completed task results
            self._distribute_improved_content(state, improved_text.strip())
            logger.info("ReflectionService: Draft content updated after improvement pass.")
            return state

        except Exception as e:
            logger.error("ReflectionService failed to improve content: %s. Keeping original content.", str(e))
            # Non-fatal: keep original content if improvement fails
            return state

    def _distribute_improved_content(self, state: AgentState, improved_content: str) -> None:
        """Splits and matches improved content block back into state task results."""
        completed_tasks = [t for t in state.tasks if t.status == TaskStatus.COMPLETED]
        if not completed_tasks:
            return

        # Attempt to split section blocks by common headers or markdown breaks (---)
        sections = re.split(r"\n*---\n*", improved_content)
        sections = [s.strip() for s in sections if s.strip()]

        # If splitting failed or doesn't map clean indices, store matching chunks where possible
        # Otherwise, split by newline blocks or allocate chunks
        if len(sections) == len(completed_tasks):
            for i, task in enumerate(completed_tasks):
                content = sections[i]
                if content.startswith(task.description):
                    content = content[len(task.description):].lstrip()
                task.result = content
                state.generated_content[task.id] = content
        else:
            # Fallback: Split by double newlines into roughly equal sections if layout matches
            # Or distribute as a single block in the first completed task and clear the rest
            logger.warning(
                "Split parts count (%d) mismatch with tasks (%d). Distributing fallback chunks.",
                len(sections),
                len(completed_tasks),
            )
            # Try to divide into paragraphs
            paragraphs_split = re.split(r"\n{2,}(?=[A-Z0-9])", improved_content, maxsplit=len(completed_tasks) - 1)
            for i, task in enumerate(completed_tasks):
                if i < len(paragraphs_split):
                    content = paragraphs_split[i].strip()
                    if content.startswith(task.description):
                        content = content[len(task.description):].lstrip()
                    task.result = content
                    state.generated_content[task.id] = content

    def _parse_json(self, text: str) -> dict:
        """Robust parsing helper to extract JSON data from the LLM response without external deps."""
        cleaned = text.strip()
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()

        if not (cleaned.startswith("{") and cleaned.endswith("}")):
            braces_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if braces_match:
                cleaned = braces_match.group(1).strip()

        try:
            data = json.loads(cleaned)
            if not isinstance(data, dict):
                raise ReflectionError("LLM response structure was not a JSON object")
            return data
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON string: %s. String content: %s", str(e), text)
            raise ReflectionError(f"Failed to parse LLM reflection JSON: {str(e)}") from e
