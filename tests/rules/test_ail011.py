"""Tests for AIL011 — TemperatureNotSet."""

from __future__ import annotations

from ailint.rules.ail011_temperature_not_set import TemperatureNotSetRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_llm_call_missing_temperature():
    """LLM call without temperature= should trigger."""
    source = """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=512,
        )
    """
    findings = parse_and_check(source, TemperatureNotSetRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL011"
    assert findings[0].severity.name == "INFO"


def test_llm_invoke_missing_temperature():
    """llm.invoke() without temperature should trigger."""
    source = """
        result = llm.invoke("What is the capital of France?")
    """
    findings = parse_and_check(source, TemperatureNotSetRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL011"


def test_generate_content_missing_temperature():
    """model.generate_content() without temperature should trigger."""
    source = """
        resp = model.generate_content("Explain black holes")
    """
    findings = parse_and_check(source, TemperatureNotSetRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL011"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_llm_call_with_temperature_zero():
    """LLM call with temperature=0.0 should not trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.0,
        )
    """
    findings = parse_and_check(source, TemperatureNotSetRule)
    assert len(findings) == 0


def test_llm_call_with_temperature_07():
    """LLM call with temperature=0.7 should not trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            temperature=0.7,
        )
    """
    findings = parse_and_check(source, TemperatureNotSetRule)
    assert len(findings) == 0


def test_non_llm_call_not_flagged():
    """Regular function call should not trigger AIL011."""
    source = """
        result = process(data=42)
    """
    findings = parse_and_check(source, TemperatureNotSetRule)
    assert len(findings) == 0
