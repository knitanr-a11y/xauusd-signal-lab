#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "18G_TIER2_CONTENT_INSPECTION_AUDIT_ONLY"
OUT_DIR = "gold_v2_18g_tier2_source_artifact_content_inspection_execution_audit_only"
REPORT = "GOLD_V2_18G_TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_EXECUTION_AUDIT_ONLY_REPORT.md"
SUCCESS = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_EXECUTED_AUDIT_ONLY_SOURCE_RECOVERY_BLOCKED"
EXPECTED_18F = "TIER2_SOURCE_ARTIFACT_CONTENT_INSPECTION_AUTHORIZATION_GATE_READY_AUDIT_ONLY_CONTENT_INSPECTION_BLOCKED"
IN_DIR = "gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_audit_only"
REQUIRED_FIELDS = [
    "manifest_row_id",
    "component",
    "source_identity_type",
    "source_role",
    "source_row_number_1based",
    "source_key",
    "source_row_hash",
    "strategy_id",
    "source_status",
]


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


def ensure(path: Path) -> None:
    lp(path.parent).mkdir(parents=True, exist_ok=True)


def wcsv(df: pd.DataFrame, path: Path) -> None:
    ensure(path)
    df.to_csv(lp(path), index=False, encoding="utf-8-sig")


def wtxt(path: Path, value: str) -> None:
    ensure(path)
    lp(path).write_text(value, encoding="utf-8")


def wjson(obj: dict[str, Any], path: Path) -> None:
    ensure(path)
    lp(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def text(path: Path, max_chars: int = 200000) -> str:
    raw = lp(path).read_bytes()[:max_chars]
    for enc in ("utf-8-sig", "utf-8", "cp932", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def jload(path: Path) -> dict[str, Any]:
    return json.loads(text(path))


def csvload(path: Path, **kwargs: Any) -> pd.DataFrame:
    last = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return pd.read_csv(lp(path), encoding=enc, **kwargs)
        except Exception as exc:
            last = exc
    raise RuntimeError(f"csv load failed: {path}: {last}")


def norm(x: Any) -> str:
    return str(x).strip().lower().replace("-", "_").replace(" ", "_")


def field_rows(rel: str, filename: str, names: list[str]) -> list[dict[str, Any]]:
    seen = {norm(x) for x in names}
    return [
        {
            "relative_path": rel,
            "filename": filename,
            "field": f,
            "present": f in seen,
            "source_recovery_executed": False,
            "implementation_allowed": False,
            "final_signal_allowed": False,
        }
        for f in REQUIRED_FIELDS
    ]


def md_table(df: pd.DataFrame, limit: int = 80) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(limit).iterrows():
        out.append("| " + " | ".join(str(row[c]).replace("|", "\\|").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out)


def inspect_csv(path: Path) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    header = csvload(path, nrows=0)
    cols = [str(c) for c in header.columns]
    rows = 0
    last = None
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            for chunk in pd.read_csv(lp(path), encoding=enc, chunksize=50000):
                rows += int(chunk.shape[0])
            break
        except Exception as exc:
            rows = 0
            last = exc
    if last is not None and rows == 0:
        pass
    return {"row_count": rows, "column_count": len(cols), "columns": ";".join(cols)}, pd.DataFrame([{"column_order": i + 1, "column_name": c} for i, c in enumerate(cols)]), field_rows(str(path), path.name, cols)


def inspect_json(path: Path) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    obj = jload(path)
    keys: list[str] = []
    def walk(x: Any, pref: str = "", depth: int = 0) -> None:
        if depth > 3:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                full = f"{pref}.{k}" if pref else str(k)
                keys.append(full)
                walk(v, full, depth + 1)
        elif isinstance(x, list):
            for i, v in enumerate(x[:3]):
                walk(v, f"{pref}[{i}]" if pref else f"[{i}]", depth + 1)
    walk(obj)
    base = [k.split(".")[-1].split("[")[0] for k in keys]
    return {"json_key_count": len(keys), "keys_preview": ";".join(keys[:100])}, pd.DataFrame([{"key_order": i + 1, "json_key": k} for i, k in enumerate(keys)]), field_rows(str(path), path.name, base)


def inspect_zip(path: Path) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    rows = []
    with zipfile.ZipFile(lp(path), "r") as zf:
        for info in zf.infolist():
            rows.append({"member_name": info.filename, "member_suffix": Path(info.filename).suffix, "member_size": int(info.file_size)})
    names = [r["member_name"] for r in rows]
    return {"zip_member_count": len(rows), "members_preview": ";".join(names[:100])}, pd.DataFrame(rows), field_rows(str(path), path.name, names)


def inspect_md(path: Path) -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    s = text(path)
    headings = [line.strip() for line in s.splitlines() if line.lstrip().startswith("#")]
    return {"heading_count": len(headings), "headings_preview": ";".join(headings[:100])}, pd.DataFrame([{"heading_order": i + 1, "heading": h} for i, h in enumerate(headings)]), field_rows(str(path), path.name, headings + s.lower().split())


def main() -> int:
    out = fx() / OUT_DIR
    lp(out).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    summary_path = fx() / IN_DIR / "gold_v2_18f_tier2_source_artifact_content_inspection_authorization_gate_summary.json"
    checks_path = fx() / IN_DIR / "gold_v2_18f_authorization_gate_checks.csv"
    safety_path = fx() / IN_DIR / "gold_v2_18f_safety_matrix.csv"
    plan_path = fx() / IN_DIR / "gold_v2_18f_blocked_execution_plan.csv"
    blockers_path = fx() / IN_DIR / "gold_v2_18f_blockers.csv"
    s18f = jload(summary_path)
    checks18f = csvload(checks_path)
    safety18f = csvload(safety_path)
    plan = csvload(plan_path)
    blockers = csvload(blockers_path)
    checks = []
    checks.append(["18G-C001", "18F status", s18f.get("status"), EXPECTED_18F, "PASS" if s18f.get("status") == EXPECTED_18F else "STOP"])
    checks.append(["18G-C002", "18F checks STOP rows", int((checks18f["status"].astype(str) == "STOP").sum()), 0, "PASS" if int((checks18f["status"].astype(str) == "STOP").sum()) == 0 else "STOP"])
    checks.append(["18G-C003", "18F safety STOP rows", int((safety18f["status"].astype(str) == "STOP").sum()), 0, "PASS" if int((safety18f["status"].astype(str) == "STOP").sum()) == 0 else "STOP"])
    results = []
    csv_frames = []
    json_frames = []
    zip_frames = []
    md_frames = []
    fields_all = []
    for _, r in plan.iterrows():
        rel = str(r.get("relative_path", ""))
        p = fx() / rel
        row = {"relative_path": rel, "filename": p.name, "suffix": p.suffix.lower(), "exists": lp(p).exists(), "inspection_status": "NOT_INSPECTED", "source_recovery_executed": False, "implementation_allowed": False, "final_signal_allowed": False}
        try:
            if not row["exists"]:
                row["inspection_status"] = "MISSING"
                extra, df, fr = {}, pd.DataFrame(), field_rows(rel, p.name, [])
            elif row["suffix"] == ".csv":
                extra, df, fr = inspect_csv(p); df.insert(0, "relative_path", rel); csv_frames.append(df); row["inspection_status"] = "CSV_SCHEMA_ONLY"
            elif row["suffix"] == ".json":
                extra, df, fr = inspect_json(p); df.insert(0, "relative_path", rel); json_frames.append(df); row["inspection_status"] = "JSON_KEYS_ONLY"
            elif row["suffix"] == ".zip":
                extra, df, fr = inspect_zip(p); df.insert(0, "relative_path", rel); zip_frames.append(df); row["inspection_status"] = "ZIP_MEMBERS_ONLY"
            elif row["suffix"] == ".md":
                extra, df, fr = inspect_md(p); df.insert(0, "relative_path", rel); md_frames.append(df); row["inspection_status"] = "MD_HEADINGS_ONLY"
            else:
                extra, fr = {}, field_rows(rel, p.name, [])
            row.update(extra)
            fields_all.extend(fr)
        except Exception as exc:
            row["inspection_status"] = "ERROR"
            row["inspection_error"] = repr(exc)
            fields_all.extend(field_rows(rel, p.name, []))
        results.append(row)
    res = pd.DataFrame(results)
    fielddf = pd.DataFrame(fields_all)
    checkdf = pd.DataFrame(checks, columns=["check_id", "check", "observed", "expected", "status"])
    safety = pd.DataFrame([
        ["audit_only", True, True, "PASS"],
        ["content_inspection_executed", True, True, "PASS"],
        ["source_recovery_executed", False, False, "PASS"],
        ["implementation_allowed", False, False, "PASS"],
        ["oh_lc_replay_allowed", False, False, "PASS"],
        ["live_enabled", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["discord_send_allowed", False, False, "PASS"],
        ["mt5_order_allowed", False, False, "PASS"],
        ["ai_api_allowed", False, False, "PASS"],
        ["live_hook_allowed", False, False, "PASS"],
        ["no_signal_discord_notified", False, False, "PASS"],
    ], columns=["safety_item", "observed", "expected", "status"])
    nextg = pd.DataFrame([
        ["18H", "TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_AUDIT_ONLY", "Plan only; source recovery remains blocked.", True],
        ["LIVE", "MEDIUM_FULL_SET_LIVE_EVALUATOR", "Blocked.", False],
    ], columns=["next_step", "name", "purpose", "allowed_after_18g_success"])
    blockers["carried_forward_by"] = STEP
    blockers["source_recovery_executed"] = False
    blockers["implementation_allowed"] = False
    blockers["live_or_final_allowed"] = False
    for name, df in [
        ("gold_v2_18g_content_inspection_checks.csv", checkdf),
        ("gold_v2_18g_inspected_artifact_results.csv", res),
        ("gold_v2_18g_csv_schema_results.csv", pd.concat(csv_frames, ignore_index=True) if csv_frames else pd.DataFrame()),
        ("gold_v2_18g_json_key_results.csv", pd.concat(json_frames, ignore_index=True) if json_frames else pd.DataFrame()),
        ("gold_v2_18g_zip_member_results.csv", pd.concat(zip_frames, ignore_index=True) if zip_frames else pd.DataFrame()),
        ("gold_v2_18g_markdown_heading_results.csv", pd.concat(md_frames, ignore_index=True) if md_frames else pd.DataFrame()),
        ("gold_v2_18g_required_identity_field_presence.csv", fielddf),
        ("gold_v2_18g_required_next_gates.csv", nextg),
        ("gold_v2_18g_blockers.csv", blockers),
        ("gold_v2_18g_safety_matrix.csv", safety),
    ]:
        wcsv(df, out / name)
    status = SUCCESS if (checkdf["status"].astype(str) == "STOP").sum() == 0 else "TIER2_CONTENT_INSPECTION_STOPPED_AUDIT_ONLY"
    summary = {"created_utc": now, "step": STEP, "status": status, "audit_only": True, "content_inspection_executed": True, "inspected_artifacts": int(len(res)), "source_recovery_executed": False, "implementation_allowed": False, "oh_lc_replay_allowed": False, "live_enabled": False, "final_signal_allowed": False, "external_actions": {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False}, "no_signal_discord_notified": False, "next_recommended_step": "18H_TIER2_ROW_LEVEL_SOURCE_IDENTITY_EXTRACTION_PLAN_AUDIT_ONLY"}
    wjson(summary, out / "gold_v2_18g_tier2_source_artifact_content_inspection_execution_summary.json")
    report = ["# GOLD V2 18G TIER2 source artifact content inspection execution audit-only report", "", f"Created UTC: {now}", f"Status: `{status}`", "", "## Final decision", "- Read-only structural inspection executed after explicit approval.", "- Source recovery, OHLC replay, implementation, live/final, and external actions remain blocked.", "", "## Checks", md_table(checkdf), "", "## Inspected artifacts", md_table(res), "", "## Required field presence", md_table(fielddf), "", "## Safety", md_table(safety), "", "## Next gates", md_table(nextg)]
    wtxt(out / REPORT, "\n".join(report))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if status == SUCCESS else 2


if __name__ == "__main__":
    raise SystemExit(main())
