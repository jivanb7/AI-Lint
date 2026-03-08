"""AIL011 — Temperature Not Set: LLM calls missing explicit temperature."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_source_line, has_keyword, is_llm_call


@registry.register
class TemperatureNotSetRule(BaseRule):
    rule_id = "AIL011"
    name = "TemperatureNotSet"
    description = "LLM call is missing explicit temperature setting"
    severity = Severity.INFO

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_llm_call(node):
                continue

            if has_keyword(node, "temperature"):
                continue

            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    message="LLM call missing explicit temperature — output may be non-deterministic",
                    location=Location(
                        file=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                    ),
                    fix_suggestion=(
                        "Add temperature=0.0 for deterministic output, "
                        "or temperature=0.7 for creative tasks"
                    ),
                    source_line=get_source_line(source_lines, node.lineno),
                )
            )

        return findings
