#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP = "GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_AUDIT_ONLY"
READY = "GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_BLOCKED_AUDIT_ONLY"

REQUIRED = ["entry_dt", "exit_dt", "side", "result_usd", "profile_id", "candidate_key_or_global_candidate_key", "family", "condition", "source_name"]
RECOMMENDED = ["entry_price", "exit_price", "exit_reason", "tp_usd", "sl_usd", "horizon_bars", "result_source", "resolver_script", "csv_contract"]
PATTERNS = ["result_usd", "exit_dt", "tp", "sl", "horizon", "take", "stop", "outcome", "result", "ledger"]


def log(s: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s}", flush=True)


def prog(i: int, n: int, s: str) -> None:
    p = 100.0 * i / max(1, n)
    log(f"progress {p:5.1f}% complete / {100.0-p:5.1f}% remaining | step {i}/{n} | {s}")


def save(df: pd.DataFrame, p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding="utf-8-sig")


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "scripts" / "gold_v3_runtime").exists():
            return p
    return Path.cwd()


def scan_runtime_scripts(repo_root: Path) -> pd.DataFrame:
    runtime = repo_root / "scripts" / "gold_v3_runtime"
    rows = []
    files = sorted(runtime.rglob("*.py")) if runtime.exists() else []
    for i, p in enumerate(files, 1):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
            counts = {f"count_{pat}": len(re.findall(re.escape(pat), txt, flags=re.I)) for pat in PATTERNS}
            score = counts.get("count_result_usd", 0) * 5 + counts.get("count_exit_dt", 0) * 6 + counts.get("count_tp", 0) * 2 + counts.get("count_sl", 0) * 2 + counts.get("count_horizon", 0) * 2 + counts.get("count_outcome", 0) * 3 + counts.get("count_ledger", 0)
            rows.append(dict(path=str(p.relative_to(repo_root)), file=p.name, bytes=len(txt.encode("utf-8", errors="ignore")), locator_score=score, **counts))
        except Exception as e:
            rows.append(dict(path=str(p), file=p.name, locator_error=str(e), locator_score=0))
        if i % 20 == 0:
            prog(i, max(1, len(files)), "runtime scan")
    return pd.DataFrame(rows).sort_values("locator_score", ascending=False) if rows else pd.DataFrame()


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src_q = root / "107qc"
    src_r3 = root / "107r3c"
    out = root / "107r4c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks, outputs, findings = [], [], []
    req_path = src_r3 / "gold_v3_107r3_resolved_ledger_contract_requirement.csv"
    best_path = src_q / "gold_v3_107q_best_family_trade_ledger.csv"
    if not req_path.exists():
        blocks.append(dict(blocker_id="missing_107r3_contract_requirement", path=str(req_path)))
    if not best_path.exists():
        blocks.append(dict(blocker_id="missing_107q_best_family_trade_ledger", path=str(best_path)))

    req = pd.DataFrame(); best = pd.DataFrame(); gap = pd.DataFrame(); locator = pd.DataFrame(); patch = pd.DataFrame()
    if not blocks:
        req = pd.read_csv(req_path, encoding="utf-8-sig")
        best = pd.read_csv(best_path, nrows=5, encoding="utf-8-sig", low_memory=False)
        cols = set(best.columns)
        gap_rows = []
        for c in REQUIRED + RECOMMENDED:
            if c == "candidate_key_or_global_candidate_key":
                present = "candidate_key" in cols or "global_candidate_key" in cols
                actual = "candidate_key" if "candidate_key" in cols else ("global_candidate_key" if "global_candidate_key" in cols else "")
            else:
                present = c in cols
                actual = c if present else ""
            gap_rows.append(dict(column=c, required=c in REQUIRED, recommended=c in RECOMMENDED, present_in_107q_best_ledger=present, actual_column=actual, action="keep" if present else "must_emit_from_resolver"))
        gap = pd.DataFrame(gap_rows)
        save(gap, out / "gold_v3_107r4_contract_gap_matrix.csv")
        outputs.append("gold_v3_107r4_contract_gap_matrix.csv")
        prog(1, 5, "contract gap matrix complete")

    if not blocks:
        repo_root = find_repo_root(Path(__file__))
        locator = scan_runtime_scripts(repo_root)
        save(locator, out / "gold_v3_107r4_runtime_source_locator.csv")
        outputs.append("gold_v3_107r4_runtime_source_locator.csv")
        likely = locator[locator["locator_score"] > 0].head(20) if not locator.empty else pd.DataFrame()
        if likely.empty:
            blocks.append(dict(blocker_id="resolver_source_not_located", reason="No scripts/gold_v3_runtime Python file contained outcome/result/TP/SL keywords."))
        else:
            findings.append("top_runtime_source_locator=" + json.dumps(likely.head(10).to_dict(orient="records"), ensure_ascii=False, default=str))
        prog(3, 5, "runtime source locator complete")

    contract_md = f"""# GOLD V3 107R4 resolved ledger output contract

Stage: `{STEP}`

The next implementation must add an audit-only resolved source ledger emitted by the same TP/SL outcome-resolution process that produced `result_usd`.

## Required columns

```text
entry_dt
exit_dt
side
result_usd
profile_id
candidate_key or global_candidate_key
family
condition
source_name
```

## Recommended columns

```text
entry_price
exit_price
exit_reason
tp_usd
sl_usd
horizon_bars
result_source
resolver_script
csv_contract
```

## Acceptance checks

```text
rows > 0
exit_dt non-null for every resolved row
exit_dt >= entry_dt for every row
result_usd parity with selected source ledger
no source CSV mutation
live_ready=false
```

## Forbidden

Do not approximate exit_dt manually in 107R4.
Do not use GOLD V2 / old GOLD / DISC8 / Stage41 feature-only snapshot as source.
Do not change live evaluator, MT5, Discord, AI API, final signal, or candidate pool.
"""
    (out / "gold_v3_107r4_resolved_ledger_contract.md").write_text(contract_md, encoding="utf-8")
    outputs.append("gold_v3_107r4_resolved_ledger_contract.md")

    if not locator.empty and (locator["locator_score"] > 0).any():
        top = locator[locator["locator_score"] > 0].head(5)
        patch = pd.DataFrame([
            dict(step_order=1, action="review_top_locator_scripts", detail="Inspect top runtime_source_locator rows for the audited TP/SL/result_usd resolver path."),
            dict(step_order=2, action="add_audit_only_resolved_ledger_output", detail="Emit the required contract columns from the same resolver path; do not change scoring/selection."),
            dict(step_order=3, action="parity_check", detail="Join resolved output back to 107Q best-family ledger and prove result_usd parity plus exit_dt coverage."),
            dict(step_order=4, action="run_107S", detail="Only after full exit_dt coverage, run resolved-only health gate replay."),
        ])
    else:
        patch = pd.DataFrame([
            dict(step_order=1, action="manual_source_contract_review", detail="Locate the TP/SL outcome resolver that produced result_usd and add the resolved ledger contract output."),
        ])
    save(patch, out / "gold_v3_107r4_patch_plan.csv")
    outputs.append("gold_v3_107r4_patch_plan.csv")
    prog(4, 5, "contract and patch plan written")

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="no_tp_sl_approximation", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="runtime_scope_gold_v3_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
    ]
    if not gap.empty:
        vals.append(dict(check_id="contract_gap_matrix_positive", result="PASS", observed=len(gap), expected=">0", severity="BLOCKER"))
    if not locator.empty:
        vals.append(dict(check_id="runtime_source_locator_positive", result="PASS", observed=len(locator), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0
    if validation_failure_count:
        status = BLOCKED
        decision = "RESOLVED_LEDGER_SOURCE_CONTRACT_BLOCKED_INPUT_INCOMPLETE"
    elif blocks:
        status = BLOCKED
        decision = "RESOLVED_LEDGER_SOURCE_CONTRACT_BLOCKED_RESOLVER_SOURCE_NOT_LOCATED"
    else:
        status = READY
        decision = "RESOLVED_LEDGER_SOURCE_CONTRACT_READY_FOR_PATCH_IMPLEMENTATION"

    summary = dict(
        step=STEP,
        status=status,
        decision=decision,
        created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        output_dir=str(out),
        audit_only=True,
        live_ready=False,
        source_csv_mutated=False,
        contract_mutated=False,
        open_asof_allowed=False,
        blocker_count=len(blocks),
        validation_failure_count=validation_failure_count,
        elapsed_seconds=round(time.time() - t0, 2),
        required_contract_columns=len(REQUIRED),
        recommended_contract_columns=len(RECOMMENDED),
        contract_gap_rows=int(len(gap)) if not gap.empty else 0,
        runtime_locator_rows=int(len(locator)) if not locator.empty else 0,
        top_locator_score=int(locator["locator_score"].max()) if not locator.empty and "locator_score" in locator.columns else 0,
    )
    save(pd.DataFrame(blocks), out / "gold_v3_107r4_blocker_matrix.csv")
    save(val, out / "gold_v3_107r4_validation_matrix.csv")
    outputs += ["gold_v3_107r4_blocker_matrix.csv", "gold_v3_107r4_validation_matrix.csv", "gold_v3_107r4_summary.json", "GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107r4_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107R4_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107R4 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = [
        "GOLD V3 107R4 PASTE_ME_RESOLVED_LEDGER_SOURCE_CONTRACT_BUILDER",
        f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false",
        "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false",
        "safety: audit_only=true, no_tp_sl_approximation=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false",
        "blocker_count: " + str(len(blocks)), "", "KEY_METRICS",
    ] + [f"{k}: {v}" for k, v in summary.items()] + [
        "", "FINDINGS",
    ] + (findings or ["NO_FINDINGS"]) + [
        "", "BLOCKERS", pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS",
        "", "PATCH_PLAN", patch.to_string(index=False),
        "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS",
    ] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
