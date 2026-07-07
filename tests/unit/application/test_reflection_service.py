"""
Unit tests for ReflectionService.

Verifies:
- Evaluation uses proper threshold settings.
- Reflection JSON is correctly parsed into a ReflectionResult domain object.
- Improvement pass invokes LLM and maps content back to AgentState.
"""
import pytest
import json
from unittest.mock import AsyncMock
from domain.entities.agent_state import AgentState
from domain.entities.agent_task import AgentTask
from domain.enums.task_status import TaskStatus
from domain.exceptions.domain_exceptions import ReflectionError
from application.ports.llm_port import LLMPort
from application.services.reflection_service import ReflectionService


@pytest.fixture
def mock_llm_port() -> AsyncMock:
    return AsyncMock(spec=LLMPort)


@pytest.fixture
def reflection_service(mock_llm_port: AsyncMock) -> ReflectionService:
    return ReflectionService(llm_port=mock_llm_port, quality_threshold=80)


@pytest.fixture
def sample_state() -> AgentState:
    state = AgentState(request="Test Request", document_type="Test Doc")
    task1 = AgentTask(id="task_1", description="Part 1")
    task1.mark_in_progress()
    task1.mark_completed("Content for Part 1")
    
    task2 = AgentTask(id="task_2", description="Part 2")
    task2.mark_in_progress()
    task2.mark_completed("Content for Part 2")
    
    state.tasks = [task1, task2]
    return state


@pytest.mark.asyncio
async def test_reflect_passes_threshold(reflection_service: ReflectionService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies that reflection correctly parses a passing score from the LLM."""
    mock_response = {
        "quality_score": 85,
        "passed": True,
        "issues": [],
        "improvement_instructions": ""
    }
    mock_llm_port.generate.return_value = json.dumps(mock_response)
    
    result_state = await reflection_service.reflect(sample_state)
    
    assert result_state.reflection is not None
    assert result_state.reflection.quality_score == 85
    assert result_state.reflection.passed is True
    assert result_state.reflection.improvement_instructions == ""
    
    mock_llm_port.generate.assert_called_once()
    assert "Test Doc" in mock_llm_port.generate.call_args.kwargs["user_prompt"]


@pytest.mark.asyncio
async def test_reflect_fails_threshold(reflection_service: ReflectionService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies that reflection correctly marks failures based on the injected threshold."""
    # Score 75 is below the threshold of 80
    mock_response = {
        "quality_score": 75,
        "passed": False,
        "issues": ["Missing details"],
        "improvement_instructions": "Add more details to Part 2."
    }
    mock_llm_port.generate.return_value = f"```json\n{json.dumps(mock_response)}\n```"
    
    result_state = await reflection_service.reflect(sample_state)
    
    assert result_state.reflection is not None
    assert result_state.reflection.quality_score == 75
    assert result_state.reflection.passed is False
    assert "Add more details" in result_state.reflection.improvement_instructions


@pytest.mark.asyncio
async def test_reflect_handles_invalid_json(reflection_service: ReflectionService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies that invalid LLM response throws ReflectionError."""
    mock_llm_port.generate.return_value = "This is not valid JSON."
    
    with pytest.raises(ReflectionError, match="Failed to parse LLM reflection JSON"):
        await reflection_service.reflect(sample_state)


@pytest.mark.asyncio
async def test_improve_skips_if_no_reflection(reflection_service: ReflectionService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies that improve does nothing if no reflection exists."""
    result_state = await reflection_service.improve(sample_state)
    
    mock_llm_port.generate.assert_not_called()
    assert result_state == sample_state


@pytest.mark.asyncio
async def test_improve_distributes_content(reflection_service: ReflectionService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies that improve parses LLM feedback and distributes to tasks."""
    # Set up failure state
    sample_state.reflection = type("ReflectionResult", (), {"improvement_instructions": "Fix things"})()
    
    # LLM returns new content separated by markdown breaks
    improved_content = "Improved Content 1\n\n---\n\nImproved Content 2"
    mock_llm_port.generate.return_value = improved_content
    
    result_state = await reflection_service.improve(sample_state)
    
    mock_llm_port.generate.assert_called_once()
    
    assert result_state.tasks[0].result == "Improved Content 1"
    assert result_state.tasks[1].result == "Improved Content 2"
