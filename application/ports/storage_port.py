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

    @abstractmethod
    def get_file_path(self, filename: str) -> str:
        """
        Retrieves the local absolute path for a stored file, if it exists.

        Args:
            filename: The requested filename.

        Returns:
            The absolute path to the file.
            
        Raises:
            ValueError: If the filename is invalid or poses a path traversal risk.
            FileNotFoundError: If the file does not exist.
        """
        pass
