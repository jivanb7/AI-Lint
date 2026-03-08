"""Tests for reporters — terminal, JSON, SARIF."""

from __future__ import annotations

import json

import pytest

from ailint.models import Finding, Location, Severity
from ailint.reporters import get_reporter
from ailint.reporters.json_reporter import JSONReporter
from ailint.reporters.sarif import SARIFReporter
from ailint.reporters.terminal import TerminalReporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_finding(
    rule_id: str = "AIL002",
    rule_name: str = "UnboundedTokenUsage",
    severity: Severity = Severity.WARNING,
    message: str = "LLM call is missing max_tokens parameter",
    file: str = "example.py",
    line: int = 10,
    col: int = 4,
    fix_suggestion: str | None = "Add max_tokens=1024",
    source_line: str | None = "    result = llm.invoke(prompt)",
) -> Finding:
    return Finding(
        rule_id=rule_id,
        rule_name=rule_name,
        severity=severity,
        message=message,
        location=Location(file=file, line=line, col=col),
        fix_suggestion=fix_suggestion,
        source_line=source_line,
    )


@pytest.fixture
def single_finding():
    return make_finding()


@pytest.fixture
def multiple_findings():
    return [
        make_finding(rule_id="AIL001", rule_name="PromptInjection",
                     severity=Severity.CRITICAL, message="User input flows unsanitized"),
        make_finding(rule_id="AIL002", rule_name="UnboundedTokenUsage",
                     severity=Severity.WARNING, message="Missing max_tokens", line=20),
        make_finding(rule_id="AIL011", rule_name="TemperatureNotSet",
                     severity=Severity.INFO, message="Temperature not set", file="other.py"),
    ]


# ---------------------------------------------------------------------------
# JSON Reporter
# ---------------------------------------------------------------------------


class TestJSONReporter:
    def test_returns_valid_json(self, single_finding):
        reporter = JSONReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)  # Should not raise
        assert isinstance(data, dict)

    def test_json_has_required_top_level_keys(self, single_finding):
        reporter = JSONReporter()
        output = reporter.report([single_finding], files_checked=3)
        data = json.loads(output)
        assert "version" in data
        assert "files_checked" in data
        assert "findings_count" in data
        assert "findings" in data

    def test_json_files_checked_is_correct(self, single_finding):
        reporter = JSONReporter()
        output = reporter.report([single_finding], files_checked=5)
        data = json.loads(output)
        assert data["files_checked"] == 5

    def test_json_findings_count_matches_list(self, multiple_findings):
        reporter = JSONReporter()
        output = reporter.report(multiple_findings, files_checked=2)
        data = json.loads(output)
        assert data["findings_count"] == 3
        assert len(data["findings"]) == 3

    def test_json_finding_has_all_fields(self, single_finding):
        reporter = JSONReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        finding = data["findings"][0]
        assert finding["rule_id"] == "AIL002"
        assert finding["rule_name"] == "UnboundedTokenUsage"
        assert finding["severity"] == "WARNING"
        assert "message" in finding
        assert "location" in finding
        assert finding["location"]["file"] == "example.py"
        assert finding["location"]["line"] == 10
        assert finding["location"]["col"] == 4
        assert finding["fix_suggestion"] == "Add max_tokens=1024"

    def test_json_empty_findings(self):
        reporter = JSONReporter()
        output = reporter.report([], files_checked=2)
        data = json.loads(output)
        assert data["findings_count"] == 0
        assert data["findings"] == []

    def test_json_severity_is_string_name(self, single_finding):
        reporter = JSONReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        assert data["findings"][0]["severity"] == "WARNING"


# ---------------------------------------------------------------------------
# SARIF Reporter
# ---------------------------------------------------------------------------


class TestSARIFReporter:
    def test_returns_valid_json(self, single_finding):
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_sarif_version_is_210(self, single_finding):
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        assert data["version"] == "2.1.0"

    def test_sarif_has_schema(self, single_finding):
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        assert "$schema" in data

    def test_sarif_has_runs(self, single_finding):
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        assert "runs" in data
        assert len(data["runs"]) == 1

    def test_sarif_tool_driver_name(self, single_finding):
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        driver = data["runs"][0]["tool"]["driver"]
        assert driver["name"] == "ailint"

    def test_sarif_results_count(self, multiple_findings):
        reporter = SARIFReporter()
        output = reporter.report(multiple_findings, files_checked=2)
        data = json.loads(output)
        results = data["runs"][0]["results"]
        assert len(results) == 3

    def test_sarif_result_has_physical_location(self, single_finding):
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        result = data["runs"][0]["results"][0]
        assert "locations" in result
        phys_loc = result["locations"][0]["physicalLocation"]
        assert "artifactLocation" in phys_loc
        assert "region" in phys_loc
        assert phys_loc["region"]["startLine"] == 10

    def test_sarif_column_is_one_indexed(self, single_finding):
        """SARIF columns are 1-indexed; col=4 in Finding → startColumn=5 in SARIF."""
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        region = data["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
        assert region["startColumn"] == 5  # col 4 + 1

    def test_sarif_severity_mapping_critical(self):
        reporter = SARIFReporter()
        finding = make_finding(severity=Severity.CRITICAL)
        output = reporter.report([finding], files_checked=1)
        data = json.loads(output)
        assert data["runs"][0]["results"][0]["level"] == "error"

    def test_sarif_severity_mapping_warning(self, single_finding):
        reporter = SARIFReporter()
        output = reporter.report([single_finding], files_checked=1)
        data = json.loads(output)
        assert data["runs"][0]["results"][0]["level"] == "warning"

    def test_sarif_severity_mapping_info(self):
        reporter = SARIFReporter()
        finding = make_finding(severity=Severity.INFO)
        output = reporter.report([finding], files_checked=1)
        data = json.loads(output)
        assert data["runs"][0]["results"][0]["level"] == "note"

    def test_sarif_empty_findings(self):
        reporter = SARIFReporter()
        output = reporter.report([], files_checked=5)
        data = json.loads(output)
        assert data["runs"][0]["results"] == []

    def test_sarif_rules_in_driver(self, multiple_findings):
        """Driver should list unique rules seen in findings."""
        reporter = SARIFReporter()
        output = reporter.report(multiple_findings, files_checked=2)
        data = json.loads(output)
        rules = data["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = {r["id"] for r in rules}
        assert "AIL001" in rule_ids
        assert "AIL002" in rule_ids


# ---------------------------------------------------------------------------
# Terminal Reporter
# ---------------------------------------------------------------------------


class TestTerminalReporter:
    def test_returns_string(self, single_finding):
        reporter = TerminalReporter()
        output = reporter.report([single_finding], files_checked=1)
        assert isinstance(output, str)

    def test_output_contains_rule_id(self, single_finding):
        reporter = TerminalReporter()
        output = reporter.report([single_finding], files_checked=1)
        assert "AIL002" in output

    def test_output_contains_message(self, single_finding):
        reporter = TerminalReporter()
        output = reporter.report([single_finding], files_checked=1)
        assert "max_tokens" in output

    def test_output_contains_file_path(self, single_finding):
        reporter = TerminalReporter()
        output = reporter.report([single_finding], files_checked=1)
        assert "example.py" in output

    def test_empty_findings_shows_no_findings(self):
        reporter = TerminalReporter()
        output = reporter.report([], files_checked=3)
        # Rich uses ANSI escape codes; strip them for comparison
        import re
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
        assert "No findings" in plain or "no findings" in plain.lower()


# ---------------------------------------------------------------------------
# Reporter factory
# ---------------------------------------------------------------------------


def test_get_reporter_terminal():
    reporter = get_reporter("terminal")
    assert isinstance(reporter, TerminalReporter)


def test_get_reporter_json():
    reporter = get_reporter("json")
    assert isinstance(reporter, JSONReporter)


def test_get_reporter_sarif():
    reporter = get_reporter("sarif")
    assert isinstance(reporter, SARIFReporter)


def test_get_reporter_unknown_raises_value_error():
    """Unknown format should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown format"):
        get_reporter("unknown_format")
