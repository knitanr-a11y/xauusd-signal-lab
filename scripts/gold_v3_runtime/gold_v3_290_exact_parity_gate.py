from __future__ import annotations
import json
from pathlib import Path

def require_exact_parity(path: Path) -> dict:
    report=json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("status")!="PASS":
        raise ValueError("exact historical admission replay is not PASS")
    rows=report.get("rows",[])
    years={int(row.get("year")) for row in rows if row.get("passed") is True}
    if years!={2024,2025,2026}:
        raise ValueError("exact historical admission replay does not pass all years")
    return report
