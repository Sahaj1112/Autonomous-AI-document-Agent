# Autonomous AI Document Agent

An autonomous AI agent that accepts natural language requests, dynamically plans tasks, generates professional business documents (.docx), and performs quality self-checks with reflection.

## Features

- **Dynamic Task Planning** — The LLM analyzes your request and generates a unique execution plan (never hardcoded)
- **Sequential Task Execution** — Each task is executed independently with full state tracking
- **Reflection / Self-Check** — Generated content is evaluated on 7 quality criteria
- **Automatic Improvement** — If quality score < 80, the agent performs one improvement iteration
- **Professional DOCX Output** — Polished Word documents with title page, styled headings, and proper formatting
- **Full Execution Trace** — API response includes the complete plan, task statuses, assumptions, and reflection results

## Architecture

```
app/
├── main.py                  # FastAPI app factory
├── api/routes.py            # POST /agent + GET /documents/{filename}
├── agent/
│   ├── autonomous_agent.py  # Orchestrator (plan → execute → reflect → generate)
│   ├── planner.py           # LLM-powered dynamic task planning
│   ├── executor.py          # Sequential task executor
│   ├── reflector.py         # Quality self-check + improvement
│   └── state.py             # Mutable execution state
├── llm/groq_client.py       # Async Groq SDK wrapper
├── tools/
│   ├── content_tool.py      # Per-section content generation
│   └── document_tool.py     # python-docx rendering
├── models/
│   ├── request_models.py    # Pydantic request validation
│   └── response_models.py   # Pydantic response schemas
├── prompts/                 # LLM prompt templates
└── core/
    ├── config.py            # pydantic-settings configuration
    └── exceptions.py        # Custom exception hierarchy
```

## Setup

### 1. Clone & Install

```bash
cd AI-Project
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` and add your Groq API key:

```
GROQ_API_KEY=your_actual_groq_api_key
```

Get a free API key at: https://console.groq.com

### 3. Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

API docs: `http://localhost:8000/docs`

## Usage

### Create a Document

```bash
curl -X POST http://localhost:8000/agent \
  -H "Content-Type: application/json" \
  -d '{"request": "Create a project plan for launching an AI customer support chatbot in 3 months."}'
```

### Download the Document

Use the `download_url` from the response:

```bash
curl -O http://localhost:8000/documents/{filename}.docx
```

## API Response

```json
{
  "request": "Original user request",
  "document_type": "Project Plan",
  "execution_plan": ["Task 1 description", "Task 2 description"],
  "tasks": [
    {
      "id": "task_1",
      "description": "Analyze project objectives",
      "status": "COMPLETED",
      "result": "Generated content..."
    }
  ],
  "assumptions": ["Assumption 1", "Assumption 2"],
  "reflection": {
    "quality_score": 85,
    "passed": true,
    "issues": [],
    "improvement_instructions": ""
  },
  "document_path": "generated_documents/project_plan_abc12345.docx",
  "download_url": "/documents/project_plan_abc12345.docx"
}
```

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core language |
| FastAPI | Web framework |
| Groq API | LLM inference (Llama 3.3 70B) |
| python-docx | Word document generation |
| Pydantic | Data validation & serialization |
| pydantic-settings | Configuration management |
| Uvicorn | ASGI server |

## Agent Workflow

```
User Request → Validation → Intent Analysis → Dynamic Planning
→ Sequential Execution → Content Generation → Reflection
→ Improvement (if needed) → DOCX Generation → API Response
```

## License

MIT
