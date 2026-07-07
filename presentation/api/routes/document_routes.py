import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/documents/{filename}")
async def download_document(filename: str) -> FileResponse:
    """Serves a generated Word document as an attachment download."""
    # Prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        logger.warning("Path traversal attempt blocked: %s", filename)
        raise HTTPException(status_code=400, detail="Invalid filename path parameter")

    filepath = os.path.join(settings.output_dir, filename)
    if not os.path.exists(filepath):
        logger.error("Requested file not found: %s", filepath)
        raise HTTPException(status_code=404, detail="The requested document file does not exist")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
