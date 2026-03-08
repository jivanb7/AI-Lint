"""AIL006 — Missing Error Handling: LLM calls not wrapped in try/except."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_source_line, is_inside_try, is_llm_call


@registry.register
class MissingErrorHandlingRule(BaseRule):
    rule_id = "AIL006"
    name = "MissingErrorHandling"
    description = "LLM API call is not wrapped in try/except"
    severity = Severity.ERROR

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_llm_call(node):
                continue

            if is_inside_try(node):
                continue

            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    message="LLM call is not inside a try/except block",
                    location=Location(
                        file=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                    ),
                    fix_suggestion=(
                        "Wrap in try/except to handle API errors "
                        "(RateLimitError, APIError, Timeout, etc.)"
                    ),
                    source_line=get_source_line(source_lines, node.lineno),
                )
            )

        return findings
