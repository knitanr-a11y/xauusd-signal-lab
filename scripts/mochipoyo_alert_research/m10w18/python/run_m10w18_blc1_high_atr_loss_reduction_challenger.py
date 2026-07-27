from __future__ import annotations

import bisect
import csv
import json
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for directory in (MR / "m10w16" / "python", MR / "m10w13" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import run_m10w16_preregistered_blind_spot_trend_continuation_evaluation as w16
import run_m10w13_frozen_historical_short_activation_interval_calibration as w13

STAGE = "M10W18_BLC1_HIGH_ATR_LOSS_REDUCTION_CHALLENGER_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w18_blc1_high_atr_loss_reduction_challenger_contract_20260728.json"
TIME_FORMAT = w16.TIME_FORMAT


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def attach_h1_atr_percentile(candidates: list[dict[str, Any]], h1: list[Any]) -> list[dict[str, Any]]:
    atrp = w13.atr_percentile100(h1)
    close_times = [bar.time + timedelta(hours=1) for bar in h1]
    output: list[dict[str, Any]] = []
    for row in candidates:
        decision = datetime.strptime(str(row["decision_time"]), TIME_FORMAT)
        index = bisect.bisect_right(close_times, decision) - 1
        value = None if index < 0 else atrp[index]
        bucket = "UNAVAILABLE"
        if value is not None:
            v = float(value)
            bucket = "HIGH_GE_0P67" if v >= 0.67 else ("LOW_LT_0P33" if v < 0.33 else "MID_0P33_TO_LT_0P67")
        output.append({**row, "h1_atr_pct100": None if value is None else float(value), "h1_atr_bucket": bucket})
    return output


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        key = str(row.get("status"))
        out[key] = out.get(key, 0) + 1
    return out


def metric_delta(filtered: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for split in ("TRAIN_2023_2024", "VALIDATION_2025", "TEST_2026", "ALL"):
        out[split] = {}
        for cost_key in ("actual", "fixed0p20", "actual_plus1bps_cost", "actual_plus2bps_cost"):
            f = filtered[split][cost_key]
            b = baseline[split][cost_key]
            out[split][cost_key] = {
                "count_delta": int(f["count"]) - int(b["count"]),
                "net_bps_delta": float(f["net_bps"]) - float(b["net_bps"]),
                "pf_delta": None if f["profit_factor"] is None or b["profit_factor"] is None else float(f["profit_factor"]) - float(b["profit_factor"]),
                "max_drawdown_bps_delta": float(f["max_drawdown_bps"]) - float(b["max_drawdown_bps"]),
            }
    return out


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W18"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE:
            raise RuntimeError("unexpected M10W18 contract")
        data_root = w16.resolve_data_root(local_root)
        bars, hashes = w16.verify_and_load(data_root)

        baseline_candidates = w16.build_candidates(bars, "LONG")
        enriched = attach_h1_atr_percentile(baseline_candidates, bars["H1"])
        filtered_candidates = [row for row in enriched if row.get("h1_atr_pct100") is not None and float(row["h1_atr_pct100"]) < 0.67]
        excluded_candidates = [row for row in enriched if row.get("h1_atr_pct100") is None or float(row["h1_atr_pct100"]) >= 0.67]

        baseline_ledger, baseline_overlap = w16.build_ledger(enriched, bars["M1"])
        filtered_ledger, filtered_overlap = w16.build_ledger(filtered_candidates, bars["M1"])
        excluded_ledger, excluded_overlap = w16.build_ledger(excluded_candidates, bars["M1"])

        baseline_metrics = w16.metric_blocks(baseline_ledger)
        filtered_metrics = w16.metric_blocks(filtered_ledger)
        excluded_metrics = w16.metric_blocks(excluded_ledger)

        summary = {
            "project":"MOCHIPOYO_ALERT_RESEARCH",
            "stage":STAGE,
            "status":"PASS_POSTHOC_RESEARCH_EXPOSED_EXACT_RESIMULATION_AUDIT_ONLY",
            "built_at_utc":datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope":"XAUUSD_GOLD_ONLY",
            "verified_sha256":hashes,
            "gate":{"accept":"h1_atr_pct100 < 0.67","exclude":"h1_atr_pct100 >= 0.67 or unavailable","threshold_origin":"M10W14 outcome-blind tercile boundary"},
            "baseline":{"candidate_count":len(enriched),"ledger_status_counts":status_counts(baseline_ledger),"overlap_skip_count":len(baseline_overlap),"metrics":baseline_metrics},
            "filtered":{"candidate_count":len(filtered_candidates),"ledger_status_counts":status_counts(filtered_ledger),"overlap_skip_count":len(filtered_overlap),"metrics":filtered_metrics},
            "excluded_high_or_unavailable":{"candidate_count":len(excluded_candidates),"ledger_status_counts":status_counts(excluded_ledger),"overlap_skip_count":len(excluded_overlap),"metrics":excluded_metrics},
            "filtered_minus_baseline":metric_delta(filtered_metrics, baseline_metrics),
            "interpretation":{
                "posthoc_research_exposed":True,
                "historical_improvement_is_clean_validation":False,
                "existing_BLC1_formula_changed":False,
                "existing_forward_modified":False,
                "fresh_prospective_required_before_support":True,
                "no_additional_filter_search_allowed_from_this_result":True,
            },
            "guardrails":contract["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W18 exact BLC1 high-ATR suppression re-simulation. Post-hoc research-exposed challenger only; no live/fresh promotion from historical results.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_enriched_baseline_candidates.csv", enriched)
        write_csv(archive / "03_filtered_candidates.csv", filtered_candidates)
        write_csv(archive / "04_baseline_ledger.csv", baseline_ledger)
        write_csv(archive / "05_filtered_ledger.csv", filtered_ledger)
        write_csv(archive / "06_excluded_high_or_unavailable_ledger.csv", excluded_ledger)
        write_csv(archive / "07_baseline_overlap.csv", baseline_overlap)
        write_csv(archive / "08_filtered_overlap.csv", filtered_overlap)
        (archive / "09_audit.log").write_text("\n".join([
            "status=PASS_POSTHOC_RESEARCH_EXPOSED_EXACT_RESIMULATION_AUDIT_ONLY",
            f"baseline_candidates={len(enriched)}",
            f"filtered_candidates={len(filtered_candidates)}",
            f"excluded_candidates={len(excluded_candidates)}",
            "gate=h1_atr_pct100_lt_0.67",
            "threshold_search=false",
            "existing_forward_modified=false",
            "fresh_prospective_required_before_support=true",
            "",
        ]), encoding="utf-8")
        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt","01_summary.json","02_enriched_baseline_candidates.csv","03_filtered_candidates.csv","04_baseline_ledger.csv","05_filtered_ledger.csv","06_excluded_high_or_unavailable_ledger.csv","07_baseline_overlap.csv","08_filtered_overlap.csv","09_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)
        print(f"[M10W18 PASS] baseline_candidates={len(enriched)} filtered_candidates={len(filtered_candidates)}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W18 BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No existing forward monitor/formula/start was modified.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
