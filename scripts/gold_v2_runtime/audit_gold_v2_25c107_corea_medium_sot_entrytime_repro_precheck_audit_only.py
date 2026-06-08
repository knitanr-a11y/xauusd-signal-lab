#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C107_COREA_MEDIUM_SOT_ENTRYTIME_REPRO_PRECHECK_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c107_corea_medium_sot_entrytime_repro_precheck_audit_only"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}
SCOPE_TOKENS = ["corea", "core_a", "medium", "arbitration", "final_sot", "selected_source_rows", "source_rows", "frozen_core", "live_evaluator_mapping"]
EXCLUDE = ["docs", "bat", "__pycache__", "25c105", "25c106"]
HARD = ["exit_time", "exit_price", "close_time", "close_price", "outcome", "result", "win", "loss", "tp_hit", "sl_hit", "hit", "mae", "mfe", "duration", "holding", "realized"]
PROFIT = ["profit", "profit_r", "selected_profit", "selected_profit_r", "top_profit", "pnl", "best_profit", "max_profit", "min_profit", "representative_profit"]
SELECT = ["selected", "top_candidate", "top_variant", "top_direction", "best", "rank", "sort", "argmax", "argmin", "arbitration", "final_sot", "priority", "chosen", "prefer"]
ENTRY = ["entry_time", "top_entry_time", "direction", "side", "strategy_id", "dataset", "regime", "range", "ret", "trend", "tr_mean", "count", "feature", "condition", "filter", "score"]


def repo_root() -> Path: return Path(__file__).resolve().parents[2]
def files_root() -> Path:
    r = repo_root(); return r.parents[1] if len(r.parents) >= 2 else r.parent
def fx_outputs() -> Path: return files_root() / "FX_OUTPUTS"
def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME; p.mkdir(parents=True, exist_ok=True); return p

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

def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:500] for c in d.columns) + " |")
    return "\n".join(lines)

def contains_any(s: str, toks: list[str]) -> bool:
    low = str(s).lower()
    return any(t in low for t in toks)

def role_for(path: str) -> str:
    p = path.lower()
    roles = []
    if ("corea" in p or "core_a" in p) and ("source" in p or "selected" in p): roles.append("corea_source_or_selected")
    if ("corea" in p or "core_a" in p) and ("mapping" in p or "frozen" in p): roles.append("corea_mapping_or_frozen")
    if "medium" in p and ("source" in p or "selected" in p): roles.append("medium_source_or_selected")
    if "medium" in p and "final_sot" in p: roles.append("medium_final_sot")
    if "medium" in p and "arbitration" in p: roles.append("medium_arbitration")
    if "medium" in p and ("mapping" in p or "frozen" in p): roles.append("medium_mapping_or_frozen")
    return ";".join(sorted(set(roles))) if roles else "unknown_gold_v2_artifact"

def component_for(path: str) -> str:
    p = path.lower()
    has_a = "corea" in p or "core_a" in p
    has_m = "medium" in p or "arbitration" in p or "final_sot" in p
    if has_a and has_m: return "both_or_unknown"
    if has_a: return "CoreA"
    if has_m: return "MEDIUM"
    return "both_or_unknown"

def flatten_json_keys(obj: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = f"{prefix}.{k}" if prefix else str(k)
            keys.append(nk)
            keys.extend(flatten_json_keys(v, nk))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            keys.extend(flatten_json_keys(v, f"{prefix}[]" if prefix else "[]"))
    return keys

def keys_for_file(p: Path) -> list[str]:
    try:
        if p.suffix.lower() == ".csv":
            return list(pd.read_csv(p, nrows=0).columns)
        if p.suffix.lower() == ".json":
            obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            return flatten_json_keys(obj)
    except Exception:
        return []
    return []

def risk_family(k: str) -> str:
    lk = k.lower()
    if any(t in lk for t in HARD): return "hard_future_or_outcome"
    if any(t in lk for t in PROFIT): return "profit_or_representative"
    if any(t in lk for t in SELECT): return "selection_or_arbitration"
    if any(t in lk for t in ENTRY): return "entry_time_candidate"
    return "other"

def collect_candidates() -> list[Path]:
    bases = [repo_root(), fx_outputs()]
    out: list[Path] = []
    seen = set()
    for base in bases:
        if not base.exists(): continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".csv", ".json"}: continue
            sp = str(p.resolve())
            rel_low = str(p).lower()
            if sp in seen: continue
            if not contains_any(rel_low, ["gold_v2"]): continue
            if not contains_any(rel_low, SCOPE_TOKENS): continue
            if contains_any(rel_low, EXCLUDE): continue
            seen.add(sp); out.append(p)
    return out

def main() -> int:
    created = datetime.now(timezone.utc).isoformat(); out = out_dir()
    candidates = collect_candidates()
    inv_rows, risk_rows = [], []
    for p in candidates:
        rel = str(p.relative_to(repo_root())) if str(p).startswith(str(repo_root())) else str(p)
        keys = keys_for_file(p)
        fams = [risk_family(k) for k in keys]
        role = role_for(rel); comp = component_for(rel)
        inv_rows.append({
            "component": comp,
            "artifact_role": role,
            "path": str(p),
            "relative_path": rel,
            "suffix": p.suffix.lower(),
            "bytes": p.stat().st_size,
            "sha256": sha256_file(p),
            "column_or_key_count": len(keys),
            "hard_future_or_outcome_keys": sum(f == "hard_future_or_outcome" for f in fams),
            "profit_or_representative_keys": sum(f == "profit_or_representative" for f in fams),
            "selection_or_arbitration_keys": sum(f == "selection_or_arbitration" for f in fams),
            "entry_time_candidate_keys": sum(f == "entry_time_candidate" for f in fams),
        })
        for k, fam in zip(keys, fams):
            if fam != "other":
                risk_rows.append({"component": comp, "artifact_role": role, "relative_path": rel, "column_or_key": k, "risk_family": fam})
    inv = pd.DataFrame(inv_rows)
    risks = pd.DataFrame(risk_rows)
    if inv.empty:
        status = "COREA_MEDIUM_SOT_PRECHECK_NO_ARTIFACTS_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
        comp = pd.DataFrame()
    else:
        high = inv[(inv["hard_future_or_outcome_keys"] > 0) | (inv["profit_or_representative_keys"] > 0) | (inv["selection_or_arbitration_keys"] > 0)].copy()
        comp = inv.groupby(["component", "artifact_role"]).agg(
            artifacts=("relative_path", "count"),
            hard_future_artifacts=("hard_future_or_outcome_keys", lambda s: int((s > 0).sum())),
            profit_artifacts=("profit_or_representative_keys", lambda s: int((s > 0).sum())),
            selection_artifacts=("selection_or_arbitration_keys", lambda s: int((s > 0).sum())),
            entry_candidate_artifacts=("entry_time_candidate_keys", lambda s: int((s > 0).sum())),
        ).reset_index()
        status = "COREA_MEDIUM_SOT_PRECHECK_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED" if len(high) else "COREA_MEDIUM_SOT_PRECHECK_NO_OBVIOUS_ARTIFACT_RISK_AUDIT_ONLY_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["candidate_artifacts_found", len(inv), ">0", "PASS" if len(inv) else "FAIL"],
        ["hard_future_or_outcome_artifacts", 0 if inv.empty else int((inv["hard_future_or_outcome_keys"] > 0).sum()), 0, "REVIEW" if (not inv.empty and int((inv["hard_future_or_outcome_keys"] > 0).sum())) else "PASS"],
        ["profit_or_representative_artifacts", 0 if inv.empty else int((inv["profit_or_representative_keys"] > 0).sum()), 0, "REVIEW" if (not inv.empty and int((inv["profit_or_representative_keys"] > 0).sum())) else "PASS"],
        ["selection_or_arbitration_artifacts", 0 if inv.empty else int((inv["selection_or_arbitration_keys"] > 0).sum()), 0, "REVIEW" if (not inv.empty and int((inv["selection_or_arbitration_keys"] > 0).sum())) else "PASS"],
        ["corea_medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B107-001", "candidate SOT/final/selected artifacts", "CLOSED" if len(inv) else "OPEN", "HARD", "Candidate artifacts found." if len(inv) else "No candidate artifacts found."],
        ["B107-002", "future/profit/selection column risk", "OPEN" if status == "COREA_MEDIUM_SOT_PRECHECK_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED" else "CLOSED", "HARD", "SOT/final/selected artifacts contain risky columns; deeper entry-time replay required."],
        ["B107-003", "CoreA/MEDIUM live evaluator", "OPEN", "HARD", "Live remains blocked until entry-time reproducibility is proven."],
        ["B107-004", "source recovery", "OPEN", "HARD", "No source recovery approval."],
        ["B107-005", "A002", "CLOSED_FOR_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {"created_utc": created, "step": STEP, "status": status, "audit_only": True, "source_recovery_approved": False, "candidate_artifacts_found": int(len(inv)), "risk_rows": int(len(risks)), "hard_future_or_outcome_artifacts": 0 if inv.empty else int((inv["hard_future_or_outcome_keys"] > 0).sum()), "profit_or_representative_artifacts": 0 if inv.empty else int((inv["profit_or_representative_keys"] > 0).sum()), "selection_or_arbitration_artifacts": 0 if inv.empty else int((inv["selection_or_arbitration_keys"] > 0).sum()), "corea_medium_live_evaluator_allowed": False, "final_signal_allowed": False, "a002_used": False, "external_actions": ACTIONS}
    inv.to_csv(out / "25c107_artifact_inventory.csv", index=False, encoding="utf-8-sig")
    risks.to_csv(out / "25c107_column_key_risk_rows.csv", index=False, encoding="utf-8-sig")
    comp.to_csv(out / "25c107_component_artifact_risk_summary.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c107_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c107_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c107_summary.json", summary)
    report = "\n".join(["# GOLD V2 25C107 CoreA/MEDIUM SOT entry-time reproducibility precheck audit-only report", "", f"Created UTC: {created}", f"Status: `{status}`", "", "## Decision matrix", md(decision), "", "## Component artifact risk summary", md(comp), "", "## Column/key risk rows", md(risks), "", "## Blockers", md(blockers), "", "## Safety", "- audit_only: true", "- artifact-column precheck only; no OHLC replay", "- absence of risky columns is not source recovery approval", "- A002 not used", "- source recovery not approved", "- live evaluator/final signal/external actions remain OFF", "- NO_SIGNAL must not notify Discord"])
    (out / "GOLD_V2_25C107_COREA_MEDIUM_SOT_ENTRYTIME_REPRO_PRECHECK_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
