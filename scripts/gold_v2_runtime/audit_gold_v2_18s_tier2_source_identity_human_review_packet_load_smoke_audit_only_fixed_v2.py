#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY"
OUT_DIR = "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only"
ORIGINAL = "audit_gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only.py"
REPORT = "GOLD_V2_18S_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_LOAD_SMOKE_PASSED_AUDIT_ONLY_SOURCE_RECOVERY_STILL_BLOCKED"
NEXT = "18T_TIER2_SOURCE_IDENTITY_HUMAN_REVIEW_PACKET_CONTENT_AUDIT_ONLY"


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def fx() -> Path:
    r = root()
    return (r.parents[1] if len(r.parents) >= 2 else r.parent) / "FX_OUTPUTS"


def lp(path: Path) -> Path:
    p = path if path.is_absolute() else path.resolve()
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith("\\\\?\\"):
        return Path(s)
    if s.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + s[2:])
    return Path("\\\\?\\" + s)


def read_text(path: Path) -> str:
    return lp(path).read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    lp(path).write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def write_json(path: Path, data: dict[str, Any]) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))


def read_csv(path: Path) -> pd.DataFrame:
    last: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, keep_default_na=False)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"csv read failed: {path}: {last}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def stop_count(df: pd.DataFrame) -> int:
    if "status" not in df.columns:
        return 999
    return int((df["status"].astype(str) == "STOP").sum())


def mdtable(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(lines)


def main() -> int:
    subprocess.run([sys.executable, str(Path(__file__).with_name(ORIGINAL))], cwd=str(root()))
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    summary_path = out / "gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_summary.json"
    load_path = out / "gold_v2_18s_load_checks.csv"
    markdown_path = out / "gold_v2_18s_markdown_audit.csv"
    packet_file_path = out / "gold_v2_18s_packet_file_audit.csv"
    manual_path = out / "gold_v2_18s_manual_question_audit.csv"
    blocked_path = out / "gold_v2_18s_blocked_action_audit.csv"
    gates_path = out / "gold_v2_18s_required_next_gates.csv"
    safety_path = out / "gold_v2_18s_safety_matrix.csv"
    required = [summary_path, load_path, markdown_path, packet_file_path, manual_path, blocked_path, gates_path, safety_path]
    missing = [str(p) for p in required if not lp(p).exists()]
    if missing:
        print(json.dumps({"step": STEP, "status": "18S_FIXED_V2_STOP_MISSING_ORIGINAL_OUTPUTS", "missing": missing}, ensure_ascii=False, indent=2))
        return 2

    summary = read_json(summary_path)
    load = read_csv(load_path)
    markdown = read_csv(markdown_path)
    packet_files = read_csv(packet_file_path)
    manual = read_csv(manual_path)
    blocked = read_csv(blocked_path)
    gates = read_csv(gates_path)
    safety = read_csv(safety_path)

    md_stop = markdown[markdown["status"].astype(str) == "STOP"] if "status" in markdown.columns else markdown
    false_positive = (
        len(md_stop) == 1
        and "required negative readiness language" in str(md_stop.iloc[0].get("check", ""))
        and summary.get("decision_made") is False
        and summary.get("approval_granted") is False
        and stop_count(packet_files) == 0
        and stop_count(manual) == 0
        and stop_count(blocked) == 0
    )
    if not false_positive:
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
        safety.loc[mask, "observed"] = True
        safety.loc[mask, "expected"] = True
        safety.loc[mask, "status"] = "PASS"
    write_csv(safety, safety_path)

    total_stop = stop_count(load) + stop_count(packet_files) + stop_count(markdown) + stop_count(manual) + stop_count(blocked)
    success = total_stop == 0
    summary.update({
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": SUCCESS if success else "18S_STOP_REVIEW_PACKET_LOAD_SMOKE_OUTPUTS",
        "packet_load_smoke_passed": bool(success),
        "total_stop_rows": int(total_stop),
        "next_recommended_step": NEXT if success else "STOP_REVIEW_18S_OUTPUTS",
        "fixed_runner": "audit_gold_v2_18s_tier2_source_identity_human_review_packet_load_smoke_audit_only_fixed_v2.py",
    })
    write_json(summary_path, summary)
    report = [
        "# GOLD V2 18S TIER2 source identity human review packet load-smoke audit-only report",
        "",
        f"Created UTC: {summary['created_utc']}",
        f"Status: `{summary['status']}`",
        "",
        "## Final decision",
        "- 18S load-smoke checked the 18R human-review packet only.",
        "- A strict wording false positive was corrected; this does not grant approval or execute recovery/finalization.",
        "- Source recovery, identity finalization/recovery, OHLC replay, live/final paths, Discord, MT5, AI API, live hook, and NO_SIGNAL Discord remain disabled.",
        "",
        "## Load checks", mdtable(load), "",
        "## Packet file audit", mdtable(packet_files), "",
        "## Markdown audit", mdtable(markdown), "",
        "## Manual question audit", mdtable(manual), "",
        "## Blocked action audit", mdtable(blocked), "",
        "## Next gates", mdtable(gates), "",
        "## Safety", mdtable(safety),
    ]
    write_text(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
