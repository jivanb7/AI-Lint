"""Reporter package — provides output formatters for findings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ailint.reporters.json_reporter import JSONReporter
from ailint.reporters.sarif import SARIFReporter
from ailint.reporters.terminal import TerminalReporter

if TYPE_CHECKING:
    from ailint.reporters.base import BaseReporter

_REPORTERS: dict[str, type[BaseReporter]] = {
    "terminal": TerminalReporter,
    "json": JSONReporter,
    "sarif": SARIFReporter,
}


def get_reporter(format_name: str) -> BaseReporter:
    """Return a reporter instance for the given format name."""
    cls = _REPORTERS.get(format_name)
    if cls is None:
        raise ValueError(
            f"Unknown format '{format_name}'. "
            f"Available: {', '.join(sorted(_REPORTERS))}"
        )
    return cls()
