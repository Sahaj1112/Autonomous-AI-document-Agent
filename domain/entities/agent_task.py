from dataclasses import dataclass
from typing import Optional
from domain.enums.task_status import TaskStatus


@dataclass
class AgentTask:
    """Domain entity representing a single planned step in the agent workflow."""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("AgentTask.id must be a non-empty string.")
        if not self.description or not self.description.strip():
            raise ValueError("AgentTask.description must be a non-empty string.")

    @property
    def is_completed(self) -> bool:
        """Returns True when this task finished successfully."""
        return self.status == TaskStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Returns True when this task finished with a failure."""
        return self.status == TaskStatus.FAILED

    def mark_in_progress(self) -> None:
        """Transition task to IN_PROGRESS status."""
        self.status = TaskStatus.IN_PROGRESS

    def mark_completed(self, result: str) -> None:
        """Transition task to COMPLETED and store its generated content."""
        if not result or not result.strip():
            raise ValueError("A completed task must have a non-empty result.")
        self.result = result
        self.status = TaskStatus.COMPLETED

    def mark_failed(self, error: str) -> None:
        """Transition task to FAILED and store the error reason."""
        self.error = error
        self.status = TaskStatus.FAILED
