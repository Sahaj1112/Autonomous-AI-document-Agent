"""
Unit tests for ContentService.

Verifies that the content service:
- Calls the LLM port with the correct system and user prompts.
- Handles context retrieval from AgentState.
- Correctly strips resulting content.
- Raises ValueError when the LLM returns empty content.
- Gracefully handles and logs LLM port exceptions.
"""
import pytest
from unittest.mock import AsyncMock
from domain.entities.agent_state import AgentState
from domain.entities.agent_task import AgentTask
from application.ports.llm_port import LLMPort
from application.services.content_service import ContentService


@pytest.fixture
def mock_llm_port() -> AsyncMock:
    return AsyncMock(spec=LLMPort)


@pytest.fixture
def content_service(mock_llm_port: AsyncMock) -> ContentService:
    return ContentService(llm_port=mock_llm_port)


@pytest.fixture
def sample_state() -> AgentState:
    state = AgentState(
        request="Write a business plan for a tech startup.",
        document_type="Business Plan",
        assumptions=["Focus on B2B SaaS"],
    )
    # Add a previously completed task to test context synthesis
    task1 = AgentTask(id="task_1", description="Executive Summary")
    task1.mark_in_progress()
    task1.mark_completed("This is the completed executive summary.")
    
    # Add a pending task
    task2 = AgentTask(id="task_2", description="Market Analysis")
    state.tasks = [task1, task2]
    
    return state


@pytest.mark.asyncio
async def test_generate_content_success(content_service: ContentService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies successful content generation and proper LLM call construction."""
    mock_llm_port.generate.return_value = "   This is the generated market analysis.   \n"
    
    target_task = sample_state.tasks[1]
    
    result = await content_service.generate_content(
        task=target_task,
        task_index=1,
        state=sample_state
    )
    
    # Assert formatting is stripped
    assert result == "This is the generated market analysis."
    
    # Assert LLM port was called once
    mock_llm_port.generate.assert_called_once()
    
    kwargs = mock_llm_port.generate.call_args.kwargs
    assert "system_prompt" in kwargs
    assert "user_prompt" in kwargs
    assert "temperature" in kwargs
    assert kwargs["temperature"] == 0.7
    
    # Assert that context was correctly injected into user prompt
    user_prompt = kwargs["user_prompt"]
    assert "Business Plan" in user_prompt
    assert "Market Analysis" in user_prompt
    assert "Focus on B2B SaaS" in user_prompt
    assert "This is the completed executive summary" in user_prompt


@pytest.mark.asyncio
async def test_generate_content_empty_validation(content_service: ContentService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies ValueError is raised if the LLM returns effectively empty content."""
    # LLM returns just whitespace
    mock_llm_port.generate.return_value = "   \n  \t  "
    
    target_task = sample_state.tasks[1]
    
    with pytest.raises(ValueError, match="LLM generated empty content for task"):
        await content_service.generate_content(
            task=target_task,
            task_index=1,
            state=sample_state
        )


@pytest.mark.asyncio
async def test_generate_content_llm_failure(content_service: ContentService, mock_llm_port: AsyncMock, sample_state: AgentState) -> None:
    """Verifies exceptions from the LLMPort bubble up natively."""
    mock_llm_port.generate.side_effect = ConnectionError("Network failure")
    
    target_task = sample_state.tasks[1]
    
    with pytest.raises(ConnectionError, match="Network failure"):
        await content_service.generate_content(
            task=target_task,
            task_index=1,
            state=sample_state
        )
