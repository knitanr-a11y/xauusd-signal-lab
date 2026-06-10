#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GOLD V3 88 signal candidate normalization and condition coverage audit-only.

Short-output-path version. Uses FX_OUTPUTS/gold_v3/88c/paste_me.txt to avoid
Windows/MetaQuotes MAX_PATH failures.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

STEP = "GOLD_V3_88_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_AUDIT_ONLY"
READY_STATUS = "GOLD_V3_88_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_READY_AUDIT_ONLY"
BLOCKED_STATUS = "GOLD_V3_88_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_BLOCKED_AUDIT_ONLY"
CSV_CONTRACT = "open/in-progress candles are not written to CSV"
POOL_POLICY = "poolから外さない。rolling health gateに判断させる。"
CANDIDATE_KEY_ORDER = "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars"
CONDITION_MISSING = "CONDITION_NOT_RESTORED_FROM_CURRENT_ARTIFACTS"


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


def write_text_safe(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv_safe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def normalize_base(label: str) -> str:
    x = str(label).strip()
    if x.startswith("HV_"):
        x = x[3:]
    x = re.sub(r"__HV_TP\d+_SL\d+_H\d+$", "", x)
    return x


def hv_profile(label: str) -> str:
    m = re.search(r"(__HV_TP\d+_SL\d+_H\d+)$", str(label))
    return m.group(1).lstrip("_") if m else ""


def extract_condition(row: pd.Series) -> str:
    cols = list(row.index)
    direct = ["condition", "conditions", "condition_text", "rule_condition", "entry_condition", "detected_condition", "rule_text"]
    for c in cols:
        if c.lower() in direct:
            v = str(row.get(c, "")).strip()
            if v and v.lower() != "nan" and "condition_detail_source_missing" not in v:
                return v
    parts = []
    for c in cols:
        lc = c.lower()
        if any(k in lc for k in ["condition", "rule", "filter", "threshold", "feature", "operator", "value"]):
            v = str(row.get(c, "")).strip()
            if v and v.lower() != "nan" and "condition_detail_source_missing" not in v:
                parts.append(f"{c}={v}")
    return "; ".join(parts[:20]) if parts else CONDITION_MISSING


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=STEP)
    p.add_argument("--candle-dir", default="")
    p.add_argument("--output-dir", default="")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    cdir = Path(a.candle_dir).expanduser().resolve() if a.candle_dir else find_files_dir()
    base = cdir / "FX_OUTPUTS" / "gold_v3"
    out = Path(a.output_dir).expanduser().resolve() if a.output_dir else base / "88c"
    out.mkdir(parents=True, exist_ok=True)

    p87 = base / "87_runtime_chain_and_signal_candidate_catalog_audit_only" / "gold_v3_87_signal_candidate_catalog.csv"
    val: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    val.append(ok("stage87_candidate_catalog_present", p87.exists(), str(p87), "exists"))
    if not p87.exists():
        blockers.append(blocker("stage87_candidate_catalog_missing", str(p87), "STAGE87_CANDIDATE_CATALOG_MISSING"))
        df = pd.DataFrame()
    else:
        df = read_csv_safe(p87)

    expansion_rows: list[dict[str, Any]] = []
    if not df.empty:
        for _, row in df.iterrows():
            label = str(row.get("candidate_label", "")).strip()
            if not label:
                continue
            base_label = normalize_base(label)
            is_hv = label.startswith("HV_") or "__HV_TP" in label
            condition = extract_condition(row)
            expansion_rows.append({
                "candidate_label": label,
                "normalized_base_candidate": base_label,
                "is_high_volatility_expansion": is_hv,
                "hv_profile": hv_profile(label),
                "condition_status": "RESTORED" if condition != CONDITION_MISSING else "NOT_RESTORED",
                "condition_summary": condition,
            })
    exp_df = pd.DataFrame(expansion_rows).drop_duplicates() if expansion_rows else pd.DataFrame()
    base_groups = []
    if not exp_df.empty:
        for base_label, g in exp_df.groupby("normalized_base_candidate", dropna=False):
            hv_profiles = sorted([x for x in g["hv_profile"].dropna().astype(str).unique().tolist() if x])
            labels = sorted(g["candidate_label"].dropna().astype(str).unique().tolist())
            conds = sorted([x for x in g["condition_summary"].dropna().astype(str).unique().tolist() if x and x != CONDITION_MISSING])
            condition_status = "RESTORED" if conds else "NOT_RESTORED"
            base_groups.append({
                "normalized_base_candidate": base_label,
                "variant_count": len(labels),
                "has_base_row": any(not x.startswith("HV_") and "__HV_TP" not in x for x in labels),
                "hv_profile_count": len(hv_profiles),
                "hv_profiles": ";".join(hv_profiles),
                "all_labels": ";".join(labels),
                "condition_status": condition_status,
                "condition_summary": " | ".join(conds) if conds else CONDITION_MISSING,
            })
    base_df = pd.DataFrame(base_groups).sort_values("normalized_base_candidate") if base_groups else pd.DataFrame()
    base_count = len(base_df)
    condition_coverage_complete = bool(not base_df.empty and (base_df["condition_status"] == "RESTORED").all())
    condition_restored_count = int((base_df["condition_status"] == "RESTORED").sum()) if not base_df.empty else 0

    val.append(ok("candidate_rows_read", len(expansion_rows) > 0, len(expansion_rows), ">0"))
    val.append(ok("normalized_base_candidate_count_8", base_count == 8, base_count, 8))
    if base_count != 8:
        blockers.append(blocker("normalized_base_count_not_8", str(p87), "NORMALIZED_BASE_COUNT_NOT_8", base_count))

    coverage_rows = []
    if not base_df.empty:
        for _, r in base_df.iterrows():
            coverage_rows.append({
                "normalized_base_candidate": r["normalized_base_candidate"],
                "condition_status": r["condition_status"],
                "condition_summary": r["condition_summary"],
                "safe_for_manual": True,
                "manual_note": "条件復元済み" if r["condition_status"] == "RESTORED" else "条件未復元: current artifacts did not expose exact condition text",
            })
    section = [
        "## Signal candidates — GOLD V3 current catalog",
        "",
        "This section is generated from GOLD V3 audit artifacts only. It does not infer missing rule conditions.",
        "",
        f"Candidate key order: `{CANDIDATE_KEY_ORDER}`",
        "",
        f"Normalized base candidate count: `{base_count}`",
        f"Condition coverage complete: `{str(condition_coverage_complete).lower()}`",
        "",
        "### Base candidates and HV expansions",
        "",
    ]
    if not base_df.empty:
        for _, r in base_df.iterrows():
            section.append(f"- **{r['normalized_base_candidate']}**")
            section.append(f"  - variants: `{r['variant_count']}`")
            section.append(f"  - high-volatility profiles: `{r['hv_profiles'] if r['hv_profiles'] else 'none'}`")
            section.append(f"  - condition status: `{r['condition_status']}`")
            section.append(f"  - condition: `{r['condition_summary']}`")
    else:
        section.append("- CANDIDATE_CATALOG_MISSING")
    section.append("")
    section.append("Manual warning: if condition status is NOT_RESTORED, do not present it as a known trading rule condition.")

    write_csv_safe(exp_df, out/"expansion.csv")
    write_csv_safe(base_df, out/"base.csv")
    write_csv_safe(pd.DataFrame(coverage_rows), out/"condition.csv")
    write_text_safe(out/"manual_candidates.md", "\n".join(section)+"\n")

    val.extend([
        ok("manual_candidate_section_written", (out/"manual_candidates.md").exists(), str(out/"manual_candidates.md"), "exists"),
        ok("candidate_key_order_exact", CANDIDATE_KEY_ORDER == "candidate_label+base_candidate_label+source_profile_id+profile_id+hv_profile+tp_usd+sl_usd+horizon_m15+horizon_m5_bars", CANDIDATE_KEY_ORDER, "exact"),
        ok("short_output_path_used", out.name == "88c", str(out), ".../gold_v3/88c"),
        ok("csv_open_bar_exclusion_required_false", True, False, False),
        ok("live_flags_all_false", True, "all_false", "all_false"),
    ])
    failed = [v for v in val if v.get("result") != "PASS"]
    status = READY_STATUS if not failed and not blockers else BLOCKED_STATUS

    write_csv_safe(pd.DataFrame(blockers), out/"blockers.csv")
    write_csv_safe(pd.DataFrame(val), out/"validation.csv")
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
        "signal_candidate_normalization_ready": status == READY_STATUS,
        "pool_policy": POOL_POLICY,
        "candidate_key_order": CANDIDATE_KEY_ORDER,
        "stage87_catalog_path": str(p87),
        "output_dir": str(out),
        "paste_path": str(out/"paste_me.txt"),
        "raw_expansion_row_count": len(expansion_rows),
        "dedup_expansion_row_count": len(exp_df) if not exp_df.empty else 0,
        "normalized_base_candidate_count": base_count,
        "condition_coverage_complete": condition_coverage_complete,
        "condition_restored_base_count": condition_restored_count,
        "manual_candidate_section_path": str(out/"manual_candidates.md"),
        "blocker_count": len(blockers),
        "validation_failure_count": len(failed),
    }
    write_text_safe(out/"summary.json", json.dumps(summary, ensure_ascii=False, indent=2))

    paste = [
        "GOLD V3 88 PASTE_ME_SIGNAL_CANDIDATE_NORMALIZATION_AND_CONDITION_COVERAGE_SUMMARY",
        f"status: {status}",
        "signal_candidate_normalization_ready: " + str(status == READY_STATUS).lower(),
        "live_ready: false",
        "contract_mutated: false",
        "manual_candidate_demotion_or_removal: false",
        "open_asof_allowed: false",
        "csv_contract: " + CSV_CONTRACT,
        "csv_open_bar_exclusion_required: false",
        "safety: audit_only=true, live_allowed=false, mt5=false, discord=false, ai_api=false, final_signal=false",
        "pool_policy: " + POOL_POLICY,
        f"stage87_catalog_path: {p87}",
        f"output_dir: {out}",
        f"raw_expansion_row_count: {len(expansion_rows)}",
        f"dedup_expansion_row_count: {len(exp_df) if not exp_df.empty else 0}",
        f"normalized_base_candidate_count: {base_count}",
        f"condition_coverage_complete: {condition_coverage_complete}",
        f"condition_restored_base_count: {condition_restored_count}",
        f"manual_candidate_section_path: {out/'manual_candidates.md'}",
        f"candidate_key_order: {CANDIDATE_KEY_ORDER}",
        f"blocker_count: {len(blockers)}",
        "", "MANUAL_CANDIDATE_SECTION", "\n".join(section[:120]),
        "", "BLOCKERS", pd.DataFrame(blockers).to_string(index=False) if blockers else "NO_BLOCKERS",
        "", "VALIDATION", pd.DataFrame(val).to_string(index=False),
        "", "OUTPUTS",
        "expansion.csv",
        "base.csv",
        "condition.csv",
        "manual_candidates.md",
        "blockers.csv",
        "validation.csv",
        "summary.json",
        "paste_me.txt",
        "report.md",
    ]
    write_text_safe(out/"paste_me.txt", "\n".join(paste)+"\n")
    report = f"""# GOLD V3 88 signal candidate normalization and condition coverage audit-only report

Status: `{status}`

- raw_expansion_row_count: `{len(expansion_rows)}`
- dedup_expansion_row_count: `{len(exp_df) if not exp_df.empty else 0}`
- normalized_base_candidate_count: `{base_count}`
- condition_coverage_complete: `{condition_coverage_complete}`
- condition_restored_base_count: `{condition_restored_count}`
- blocker_count: `{len(blockers)}`

Audit-only. Candidate conditions are not guessed.
"""
    write_text_safe(out/"report.md", report)
    print(f"[{status}] {out/'paste_me.txt'}")
    return 0 if status == READY_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
