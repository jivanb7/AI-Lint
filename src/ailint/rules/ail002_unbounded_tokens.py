"""AIL002 — Unbounded Token Usage: LLM calls missing max_tokens."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_source_line, has_keyword, is_llm_call


@registry.register
class UnboundedTokensRule(BaseRule):
    rule_id = "AIL002"
    name = "UnboundedTokenUsage"
    description = "LLM API call is missing max_tokens, risking unbounded costs"
    severity = Severity.WARNING

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_llm_call(node):
                continue

            if has_keyword(node, "max_tokens") or has_keyword(node, "max_completion_tokens"):
                continue

            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    message="LLM call is missing max_tokens parameter",
                    location=Location(
                        file=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                    ),
                    fix_suggestion="Add max_tokens=1024 (or appropriate limit) to control costs",
                    source_line=get_source_line(source_lines, node.lineno),
                )
            )

        return findings
