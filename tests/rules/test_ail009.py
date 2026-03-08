"""Tests for AIL009 — MissingTimeout."""

from __future__ import annotations

from ailint.rules.ail009_missing_timeout import MissingTimeoutRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_requests_get_no_timeout():
    """requests.get() without timeout should trigger."""
    source = """
        import requests
        response = requests.get("https://api.example.com/data")
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL009"
    assert "HTTP" in findings[0].message


def test_requests_post_no_timeout():
    """requests.post() without timeout should trigger."""
    source = """
        import requests
        response = requests.post("https://api.example.com/submit", json={"key": "val"})
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL009"


def test_httpx_get_no_timeout():
    """httpx.get() without timeout should trigger."""
    source = """
        import httpx
        response = httpx.get("https://api.example.com/data")
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL009"


def test_llm_call_no_timeout():
    """LLM call without timeout should trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Hi"}]
        )
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) >= 1
    assert any(f.rule_id == "AIL009" for f in findings)


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_requests_get_with_timeout():
    """requests.get() with timeout= should not trigger."""
    source = """
        import requests
        response = requests.get("https://api.example.com/data", timeout=30)
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) == 0


def test_httpx_post_with_timeout():
    """httpx.post() with timeout= should not trigger."""
    source = """
        import httpx
        response = httpx.post("https://api.example.com/data", timeout=10)
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) == 0


def test_llm_call_with_timeout():
    """LLM call with timeout= keyword should not trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            timeout=30,
        )
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) == 0


def test_non_http_call_not_flagged():
    """Arbitrary function calls should not trigger."""
    source = """
        result = process_data(items)
        count = len(items)
    """
    findings = parse_and_check(source, MissingTimeoutRule)
    assert len(findings) == 0
