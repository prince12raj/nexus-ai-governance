"""
utils/export_utils.py — Export helper functions.
"""
import csv
import io
import json
from typing import Any, Dict, List

from models.audit_models import AuditReport


def report_to_dict(report: AuditReport) -> Dict[str, Any]:
    return report.model_dump()


def reports_to_csv_bytes(reports: List[AuditReport]) -> bytes:
    rows = [{"framework": r.framework_targeted,
             "score":     r.compliance_score,
             "findings":  r.total_findings,
             "critical":  r.critical_findings,
             "timestamp": r.generated_timestamp}
            for r in reports]
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode()


def report_to_json_bytes(report: AuditReport) -> bytes:
    return json.dumps(report.model_dump(), indent=2).encode()
