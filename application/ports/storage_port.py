from abc import ABC, abstractmethod


class StoragePort(ABC):
    """Abstract interface defining the boundary for file and document storage."""

    @abstractmethod
    async def save_file(self, filename: str, content: bytes) -> str:
        """
        Saves the binary content to persistent storage.

        Args:
            filename: The intended name of the file.
            content: The binary content to store.

        Returns:
            The URI or local path where the file is stored.
        """
        pass
