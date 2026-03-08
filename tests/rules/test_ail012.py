"""Tests for AIL012 — NoStreamingForLongResponse."""

from __future__ import annotations

from ailint.rules.ail012_no_streaming import NoStreamingRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_large_max_tokens_no_stream():
    """LLM call with max_tokens>=1000 and no stream=True should trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            max_tokens=1000,
        )
    """
    findings = parse_and_check(source, NoStreamingRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL012"
    assert "1000" in findings[0].message


def test_very_large_max_tokens_no_stream():
    """max_tokens=4096 without stream=True should trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            max_tokens=4096,
        )
    """
    findings = parse_and_check(source, NoStreamingRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL012"


def test_stream_false_with_large_tokens():
    """max_tokens>=1000 with stream=False should trigger (not True)."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            max_tokens=2000,
            stream=False,
        )
    """
    findings = parse_and_check(source, NoStreamingRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL012"


def test_max_completion_tokens_large_no_stream():
    """max_completion_tokens>=1000 without stream should trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            max_completion_tokens=1500,
        )
    """
    findings = parse_and_check(source, NoStreamingRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL012"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_large_max_tokens_with_stream_true():
    """max_tokens>=1000 with stream=True should not trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            max_tokens=2000,
            stream=True,
        )
    """
    findings = parse_and_check(source, NoStreamingRule)
    assert len(findings) == 0


def test_small_max_tokens_no_stream():
    """max_tokens=500 (below threshold) without stream should not trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            max_tokens=500,
        )
    """
    findings = parse_and_check(source, NoStreamingRule)
    assert len(findings) == 0


def test_no_max_tokens_keyword():
    """LLM call with no max_tokens keyword should not trigger AIL012."""
    source = """
        response = client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, NoStreamingRule)
    assert len(findings) == 0


def test_custom_threshold():
    """Custom threshold of 500 should flag max_tokens=500."""
    import ast
    import textwrap
    from ailint.visitor import annotate_parents

    source = textwrap.dedent("""
        response = client.chat.completions.create(
            messages=[],
            max_tokens=500,
        )
    """)
    tree = ast.parse(source, filename="<test>")
    annotate_parents(tree)
    rule = NoStreamingRule(threshold=500)
    findings = rule.check(tree, source.splitlines(), "<test>")
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL012"
