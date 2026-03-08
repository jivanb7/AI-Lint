"""AIL003 — Hardcoded Model Name: model names should come from config."""

from __future__ import annotations

import ast
import re

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_source_line

_MODEL_PATTERN = re.compile(
    r"^(gpt-[34][\w.-]*|claude-[\w.-]+|gemini-[\w.-]+|llama[\w.-]*"
    r"|mistral[\w.-]*|text-davinci[\w.-]*|o[134]-[\w.-]*)$",
    re.IGNORECASE,
)

_MODEL_VAR_PATTERN = re.compile(r"^model", re.IGNORECASE)


@registry.register
class HardcodedModelRule(BaseRule):
    rule_id = "AIL003"
    name = "HardcodedModelName"
    description = "Model name is hardcoded instead of loaded from configuration"
    severity = Severity.WARNING

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue

            if not _MODEL_PATTERN.match(node.value):
                continue

            parent = getattr(node, "parent", None)

            # Case 1: keyword argument model="gpt-4o"
            if isinstance(parent, ast.keyword) and parent.arg == "model":
                findings.append(self._make_finding(node, file_path, source_lines))
                continue

            # Case 2: assigned to a variable named model*
            if isinstance(parent, ast.Assign):
                for target in parent.targets:
                    if isinstance(target, ast.Name) and _MODEL_VAR_PATTERN.match(
                        target.id
                    ):
                        findings.append(
                            self._make_finding(node, file_path, source_lines)
                        )
                        break

        return findings

    def _make_finding(
        self, node: ast.Constant, file_path: str, source_lines: list[str]
    ) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            rule_name=self.name,
            severity=self.severity,
            message=f'Hardcoded model name "{node.value}" — use a config variable instead',
            location=Location(
                file=file_path,
                line=node.lineno,
                col=node.col_offset,
            ),
            fix_suggestion='Use MODEL = os.getenv("MODEL_NAME", "gpt-4o") and reference the variable',
            source_line=get_source_line(source_lines, node.lineno),
        )
