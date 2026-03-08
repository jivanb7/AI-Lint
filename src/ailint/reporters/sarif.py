"""SARIF 2.1.0 reporter for GitHub Code Scanning integration."""

from __future__ import annotations

import json
from collections import OrderedDict

from ailint.models import Finding, Severity
from ailint.reporters.base import BaseReporter

_SARIF_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json"
_SARIF_VERSION = "2.1.0"

_SEVERITY_TO_LEVEL: dict[Severity, str] = {
    Severity.CRITICAL: "error",
    Severity.ERROR: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "note",
}


class SARIFReporter(BaseReporter):
    """Produces SARIF 2.1.0 JSON for GitHub Code Scanning."""

    def report(self, findings: list[Finding], files_checked: int) -> str:
        # Collect unique rules
        rules_seen: OrderedDict[str, Finding] = OrderedDict()
        for f in findings:
            if f.rule_id not in rules_seen:
                rules_seen[f.rule_id] = f

        rule_index = {rule_id: idx for idx, rule_id in enumerate(rules_seen)}

        sarif = {
            "$schema": _SARIF_SCHEMA,
            "version": _SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "ailint",
                            "version": "0.1.0",
                            "informationUri": "https://github.com/jivanb/AI-Lint",
                            "rules": [
                                {
                                    "id": f.rule_id,
                                    "name": f.rule_name,
                                    "shortDescription": {"text": f.message},
                                    "defaultConfiguration": {
                                        "level": _SEVERITY_TO_LEVEL.get(
                                            f.severity, "warning"
                                        )
                                    },
                                }
                                for f in rules_seen.values()
                            ],
                        }
                    },
                    "results": [
                        {
                            "ruleId": f.rule_id,
                            "ruleIndex": rule_index[f.rule_id],
                            "level": _SEVERITY_TO_LEVEL.get(f.severity, "warning"),
                            "message": {"text": f.message},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "uri": f.location.file,
                                            "uriBaseId": "%SRCROOT%",
                                        },
                                        "region": {
                                            "startLine": f.location.line,
                                            "startColumn": f.location.col + 1,  # SARIF is 1-indexed
                                        },
                                    }
                                }
                            ],
                            **(
                                {"fixes": [{"description": {"text": f.fix_suggestion}}]}
                                if f.fix_suggestion
                                else {}
                            ),
                        }
                        for f in findings
                    ],
                }
            ],
        }

        return json.dumps(sarif, indent=2)
