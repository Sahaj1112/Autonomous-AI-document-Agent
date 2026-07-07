import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from domain.exceptions.domain_exceptions import (
    DomainError,
    PlanningError,
    ExecutionError,
    ReflectionError,
    DocumentGenerationError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers exception handlers mapping domain exceptions to appropriate HTTP responses."""

    @app.exception_handler(PlanningError)
    async def planning_error_handler(request: Request, exc: PlanningError) -> JSONResponse:
        logger.error("Planning error encountered: %s", str(exc))
        return JSONResponse(
            status_code=422,
            content={"detail": f"Document planning failure: {str(exc)}"},
        )

    @app.exception_handler(ExecutionError)
    async def execution_error_handler(request: Request, exc: ExecutionError) -> JSONResponse:
        logger.error("Execution error encountered: %s", str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": f"Document content execution failed: {str(exc)}"},
        )

    @app.exception_handler(ReflectionError)
    async def reflection_error_handler(request: Request, exc: ReflectionError) -> JSONResponse:
        logger.error("Reflection self-check failed: %s", str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": f"Document quality verification failed: {str(exc)}"},
        )

    @app.exception_handler(DocumentGenerationError)
    async def docx_generation_error_handler(request: Request, exc: DocumentGenerationError) -> JSONResponse:
        logger.error("Word file generation adapter failed: %s", str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": f"Word file generation failed: {str(exc)}"},
        )

    @app.exception_handler(DomainError)
    async def general_domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        logger.error("General Domain error encountered: %s", str(exc))
        # Map validation-like domain errors to 400, others to 500
        status_code = 400 if "must be at least 10 characters" in str(exc) else 500
        return JSONResponse(
            status_code=status_code,
            content={"detail": f"Agent workflow error: {str(exc)}"},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled internal server error: %s", str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected internal server error occurred."},
        )
