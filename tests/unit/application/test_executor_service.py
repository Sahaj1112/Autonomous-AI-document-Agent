"""
Unit tests for ExecutorService.

Verifies that the executor:
- Executes tasks in the correct planned order.
- Tracks task execution status using domain methods.
- Collects outputs from completed tasks.
- Handles individual task failures gracefully without crashing.
- Raises ExecutionError if all tasks fail.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from domain.entities.agent_state import AgentState
from domain.entities.agent_task import AgentTask
from domain.enums.task_status import TaskStatus
from domain.exceptions.domain_exceptions import ExecutionError
from application.services.executor_service import ExecutorService
from application.services.content_service import ContentService


@pytest.fixture
def content_service_mock() -> AsyncMock:
    """Provides a mocked ContentService."""
    return AsyncMock(spec=ContentService)


@pytest.fixture
def executor(content_service_mock: AsyncMock) -> ExecutorService:
    """Provides an ExecutorService injected with the mocked ContentService."""
    return ExecutorService(content_service=content_service_mock)


@pytest.fixture
def initial_state() -> AgentState:
    """Provides a fresh AgentState with 3 pending tasks."""
    state = AgentState(request="Test Request")
    state.tasks = [
        AgentTask(id="task_1", description="First task"),
        AgentTask(id="task_2", description="Second task"),
        AgentTask(id="task_3", description="Third task"),
    ]
    return state


@pytest.mark.asyncio
async def test_executor_successful_run(executor: ExecutorService, content_service_mock: AsyncMock, initial_state: AgentState) -> None:
    """Verifies all tasks are executed and marked completed with outputs collected."""
    # Arrange
    content_service_mock.generate_content.side_effect = ["Result 1", "Result 2", "Result 3"]

    # Act
    final_state = await executor.execute_tasks(initial_state)

    # Assert
    assert content_service_mock.generate_content.call_count == 3
    
    # Check that calls were made with the correct arguments and index
    calls = content_service_mock.generate_content.call_args_list
    assert calls[0].kwargs["task"].id == "task_1"
    assert calls[0].kwargs["task_index"] == 0
    assert calls[1].kwargs["task"].id == "task_2"
    assert calls[1].kwargs["task_index"] == 1
    assert calls[2].kwargs["task"].id == "task_3"
    assert calls[2].kwargs["task_index"] == 2

    # Check state updates
    for task in final_state.tasks:
        assert task.status == TaskStatus.COMPLETED
        assert task.result is not None
        assert final_state.generated_content[task.id] == task.result

    assert final_state.generated_content["task_1"] == "Result 1"
    assert final_state.generated_content["task_2"] == "Result 2"
    assert final_state.generated_content["task_3"] == "Result 3"


@pytest.mark.asyncio
async def test_executor_handles_individual_failures(executor: ExecutorService, content_service_mock: AsyncMock, initial_state: AgentState) -> None:
    """Verifies that an exception in one task doesn't stop the execution of subsequent tasks."""
    # Arrange
    # Task 2 fails, Task 1 and Task 3 succeed.
    async def mock_generate_content(task, task_index, state):
        if task.id == "task_2":
            raise ValueError("LLM Error for Task 2")
        return f"Success for {task.id}"

    content_service_mock.generate_content.side_effect = mock_generate_content

    # Act
    final_state = await executor.execute_tasks(initial_state)

    # Assert
    assert content_service_mock.generate_content.call_count == 3

    # Task 1 check
    assert final_state.tasks[0].status == TaskStatus.COMPLETED
    assert final_state.tasks[0].result == "Success for task_1"

    # Task 2 check
    assert final_state.tasks[1].status == TaskStatus.FAILED
    assert final_state.tasks[1].error == "LLM Error for Task 2"
    assert final_state.tasks[1].result is None
    assert "task_2" not in final_state.generated_content

    # Task 3 check
    assert final_state.tasks[2].status == TaskStatus.COMPLETED
    assert final_state.tasks[2].result == "Success for task_3"


@pytest.mark.asyncio
async def test_executor_raises_when_all_fail(executor: ExecutorService, content_service_mock: AsyncMock, initial_state: AgentState) -> None:
    """Verifies that ExecutionError is raised when absolutely all tasks fail."""
    # Arrange
    content_service_mock.generate_content.side_effect = Exception("General Failure")

    # Act & Assert
    with pytest.raises(ExecutionError, match="Every planned task execution failed"):
        await executor.execute_tasks(initial_state)

    # Assert state post-failure
    assert content_service_mock.generate_content.call_count == 3
    for task in initial_state.tasks:
        assert task.status == TaskStatus.FAILED
        assert task.error == "General Failure"
        assert task.id not in initial_state.generated_content
