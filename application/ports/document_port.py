from abc import ABC, abstractmethod


class DocumentPort(ABC):
    """Abstract interface defining the boundary for Document rendering operations."""

    @abstractmethod
    def generate_document(
        self,
        content: str,
        document_type: str,
    ) -> bytes:
        """
        Generate a styled Word document from structural text content.

        Args:
            content: Consolidated section content text.
            document_type: Detected type of document.

        Returns:
            The binary content (bytes) of the generated document.
        """
        pass
