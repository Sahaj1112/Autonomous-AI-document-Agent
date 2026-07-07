from dataclasses import dataclass, field
from typing import List


@dataclass
class ReflectionResult:
    quality_score: int
    passed: bool
    issues: List[str] = field(default_factory=list)
    improvement_instructions: str = ""
