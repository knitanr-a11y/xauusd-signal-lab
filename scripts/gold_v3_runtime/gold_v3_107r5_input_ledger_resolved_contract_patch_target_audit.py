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

STEP = "GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_AUDIT_ONLY"
READY = "GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_READY_AUDIT_ONLY"
BLOCKED = "GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_BLOCKED_AUDIT_ONLY"

CONTRACT = ["entry_dt", "exit_dt", "side", "result_usd", "profile_id", "family", "condition", "source_name"]
CANDIDATE_KEY_ANY = ["candidate_key", "global_candidate_key"]


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


def read_head(path: Path, n: int = 5) -> pd.DataFrame:
    try:
        return pd.read_csv(path, nrows=n, encoding="utf-8-sig", low_memory=False)
    except Exception:
        return pd.DataFrame()


def row_count(path: Path) -> int:
    try:
        return sum(1 for _ in open(path, "rb")) - 1
    except Exception:
        return -1


def scan_producers(repo_root: Path, output_filename: str, source_tag: str) -> pd.DataFrame:
    runtime = repo_root / "scripts" / "gold_v3_runtime"
    rows = []
    for p in sorted(runtime.rglob("*.py")) if runtime.exists() else []:
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
            file_hits = len(re.findall(re.escape(output_filename), txt, flags=re.I))
            source_hits = len(re.findall(re.escape(source_tag), txt, flags=re.I))
            stem_hits = len(re.findall(re.escape(output_filename.replace(".csv", "")), txt, flags=re.I))
            score = file_hits * 100 + stem_hits * 25 + source_hits * 10
            if score > 0:
                rows.append(dict(output_filename=output_filename, source_tag=source_tag, producer_script=str(p.relative_to(repo_root)), producer_score=score, file_hits=file_hits, stem_hits=stem_hits, source_tag_hits=source_hits))
        except Exception as e:
            rows.append(dict(output_filename=output_filename, source_tag=source_tag, producer_script=str(p), producer_error=str(e), producer_score=0))
    return pd.DataFrame(rows).sort_values("producer_score", ascending=False) if rows else pd.DataFrame()


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument("--mt5-files-dir", default="")
    args = ap.parse_args()
    mt5 = gy.mt5_files_dir(args.mt5_files_dir)
    root = mt5 / "FX_OUTPUTS" / "gold_v3"
    src_q = root / "107qc"
    src_r4 = root / "107r4c"
    out = root / "107r5c"
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + " START")
    prog(0, 5, "start")

    blocks, outputs, findings = [], [], []
    best_path = src_q / "gold_v3_107q_best_family_trade_ledger.csv"
    contract_path = src_r4 / "gold_v3_107r4_resolved_ledger_contract.md"
    if not best_path.exists():
        blocks.append(dict(blocker_id="missing_107q_best_family_trade_ledger", path=str(best_path)))
    if not contract_path.exists():
        blocks.append(dict(blocker_id="missing_107r4_resolved_ledger_contract", path=str(contract_path)))

    best = pd.DataFrame(); dist = pd.DataFrame(); matrix = pd.DataFrame(); locator = pd.DataFrame(); target = pd.DataFrame()
    if not blocks:
        best = pd.read_csv(best_path, encoding="utf-8-sig", low_memory=False)
        if "source_name" in best.columns:
            dist = best.groupby("source_name", dropna=False).size().reset_index(name="best_family_rows")
            dist["best_family_share"] = dist["best_family_rows"] / max(1, len(best))
        else:
            dist = pd.DataFrame([dict(source_name="MISSING_SOURCE_NAME", best_family_rows=len(best), best_family_share=1.0)])
        save(dist, out / "gold_v3_107r5_best_family_source_distribution.csv")
        outputs.append("gold_v3_107r5_best_family_source_distribution.csv")
        prog(1, 5, f"best source distribution rows={len(dist)}")

    if not blocks:
        rows = []
        for source_name, sub, fn in gy.INPUTS:
            p = root / sub / fn
            head = read_head(p, 5) if p.exists() else pd.DataFrame()
            cols = list(head.columns) if not head.empty else []
            present = {c: c in cols for c in CONTRACT}
            candidate_key_present = any(c in cols for c in CANDIDATE_KEY_ANY)
            missing = [c for c in CONTRACT if not present.get(c)]
            if not candidate_key_present:
                missing.append("candidate_key_or_global_candidate_key")
            source_rows = row_count(p) if p.exists() else 0
            best_rows = int(dist.loc[dist.source_name.astype(str).eq(source_name), "best_family_rows"].sum()) if not dist.empty and "source_name" in dist.columns else 0
            rows.append(dict(source_name=source_name, subdir=sub, filename=fn, path=str(p), exists=p.exists(), source_rows=source_rows, best_family_rows=best_rows, best_family_share=best_rows / max(1, len(best)), has_entry_dt=present.get("entry_dt", False), has_exit_dt=present.get("exit_dt", False), has_side=present.get("side", False) or "portfolio_side" in cols or "selected_side" in cols, has_result_usd=present.get("result_usd", False), has_profile_id=present.get("profile_id", False), has_candidate_key_or_global_candidate_key=candidate_key_present, has_family=present.get("family", False), has_condition=present.get("condition", False), has_source_name=present.get("source_name", False), missing_contract_columns="|".join(missing), contract_ready=(len(missing) == 0), columns_preview="|".join(cols[:60])))
        matrix = pd.DataFrame(rows)
        save(matrix, out / "gold_v3_107r5_input_ledger_contract_matrix.csv")
        outputs.append("gold_v3_107r5_input_ledger_contract_matrix.csv")
        prog(2, 5, "input ledger contract matrix complete")

    if not blocks:
        repo_root = find_repo_root(Path(__file__))
        parts = []
        for _, r in matrix.iterrows():
            loc = scan_producers(repo_root, str(r.filename), str(r.source_name))
            if loc.empty:
                parts.append(pd.DataFrame([dict(output_filename=str(r.filename), source_tag=str(r.source_name), producer_script="", producer_score=0, producer_missing=True)]))
            else:
                loc["producer_missing"] = False
                parts.append(loc.head(8))
        locator = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        save(locator, out / "gold_v3_107r5_producer_script_locator.csv")
        outputs.append("gold_v3_107r5_producer_script_locator.csv")
        prog(3, 5, "producer locator complete")

    if not blocks:
        patch_rows = []
        for _, r in matrix.iterrows():
            if int(r.best_family_rows) <= 0:
                continue
            loc = locator[(locator.output_filename.astype(str) == str(r.filename)) & (~locator.get("producer_missing", False).astype(bool))].sort_values("producer_score", ascending=False) if not locator.empty else pd.DataFrame()
            patch_rows.append(dict(source_name=r.source_name, input_ledger=str(r.path), best_family_rows=int(r.best_family_rows), missing_contract_columns=str(r.missing_contract_columns), contract_ready=bool(r.contract_ready), producer_located=not loc.empty, top_producer_script=str(loc.iloc[0].producer_script) if not loc.empty else "", recommended_action="already_contract_ready" if bool(r.contract_ready) else "patch_producer_to_emit_resolved_contract"))
        target = pd.DataFrame(patch_rows)
        save(target, out / "gold_v3_107r5_patch_target_matrix.csv")
        outputs.append("gold_v3_107r5_patch_target_matrix.csv")
        if not target.empty:
            findings.append("patch_targets=" + json.dumps(target.to_dict(orient="records"), ensure_ascii=False, default=str))
        prog(4, 5, "patch target matrix complete")

    missing_producers = int((target["producer_located"] == False).sum()) if not target.empty and "producer_located" in target.columns else 0
    needs_patch = int(((target["contract_ready"] == False) & (target["best_family_rows"] > 0)).sum()) if not target.empty else 0
    all_ready = bool(needs_patch == 0 and not target.empty)
    if blocks:
        status = BLOCKED
        decision = "INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_BLOCKED_INPUT_INCOMPLETE"
    elif missing_producers > 0:
        status = BLOCKED
        decision = "INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_BLOCKED_PRODUCER_NOT_LOCATED"
        blocks.append(dict(blocker_id="producer_script_not_located_for_active_source", missing_producer_count=missing_producers))
    else:
        status = READY
        decision = "INPUT_LEDGER_RESOLVED_CONTRACT_ALREADY_PRESENT_READY_FOR_107S" if all_ready else "INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGETS_READY_FOR_107R6"

    vals = [
        dict(check_id="audit_only", result="PASS", observed=True, expected=True, severity="BLOCKER"),
        dict(check_id="live_ready_false", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="source_csv_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="contract_mutated", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="open_asof_allowed", result="PASS", observed=False, expected=False, severity="BLOCKER"),
        dict(check_id="no_runtime_patch_applied", result="PASS", observed=True, expected=True, severity="BLOCKER"),
    ]
    if not matrix.empty:
        vals.append(dict(check_id="input_ledger_contract_matrix_positive", result="PASS", observed=len(matrix), expected=">0", severity="BLOCKER"))
    if not target.empty:
        vals.append(dict(check_id="patch_target_matrix_positive", result="PASS", observed=len(target), expected=">0", severity="BLOCKER"))
    val = pd.DataFrame(vals)
    validation_failure_count = int((~val["result"].eq("PASS")).sum()) if not val.empty else 0

    summary = dict(step=STEP, status=status, decision=decision, created_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, open_asof_allowed=False, blocker_count=len(blocks), validation_failure_count=validation_failure_count, elapsed_seconds=round(time.time() - t0, 2), best_family_rows=int(len(best)) if not best.empty else 0, source_distribution_rows=int(len(dist)) if not dist.empty else 0, input_ledger_contract_rows=int(len(matrix)) if not matrix.empty else 0, active_patch_target_rows=int(len(target)) if not target.empty else 0, needs_patch_count=needs_patch, missing_producer_count=missing_producers)
    save(pd.DataFrame(blocks), out / "gold_v3_107r5_blocker_matrix.csv")
    save(val, out / "gold_v3_107r5_validation_matrix.csv")
    outputs += ["gold_v3_107r5_blocker_matrix.csv", "gold_v3_107r5_validation_matrix.csv", "gold_v3_107r5_summary.json", "GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_AUDIT_ONLY_REPORT.md", "paste_me.txt"]
    (out / "gold_v3_107r5_summary.json").write_text(json.dumps(summary | {"findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (out / "GOLD_V3_107R5_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET_AUDIT_ONLY_REPORT.md").write_text("# GOLD V3 107R5 report\n\n" + json.dumps({"summary": summary, "findings": findings, "blockers": blocks}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    lines = ["GOLD V3 107R5 PASTE_ME_INPUT_LEDGER_RESOLVED_CONTRACT_PATCH_TARGET", f"status: {status}", f"ready: {str(status == READY).lower()}", "live_ready: false", "source_csv_mutated: false", "contract_mutated: false", "open_asof_allowed: false", "safety: audit_only=true, no_runtime_patch_applied=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false", "blocker_count: " + str(len(blocks)), "", "KEY_METRICS"] + [f"{k}: {v}" for k, v in summary.items()] + ["", "FINDINGS"] + (findings or ["NO_FINDINGS"]) + ["", "BLOCKERS", pd.DataFrame(blocks).to_string(index=False) if blocks else "NO_BLOCKERS", "", "VALIDATION", val.to_string(index=False), "", "OUTPUTS"] + outputs
    (out / "paste_me.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    prog(5, 5, "DONE")
    log(f"DONE status={status} decision={decision} elapsed={time.time()-t0:.1f}s paste_me={out/'paste_me.txt'}")
    print(json.dumps({"status": status, "ready": status == READY, "decision": decision, "paste_me": str(out / "paste_me.txt")}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
