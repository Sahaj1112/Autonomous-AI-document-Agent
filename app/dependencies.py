from functools import lru_cache
from fastapi import Depends

from infrastructure.config.settings import settings
from infrastructure.llm.groq_llm_adapter import GroqLLMAdapter
from infrastructure.document.docx_document_adapter import DocxDocumentAdapter
from infrastructure.storage.local_storage_adapter import LocalDiskStorageAdapter

from application.ports.llm_port import LLMPort
from application.ports.document_port import DocumentPort
from application.ports.storage_port import StoragePort

from application.services.planner_service import PlannerService
from application.services.content_service import ContentService
from application.services.executor_service import ExecutorService
from application.services.reflection_service import ReflectionService

from application.use_cases.run_autonomous_agent import RunAutonomousAgentUseCase


@lru_cache
def get_llm_port() -> LLMPort:
    """Instantiates and caches the Groq LLM Adapter."""
    return GroqLLMAdapter(api_key=settings.groq_api_key, model=settings.groq_model)


@lru_cache
def get_document_port() -> DocumentPort:
    """Instantiates and caches the DOCX Document Adapter."""
    return DocxDocumentAdapter()


@lru_cache
def get_storage_port() -> StoragePort:
    """Instantiates and caches the Local Disk Storage Adapter."""
    return LocalDiskStorageAdapter(output_dir=settings.output_dir)


def get_agent_use_case(
    llm_port: LLMPort = Depends(get_llm_port),
    document_port: DocumentPort = Depends(get_document_port),
    storage_port: StoragePort = Depends(get_storage_port),
) -> RunAutonomousAgentUseCase:
    """
    Composition root for the Autonomous Agent Use Case.
    Wires infrastructure implementations to application abstractions via dependency injection.
    """
    planner_service = PlannerService(llm_port=llm_port)
    content_service = ContentService(llm_port=llm_port)
    executor_service = ExecutorService(content_service=content_service)
    reflection_service = ReflectionService(
        llm_port=llm_port,
        quality_threshold=settings.reflection_quality_threshold
    )
    
    return RunAutonomousAgentUseCase(
        planner_port=planner_service,
        executor_service=executor_service,
        reflection_port=reflection_service,
        document_port=document_port,
        storage_port=storage_port,
        max_reflection_retries=settings.max_reflection_retries,
    )
