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
        from pathlib import Path
        import re

        # Basic sanitization of filename to remove unsafe characters
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        
        # Ensure filename does not contain path traversal characters
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError(f"Invalid filename: {filename}")

        base_dir = Path(self.output_dir).resolve(strict=False)
        filepath = (base_dir / safe_filename).resolve(strict=False)

        # Ensure the resolved path remains inside the configured output directory
        filepath.relative_to(base_dir)

        with open(filepath, "wb") as f:
            f.write(content)
        return str(filepath)

    def get_file_path(self, filename: str) -> str:
        """
        Validates the requested filename and returns its absolute path.
        """
        from pathlib import Path
        
        # Ensure filename does not contain path traversal characters
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Path traversal attempt detected in filename.")

        base_dir = Path(self.output_dir).resolve(strict=False)
        filepath = (base_dir / filename).resolve(strict=False)

        # Enforce sandbox: ensure the resolved path remains inside the output directory
        try:
            filepath.relative_to(base_dir)
        except ValueError:
            raise ValueError("Requested file path escapes the configured document directory.")

        if not filepath.exists() or not filepath.is_file():
            raise FileNotFoundError(f"The document '{filename}' could not be found.")

        return str(filepath)
