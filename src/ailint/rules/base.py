"""Abstract base class for all AI-Lint rules."""

from __future__ import annotations

import ast
from abc import ABC, abstractmethod
from typing import ClassVar

from ailint.models import Finding, RuleMetadata, Severity


class BaseRule(ABC):
    """Base class that all lint rules must subclass.

    Subclasses must define the class-level attributes (rule_id, name,
    description, severity) and implement the check() method.
    """

    rule_id: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    severity: ClassVar[Severity]

    @abstractmethod
    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        """Analyze an AST tree and return any findings.

        Args:
            tree: Pre-parsed and parent-annotated AST module.
            source_lines: Raw source lines of the file.
            file_path: Absolute path to the source file.

        Returns:
            List of Finding objects for detected issues.
        """
        ...

    @classmethod
    def get_metadata(cls) -> RuleMetadata:
        """Return metadata for this rule."""
        return RuleMetadata(
            rule_id=cls.rule_id,
            name=cls.name,
            description=cls.description,
            severity=cls.severity,
        )
