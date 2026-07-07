REFLECTION_SYSTEM_PROMPT = """You are a senior document quality reviewer.

Your job is to evaluate a generated business document against the original user request.

Evaluate the document on these criteria:
1. Requirement Coverage — Does the document address everything the user asked for?
2. Completeness — Are all necessary sections present and sufficiently detailed?
3. Business Professionalism — Is the tone, language, and formatting professional?
4. Logical Structure — Do sections flow logically from one to the next?
5. Internal Consistency — Are there contradictions or inconsistencies between sections?
6. Missing Sections — Are there obvious sections that should be present but are not?
7. Unsupported Assumptions — Are any assumptions unreasonable or not clearly stated?

You MUST respond with valid JSON in exactly this format:
{
    "quality_score": <integer 0-100>,
    "passed": <true if quality_score >= 80, false otherwise>,
    "issues": ["issue 1", "issue 2"],
    "improvement_instructions": "Specific, actionable instructions for improving the document. Empty string if passed."
}

Be critical but fair. A score of 70-79 means acceptable but with notable gaps.
A score of 80+ means the document meets professional standards.

Return ONLY the JSON object. No markdown, no explanation, no code fences."""


def build_reflection_prompt(user_request: str, document_type: str, full_content: str) -> str:
    """Build the user prompt for reflection/self-check."""
    return f"""Evaluate the following generated {document_type} against the original user request.

Original User Request:
\"{user_request}\"

Document Type: {document_type}

Generated Document Content:
---
{full_content}
---

Evaluate the document quality and return your assessment as JSON."""


IMPROVEMENT_SYSTEM_PROMPT = """You are an expert business document editor.

You will receive a generated document along with specific improvement instructions from a quality reviewer.

Your job is to rewrite and improve the document content following the reviewer's instructions.

Rules:
- Address every issue mentioned in the improvement instructions.
- Maintain the same overall structure and section order.
- Improve clarity, completeness, and professionalism.
- Do NOT include markdown formatting symbols (no #, *, **, etc.). Write in plain text.
- Return ONLY the improved content, preserving section boundaries with clear headings."""


def build_improvement_prompt(
    user_request: str,
    document_type: str,
    full_content: str,
    improvement_instructions: str,
) -> str:
    """Build the user prompt for content improvement."""
    return f"""Improve the following {document_type} based on the reviewer's feedback.

Original User Request:
\"{user_request}\"

Document Type: {document_type}

Current Document Content:
---
{full_content}
---

Reviewer's Improvement Instructions:
{improvement_instructions}

Rewrite and improve the document now. Return ONLY the improved content."""
