from abc import ABC, abstractmethod


class LLMPort(ABC):
    """Abstract interface defining the boundary for LLM communication."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """
        Send a chat completion request to the LLM.

        Args:
            system_prompt: System instructions/constraints.
            user_prompt: The prompt describing the task.
            temperature: Response randomness.

        Returns:
            The raw text response from the LLM.
        """
        pass
