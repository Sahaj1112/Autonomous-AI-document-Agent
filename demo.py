import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load env variables at the very beginning
load_dotenv()

# Set up clean logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("demo_script")

from infrastructure.config.settings import settings
from infrastructure.llm.groq_llm_adapter import GroqLLMAdapter
from infrastructure.document.docx_document_adapter import DocxDocumentAdapter
from application.services.planner_service import PlannerService
from application.services.content_service import ContentService
from application.services.executor_service import ExecutorService
from application.services.reflection_service import ReflectionService
from application.use_cases.run_autonomous_agent import RunAutonomousAgentUseCase


async def run_demo(request_text: str):
    """Directly triggers the use case, demonstrating separation of concerns from FastAPI."""
    logger.info("Initializing Agent Dependencies...")

    # Wire up concrete adapters and services using manual dependency injection
    llm_adapter = GroqLLMAdapter(api_key=settings.groq_api_key, model=settings.groq_model)
    document_adapter = DocxDocumentAdapter()
    from infrastructure.storage.local_storage_adapter import LocalDiskStorageAdapter
    storage_adapter = LocalDiskStorageAdapter(output_dir=settings.output_dir)

    planner = PlannerService(llm_port=llm_adapter)
    content = ContentService(llm_port=llm_adapter)
    executor = ExecutorService(content_service=content)
    reflector = ReflectionService(llm_port=llm_adapter)

    use_case = RunAutonomousAgentUseCase(
        planner_port=planner,
        executor_service=executor,
        reflection_port=reflector,
        document_port=document_adapter,
        storage_port=storage_adapter,
    )

    logger.info("Starting run for prompt: '%s'", request_text)
    try:
        final_state = await use_case.execute(request_text)

        print("\n" + "=" * 80)
        print("AGENT WORKFLOW RUN RESULTS")
        print("=" * 80)
        print(f"Request:          {final_state.request}")
        print(f"Document Type:    {final_state.document_type}")
        print(f"Assumptions:      {final_state.assumptions}")
        print("-" * 80)
        print("Task Execution Plan:")
        for t in final_state.tasks:
            print(f"  - [{t.id}] {t.description} -> {t.status.value}")
            if t.error:
                print(f"    Error: {t.error}")

        print("-" * 80)
        if final_state.reflection:
            print("Reflection Result:")
            print(f"  Quality Score: {final_state.reflection.quality_score}/100")
            print(f"  Passed:        {final_state.reflection.passed}")
            print(f"  Issues:        {final_state.reflection.issues}")
            print(f"  Instructions:  {final_state.reflection.improvement_instructions}")
        else:
            print("No reflection results recorded.")
        print("-" * 80)
        print(f"Output Path:      {final_state.document_path}")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error("Workflow failed with error: %s", str(e), exc_info=True)


if __name__ == "__main__":
    # Suppress verbose httpx logging
    logging.getLogger("httpx").setLevel(logging.WARNING)

    demos = [
        "Create a project plan for launching an AI customer support chatbot in 3 months.",
        "Write a business proposal for adopting generative AI in a mid-sized marketing company.",
        "Create an implementation strategy for an AI-powered financial analytics platform."
    ]

    for i, prompt in enumerate(demos, 1):
        print(f"\n\n{'=' * 80}")
        print(f"RUNNING DEMO CASE {i}/3")
        print(f"{'=' * 80}")
        asyncio.run(run_demo(prompt))
