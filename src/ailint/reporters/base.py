"""Abstract base reporter for AI-Lint output."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ailint.models import Finding


class BaseReporter(ABC):
    """Base class for all output reporters."""

    @abstractmethod
    def report(self, findings: list[Finding], files_checked: int) -> str:
        """Format findings into a string.

        Args:
            findings: List of findings to report.
            files_checked: Total number of files analyzed.

        Returns:
            Formatted output string.
        """
        ...
