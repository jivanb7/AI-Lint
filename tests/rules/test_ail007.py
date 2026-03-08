"""Tests for AIL007 — NoInputValidation."""

from __future__ import annotations

from ailint.rules.ail007_no_input_validation import NoInputValidationRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_user_input_passed_without_validation():
    """user_input passed to LLM with no validation should trigger."""
    source = """
        def ask(user_input):
            return llm.invoke(user_input)
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL007"


def test_message_param_no_validation():
    """'message' param passed to LLM without validation should trigger."""
    source = """
        def respond(message):
            return client.chat.completions.create(
                messages=[{"role": "user", "content": message}]
            )
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL007"


def test_text_param_to_generate_content():
    """'text' param passed to generate_content without validation should trigger."""
    source = """
        def generate(text):
            return model.generate_content(text)
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL007"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_len_check_before_llm_call():
    """len() check on input before LLM call should not trigger."""
    source = """
        def ask(user_input):
            if len(user_input) > 1000:
                raise ValueError("Too long")
            return llm.invoke(user_input)
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 0


def test_strip_before_llm_call():
    """strip() call on input before LLM call should not trigger."""
    source = """
        def ask(user_input):
            user_input = user_input.strip()
            return llm.invoke(user_input)
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 0


def test_slicing_before_llm_call():
    """Slicing input before LLM call should not trigger."""
    source = """
        def ask(user_input):
            truncated = user_input[:500]
            return llm.invoke(truncated)
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 0


def test_non_tainted_param_not_flagged():
    """Function with non-tainted param names should not trigger."""
    source = """
        def summarize(document):
            return llm.invoke(document)
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 0


def test_no_tainted_param_used_in_call():
    """Tainted param present but not used in LLM call should not trigger."""
    source = """
        def ask(user_input, system_prompt):
            return llm.invoke(system_prompt)
    """
    findings = parse_and_check(source, NoInputValidationRule)
    assert len(findings) == 0
