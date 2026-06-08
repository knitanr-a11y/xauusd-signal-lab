#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GOLD V2 25C82 local CoreB historical SOT report package audit-only.

This packages the 25C81 PASS result into a local-official historical CoreB
SOT report. It does not recover cluster logic and does not enable live.

No Discord, MT5, AI API, live hook, live evaluator, or final signal.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "25C82_LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_AUDIT_ONLY"
OUT_DIR_NAME = "gold_v2_25c82_local_coreb_historical_sot_report_package_audit_only"
UPSTREAM_DIR_NAME = "gold_v2_25c81_coreb_direct_sot_local_replay_audit_only"

EXTERNAL_ACTIONS = {
    "discord_send_allowed": False,
    "mt5_order_allowed": False,
    "ai_api_allowed": False,
    "live_hook_allowed": False,
}

UPSTREAM_FILES = {
    "summary": "25c81_summary.json",
    "metrics": "25c81_coreb_direct_metrics.csv",
    "top_filter_parity": "25c81_top_filter_parity.csv",
    "final_sot_join_parity": "25c81_final_sot_join_parity.csv",
    "readiness": "25c81_readiness_matrix.csv",
    "guardrail": "25c81_guardrail_matrix.csv",
    "report": "GOLD_V2_25C81_COREB_DIRECT_SOT_LOCAL_REPLAY_AUDIT_ONLY_REPORT.md",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def files_root() -> Path:
    root = repo_root()
    return root.parents[1] if len(root.parents) >= 2 else root.parent


def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"


def out_dir() -> Path:
    out = fx_outputs() / OUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    return out


def upstream_dir() -> Path:
    return fx_outputs() / UPSTREAM_DIR_NAME


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_json(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): clean_json(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean_json(v) for v in x]
    if isinstance(x, float):
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return x
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    return x


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(clean_json(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def file_inventory() -> pd.DataFrame:
    rows = []
    base = upstream_dir()
    for label, filename in UPSTREAM_FILES.items():
        p = base / filename
        row: dict[str, Any] = {
            "label": label,
            "filename": filename,
            "exists": p.exists(),
            "path": str(p),
        }
        if p.exists():
            row["bytes"] = p.stat().st_size
            row["sha256"] = sha256_file(p)
        rows.append(row)
    return pd.DataFrame(rows)


def status_pass(df: pd.DataFrame) -> bool:
    if df.empty or "status" not in df.columns:
        return False
    return bool((df["status"].astype(str) == "PASS").all())


def build_final_status(summary81: dict[str, Any], metrics: pd.DataFrame, top: pd.DataFrame, final_join: pd.DataFrame, inv: pd.DataFrame) -> pd.DataFrame:
    total = metrics[metrics.get("dataset", pd.Series(dtype=str)).astype(str).eq("total")] if not metrics.empty and "dataset" in metrics.columns else pd.DataFrame()
    metric_ok = bool(len(total) and int(total.iloc[0].get("count", -1)) == 125)
    rows = [
        ["25C81_upstream_status", summary81.get("status"), "COREB_DIRECT_SOT_LOCAL_REPLAY_PASSED_AUDIT_ONLY_LIVE_BLOCKED", "PASS" if summary81.get("status") == "COREB_DIRECT_SOT_LOCAL_REPLAY_PASSED_AUDIT_ONLY_LIVE_BLOCKED" else "FAIL"],
        ["25C81_upstream_ready", summary81.get("coreb_direct_sot_local_official_ready"), True, "PASS" if summary81.get("coreb_direct_sot_local_official_ready") is True else "FAIL"],
        ["upstream_files_present", bool(inv["exists"].all()) if not inv.empty else False, True, "PASS" if not inv.empty and bool(inv["exists"].all()) else "FAIL"],
        ["coreb_total_count", int(total.iloc[0].get("count", -1)) if len(total) else None, 125, "PASS" if metric_ok else "FAIL"],
        ["top_filter_parity", status_pass(top), True, "PASS" if status_pass(top) else "FAIL"],
        ["final_sot_join_parity", status_pass(final_join), True, "PASS" if status_pass(final_join) else "FAIL"],
        ["a002_used_for_coreb_metrics", summary81.get("a002_used_for_coreb_metrics"), False, "PASS" if summary81.get("a002_used_for_coreb_metrics") is False else "FAIL"],
        ["coreb_live_evaluator_allowed", summary81.get("coreb_live_evaluator_allowed"), False, "PASS" if summary81.get("coreb_live_evaluator_allowed") is False else "FAIL"],
        ["final_signal_allowed", summary81.get("final_signal_allowed"), False, "PASS" if summary81.get("final_signal_allowed") is False else "FAIL"],
    ]
    return pd.DataFrame(rows, columns=["check", "observed", "expected", "status"])


def build_carry_forward_blockers() -> pd.DataFrame:
    return pd.DataFrame([
        ["B82-001", "CoreB live evaluator", "OPEN", "HARD", "same_count / cluster_id / representative profit generation logic is not recovered from source."],
        ["B82-002", "A002", "CLOSED_FOR_COREB_MAIN_PATH", "INFO", "A002 is demoted to auxiliary evidence and is not used for CoreB WR/PF."],
        ["B82-003", "External actions", "OPEN", "SAFETY", "Discord, MT5, AI API, live hook, live evaluator, and final signal remain OFF."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])


def markdown_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    d = df.head(max_rows).fillna("").copy()
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ") for c in d.columns) + " |")
    return "\n".join(lines)


def build_report(summary82: dict[str, Any], inv: pd.DataFrame, final_status: pd.DataFrame, metrics: pd.DataFrame, top: pd.DataFrame, final_join: pd.DataFrame, blockers: pd.DataFrame) -> str:
    return "\n".join([
        "# GOLD V2 25C82 local CoreB historical SOT report package audit-only report",
        "",
        f"Created UTC: {summary82['created_utc']}",
        f"Status: `{summary82['status']}`",
        "",
        "## Decision",
        "",
        "CoreB historical SOT is locally reportable from the 125-row direct SOT. A002 is not used for CoreB performance. CoreB live evaluator remains blocked.",
        "",
        "## Upstream 25C81 inventory",
        markdown_table(inv[["label", "filename", "exists", "path"]]),
        "",
        "## Final status checks",
        markdown_table(final_status),
        "",
        "## CoreB historical metrics",
        markdown_table(metrics),
        "",
        "## Top-ledger parity carry-forward",
        markdown_table(top),
        "",
        "## Final SOT join parity carry-forward",
        markdown_table(final_join),
        "",
        "## Blockers carried forward",
        markdown_table(blockers),
        "",
        "## Safety",
        "",
        "- audit_only: true",
        "- Discord/MT5/AI/live_hook/final_signal: false",
        "- CoreB live evaluator: blocked",
    ])


def main() -> int:
    out = out_dir()
    created = datetime.now(timezone.utc).isoformat()
    base = upstream_dir()

    inv = file_inventory()
    summary81 = read_json(base / UPSTREAM_FILES["summary"])
    metrics = read_csv(base / UPSTREAM_FILES["metrics"])
    top = read_csv(base / UPSTREAM_FILES["top_filter_parity"])
    final_join = read_csv(base / UPSTREAM_FILES["final_sot_join_parity"])
    readiness = read_csv(base / UPSTREAM_FILES["readiness"])
    guardrail = read_csv(base / UPSTREAM_FILES["guardrail"])

    final_status = build_final_status(summary81, metrics, top, final_join, inv)
    blockers = build_carry_forward_blockers()
    all_pass = bool((final_status["status"].astype(str) == "PASS").all()) if not final_status.empty else False

    status = "LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_READY_AUDIT_ONLY_LIVE_BLOCKED" if all_pass else "LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_REVIEW_REQUIRED_AUDIT_ONLY"
    summary82 = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "upstream_25c81_status": summary81.get("status"),
        "coreb_historical_sot_report_allowed": all_pass,
        "coreb_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "a002_used_for_coreb_metrics": False,
        "a002_role": "DEMOTED_AUXILIARY_ONLY",
        "external_actions": EXTERNAL_ACTIONS,
        "next_recommended_step": "25C83_CLUSTER_REPRESENTATIVE_LOGIC_RECOVERY_AUDIT_ONLY_OR_HISTORICAL_REPORT_HANDOFF" if all_pass else "REVIEW_25C82_FAILURES",
    }

    inv.to_csv(out / "25c82_upstream_inventory.csv", index=False, encoding="utf-8-sig")
    final_status.to_csv(out / "25c82_final_status_checks.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(out / "25c82_coreb_historical_metrics.csv", index=False, encoding="utf-8-sig")
    top.to_csv(out / "25c82_top_filter_parity_carry_forward.csv", index=False, encoding="utf-8-sig")
    final_join.to_csv(out / "25c82_final_sot_join_parity_carry_forward.csv", index=False, encoding="utf-8-sig")
    readiness.to_csv(out / "25c82_readiness_carry_forward.csv", index=False, encoding="utf-8-sig")
    guardrail.to_csv(out / "25c82_guardrail_carry_forward.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c82_blocker_carry_forward.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c82_summary.json", summary82)
    (out / "GOLD_V2_25C82_LOCAL_COREB_HISTORICAL_SOT_REPORT_PACKAGE_AUDIT_ONLY_REPORT.md").write_text(build_report(summary82, inv, final_status, metrics, top, final_join, blockers), encoding="utf-8")

    zip_path = fx_outputs() / "gold_v2_25c82_local_coreb_historical_sot_report_package_audit_only.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir():
            z.write(p, arcname=p.name)

    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2, allow_nan=False))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
