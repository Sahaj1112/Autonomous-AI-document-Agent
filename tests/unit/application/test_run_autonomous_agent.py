import pytest
from unittest.mock import AsyncMock, MagicMock
from domain.entities.agent_state import AgentState
from domain.entities.agent_task import AgentTask
from domain.entities.reflection_result import ReflectionResult
from domain.enums.task_status import TaskStatus
from application.use_cases.run_autonomous_agent import RunAutonomousAgentUseCase
from application.services.planner_service import PlannerService
from application.services.executor_service import ExecutorService
from application.services.reflection_service import ReflectionService
from application.ports.document_port import DocumentPort


@pytest.mark.asyncio
async def test_use_case_reflection_pass() -> None:
    """Verifies use case workflow when reflection self-check passes immediately."""
    # 1. Arrange Mock Services
    planner_mock = AsyncMock(spec=PlannerService)
    executor_mock = AsyncMock(spec=ExecutorService)
    reflector_mock = AsyncMock(spec=ReflectionService)
    document_mock = MagicMock(spec=DocumentPort)
    storage_mock = AsyncMock()

    # Set up states returned by planner and executor mocks
    def plan_side_effect(state: AgentState) -> AgentState:
        state.document_type = "Project Plan"
        state.tasks = [AgentTask(id="t1", description="Draft section")]
        state.assumptions = ["Assumed target"]
        return state

    def execute_side_effect(state: AgentState) -> AgentState:
        state.tasks[0].status = TaskStatus.COMPLETED
        state.tasks[0].result = "Draft contents"
        state.generated_content["t1"] = "Draft contents"
        return state

    def reflect_side_effect(state: AgentState) -> AgentState:
        state.reflection = ReflectionResult(quality_score=90, passed=True)
        return state

    planner_mock.plan.side_effect = plan_side_effect
    executor_mock.execute_tasks.side_effect = execute_side_effect
    reflector_mock.reflect.side_effect = reflect_side_effect
    document_mock.generate_document.return_value = b"mock bytes"
    storage_mock.save_file.return_value = "generated_documents/test.docx"

    # Instantiate use case
    use_case = RunAutonomousAgentUseCase(
        planner_port=planner_mock,
        executor_service=executor_mock,
        reflection_port=reflector_mock,
        document_port=document_mock,
        storage_port=storage_mock,
    )

    # 2. Act
    final_state = await use_case.execute("Generate plan")

    # 3. Assert
    assert final_state.document_type == "Project Plan"
    assert final_state.tasks[0].status == TaskStatus.COMPLETED
    assert final_state.reflection.quality_score == 90
    assert final_state.document_filename == "test.docx"

    # Check execution sequence count
    planner_mock.plan.assert_called_once()
    executor_mock.execute_tasks.assert_called_once()
    reflector_mock.reflect.assert_called_once()
    reflector_mock.improve.assert_not_called()  # Reflection score was >= 80, should not improve
    document_mock.generate_document.assert_called_once()
    storage_mock.save_file.assert_called_once()


@pytest.mark.asyncio
async def test_use_case_reflection_fail_and_improve() -> None:
    """Verifies use case workflow runs improvement pass when reflection self-check score is < 80."""
    planner_mock = AsyncMock(spec=PlannerService)
    executor_mock = AsyncMock(spec=ExecutorService)
    reflector_mock = AsyncMock(spec=ReflectionService)
    document_mock = MagicMock(spec=DocumentPort)
    storage_mock = AsyncMock()

    # Mock side effects
    planner_mock.plan.side_effect = lambda s: s
    executor_mock.execute_tasks.side_effect = lambda s: s

    # Set mock reflection score to fail first, then pass
    reflect_counter = 0

    async def reflect_side_effect(state: AgentState) -> AgentState:
        nonlocal reflect_counter
        if reflect_counter == 0:
            state.reflection = ReflectionResult(
                quality_score=60, passed=False, improvement_instructions="Fix formatting"
            )
        else:
            state.reflection = ReflectionResult(quality_score=85, passed=True)
        reflect_counter += 1
        return state

    reflector_mock.reflect.side_effect = reflect_side_effect
    reflector_mock.improve.side_effect = lambda s: s
    document_mock.generate_document.return_value = b"mock bytes"
    storage_mock.save_file.return_value = "generated_documents/test.docx"

    use_case = RunAutonomousAgentUseCase(
        planner_port=planner_mock,
        executor_service=executor_mock,
        reflection_port=reflector_mock,
        document_port=document_mock,
        storage_port=storage_mock,
    )

    # Act
    final_state = await use_case.execute("Generate plan")

    # Assert
    assert final_state.reflection.quality_score == 85
    assert final_state.reflection.passed is True
    assert planner_mock.plan.call_count == 1
    assert executor_mock.execute_tasks.call_count == 1
    assert reflector_mock.reflect.call_count == 2  # Once before improvement, once after
    assert reflector_mock.improve.call_count == 1  # Called due to score 60 < 80
    document_mock.generate_document.assert_called_once()
    storage_mock.save_file.assert_called_once()


@pytest.mark.asyncio
async def test_use_case_reflection_exhausts_retries() -> None:
    """Verifies that reflection improvement loop terminates after max_reflection_retries if score remains low."""
    planner_mock = AsyncMock(spec=PlannerService)
    executor_mock = AsyncMock(spec=ExecutorService)
    reflector_mock = AsyncMock(spec=ReflectionService)
    document_mock = MagicMock(spec=DocumentPort)
    storage_mock = AsyncMock()

    planner_mock.plan.side_effect = lambda s: s
    executor_mock.execute_tasks.side_effect = lambda s: s

    # Always return a failing reflection score
    async def reflect_side_effect(state: AgentState) -> AgentState:
        state.reflection = ReflectionResult(
            quality_score=50, passed=False, improvement_instructions="Still bad"
        )
        return state

    reflector_mock.reflect.side_effect = reflect_side_effect
    reflector_mock.improve.side_effect = lambda s: s
    document_mock.generate_document.return_value = b"mock bytes"
    storage_mock.save_file.return_value = "generated_documents/test.docx"

    use_case = RunAutonomousAgentUseCase(
        planner_port=planner_mock,
        executor_service=executor_mock,
        reflection_port=reflector_mock,
        document_port=document_mock,
        storage_port=storage_mock,
        max_reflection_retries=2, # Set max retries to 2
    )

    final_state = await use_case.execute("Generate plan")

    assert final_state.reflection.quality_score == 50
    assert final_state.reflection.passed is False
    # reflect called once initially, and once per retry loop (2 retries) = 3 total calls
    assert reflector_mock.reflect.call_count == 3
    # improve called exactly max_reflection_retries times
    assert reflector_mock.improve.call_count == 2
    document_mock.generate_document.assert_called_once()
