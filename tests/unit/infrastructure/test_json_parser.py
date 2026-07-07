import pytest
from infrastructure.parsers.json_parser import parse_llm_json
from domain.exceptions.domain_exceptions import PlanningError


def test_parse_llm_json_clean() -> None:
    """Verifies that clean JSON gets parsed directly."""
    raw = '{"document_type": "Report", "tasks": []}'
    parsed = parse_llm_json(raw)
    assert parsed == {"document_type": "Report", "tasks": []}


def test_parse_llm_json_markdown() -> None:
    """Verifies extraction of JSON wrapped in codeblock markdown fences."""
    raw = 'Here is the plan:\n```json\n{"document_type": "Plan", "tasks": [{"description": "First"}]}\n```\nHope you like it.'
    parsed = parse_llm_json(raw)
    assert parsed == {"document_type": "Plan", "tasks": [{"description": "First"}]}


def test_parse_llm_json_codeblock_no_syntax() -> None:
    """Verifies extraction of JSON wrapped in codeblocks without explicit language tag."""
    raw = '```\n{"test": "value"}\n```'
    parsed = parse_llm_json(raw)
    assert parsed == {"test": "value"}


def test_parse_llm_json_braces_extraction() -> None:
    """Verifies that json_parser can extract first brace start to last brace end if wrapped in conversation text."""
    raw = 'I generated this output: {"status": "success"} with some text after.'
    parsed = parse_llm_json(raw)
    assert parsed == {"status": "success"}


def test_parse_llm_json_invalid() -> None:
    """Verifies that invalid formatting throws PlanningError."""
    raw = 'This is not JSON: {invalid}'
    with pytest.raises(PlanningError):
        parse_llm_json(raw)
