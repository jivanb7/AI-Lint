"""Click CLI entry point for AI-Lint."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ailint import __version__
from ailint.config import AilintConfig, get_yaml_template, load_config
from ailint.engine import AnalysisEngine
from ailint.models import Severity
from ailint.registry import registry
from ailint.reporters import get_reporter

# Importing rules triggers auto-registration via the registry decorator.
import ailint.rules  # noqa: F401

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="ailint")
def cli() -> None:
    """AI-Lint: Static analysis for AI/ML Python code."""
    pass


@cli.command()
@click.argument("paths", nargs=-1)
@click.option("--config", "config_path", default=None, help="Path to config file")
@click.option("--select", default=None, help="Comma-separated rule IDs to enable")
@click.option("--ignore", default=None, help="Comma-separated rule IDs to skip")
@click.option(
    "--severity",
    default=None,
    type=click.Choice(["INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Minimum severity to report",
)
@click.option(
    "--format",
    "output_format",
    default=None,
    type=click.Choice(["terminal", "json", "sarif"], case_sensitive=False),
    help="Output format",
)
def check(
    paths: tuple[str, ...],
    config_path: str | None,
    select: str | None,
    ignore: str | None,
    severity: str | None,
    output_format: str | None,
) -> None:
    """Run AI-Lint analysis on Python files."""
    if not paths:
        paths = (".",)

    # Build CLI overrides
    overrides: dict[str, object] = {}
    if select:
        overrides["select"] = [s.strip() for s in select.split(",")]
    if ignore:
        overrides["ignore"] = [s.strip() for s in ignore.split(",")]
    if severity:
        overrides["severity"] = severity.upper()
    if output_format:
        overrides["format"] = output_format.lower()

    try:
        config = load_config(config_path, overrides)
    except Exception as exc:
        console.print(f"[red]Configuration error: {exc}[/red]")
        sys.exit(2)

    engine = AnalysisEngine(config, registry)

    try:
        findings, files_checked = engine.analyze_paths(list(paths))
    except Exception as exc:
        console.print(f"[red]Analysis error: {exc}[/red]")
        sys.exit(2)

    reporter = get_reporter(config.format)
    output = reporter.report(findings, files_checked)
    click.echo(output)

    if findings:
        sys.exit(1)
    sys.exit(0)


@cli.command("list-rules")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json"], case_sensitive=False),
    help="Output format",
)
def list_rules(output_format: str) -> None:
    """List all registered AI-Lint rules."""
    rules = registry.list_rules()

    if output_format == "json":
        import json

        data = [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "severity": r.severity.name,
                "description": r.description,
            }
            for r in rules
        ]
        click.echo(json.dumps(data, indent=2))
        return

    table = Table(title="AI-Lint Rules")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Severity")
    table.add_column("Description")

    severity_styles = {
        Severity.CRITICAL: "bold red",
        Severity.ERROR: "red",
        Severity.WARNING: "yellow",
        Severity.INFO: "blue",
    }

    for rule in rules:
        style = severity_styles.get(rule.severity, "white")
        table.add_row(
            rule.rule_id,
            rule.name,
            f"[{style}]{rule.severity.name}[/{style}]",
            rule.description,
        )

    console.print(table)


@cli.command()
def init() -> None:
    """Create a default .ailint.yaml configuration file."""
    target = Path.cwd() / ".ailint.yaml"
    if target.exists():
        console.print("[yellow].ailint.yaml already exists — not overwriting.[/yellow]")
        sys.exit(1)

    target.write_text(get_yaml_template())
    console.print("[green]Created .ailint.yaml with default configuration.[/green]")
