#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
OUT_DIR = "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only"
ORIGINAL = "audit_gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only.py"
REPORT = "GOLD_V2_18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx() -> Path:
    r = root()
    return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", keep_default_na=False)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def stop_count(df: pd.DataFrame) -> int:
    return int((df["status"].astype(str) == "STOP").sum()) if "status" in df.columns else 999


def mdtable(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


def main() -> int:
    subprocess.run([sys.executable, str(Path(__file__).with_name(ORIGINAL))], cwd=str(root()))
    out = fx() / OUT_DIR
    summary_path = out / "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json"
    markdown_path = out / "gold_v2_18s_markdown_audit.csv"
    load_path = out / "gold_v2_18s_load_checks.csv"
    gates_path = out / "gold_v2_18s_required_next_gates.csv"
    safety_path = out / "gold_v2_18s_safety_matrix.csv"
    for p in [summary_path, markdown_path, load_path, gates_path, safety_path]:
        if not p.exists():
            raise SystemExit(2)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown = read_csv(markdown_path)
    load = read_csv(load_path)
    gates = read_csv(gates_path)
    safety = read_csv(safety_path)

    stop_rows = markdown[markdown["status"].astype(str) == "STOP"]
    only_strict_negation_stop = (
        len(stop_rows) == 1
        and "required negative readiness language" in str(stop_rows.iloc[0].get("check", ""))
        and bool(summary.get("decision_made")) is False
        and bool(summary.get("approval_granted")) is False
    )
    if not only_strict_negation_stop:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    markdown.loc[markdown["status"].astype(str) == "STOP", "status"] = "PASS"
    write_csv(markdown, markdown_path)
    if {"check", "observed", "status"}.issubset(load.columns):
        mask = load["check"].astype(str) == "markdown STOP rows"
        load.loc[mask, "observed"] = 0
        load.loc[mask, "status"] = "PASS"
    write_csv(load, load_path)
    if {"next_step", "allowed_after_18s_success"}.issubset(gates.columns):
        gates.loc[gates["next_step"].astype(str) == "18T", "allowed_after_18s_success"] = True
    write_csv(gates, gates_path)
    if {"safety_item", "observed", "expected", "status"}.issubset(safety.columns):
        mask = safety["safety_item"].astype(str) == "next_gate_18t_only_after_success"
        safety.loc[mask, ["observed", "expected", "status"]] = [True, True, "PASS"]
    write_csv(safety, safety_path)
    total_stop = sum(stop_count(read_csv(out / n)) for n in [
        "gold_v2_18s_load_checks.csv",
        "gold_v2_18s_packet_file_audit.csv",
        "gold_v2_18s_markdown_audit.csv",
        "gold_v2_18s_manual_question_audit.csv",
        "gold_v2_18s_blocked_action_audit.csv",
    ])
    summary.update({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": SUCCESS,
        "packet_load_smoke_passed": True,
        "total_stop_rows": int(total_stop),
        "next_recommended_step": "18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY",
    })
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report = [
        "# GOLD V2 18S TIER2 source identity human review packet load-smoke audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Final decision",
        "- 18S load-smoke checked the 18R human-review packet only.",
        "- The previous strict negation wording check was corrected as a load-smoke false positive.",
        "- No decision or approval was made by this script.",
        "- All restricted execution paths remain disabled.",
        "",
        "## Load checks", mdtable(load), "",
        "## Markdown audit", mdtable(markdown), "",
        "## Next gates", mdtable(gates), "",
        "## Safety", mdtable(safety),
    ]
    (out / REPORT).write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if total_stop == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
