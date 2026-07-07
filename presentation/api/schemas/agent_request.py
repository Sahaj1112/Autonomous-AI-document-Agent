from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Pydantic schema validating agent requests."""

    request: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Natural language request detailing the document contents/objective.",
        examples=["Create a project plan for launching an AI customer support chatbot in 3 months."],
    )
