from domain.entities.agent_state import AgentState
from domain.entities.agent_task import AgentTask
from domain.enums.task_status import TaskStatus


def test_agent_state_get_full_content() -> None:
    """Verifies that completed tasks are consolidated correctly into a formatted content block."""
    state = AgentState(request="Develop a user guide")
    state.tasks = [
        AgentTask(id="t1", description="Introduction", status=TaskStatus.COMPLETED, result="Welcome text"),
        AgentTask(id="t2", description="Overview", status=TaskStatus.PENDING, result="Pending text"),
        AgentTask(id="t3", description="Conclusion", status=TaskStatus.COMPLETED, result="Final words"),
    ]

    full_content = state.get_full_content()
    expected = "Introduction\n\nWelcome text\n\n---\n\nConclusion\n\nFinal words"
    assert full_content == expected


def test_agent_state_get_previous_sections_summary() -> None:
    """Verifies summary generation for contextual flow inside content service."""
    state = AgentState(request="Guide")
    state.tasks = [
        AgentTask(id="t1", description="Section 1", status=TaskStatus.COMPLETED, result="A short text"),
        AgentTask(id="t2", description="Section 2", status=TaskStatus.COMPLETED, result="A very long text " * 50),
        AgentTask(id="t3", description="Section 3", status=TaskStatus.PENDING),
    ]

    # At task 2 (index 1), only section 1 (index 0) has completed
    summary_at_1 = state.get_previous_sections_summary(1)
    assert summary_at_1 == "[Section 1]: A short text"

    # At task 3 (index 2), both section 1 and 2 completed. Section 2 should be truncated.
    summary_at_2 = state.get_previous_sections_summary(2)
    assert "[Section 1]: A short text" in summary_at_2
    assert "[Section 2]:" in summary_at_2
    assert "..." in summary_at_2
