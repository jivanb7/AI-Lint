"""AIL012 — No Streaming: large max_tokens without stream=True."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_keyword_value, get_source_line, has_keyword, is_llm_call

DEFAULT_MAX_TOKENS_THRESHOLD = 1000


@registry.register
class NoStreamingRule(BaseRule):
    rule_id = "AIL012"
    name = "NoStreamingForLongResponse"
    description = "Large max_tokens without streaming enabled"
    severity = Severity.WARNING

    def __init__(self, threshold: int = DEFAULT_MAX_TOKENS_THRESHOLD) -> None:
        self.threshold = threshold

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_llm_call(node):
                continue

            max_tokens_node = get_keyword_value(node, "max_tokens")
            if max_tokens_node is None:
                max_tokens_node = get_keyword_value(node, "max_completion_tokens")
            if max_tokens_node is None:
                continue

            # Only check constant integer values
            if not isinstance(max_tokens_node, ast.Constant):
                continue
            if not isinstance(max_tokens_node.value, int):
                continue

            if max_tokens_node.value < self.threshold:
                continue

            if has_keyword(node, "stream"):
                stream_val = get_keyword_value(node, "stream")
                if isinstance(stream_val, ast.Constant) and stream_val.value is True:
                    continue

            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    message=(
                        f"max_tokens={max_tokens_node.value} without stream=True "
                        f"— response will be slow for the user"
                    ),
                    location=Location(
                        file=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                    ),
                    fix_suggestion="Add stream=True for long responses to improve perceived latency",
                    source_line=get_source_line(source_lines, node.lineno),
                )
            )

        return findings
