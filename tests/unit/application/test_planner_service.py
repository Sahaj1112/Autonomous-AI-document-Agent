"""
Unit tests for PlannerService dynamic planning.

Two conceptually different document request types are covered:

1. Project Plan  — structured management document with milestones and resources.
2. Market Research Report — analytical document with segmentation and competitive data.

Both verify that:
  - The LLM response is parsed into domain AgentTask objects.
  - document_type and assumptions are populated on the state.
  - Tasks have non-empty ids and descriptions.
  - The task list is specific to the request (not a fixed generic list).
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from domain.entities.agent_state import AgentState
from domain.enums.task_status import TaskStatus
from domain.exceptions.domain_exceptions import PlanningError
from application.ports.llm_port import LLMPort
from application.services.planner_service import PlannerService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_llm_response(document_type: str, tasks: list[dict], assumptions: list[str]) -> str:
    """Builds a well-formed JSON string that the LLM would return."""
    return json.dumps({
        "document_type": document_type,
        "tasks": tasks,
        "assumptions": assumptions,
    })


def _make_planner(llm_response: str) -> tuple[PlannerService, AsyncMock]:
    """Return a PlannerService wired to a mock LLMPort that returns *llm_response*."""
    mock_llm = AsyncMock(spec=LLMPort)
    mock_llm.generate.return_value = llm_response
    return PlannerService(llm_port=mock_llm), mock_llm


# ---------------------------------------------------------------------------
# Test 1: Project Plan request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_project_plan_request() -> None:
    """
    Verifies dynamic planning for a product-launch project plan request.

    The LLM must produce tasks that are specific to a project plan document
    (e.g. milestones, resources, budget) rather than a generic list.
    """
    llm_response = _make_llm_response(
        document_type="Product Launch Project Plan",
        tasks=[
            {"id": "task_1", "description": "Executive Summary — business case and strategic rationale for launching the AI chatbot product in Q3"},
            {"id": "task_2", "description": "Scope & Objectives — define in-scope features, out-of-scope items, and SMART success criteria"},
            {"id": "task_3", "description": "Project Timeline & Milestones — 3-month Gantt schedule with discovery, development, testing, and launch phases"},
            {"id": "task_4", "description": "Team Structure & Responsibilities — product owner, dev lead, QA, and customer success roles with RACI matrix"},
            {"id": "task_5", "description": "Budget & Resource Allocation — engineering hours, infrastructure costs, and marketing spend breakdown"},
            {"id": "task_6", "description": "Risk Register — top 7 risks with probability, impact, and mitigation strategies"},
            {"id": "task_7", "description": "Communication & Stakeholder Plan — steering committee cadence, sprint reviews, and launch communications"},
        ],
        assumptions=[
            "Target launch date is end of Q3 of the current calendar year.",
            "Engineering team consists of 4 developers and 1 QA engineer.",
            "Budget ceiling is £150,000 inclusive of cloud infrastructure.",
        ],
    )

    planner, mock_llm = _make_planner(llm_response)
    state = AgentState(request="Create a project plan for launching an AI customer support chatbot in 3 months.")

    result = await planner.plan(state)

    # --- Structural assertions ---
    assert result.document_type == "Product Launch Project Plan"
    assert len(result.tasks) == 7
    assert len(result.assumptions) == 3

    # --- Every task is a valid domain object ---
    for task in result.tasks:
        assert task.id.startswith("task_")
        assert len(task.description) > 10
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None

    # --- Task descriptions are specific to a project plan (not generic) ---
    descriptions = [t.description for t in result.tasks]
    assert any("Milestone" in d or "Timeline" in d or "Gantt" in d for d in descriptions), \
        "Expected at least one task relating to project timeline/milestones"
    assert any("Risk" in d for d in descriptions), \
        "Expected at least one task relating to a risk register"
    assert any("Budget" in d or "Resource" in d for d in descriptions), \
        "Expected at least one task relating to budget or resources"

    # --- LLM was called exactly once with a non-empty prompt ---
    mock_llm.generate.assert_called_once()
    call_kwargs = mock_llm.generate.call_args.kwargs
    assert "system_prompt" in call_kwargs
    assert "user_prompt" in call_kwargs
    assert "chatbot" in call_kwargs["user_prompt"].lower() or \
           "project plan" in call_kwargs["user_prompt"].lower()


# ---------------------------------------------------------------------------
# Test 2: Market Research Report request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_market_research_report_request() -> None:
    """
    Verifies dynamic planning for a market research report request.

    Tasks must be analytical in nature (market size, competitors, consumer
    segments) rather than project-management oriented — demonstrating that the
    planner adapts to completely different document types.
    """
    llm_response = _make_llm_response(
        document_type="UK Plant-Based Meat Market Research Report",
        tasks=[
            {"id": "task_1", "description": "Executive Summary — key findings on the UK plant-based meat market size, growth, and strategic implications"},
            {"id": "task_2", "description": "Market Size & Growth — current UK market value in £, CAGR through 2028, and volume by sub-category (burgers, sausages, mince)"},
            {"id": "task_3", "description": "Consumer Segmentation — flexitarians vs. vegans vs. health-conscious buyers, purchase drivers, and price sensitivity"},
            {"id": "task_4", "description": "Competitive Landscape — market share of Beyond Meat, Quorn, THIS, Meatless Farm; pricing and distribution channel analysis"},
            {"id": "task_5", "description": "Regulatory Environment — UK FSA labelling rules, HFSS restrictions, and sustainability certification trends"},
            {"id": "task_6", "description": "Innovation & Product Trends — whole-cut analogues, fermentation proteins, and retail vs. food-service channel shifts"},
            {"id": "task_7", "description": "Strategic Recommendations — white-space opportunities and go-to-market entry strategies for a new entrant"},
        ],
        assumptions=[
            "Research scope is limited to the United Kingdom retail and food-service market.",
            "Data referenced covers the period 2022–2024.",
            "The report is intended for a FMCG investor audience.",
        ],
    )

    planner, mock_llm = _make_planner(llm_response)
    state = AgentState(request="Create a market research report on the UK plant-based meat market.")

    result = await planner.plan(state)

    # --- Structural assertions ---
    assert result.document_type == "UK Plant-Based Meat Market Research Report"
    assert len(result.tasks) == 7
    assert len(result.assumptions) == 3

    # --- Tasks are analytical, not project-management style ---
    descriptions = [t.description for t in result.tasks]
    assert any("Market Size" in d or "CAGR" in d or "market value" in d.lower() for d in descriptions), \
        "Expected at least one market-sizing task"
    assert any("Competitive" in d or "Landscape" in d or "market share" in d.lower() for d in descriptions), \
        "Expected a competitive landscape task"
    assert any("Consumer" in d or "Segment" in d for d in descriptions), \
        "Expected a consumer segmentation task"

    # --- No overlap with project-plan vocabulary ---
    assert not any("Gantt" in d or "Milestone" in d or "RACI" in d for d in descriptions), \
        "Market research tasks should not contain project-plan language"

    # --- All tasks are valid domain objects ---
    for task in result.tasks:
        assert task.status == TaskStatus.PENDING
        assert len(task.id) > 0
        assert len(task.description) > 10


# ---------------------------------------------------------------------------
# Test 3: Malformed LLM response — missing 'tasks' key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_raises_on_missing_tasks_key() -> None:
    """PlanningError is raised when the LLM omits the 'tasks' key."""
    bad_response = json.dumps({"document_type": "Report", "assumptions": []})
    planner, _ = _make_planner(bad_response)
    state = AgentState(request="Write a quarterly financial report for our board.")

    with pytest.raises(PlanningError, match="missing required 'tasks' key"):
        await planner.plan(state)


# ---------------------------------------------------------------------------
# Test 4: All tasks have blank descriptions — PlanningError raised
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_raises_when_all_task_descriptions_blank() -> None:
    """PlanningError is raised when every task description is an empty string."""
    bad_response = _make_llm_response(
        document_type="SOP",
        tasks=[
            {"id": "task_1", "description": ""},
            {"id": "task_2", "description": "   "},
            {"id": "task_3", "description": ""},
        ],
        assumptions=[],
    )
    planner, _ = _make_planner(bad_response)
    state = AgentState(request="Create a standard operating procedure for employee onboarding.")

    with pytest.raises(PlanningError, match="0 valid task"):
        await planner.plan(state)


# ---------------------------------------------------------------------------
# Test 5: LLM wraps response in markdown fences — still parses correctly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_handles_markdown_fenced_json() -> None:
    """PlannerService correctly strips ```json … ``` fences from the LLM response."""
    inner = _make_llm_response(
        document_type="HR Onboarding Guide",
        tasks=[
            {"id": "task_1", "description": "Welcome & Company Overview — mission, values, and organisational structure"},
            {"id": "task_2", "description": "Role & Responsibilities — job description deep-dive and first 90-day expectations"},
            {"id": "task_3", "description": "Systems & Tools Setup — IT provisioning checklist and software access guide"},
            {"id": "task_4", "description": "Policies & Compliance — key HR policies, code of conduct, and mandatory training links"},
            {"id": "task_5", "description": "Contacts & Escalation Paths — line manager, HR partner, IT helpdesk, and buddy system"},
        ],
        assumptions=["New hire is a full-time employee based in the UK office."],
    )
    fenced_response = f"```json\n{inner}\n```"

    planner, _ = _make_planner(fenced_response)
    state = AgentState(request="Create an onboarding guide for new employees joining our HR team.")

    result = await planner.plan(state)

    assert result.document_type == "HR Onboarding Guide"
    assert len(result.tasks) == 5
    assert result.tasks[0].id == "task_1"


# ---------------------------------------------------------------------------
# Test 6: LLM exceeds max task limit — truncated to _MAX_TASKS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_truncates_excess_tasks() -> None:
    """Tasks beyond _MAX_TASKS (10) are truncated with a warning."""
    tasks = [
        {"id": f"task_{i}", "description": f"Section {i} covering detailed content area {i}"}
        for i in range(1, 14)  # 13 tasks — exceeds the 10-task cap
    ]
    response = _make_llm_response("Technical Specification", tasks, [])
    planner, _ = _make_planner(response)
    state = AgentState(request="Write a full technical specification for a REST API gateway service.")

    result = await planner.plan(state)

    assert len(result.tasks) == 10  # capped at _MAX_TASKS
