"""JSON reporter for AI-Lint."""

from __future__ import annotations

import json

from ailint.models import Finding
from ailint.reporters.base import BaseReporter


class JSONReporter(BaseReporter):
    """Machine-readable JSON output."""

    def report(self, findings: list[Finding], files_checked: int) -> str:
        output = {
            "version": "1.0",
            "files_checked": files_checked,
            "findings_count": len(findings),
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "rule_name": f.rule_name,
                    "severity": f.severity.name,
                    "message": f.message,
                    "location": {
                        "file": f.location.file,
                        "line": f.location.line,
                        "col": f.location.col,
                    },
                    "fix_suggestion": f.fix_suggestion,
                }
                for f in findings
            ],
        }
        return json.dumps(output, indent=2)
