"""Rich-powered terminal reporter for AI-Lint."""

from __future__ import annotations

from collections import defaultdict
from io import StringIO

from rich.console import Console
from rich.text import Text

from ailint.models import Finding, Severity
from ailint.reporters.base import BaseReporter

_SEVERITY_STYLES: dict[Severity, str] = {
    Severity.CRITICAL: "bold red",
    Severity.ERROR: "red",
    Severity.WARNING: "yellow",
    Severity.INFO: "blue",
}


class TerminalReporter(BaseReporter):
    """Colorized terminal output using Rich, grouped by file."""

    def report(self, findings: list[Finding], files_checked: int) -> str:
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=120)

        if not findings:
            console.print("[green bold]No findings.[/green bold]")
            console.print(f"  {files_checked} file(s) checked.")
            return buf.getvalue()

        # Group by file
        by_file: dict[str, list[Finding]] = defaultdict(list)
        for f in findings:
            by_file[f.location.file].append(f)

        for file_path, file_findings in sorted(by_file.items()):
            console.print()
            console.print(f"[bold]{file_path}[/bold]")

            for finding in sorted(file_findings, key=lambda f: f.location.line):
                style = _SEVERITY_STYLES.get(finding.severity, "white")
                severity_label = finding.severity.name

                line = Text()
                line.append(f"  {finding.location.line}:{finding.location.col}  ")
                line.append(f"[{severity_label}]", style=style)
                line.append(f"  {finding.rule_id}  ")
                line.append(finding.message)
                console.print(line)

                if finding.source_line:
                    console.print(f"    [dim]{finding.source_line.strip()}[/dim]")

                if finding.fix_suggestion:
                    console.print(f"    [dim italic]Fix: {finding.fix_suggestion}[/dim italic]")

        # Summary
        files_with_findings = len(by_file)
        console.print()
        console.print(
            f"[bold]Found {len(findings)} finding(s) in "
            f"{files_with_findings} file(s) "
            f"({files_checked} file(s) checked)[/bold]"
        )

        return buf.getvalue()
