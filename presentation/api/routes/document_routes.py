import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from application.ports.storage_port import StoragePort
from app.dependencies import get_storage_port

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/documents/{filename}")
async def download_document(
    filename: str,
    storage_port: StoragePort = Depends(get_storage_port)
) -> FileResponse:
    """Serves a generated Word document as an attachment download."""
    try:
        # storage_port.get_file_path handles path traversal and existence validation natively
        filepath = storage_port.get_file_path(filename)
    except ValueError as e:
        logger.warning("Invalid file request: %s", str(e))
        raise HTTPException(status_code=400, detail="Invalid filename path parameter")
    except FileNotFoundError as e:
        logger.error("Requested file not found: %s", filename)
        raise HTTPException(status_code=404, detail="The requested document file does not exist")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
