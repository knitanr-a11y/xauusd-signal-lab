#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C106_GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_TRIAGE_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c106_goldv2_corea_medium_high_signal_triage_audit_only"
INPUTS = ["25c105_summary.json", "25c105_file_inventory.csv", "25c105_suspicious_file_hits.csv", "25c105_component_risk_summary.csv", "25c105_decision_matrix.csv", "25c105_blocker_matrix.csv"]
EXPECTED_25C105_STATUS = "COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
EXCLUDE = ["gold_h1h4_bear", "strict_7", "gold_strict_7", "ai_evaluation_guardrails", "mochipoyo", "multi_strategy", "btcusd", "btc"]
SCOPE = ["docs\\gold_v2", "docs/gold_v2", "scripts\\gold_v2_runtime", "scripts/gold_v2_runtime", "fx_outputs\\gold_v2", "fx_outputs/gold_v2"]
SIGNAL = ["corea", "core_a", "coreb", "medium", "arbitration", "frozen_core", "final_sot", "live_evaluator"]
HARD = ["exit_time", "exit_price", "close_time", "close_price", "future", "lookahead", "leakage", "outcome", "result", "win", "loss", "hit", "tp_hit", "sl_hit", "mae", "mfe", "duration", "holding"]
PROFIT = ["profit", "profit_r", "top_profit", "realized", "pnl", "best", "max_profit", "min_profit", "selected", "top_candidate", "representative", "rank", "sort", "argmax", "argmin"]
ARB = ["arbitration", "final_sot", "final_signal", "choose", "chosen", "prefer", "priority", "tie_break", "compare"]


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME; p.mkdir(parents=True, exist_ok=True); return p


def find_file(name: str) -> Path | None:
    for c in [repo_root() / name, fx_outputs() / name]:
        if c.exists(): return c
    for base in [fx_outputs(), repo_root()]:
        if base.exists():
            found = sorted(base.rglob(name))
            if found: return found[0]
    return None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()


def clean(x: Any) -> Any:
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, list): return [clean(v) for v in x]
    try:
        if pd.isna(x): return None
    except Exception: pass
    return x.isoformat() if hasattr(x, "isoformat") else x

def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def read_json(p: Path | None) -> dict[str, Any]:
    if not p or not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

def read_csv(p: Path | None) -> pd.DataFrame:
    return pd.read_csv(p) if p and p.exists() else pd.DataFrame()

def inventory(paths: dict[str, Path | None]) -> pd.DataFrame:
    rows = []
    for n, p in paths.items():
        r = {"filename": n, "exists": bool(p and p.exists()), "path": str(p) if p else ""}
        if p and p.exists():
            r["bytes"] = p.stat().st_size; r["sha256"] = sha256_file(p)
            if p.suffix.lower() == ".csv":
                r["row_count"] = len(pd.read_csv(p)); r["columns"] = ";".join(pd.read_csv(p, nrows=0).columns)
        rows.append(r)
    return pd.DataFrame(rows)

def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:500] for c in d.columns) + " |")
    return "\n".join(lines)

def contains_any(text: str, pats: list[str]) -> bool:
    low = str(text).lower()
    return any(p in low for p in pats)

def evidence_class(row: pd.Series) -> str:
    tok = str(row.get("token", "")).lower()
    if tok in HARD: return "hard_future_or_outcome"
    if tok in PROFIT: return "profit_or_representative_selection"
    if tok in ARB: return "medium_arbitration_or_final_sot"
    return "other"

def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir(); paths = {n: find_file(n) for n in INPUTS}
    inv_inputs = inventory(paths); s105 = read_json(paths["25c105_summary.json"])
    inv = read_csv(paths["25c105_file_inventory.csv"]); hits = read_csv(paths["25c105_suspicious_file_hits.csv"])
    inputs_ok = bool(inv_inputs["exists"].all()) if not inv_inputs.empty else False
    upstream_ok = s105.get("status") == EXPECTED_25C105_STATUS
    for df in [inv, hits]:
        if not df.empty and "relative_path" in df.columns:
            df["_rel_lower"] = df["relative_path"].astype(str).str.lower()
    scope_mask = inv["_rel_lower"].apply(lambda x: contains_any(x, SCOPE)) if not inv.empty else pd.Series(dtype=bool)
    excl_mask = inv["_rel_lower"].apply(lambda x: contains_any(x, EXCLUDE)) if not inv.empty else pd.Series(dtype=bool)
    sig_mask = inv.apply(lambda r: contains_any(str(r.get("relative_path", "")) + " " + str(r.get("hard_future_hits", "")) + " " + str(r.get("profit_selection_hits", "")) + " " + str(r.get("medium_arbitration_hits", "")), SIGNAL), axis=1) if not inv.empty else pd.Series(dtype=bool)
    high_inv = inv[scope_mask & ~excl_mask & sig_mask].copy() if not inv.empty else pd.DataFrame()
    excluded = inv[scope_mask & excl_mask].copy() if not inv.empty else pd.DataFrame()
    if not hits.empty:
        h_scope = hits["_rel_lower"].apply(lambda x: contains_any(x, SCOPE))
        h_excl = hits["_rel_lower"].apply(lambda x: contains_any(x, EXCLUDE))
        h_sig = hits.apply(lambda r: contains_any(str(r.get("relative_path", "")) + " " + str(r.get("token", "")) + " " + str(r.get("snippet", "")), SIGNAL), axis=1)
        high_hits = hits[h_scope & ~h_excl & h_sig].copy()
        high_hits["evidence_class"] = high_hits.apply(evidence_class, axis=1) if not high_hits.empty else []
    else:
        high_hits = pd.DataFrame()
    if high_inv.empty:
        comp = pd.DataFrame()
    else:
        comp = high_inv.groupby("component").agg(
            files=("relative_path", "count"),
            hard_future_hit_files=("hard_future_hit_count", lambda s: int((s > 0).sum())),
            profit_selection_hit_files=("profit_selection_hit_count", lambda s: int((s > 0).sum())),
            medium_arbitration_hit_files=("medium_arbitration_hit_count", lambda s: int((s > 0).sum())),
            safety_hit_files=("safety_hit_count", lambda s: int((s > 0).sum())),
        ).reset_index()
    risk_rows = len(high_hits) if not high_hits.empty else 0
    if not (inputs_ok and upstream_ok):
        status = "GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_TRIAGE_INPUT_REVIEW_REQUIRED_AUDIT_ONLY"
    elif risk_rows > 0:
        status = "GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_RISK_REMAINS_AUDIT_ONLY_LIVE_BLOCKED"
    else:
        status = "GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_NO_OBVIOUS_RISK_AFTER_NOISE_FILTER_AUDIT_ONLY_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["inputs_present", inputs_ok, True, "PASS" if inputs_ok else "FAIL"],
        ["upstream_25c105_ok", upstream_ok, True, "PASS" if upstream_ok else "FAIL"],
        ["high_signal_files", len(high_inv), 0, "REVIEW" if len(high_inv) else "PASS"],
        ["high_signal_suspicious_hits", risk_rows, 0, "REVIEW" if risk_rows else "PASS"],
        ["excluded_noise_files", len(excluded), 0, "INFO"],
        ["corea_medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B106-001", "25C105 inputs", "CLOSED" if inputs_ok and upstream_ok else "OPEN", "HARD", "25C105 outputs must be present."],
        ["B106-002", "high_signal_corea_medium_risk", "OPEN" if risk_rows else "CLOSED", "HARD", "Scoped GOLD V2 CoreA/MEDIUM suspicious hits remain." if risk_rows else "No high-signal rows after noise filter; deeper replay still required before approval."],
        ["B106-003", "CoreA/MEDIUM live evaluator", "OPEN", "HARD", "Live remains blocked until entry-time reproducibility is proven."],
        ["B106-004", "source recovery", "OPEN", "HARD", "No source recovery approval."],
        ["B106-005", "A002", "CLOSED_FOR_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "upstream_25c105_ok": upstream_ok, "inputs_present": inputs_ok, "input_files_total": int(len(inv)) if not inv.empty else 0, "high_signal_files": int(len(high_inv)), "high_signal_suspicious_hits": int(risk_rows), "excluded_noise_files": int(len(excluded)), "corea_medium_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv_inputs.to_csv(out / "25c106_input_inventory.csv", index=False, encoding="utf-8-sig")
    high_inv.drop(columns=[c for c in ["_rel_lower"] if c in high_inv.columns]).to_csv(out / "25c106_high_signal_file_inventory.csv", index=False, encoding="utf-8-sig")
    excluded.drop(columns=[c for c in ["_rel_lower"] if c in excluded.columns]).to_csv(out / "25c106_excluded_noise_inventory.csv", index=False, encoding="utf-8-sig")
    high_hits.drop(columns=[c for c in ["_rel_lower"] if c in high_hits.columns]).to_csv(out / "25c106_high_signal_suspicious_hits.csv", index=False, encoding="utf-8-sig")
    comp.to_csv(out / "25c106_high_signal_component_risk_summary.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c106_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c106_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c106_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C106 scoped CoreA/MEDIUM high-signal triage audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## High-signal component risk summary", md(comp), "", "## High-signal suspicious hits", md(high_hits.drop(columns=[c for c in ["_rel_lower"] if c in high_hits.columns]) if not high_hits.empty else high_hits), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- scoped text/column triage only; no replay", "- absence of high-signal rows is not source recovery approval", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C106_GOLDV2_COREA_MEDIUM_HIGH_SIGNAL_TRIAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
