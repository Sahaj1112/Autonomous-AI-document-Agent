from dataclasses import dataclass, field
from typing import List, Dict, Optional
from domain.entities.agent_task import AgentTask
from domain.entities.reflection_result import ReflectionResult
from domain.enums.task_status import TaskStatus


@dataclass
class AgentState:
    request: str
    document_type: Optional[str] = None
    tasks: List[AgentTask] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    generated_content: Dict[str, str] = field(default_factory=dict)  # task_id -> content string
    reflection: Optional[ReflectionResult] = None
    document_path: Optional[str] = None
    document_filename: Optional[str] = None

    def get_full_content(self) -> str:
        """Assembles all successfully completed task results into a single formatted string."""
        sections = []
        for task in self.tasks:
            if task.status == TaskStatus.COMPLETED and task.result:
                sections.append(f"{task.description}\n\n{task.result}")
        return "\n\n---\n\n".join(sections)

    def get_previous_sections_summary(self, current_task_index: int) -> str:
        """Constructs a summary of previously completed tasks for context when generating content."""
        summaries = []
        for i, task in enumerate(self.tasks):
            if i >= current_task_index:
                break
            if task.status == TaskStatus.COMPLETED and task.result:
                preview = task.result[:200] + "..." if len(task.result) > 200 else task.result
                summaries.append(f"[{task.description}]: {preview}")
        return "\n\n".join(summaries) if summaries else ""
