import os
from application.ports.storage_port import StoragePort


class LocalDiskStorageAdapter(StoragePort):
    """Infrastructure adapter for storing files on the local filesystem."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def save_file(self, filename: str, content: bytes) -> str:
        """
        Saves the binary content to a local file.

        Args:
            filename: The name of the file to save.
            content: The binary content of the file.

        Returns:
            The absolute path to the saved file.
        """
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(content)
        return os.path.abspath(filepath)
