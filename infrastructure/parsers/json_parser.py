import json
import re
import logging
from typing import Dict, Any
from domain.exceptions.domain_exceptions import PlanningError

logger = logging.getLogger(__name__)


def parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """
    Robustly parses a JSON string returned by the LLM.
    Handles markdown codeblocks and extracts the clean JSON contents.
    """
    cleaned = raw_text.strip()

    # Match markdown codeblocks (e.g. ```json ... ``` or ``` ... ```)
    codeblock_pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(codeblock_pattern, cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()

    # If codeblock extraction failed, fallback to searching for first '{' and last '}'
    if not (cleaned.startswith("{") and cleaned.endswith("}")):
        braces_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if braces_match:
            cleaned = braces_match.group(1).strip()

    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise PlanningError("LLM response did not contain a JSON object")
        return data
    except json.JSONDecodeError as e:
        logger.error("JSON parsing error: %s. Raw text received: %s", str(e), raw_text)
        raise PlanningError(f"Malformed LLM JSON output: {str(e)}") from e
