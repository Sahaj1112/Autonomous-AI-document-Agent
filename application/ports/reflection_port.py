from abc import ABC, abstractmethod
from domain.entities.agent_state import AgentState


class ReflectionPort(ABC):
    """Abstract interface defining the boundary for content reflection and quality evaluation."""

    @abstractmethod
    async def reflect(self, state: AgentState) -> AgentState:
        """
        Evaluates generated content completeness and quality.

        Args:
            state: The current agent state containing generated content.

        Returns:
            The updated agent state containing the reflection result.
        """
        pass

    @abstractmethod
    async def improve(self, state: AgentState) -> AgentState:
        """
        Improves document draft text based on reflection feedback.

        Args:
            state: The current agent state containing the reflection issues.

        Returns:
            The updated agent state with improved content.
        """
        pass
