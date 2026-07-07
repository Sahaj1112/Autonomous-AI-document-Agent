CONTENT_SYSTEM_PROMPT = """You are an expert business document writer.

Your job is to write professional, detailed content for a specific section of a business document.

Rules:
- Write in a professional business tone.
- Be thorough and specific — include concrete details, not vague statements.
- Use proper formatting: include bullet points, numbered lists, and sub-headings where appropriate.
- Content should be ready to be placed directly into a Word document.
- Do NOT include markdown formatting symbols (no #, *, **, etc.). Write in plain text with clear structure.
- Use line breaks to separate paragraphs and sections.
- Each section should be 150-400 words depending on complexity.
- Make reasonable assumptions and state them naturally within the content when needed."""


def build_content_prompt(
    user_request: str,
    document_type: str,
    task_description: str,
    previous_sections: str,
    assumptions: list[str],
) -> str:
    """
    Build the user prompt for generating content for a single task/section.

    Args:
        user_request: The original user request.
        document_type: Detected document type.
        task_description: What this specific task should produce.
        previous_sections: Content from previously completed tasks for coherence.
        assumptions: List of assumptions made by the planner.
    """
    assumptions_text = "\n".join(f"- {a}" for a in assumptions) if assumptions else "None"

    return f"""Write the content for the following section of a {document_type}.

Original User Request:
\"{user_request}\"

Document Type: {document_type}

Current Task/Section to Write:
{task_description}

Assumptions Made:
{assumptions_text}

Previously Written Sections (for context and coherence):
{previous_sections if previous_sections else "This is the first section."}

Write the content for the current section now. Return ONLY the section content, no metadata or labels."""
