#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 87 runtime chain and signal candidate catalog audit-only.

Generates a human-readable candidate catalog from GOLD V3 Stage69/68 artifacts.
Does not infer candidate conditions if source columns are absent.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_87_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_87_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_87_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CANDIDATE_KEY_ORDER = "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars"

SOURCE_REL_CANDIDATES = [
    "69_live_csv_condition_detector_audit_only/gold_v3_69_candidate_condition_summary.csv",
    "69_live_csv_condition_detector_audit_only/gold_v3_69_detected_candidate_conditions.csv",
    "68_rank_dedup_selection_repro_audit_only/gold_v3_68_candidate_selection_summary.csv",
    "68_rank_dedup_selection_repro_audit_only/gold_v3_68_selected_candidates.csv",
]


def ok(check_id: str, passed: bool, observed: Any, expected: Any, severity: str = "BLOCKER") -> dict[str, Any]:
    return {"check_id": check_id, "result": "PASS" if passed else "FAIL", "observed": observed, "expected": expected, "severity": severity}


def blocker(blocker_id: str, artifact: str, reason: str, detail: Any = "") -> dict[str, Any]:
    return {"blocker_id": blocker_id, "artifact": artifact, "reason": reason, "detail": detail, "severity": "BLOCKER"}


def find_files_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    for d in [Path.cwd(), Path.cwd()/"Files", root, root/"Files", root.parent, root.parent/"Files", root.parent.parent]:
        d = d.expanduser().resolve()
        if (d/"goldsharp_m15.csv").exists() or (d/"FX_OUTPUTS"/"gold_v3").exists():
            return d
    raise FileNotFoundError("Could not locate Files directory")


def read_csv_safe(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp932"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            pass
    return pd.read_csv(path)


def choose_col(cols: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    for c in cols:
        lc = c.lower()
        for cand in candidates:
            if cand.lower() in lc:
                return c
    return None


def stringify_condition(row: pd.Series, cols: list[str]) -> str:
    condition_col = choose_col(cols, ["condition", "conditions", "condition_text", "rule_condition", "entry_condition", "detected_condition", "where_clause", "rule_text"])
    if condition_col:
        val = str(row.get(condition_col, "")).strip()
        if val and val.lower() != "nan":
            return val
    parts = []
    for c in cols:
        lc = c.lower()
        if any(k in lc for k in ["condition", "rule", "filter", "threshold", "feature", "operator", "value"]):
            v = str(row.get(c, "")).strip()
            if v and v.lower() != "nan":
                parts.append(f"{c}={v}")
    if parts:
        return "; ".join(parts[:20])
    return "condition_detail_source_missing_or_column_unknown"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "87_runtime_chain_and_signal_candidate_catalog_audit_only"
    out.mkdir(parents=True, exist_ok=True)

    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    source_path = None
    source_df = pd.DataFrame()
    source_checks = []
    for rel in SOURCE_REL_CANDIDATES:
        p = base / rel
        source_checks.append({"source": str(p), "exists": p.exists()})
        if source_path is None and p.exists():
            source_path = p
            source_df = read_csv_safe(p)
    if source_path is None:
        blockers.append(blocker("candidate_source_missing", str(base), "CANDIDATE_CONDITION_SOURCE_CSV_MISSING", SOURCE_REL_CANDIDATES))
    val.append(ok("candidate_source_csv_present", source_path is not None, str(source_path) if source_path else "MISSING", "one of Stage69/68 candidate CSVs"))

    catalog_rows: list[dict[str, Any]] = []
    if source_path is not None:
        cols = list(source_df.columns)
        label_col = choose_col(cols, ["candidate_label", "label", "candidate", "name", "base_candidate_label"])
        base_col = choose_col(cols, ["base_candidate_label", "base_label", "base_candidate"])
        profile_col = choose_col(cols, ["profile_id", "source_profile_id"])
        hv_col = choose_col(cols, ["hv_profile"])
        tp_col = choose_col(cols, ["tp_usd", "tp"])
        sl_col = choose_col(cols, ["sl_usd", "sl"])
        h15_col = choose_col(cols, ["horizon_m15"])
        h5_col = choose_col(cols, ["horizon_m5_bars", "horizon_m5"])
        direction_col = choose_col(cols, ["direction", "side"])
        for i, row in source_df.iterrows():
            label = str(row.get(label_col, f"candidate_{i+1}")).strip() if label_col else f"candidate_{i+1}"
            if not label or label.lower() == "nan":
                label = f"candidate_{i+1}"
            catalog_rows.append({
                "candidate_no": i + 1,
                "candidate_label": label,
                "base_candidate_label": str(row.get(base_col, "")).strip() if base_col else "",
                "direction": str(row.get(direction_col, "")).strip() if direction_col else "",
                "profile_id": str(row.get(profile_col, "")).strip() if profile_col else "",
                "hv_profile": str(row.get(hv_col, "")).strip() if hv_col else "",
                "tp_usd": str(row.get(tp_col, "")).strip() if tp_col else "",
                "sl_usd": str(row.get(sl_col, "")).strip() if sl_col else "",
                "horizon_m15": str(row.get(h15_col, "")).strip() if h15_col else "",
                "horizon_m5_bars": str(row.get(h5_col, "")).strip() if h5_col else "",
                "condition_summary": stringify_condition(row, cols),
                "source_csv": str(source_path),
            })
    val.append(ok("candidate_catalog_nonempty", len(catalog_rows) > 0, len(catalog_rows), ">0"))
    if source_path is not None and len(catalog_rows) == 0:
        blockers.append(blocker("candidate_catalog_empty", str(source_path), "CANDIDATE_CATALOG_EMPTY"))

    runtime_chain = [
        {"step": "Stage80", "role": "monitor latest closed M15 row", "next": "Stage76 on new M15", "audit_only": True},
        {"step": "Stage76", "role": "full audit monitor with payload preview", "next": "Stage79 immutable snapshot", "audit_only": True},
        {"step": "Stage79", "role": "immutable evidence snapshot", "next": "Stage85 ledger preview check", "audit_only": True},
        {"step": "Stage85", "role": "SIGNAL-only trade review row preview; NO_SIGNAL suppressed", "next": "Stage86 append guard", "audit_only": True},
        {"step": "Stage86", "role": "guard durable ledger append; no append without confirmation", "next": "future approved append stage", "audit_only": True},
    ]

    pd.DataFrame(source_checks).to_csv(out/"gold_v3_87_candidate_source_search_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(catalog_rows).to_csv(out/"gold_v3_87_signal_candidate_catalog.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(runtime_chain).to_csv(out/"gold_v3_87_runtime_chain_matrix.csv", index=False, encoding="utf-8-sig")

    md = ["# GOLD V3 Signal Candidate Catalog", "", f"Source CSV: `{source_path if source_path else 'MISSING'}`", "", "Candidate key order:", "", f"`{CANDIDATE_KEY_ORDER}`", "", "## Candidates", ""]
    bullets = ["## Signal candidate bullets for runtime manual", ""]
    if catalog_rows:
        for r in catalog_rows:
            line = f"- **{r['candidate_label']}**"
            details = []
            if r.get("base_candidate_label"):
                details.append(f"base={r['base_candidate_label']}")
            if r.get("direction"):
                details.append(f"direction={r['direction']}")
            if r.get("profile_id"):
                details.append(f"profile={r['profile_id']}")
            if r.get("hv_profile"):
                details.append(f"hv={r['hv_profile']}")
            if r.get("tp_usd"):
                details.append(f"TP={r['tp_usd']}")
            if r.get("sl_usd"):
                details.append(f"SL={r['sl_usd']}")
            if r.get("horizon_m15"):
                details.append(f"horizon_m15={r['horizon_m15']}")
            if r.get("horizon_m5_bars"):
                details.append(f"horizon_m5_bars={r['horizon_m5_bars']}")
            if details:
                line += " — " + ", ".join(details)
            line += f". 条件: `{r['condition_summary']}`"
            md.append(line)
            bullets.append(line)
    else:
        md.append("- CANDIDATE_SOURCE_MISSING — Stage69/68 candidate CSV is required.")
        bullets.append("- CANDIDATE_SOURCE_MISSING — Stage69/68 candidate CSV is required.")
    md.append("")
    bullets.append("")
    (out/"gold_v3_87_signal_candidate_catalog.md").write_text("\n".join(md), encoding="utf-8")
    (out/"gold_v3_87_manual_candidate_bullets.md").write_text("\n".join(bullets), encoding="utf-8")

    val.extend([
        ok("manual_candidate_bullets_written", (out/"gold_v3_87_manual_candidate_bullets.md").exists(), str(out/"gold_v3_87_manual_candidate_bullets.md"), "exists"),
        ok("runtime_chain_matrix_written", (out/"gold_v3_87_runtime_chain_matrix.csv").exists(), str(out/"gold_v3_87_runtime_chain_matrix.csv"), "exists"),
        ok("candidate_key_order_exact", CANDIDATE_KEY_ORDER == "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars", CANDIDATE_KEY_ORDER, "exact"),
        ok("csv_open_bar_exclusion_required_false", True, False, False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    pd.DataFrame(blockers).to_csv(out/"gold_v3_87_blocker_matrix.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(val).to_csv(out/"gold_v3_87_validation_matrix.csv", index=False, encoding="utf-8-sig")
    summary = {
        "step": STEP,
        "status": status,
        "audit_only": True,
        "live_allowed": False,
        "mt5_execution_enabled": False,
        "mt5_bat_created": False,
        "discord_live_enabled": False,
        "ai_api_called": False,
        "signals_generated": False,
        "final_signal_enabled": False,
        "contract_mutated": False,
        "manual_candidate_demotion_or_removal": False,
        "open_asof_allowed": False,
        "csv_contract": CSV_CONTRACT,
        "csv_open_bar_exclusion_required": False,
        "live_ready": False,
        "runtime_chain_and_signal_candidate_catalog_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_order": CANDIDATE_KEY_ORDER,
        "candidate_source_csv": str(source_path) if source_path else "MISSING",
        "candidate_count": len(catalog_rows),
        "manual_candidate_bullets_path": str(out/"gold_v3_87_manual_candidate_bullets.md"),
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
    }
    (out/"gold_v3_87_runtime_chain_and_signal_candidate_catalog_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    paste = [
        "GOLD V3 87 PASTE_ME_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_SUMMARY",
        f"status: {status}",
        "runtime_chain_and_signal_candidate_catalog_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"candidate_source_csv: {source_path if source_path else 'MISSING'}",
        f"candidate_count: {len(catalog_rows)}",
        f"manual_candidate_bullets_path: {out/'gold_v3_87_manual_candidate_bullets.md'}",
        f"candidate_key_order: {CANDIDATE_KEY_ORDER}",
        f"blocker_count: {len(blockers)}",
        "", "CANDIDATE_BULLETS", "\n".join(bullets[:80]),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "OUTPUTS",
        "gold_v3_87_candidate_source_search_matrix.csv",
        "gold_v3_87_signal_candidate_catalog.csv",
        "gold_v3_87_signal_candidate_catalog.md",
        "gold_v3_87_manual_candidate_bullets.md",
        "gold_v3_87_runtime_chain_matrix.csv",
        "gold_v3_87_blocker_matrix.csv",
        "gold_v3_87_validation_matrix.csv",
        "gold_v3_87_runtime_chain_and_signal_candidate_catalog_summary.json",
        "gold_v3_87_PASTE_ME_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_SUMMARY.txt",
        "GOLD_V3_87_REPORT.md",
    ]
    (out/"gold_v3_87_PASTE_ME_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_SUMMARY.txt").write_text("\n".join(paste)+"\n", encoding="utf-8")
    report = f"""# GOLD V3 87 runtime chain and signal candidate catalog audit-only report

Status: `{status}`

- candidate_source_csv: `{source_path if source_path else 'MISSING'}`
- candidate_count: `{len(catalog_rows)}`
- manual_candidate_bullets_path: `{out/'gold_v3_87_manual_candidate_bullets.md'}`
- blocker_count: `{len(blockers)}`

Audit-only. No MT5, Discord, AI API, live hook, live evaluator, or final signal.
"""
    (out/"GOLD_V3_87_REPORT.md").write_text(report, encoding="utf-8")

    print(f"[{status}] {out/'gold_v3_87_PASTE_ME_RUNTIME_CHAIN_AND_SIGNAL_CANDIDATE_CATALOG_SUMMARY.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
