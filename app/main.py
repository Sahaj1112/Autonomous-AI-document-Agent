"""
FastAPI application entry point configured with Strict Clean Architecture.
Integrates presentation layer routes, CORS middleware, and domain exception mapping handlers.
"""

import os
import sys
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from presentation.api.routes.agent_routes import router as agent_router
from presentation.api.routes.document_routes import router as document_router
from presentation.api.exception_handlers import register_exception_handlers
from infrastructure.config.settings import settings

# --- Setup Application-wide Logger ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler: runs startup logic then yields for app lifetime."""
    # --- Startup ---
    os.makedirs(settings.output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info("Autonomous AI Document Agent — Starting (Clean Architecture)")
    logger.info("Output directory path: %s", os.path.abspath(settings.output_dir))
    logger.info("LLM model: %s", settings.groq_model)
    logger.info("Reflection threshold: %d", settings.reflection_quality_threshold)
    logger.info("=" * 60)
    yield
    # --- Shutdown (add cleanup here if needed) ---


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Autonomous AI Document Agent",
        description=(
            "An autonomous AI agent that accepts natural language requests, "
            "dynamically plans tasks, generates professional business documents, "
            "and performs quality self-checks with reflection under Clean Architecture."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # --- CORS Middleware Configuration ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Domain & Application Exception Handlers Registration ---
    register_exception_handlers(app)

    # --- Include Presentation Layer Routes ---
    app.include_router(agent_router)
    app.include_router(document_router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
