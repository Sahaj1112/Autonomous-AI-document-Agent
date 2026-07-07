from typing import List, Optional
from pydantic import BaseModel, Field
from domain.enums.task_status import TaskStatus


class AgentTaskResponse(BaseModel):
    id: str
    description: str
    status: TaskStatus
    result: Optional[str] = None
    error: Optional[str] = None


class ReflectionResultResponse(BaseModel):
    quality_score: int
    passed: bool
    issues: List[str]
    improvement_instructions: str


class AgentResponse(BaseModel):
    """Pydantic schema representing the complete trace and results of the agent request execution."""

    request: str = Field(..., description="Original user request text.")
    document_type: str = Field(..., description="Detected type of document.")
    execution_plan: List[str] = Field(..., description="Task descriptions planned by the LLM.")
    tasks: List[AgentTaskResponse] = Field(..., description="Sequential list of execution tasks and statuses.")
    assumptions: List[str] = Field(..., description="Implicit assumptions established during planning.")
    reflection: ReflectionResultResponse = Field(..., description="Quality verification check score and results.")
    document_path: str = Field(..., description="Absolute server-side path to output document.")
    download_url: str = Field(..., description="API download endpoint location.")
