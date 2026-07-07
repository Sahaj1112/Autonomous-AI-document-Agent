# Autonomous AI Document Agent

## Project Overview
The Autonomous AI Document Agent is a sophisticated backend service that automatically translates high-level, natural language requests into comprehensive, professionally formatted Microsoft Word (`.docx`) documents. Instead of generating a single large block of text, the agent acts autonomously by breaking complex requests down into a structured execution plan, sequentially generating contextualized content, and rigorously evaluating its own output for quality before compiling the final deliverable.

## Problem Statement
Creating high-quality business documents (like project plans, proposals, and strategy reports) is often time-consuming. Off-the-shelf LLMs frequently produce superficial, unstructured, or hallucinated content when asked to write an entire document in a single prompt. This project solves that problem by introducing an autonomous, multi-step orchestration pipeline that dynamically plans, executes, and self-reviews document generation to guarantee depth, accuracy, and structural integrity.

## Key Features & Autonomous Workflow
1. **Dynamic Planning**: The agent dynamically parses natural language requests and authors a multi-step task execution plan (e.g., separating an Executive Summary from an Implementation Roadmap).
2. **Sequential Task Execution**: The agent iterates through its plan, generating extensive, deeply contextualized content for each section one by one.
3. **Reflection and Self-Check Mechanism**: After execution, the agent acts as its own critic. It grades the compiled document on a 1-100 scale. If the quality falls below the strict threshold (80/100), the agent automatically enters an improvement loop to rewrite and enhance weak sections.
4. **Professional Document Generation**: The finalized markdown is securely compiled and rendered into a native, stylized `.docx` file ready for business distribution.

## Clean Architecture
This project strictly adheres to **Clean Architecture** principles to guarantee maintainability, testability, and separation of concerns.
- **Dependency Rule**: `Presentation -> Application -> Domain`. Inner layers never depend on outer layers.
- **Domain Layer**: Contains pure business rules, entities, and custom exceptions. It is entirely agnostic of web frameworks or third-party APIs.
- **Application Layer**: Orchestrates the autonomous workflow (Planner, Executor, Reflector) utilizing abstract Ports.
- **Infrastructure Layer**: Implements Application Ports. It houses all external dependencies (Groq SDK, `python-docx`, local file storage).
- **Presentation Layer**: Exposes business logic via FastAPI endpoints, utilizing strict Dependency Injection from a centralized composition root (`app/dependencies.py`).

### Project Folder Structure
```text
Autonomous-AI-document-Agent/
├── app/                  # Application composition root and FastAPI lifecycle
├── application/          # Use cases, core services, and abstract ports
├── domain/               # Pure business entities and domain exceptions
├── infrastructure/       # Concrete adapters (Groq LLM, python-docx, Storage)
├── presentation/         # HTTP API routing and Pydantic validation schemas
├── tests/                # Comprehensive unit and integration test suite
├── generated_documents/  # Default storage directory for generated Word files
├── demo.py               # Standalone execution script for testing the agent
└── requirements.txt      # Project dependencies
```

## Technology Stack
- **Language**: Python 3.12+
- **Web Framework**: FastAPI (Uvicorn)
- **AI/LLM**: Groq API Integration (`llama-3.3-70b-versatile` model)
- **Document Generation**: `python-docx`
- **Testing**: `pytest`, `pytest-asyncio`

## Getting Started

### Installation Instructions (Windows PowerShell)

1. **Clone the repository and navigate into it**:
```powershell
git clone <repository-url>
cd Autonomous-AI-document-Agent
```

2. **Create and activate a virtual environment**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. **Install dependencies**:
```powershell
pip install -r requirements.txt
```

4. **Environment Configuration**:
Create a `.env` file in the root directory and configure your Groq API Key (never commit this key to version control):
```env
# .env
GROQ_API_KEY=gsk_your_actual_api_key_here
```

### Running the Application
Start the application locally with live-reload enabled:
```powershell
uvicorn app.main:app --reload
```

- **Swagger API Documentation**: Navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to explore and interact with the endpoints.

## API Endpoints

- `GET /health`
  Returns the liveness status of the application.

- `POST /agent`
  Submits a natural language document generation request.
  **Example Request:**
  ```json
  {
    "request": "Create a project plan for launching an AI customer support chatbot in 3 months."
  }
  ```
  **Example Response (abridged):**
  ```json
  {
    "execution_plan": ["Executive Summary", "Implementation Roadmap"],
    "reflection": {
      "quality_score": 92,
      "passed": true
    },
    "document_path": "C:\\...\\generated_documents\\agent_doc_f617ebc5.docx",
    "download_url": "/documents/agent_doc_f617ebc5.docx"
  }
  ```

- `GET /documents/{filename}`
  Securely serves the generated `.docx` file for download.

## Standalone Demonstration (`demo.py`)
You can run the agent workflow directly from your terminal, bypassing the web server entirely, to observe the orchestration logs in real-time.
```powershell
python demo.py
```
This script sequentially runs three high-complexity demonstration cases (e.g., Financial Analytics strategies, Chatbot proposals) and prints the detailed execution trace, proving the system's dynamic adaptability.

## Testing Instructions
The repository includes a comprehensive 30+ test suite verifying domain rules, autonomous orchestration, dependency injection, and API endpoint behavior (with LLMs accurately mocked).
Run the full test suite using:
```powershell
pytest -v
```

## Security Considerations
- **Path Traversal Protection**: The storage adapter strictly validates and sanitizes all document filenames before retrieval, blocking `../` traversal attacks with instant HTTP 400 rejections.
- **Traceback Suppression**: Global exception handlers trap uncaught server crashes and domain failures, returning safe HTTP 500 JSON responses without exposing raw Python tracebacks or infrastructure internals.
- **Secure Configuration**: The API key is securely injected directly into the Infrastructure layer at runtime via `pydantic-settings`, guaranteeing it is never printed or unintentionally exposed in API responses.

## Future Improvements
- **Asynchronous Webhooks**: Transitioning the HTTP API to return a `job_id` and using WebSockets or webhooks for long-running document generation notifications.
- **Advanced File Types**: Implementing additional infrastructure adapters for PDF, Markdown, and HTML exports.
- **Vector Search / RAG Integration**: Connecting the `ContentService` to a Retrieval-Augmented Generation pipeline to cite internal company data during document compilation.
