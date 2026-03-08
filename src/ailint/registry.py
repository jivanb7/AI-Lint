"""Rule registry — central store for all registered lint rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ailint.models import RuleMetadata, Severity

if TYPE_CHECKING:
    from ailint.rules.base import BaseRule


class RuleRegistry:
    """Singleton-style registry that holds all available rules."""

    def __init__(self) -> None:
        self._rules: dict[str, type[BaseRule]] = {}

    def register(self, cls: type[BaseRule]) -> type[BaseRule]:
        """Register a rule class. Usable as a decorator."""
        self._rules[cls.rule_id] = cls
        return cls

    def get_active_rules(
        self,
        select: list[str] | None = None,
        ignore: list[str] | None = None,
        min_severity: Severity = Severity.INFO,
    ) -> list[BaseRule]:
        """Return instantiated rule objects filtered by selection criteria."""
        active: list[BaseRule] = []
        for rule_id, rule_cls in sorted(self._rules.items()):
            if select and rule_id not in select:
                continue
            if ignore and rule_id in ignore:
                continue
            if rule_cls.severity < min_severity:
                continue
            active.append(rule_cls())
        return active

    def list_rules(self) -> list[RuleMetadata]:
        """Return metadata for all registered rules."""
        return [
            cls.get_metadata() for cls in sorted(self._rules.values(), key=lambda c: c.rule_id)
        ]


# Global registry instance — rules register against this on import.
registry = RuleRegistry()
