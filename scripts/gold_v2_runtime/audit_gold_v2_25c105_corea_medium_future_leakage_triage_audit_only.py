#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib, json, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

STEP = "25C105_COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_AUDIT_ONLY"
OUT_NAME = "gold_v2_25c105_corea_medium_future_leakage_triage_audit_only"
ACTIONS = {"discord_send_allowed": False, "mt5_order_allowed": False, "ai_api_allowed": False, "live_hook_allowed": False, "live_evaluator_allowed": False, "final_signal_allowed": False}

COMPONENT_PATTERNS = {
    "CoreA": ["corea", "core_a", "core-a", "frozen_corea", "frozen_corea", "frozen_coreA"],
    "MEDIUM": ["medium", "arbitration", "frozen_medium"],
}
HARD_FUTURE = ["exit_time", "exit_price", "close_time", "close_price", "future", "lookahead", "leakage", "outcome", "result", "win", "loss", "hit", "tp_hit", "sl_hit", "mae", "mfe", "duration", "holding"]
PROFIT_SELECTION = ["profit", "profit_r", "top_profit", "realized", "pnl", "best", "max_profit", "min_profit", "selected", "top_candidate", "representative", "rank", "sort", "argmax", "argmin"]
MEDIUM_ARB = ["arbitration", "final_sot", "final_signal", "choose", "chosen", "prefer", "priority", "tie_break", "compare"]
SAFETY = ["audit_only", "live_blocked", "source_recovery_approved", "live_evaluator_allowed", "final_signal_allowed"]
EXTS = {".py", ".md", ".json", ".csv", ".txt", ".bat"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def files_root() -> Path:
    r = repo_root()
    return r.parents[1] if len(r.parents) >= 2 else r.parent

def fx_outputs() -> Path:
    return files_root() / "FX_OUTPUTS"

def out_dir() -> Path:
    p = fx_outputs() / OUT_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def clean(obj: Any) -> Any:
    if isinstance(obj, dict): return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, list): return [clean(v) for v in obj]
    try:
        if pd.isna(obj): return None
    except Exception:
        pass
    return obj.isoformat() if hasattr(obj, "isoformat") else obj

def write_json(p: Path, obj: dict[str, Any]) -> None:
    p.write_text(json.dumps(clean(obj), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

def md(df: pd.DataFrame, n: int = 80) -> str:
    if df.empty: return "_No rows._"
    d = df.head(n).fillna("")
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]).replace("|", "\\|").replace("\n", " ")[:500] for c in d.columns) + " |")
    return "\n".join(lines)

def component_for(text: str) -> str:
    low = text.lower()
    has_corea = any(p.lower() in low for p in COMPONENT_PATTERNS["CoreA"])
    has_medium = any(p.lower() in low for p in COMPONENT_PATTERNS["MEDIUM"])
    if has_corea and has_medium: return "both_or_unknown"
    if has_corea: return "CoreA"
    if has_medium: return "MEDIUM"
    return "none"

def scan_text(text: str) -> dict[str, list[str]]:
    low = text.lower()
    def hits(tokens: list[str]) -> list[str]:
        return sorted({t for t in tokens if t.lower() in low})
    return {
        "hard_future_hits": hits(HARD_FUTURE),
        "profit_selection_hits": hits(PROFIT_SELECTION),
        "medium_arbitration_hits": hits(MEDIUM_ARB),
        "safety_hits": hits(SAFETY),
    }

def safe_read(p: Path, max_bytes: int = 2_000_000) -> str:
    try:
        if p.stat().st_size > max_bytes:
            data = p.open("rb").read(max_bytes)
            return data.decode("utf-8", errors="ignore")
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def collect_files() -> list[Path]:
    bases = [repo_root(), fx_outputs()]
    files: list[Path] = []
    seen = set()
    for base in bases:
        if not base.exists(): continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXTS: continue
            sp = str(p.resolve())
            if sp in seen: continue
            seen.add(sp); files.append(p)
    return files

def main() -> int:
    created = datetime.now(timezone.utc).isoformat()
    out = out_dir()
    inv_rows, hit_rows = [], []
    files = collect_files()
    for p in files:
        rel = str(p.relative_to(repo_root())) if str(p).startswith(str(repo_root())) else str(p)
        path_comp = component_for(rel)
        text = safe_read(p)
        content_comp = component_for(text[:200000])
        comp = path_comp if path_comp != "none" else content_comp
        if comp == "none":
            continue
        scan = scan_text(rel + "\n" + text)
        row = {
            "component": comp,
            "path": str(p),
            "relative_path": rel,
            "suffix": p.suffix.lower(),
            "bytes": p.stat().st_size,
            "sha256": sha256_file(p),
            "hard_future_hit_count": len(scan["hard_future_hits"]),
            "profit_selection_hit_count": len(scan["profit_selection_hits"]),
            "medium_arbitration_hit_count": len(scan["medium_arbitration_hits"]),
            "safety_hit_count": len(scan["safety_hits"]),
            "hard_future_hits": ";".join(scan["hard_future_hits"]),
            "profit_selection_hits": ";".join(scan["profit_selection_hits"]),
            "medium_arbitration_hits": ";".join(scan["medium_arbitration_hits"]),
            "safety_hits": ";".join(scan["safety_hits"]),
        }
        inv_rows.append(row)
        if row["hard_future_hit_count"] or row["profit_selection_hit_count"] or row["medium_arbitration_hit_count"]:
            # capture compact snippets for top hits only
            low = text.lower()
            toks = scan["hard_future_hits"] + scan["profit_selection_hits"] + scan["medium_arbitration_hits"]
            for tok in toks[:20]:
                idx = low.find(tok.lower())
                snippet = text[max(0, idx-120):idx+180].replace("\r", " ").replace("\n", " ") if idx >= 0 else ""
                hit_rows.append({"component": comp, "relative_path": rel, "token": tok, "snippet": snippet})
    inv = pd.DataFrame(inv_rows)
    hits = pd.DataFrame(hit_rows)
    if inv.empty:
        status = "COREA_MEDIUM_TRIAGE_NO_SOURCE_FILES_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
        comp_summary = pd.DataFrame()
    else:
        comp_summary = inv.groupby("component").agg(
            files=("relative_path", "count"),
            hard_future_hit_files=("hard_future_hit_count", lambda s: int((s > 0).sum())),
            profit_selection_hit_files=("profit_selection_hit_count", lambda s: int((s > 0).sum())),
            medium_arbitration_hit_files=("medium_arbitration_hit_count", lambda s: int((s > 0).sum())),
            safety_hit_files=("safety_hit_count", lambda s: int((s > 0).sum())),
        ).reset_index()
        risk = int((inv["hard_future_hit_count"] > 0).sum() + (inv["profit_selection_hit_count"] > 0).sum() + (inv["medium_arbitration_hit_count"] > 0).sum())
        status = "COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED" if risk else "COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_NO_OBVIOUS_RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED"
    decision = pd.DataFrame([
        ["corea_medium_files_found", 0 if inv.empty else len(inv), ">0", "PASS" if not inv.empty else "FAIL"],
        ["hard_future_hit_files", 0 if inv.empty else int((inv["hard_future_hit_count"] > 0).sum()), 0, "REVIEW" if (not inv.empty and int((inv["hard_future_hit_count"] > 0).sum()) > 0) else "PASS"],
        ["profit_selection_hit_files", 0 if inv.empty else int((inv["profit_selection_hit_count"] > 0).sum()), 0, "REVIEW" if (not inv.empty and int((inv["profit_selection_hit_count"] > 0).sum()) > 0) else "PASS"],
        ["medium_arbitration_hit_files", 0 if inv.empty else int((inv["medium_arbitration_hit_count"] > 0).sum()), 0, "REVIEW" if (not inv.empty and int((inv["medium_arbitration_hit_count"] > 0).sum()) > 0) else "PASS"],
        ["coreb_live_evaluator_allowed", False, False, "PASS"],
        ["corea_medium_live_evaluator_allowed", False, False, "PASS"],
        ["final_signal_allowed", False, False, "PASS"],
        ["source_recovery_approved", False, False, "PASS"],
        ["a002_used", False, False, "PASS"],
    ], columns=["decision_item", "observed", "required", "status"])
    blockers = pd.DataFrame([
        ["B105-001", "CoreA/MEDIUM source triage", "OPEN" if inv.empty else "REVIEW", "HARD", "No files found." if inv.empty else "Files found; suspicious hits require human review."],
        ["B105-002", "future/outcome/profit-selection tokens", "OPEN" if status.endswith("RISK_FOUND_AUDIT_ONLY_LIVE_BLOCKED") else "CLOSED", "HARD", "Text/column triage found suspicious tokens; deeper replay/provenance audit required."],
        ["B105-003", "CoreA/MEDIUM live evaluator", "OPEN", "HARD", "Live remains blocked until entry-time reproducibility is proven."],
        ["B105-004", "source recovery", "OPEN", "HARD", "No source recovery approval."],
        ["B105-005", "A002", "CLOSED_FOR_MAIN_PATH", "INFO", "A002 is auxiliary-only and not used."],
    ], columns=["blocker_id", "component", "status", "severity", "detail"])
    summary = {
        "created_utc": created,
        "step": STEP,
        "status": status,
        "audit_only": True,
        "source_recovery_approved": False,
        "files_scanned_total": len(files),
        "corea_medium_files_found": 0 if inv.empty else int(len(inv)),
        "hard_future_hit_files": 0 if inv.empty else int((inv["hard_future_hit_count"] > 0).sum()),
        "profit_selection_hit_files": 0 if inv.empty else int((inv["profit_selection_hit_count"] > 0).sum()),
        "medium_arbitration_hit_files": 0 if inv.empty else int((inv["medium_arbitration_hit_count"] > 0).sum()),
        "corea_medium_live_evaluator_allowed": False,
        "final_signal_allowed": False,
        "a002_used": False,
        "external_actions": ACTIONS,
    }
    inv.to_csv(out / "25c105_file_inventory.csv", index=False, encoding="utf-8-sig")
    hits.to_csv(out / "25c105_suspicious_file_hits.csv", index=False, encoding="utf-8-sig")
    comp_summary.to_csv(out / "25c105_component_risk_summary.csv", index=False, encoding="utf-8-sig")
    decision.to_csv(out / "25c105_decision_matrix.csv", index=False, encoding="utf-8-sig")
    blockers.to_csv(out / "25c105_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    write_json(out / "25c105_summary.json", summary)
    report = "\n".join([
        "# GOLD V2 25C105 CoreA/MEDIUM future leakage triage audit-only report",
        "", f"Created UTC: {created}", f"Status: `{status}`", "",
        "## Decision matrix", md(decision), "",
        "## Component risk summary", md(comp_summary), "",
        "## Suspicious hits", md(hits), "",
        "## Blockers", md(blockers), "",
        "## Safety",
        "- audit_only: true",
        "- text/column triage only; no full replay",
        "- absence of tokens is not source recovery approval",
        "- A002 not used",
        "- source recovery not approved",
        "- live evaluator/final signal/external actions remain OFF",
        "- NO_SIGNAL must not notify Discord",
    ])
    (out / "GOLD_V2_25C105_COREA_MEDIUM_FUTURE_LEAKAGE_TRIAGE_AUDIT_ONLY_REPORT.md").write_text(report, encoding="utf-8")
    zip_path = fx_outputs() / f"{OUT_NAME}.zip"
    if zip_path.exists(): zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in out.iterdir(): z.write(p, arcname=p.name)
    print(json.dumps({"status": status, "output_dir": str(out), "zip": str(zip_path)}, ensure_ascii=False, indent=2))
    print("No Discord, MT5, AI API, live hook, live evaluator, or final signal action was performed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
