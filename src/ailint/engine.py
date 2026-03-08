"""Core analysis engine — orchestrates file discovery, AST parsing, and rule execution."""

from __future__ import annotations

import ast
import re
import warnings
from fnmatch import fnmatch
from pathlib import Path

from ailint.config import AilintConfig
from ailint.models import Finding, Severity
from ailint.registry import RuleRegistry
from ailint.visitor import annotate_parents

# Pattern for inline ignore comments: # ailint: ignore  or  # ailint: ignore[AIL001,AIL002]
# Character class is bounded to {1,200} to prevent ReDoS on crafted input.
_IGNORE_PATTERN = re.compile(
    r"#\s*ailint:\s*ignore(?:\[([A-Z0-9, \t]{1,200})\])?", re.IGNORECASE
)


class AnalysisEngine:
    """Discovers Python files, runs all active rules, and collects findings."""

    def __init__(self, config: AilintConfig, rule_registry: RuleRegistry) -> None:
        self.config = config
        self.registry = rule_registry
        self._severity_map = {s.name: s for s in Severity}

    def analyze_paths(self, paths: list[str]) -> tuple[list[Finding], int]:
        """Analyze all Python files under the given paths.

        Returns:
            Tuple of (findings, files_checked_count).
        """
        files = self._collect_files(paths)
        all_findings: list[Finding] = []

        min_severity = self._severity_map.get(
            self.config.severity.upper(), Severity.INFO
        )
        rules = self.registry.get_active_rules(
            select=self.config.select or None,
            ignore=self.config.ignore or None,
            min_severity=min_severity,
        )

        # Wire config values into rules that declare configurable thresholds.
        # NoStreamingRule (AIL012) accepts a threshold via its .threshold attribute.
        for rule in rules:
            if hasattr(rule, "threshold"):
                rule.threshold = self.config.max_tokens_threshold

        for file_path in files:
            findings = self.analyze_file(str(file_path), rules)
            all_findings.extend(findings)

        return all_findings, len(files)

    def analyze_file(
        self, file_path: str, rules: list
    ) -> list[Finding]:
        """Parse and analyze a single file."""
        try:
            source = Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []

        try:
            tree = ast.parse(source, filename=file_path)
        except (SyntaxError, RecursionError, MemoryError):
            return []

        source_lines = source.splitlines()

        # Pre-pass: annotate every node with its parent reference.
        # This mutates AST node objects — safe in CPython but non-obvious.
        annotate_parents(tree)

        findings: list[Finding] = []
        for rule in rules:
            try:
                rule_findings = rule.check(tree, source_lines, file_path)
                findings.extend(rule_findings)
            except Exception as exc:
                # A rule failure should not crash the entire analysis.
                warnings.warn(
                    f"Rule {rule.rule_id} failed on {file_path}: {exc}",
                    stacklevel=2,
                )
                continue

        # Apply inline ignore comments
        findings = self._apply_inline_ignores(findings, source_lines)

        return findings

    def _collect_files(self, paths: list[str]) -> list[Path]:
        """Expand paths into a sorted list of .py files, respecting exclude patterns."""
        files: list[Path] = []

        for path_str in paths:
            path = Path(path_str).resolve()
            if path.is_file() and path.suffix == ".py":
                if not self._is_excluded(path):
                    files.append(path)
            elif path.is_dir():
                root = path
                for py_file in sorted(path.rglob("*.py")):
                    # Resolve the file to catch symlinks; reject any path that
                    # escapes the requested root directory (symlink traversal guard).
                    try:
                        resolved = py_file.resolve()
                        resolved.relative_to(root)
                    except ValueError:
                        # Path resolves outside of root — skip it.
                        continue
                    if not self._is_excluded(py_file):
                        files.append(py_file)

        # Deduplicate while preserving order
        seen: set[Path] = set()
        unique: list[Path] = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique.append(f)

        return unique

    def _is_excluded(self, path: Path) -> bool:
        """Check if a path matches any exclusion pattern."""
        path_str = str(path)
        for pattern in self.config.exclude:
            # Check if any part of the path matches the pattern
            for part in path.parts:
                if fnmatch(part, pattern):
                    return True
            if fnmatch(path_str, pattern):
                return True
        return False

    def _apply_inline_ignores(
        self, findings: list[Finding], source_lines: list[str]
    ) -> list[Finding]:
        """Remove findings that have inline ignore comments on their line."""
        filtered: list[Finding] = []

        for finding in findings:
            line_idx = finding.location.line - 1
            if 0 <= line_idx < len(source_lines):
                match = _IGNORE_PATTERN.search(source_lines[line_idx])
                if match:
                    rule_ids_str = match.group(1)
                    if rule_ids_str is None:
                        # Bare `# ailint: ignore` — ignores all rules on this line
                        continue
                    ignored_ids = {
                        rid.strip().upper() for rid in rule_ids_str.split(",")
                    }
                    if finding.rule_id.upper() in ignored_ids:
                        continue

            filtered.append(finding)

        return filtered
