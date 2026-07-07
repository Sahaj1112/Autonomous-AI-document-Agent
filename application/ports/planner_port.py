from abc import ABC, abstractmethod
from domain.entities.agent_state import AgentState


class PlannerPort(ABC):
    """Abstract interface defining the boundary for planning capabilities."""

    @abstractmethod
    async def plan(self, state: AgentState) -> AgentState:
        """
        Analyze the request and build the sequential execution plan.
        Updates document_type, assumptions, and tasks in the agent state.

        Args:
            state: The current agent state containing the user request.

        Returns:
            The updated agent state containing the plan.
        """
        pass
