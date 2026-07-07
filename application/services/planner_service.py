"""
PlannerService — application service responsible for dynamic planning.

Calls the LLM via LLMPort to interpret a natural-language document request
and produce an ordered list of AgentTask domain objects.  The plan adapts
entirely to the request — no tasks are hardcoded.
"""
import json
import re
import logging
from typing import Any
from application.ports.llm_port import LLMPort
from application.ports.planner_port import PlannerPort
from domain.entities.agent_state import AgentState
from domain.entities.agent_task import AgentTask
from domain.enums.task_status import TaskStatus
from domain.exceptions.domain_exceptions import PlanningError
from prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, build_planner_prompt

logger = logging.getLogger(__name__)

# Absolute hard caps enforced in the service (prompt also asks for 5–10)
_MIN_TASKS = 1
_MAX_TASKS = 10


class PlannerService(PlannerPort):
    """
    Application service that turns a free-form user request into a dynamic,
    ordered sequence of AgentTask objects using an LLM.

    The service:
    1. Validates the request before calling the LLM.
    2. Sends the request to the LLM via LLMPort (no direct Groq dependency).
    3. Parses and validates the structured JSON plan returned by the LLM.
    4. Constructs domain AgentTask objects with meaningful descriptions.
    5. Handles malformed or incomplete LLM responses with structured logging.
    """

    def __init__(self, llm_port: LLMPort) -> None:
        self._llm_port = llm_port
        logger.debug("PlannerService initialised.")

    # ------------------------------------------------------------------
    # PlannerPort implementation
    # ------------------------------------------------------------------

    async def plan(self, state: AgentState) -> AgentState:
        """
        Analyse the user request and build the sequential dynamic execution plan.

        Populates state.document_type, state.assumptions, and state.tasks.

        Args:
            state: Current agent state carrying the user request.

        Returns:
            Updated AgentState with the plan populated.

        Raises:
            PlanningError: If the LLM returns a response that cannot be parsed
                           into a valid plan, or if no valid tasks can be built.
        """
        request_preview = state.request[:120].replace("\n", " ")
        logger.info(
            "PlannerService.plan | starting | request_preview='%s...'",
            request_preview,
        )

        # Validate request before hitting the LLM
        try:
            user_prompt = build_planner_prompt(state.request)
        except ValueError as exc:
            raise PlanningError(f"Invalid planning request: {exc}") from exc

        # --- LLM call ---
        try:
            raw_response = await self._llm_port.generate(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,  # Low temperature → deterministic structure
            )
        except Exception as exc:
            logger.error(
                "PlannerService.plan | LLM call failed | error=%s", str(exc)
            )
            raise PlanningError(
                f"LLM failed during planning phase: {type(exc).__name__}: {exc}"
            ) from exc

        # --- Parse JSON plan ---
        try:
            plan_dict = self._parse_plan_json(raw_response)
        except PlanningError:
            raise  # already a PlanningError with context

        # --- Extract top-level fields ---
        document_type: str = (
            plan_dict.get("document_type") or "Business Document"
        ).strip()
        assumptions: list[str] = [
            str(a).strip()
            for a in plan_dict.get("assumptions", [])
            if str(a).strip()
        ]
        raw_tasks: list[Any] = plan_dict.get("tasks", [])

        logger.info(
            "PlannerService.plan | LLM plan received | document_type='%s' | "
            "raw_task_count=%d | assumptions=%d",
            document_type,
            len(raw_tasks),
            len(assumptions),
        )

        # --- Cap task list ---
        if len(raw_tasks) > _MAX_TASKS:
            logger.warning(
                "PlannerService.plan | LLM returned %d tasks — truncating to %d.",
                len(raw_tasks),
                _MAX_TASKS,
            )
            raw_tasks = raw_tasks[:_MAX_TASKS]

        # --- Build domain AgentTask objects ---
        tasks = self._build_tasks(raw_tasks)

        if len(tasks) < _MIN_TASKS:
            raise PlanningError(
                f"Planning produced {len(tasks)} valid task(s) "
                f"(minimum required: {_MIN_TASKS}). "
                "The LLM plan was empty or all tasks had blank descriptions."
            )

        # --- Populate state ---
        state.document_type = document_type
        state.assumptions = assumptions
        state.tasks = tasks

        logger.info(
            "PlannerService.plan | complete | document_type='%s' | "
            "tasks_accepted=%d | tasks_skipped=%d",
            document_type,
            len(tasks),
            len(raw_tasks) - len(tasks),
        )
        for i, task in enumerate(tasks):
            logger.debug(
                "  task[%d] id='%s' | description='%s'",
                i + 1,
                task.id,
                task.description[:80],
            )

        return state

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_tasks(self, raw_tasks: list[Any]) -> list[AgentTask]:
        """
        Convert raw dicts from the LLM JSON response into AgentTask domain objects.

        Skips (with a warning) any task whose id or description is blank so that
        domain invariants are never violated.
        """
        tasks: list[AgentTask] = []
        for i, raw in enumerate(raw_tasks):
            if not isinstance(raw, dict):
                logger.warning(
                    "PlannerService._build_tasks | task[%d] is not a dict — skipping.",
                    i,
                )
                continue

            # Derive a guaranteed non-empty id
            raw_id: str = str(raw.get("id") or "").strip()
            task_id: str = raw_id if raw_id else f"task_{i + 1}"

            description: str = str(raw.get("description") or "").strip()
            if not description:
                logger.warning(
                    "PlannerService._build_tasks | task[%d] (id='%s') has empty "
                    "description — skipping.",
                    i,
                    task_id,
                )
                continue

            try:
                task = AgentTask(
                    id=task_id,
                    description=description,
                    status=TaskStatus.PENDING,
                )
                tasks.append(task)
            except ValueError as exc:
                # AgentTask.__post_init__ raised — log and skip
                logger.warning(
                    "PlannerService._build_tasks | task[%d] failed domain "
                    "validation (%s) — skipping.",
                    i,
                    exc,
                )

        return tasks

    def _parse_plan_json(self, text: str) -> dict:
        """
        Extract and parse the JSON planning object from the raw LLM response.

        Handles:
        - Markdown code fences (```json … ```)
        - Leading/trailing prose before or after the JSON object
        - Whitespace-only wrappers

        Raises:
            PlanningError: If a valid JSON object cannot be extracted.
        """
        cleaned = text.strip()

        # Strip markdown code fences if present
        fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1).strip()

        # If the result isn't wrapped in braces, try to find the first {...} block
        if not (cleaned.startswith("{") and cleaned.endswith("}")):
            brace_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if brace_match:
                cleaned = brace_match.group(1).strip()

        if not cleaned:
            raise PlanningError(
                "LLM planning response was empty after stripping markdown wrappers."
            )

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(
                "PlannerService._parse_plan_json | JSON decode failed | "
                "error='%s' | raw_response_preview='%s'",
                exc,
                text[:300],
            )
            raise PlanningError(
                f"Failed to parse LLM planning JSON: {exc}. "
                "Ensure the LLM is returning a valid JSON object."
            ) from exc

        if not isinstance(data, dict):
            raise PlanningError(
                f"LLM planning response was valid JSON but not an object "
                f"(got {type(data).__name__})."
            )

        # Minimal schema check
        if "tasks" not in data:
            raise PlanningError(
                "LLM planning JSON is missing required 'tasks' key. "
                f"Keys found: {list(data.keys())}"
            )

        return data
