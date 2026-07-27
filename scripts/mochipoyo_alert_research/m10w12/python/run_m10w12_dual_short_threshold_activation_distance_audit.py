from __future__ import annotations

import bisect
import csv
import json
import math
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
for directory in (
    MR / "m10p" / "python",
    MR / "m10p2" / "python",
    MR / "m9p" / "python",
    MR / "m10a" / "python",
):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import m10p_runtime as m10p
import m10p2_runtime as m10p2
import m10p_guarded_runtime as m10p_guard
import m10p2_guarded_runtime as m10p2_guard
import run_gold_dynamic_core_reproduction_audit as m9p
import frozen_core as frozen

STAGE = "M10W12_DUAL_SHORT_THRESHOLD_ACTIVATION_DISTANCE_AUDIT_ONLY"
TIME_FORMAT = m9p.TIME_FORMAT


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def fmt_time(value: datetime) -> str:
    return value.strftime(TIME_FORMAT)


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


def margin_ge(value: float, threshold: float) -> float:
    return value - threshold


def margin_le(value: float, threshold: float) -> float:
    return threshold - value


def failed_deficit(margin: float, threshold: float) -> float:
    if margin >= 0:
        return 0.0
    return (-margin) / max(abs(threshold), 1.0)


def summarize_rows(
    rows: list[dict[str, Any]],
    condition_names: list[str],
    subgroup_flags: dict[str, list[str]],
    expected_candidate_count: int,
) -> dict[str, Any]:
    pass_counts = {
        name: sum(bool(row[f"pass_{name}"]) for row in rows)
        for name in condition_names
    }
    subgroup_counts = {
        group: sum(all(bool(row[f"pass_{name}"]) for name in names) for row in rows)
        for group, names in subgroup_flags.items()
    }
    all_pass = sum(int(row["failed_condition_count"]) == 0 for row in rows)
    latest = rows[-1] if rows else None
    if all_pass != expected_candidate_count:
        raise RuntimeError(
            f"candidate cross-check mismatch: audit_all_pass={all_pass} latest_summary_candidate_count={expected_candidate_count}"
        )
    never_activated = [name for name, count in pass_counts.items() if count == 0]
    if all_pass > 0:
        interpretation = "One or more frozen candidates activated; cross-check matches the running shadow summary."
    elif not never_activated:
        interpretation = "Every frozen condition activated individually at least once, but the full conjunction has not occurred in the observed post-start interval."
    else:
        interpretation = "The full conjunction has not occurred; one or more frozen condition legs have not activated in the observed post-start interval."
    return {
        "decision_count": len(rows),
        "condition_pass_counts": pass_counts,
        "joint_subgroup_pass_counts": subgroup_counts,
        "all_conditions_pass_count": all_pass,
        "expected_candidate_match_count": expected_candidate_count,
        "candidate_crosscheck_pass": True,
        "never_activated_conditions": never_activated,
        "latest_decision": latest,
        "interpretation": interpretation,
    }


def near_misses(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            int(row["failed_condition_count"]),
            float(row["normalized_failed_deficit_sum"]),
            -parse_time(str(row["decision_time"])).timestamp(),
        ),
    )[:limit]


def audit_m10p(root: Path, start: datetime, cutoff: datetime, expected_candidates: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    contract = load_json(m10p.CONTRACT)
    fmap = contract["data"]["live_file_map"]
    m1 = m10p.load_bars_retry(root / fmap["M1"])
    h1 = m10p.load_bars_retry(root / fmap["H1"])
    d1 = m10p.load_bars_retry(root / fmap["D1"])
    h1_line, h1_hist, h1_ret3 = m10p.feature_arrays(h1)
    _, d1_hist, _ = m10p.feature_arrays(d1)
    d1_close_times = [bar.time + timedelta(days=1) for bar in d1]

    decisions: list[tuple[datetime, int]] = []
    for i in range(3, len(h1) - 1):
        decision = h1[i + 1].time
        if decision <= cutoff:
            decisions.append((decision, i))
    last_i = len(h1) - 1
    nominal = h1[last_i].time + timedelta(hours=1)
    frontier: datetime | None = None
    for bar in m1:
        if bar.time < nominal:
            continue
        if bar.time > cutoff:
            break
        if bar.time.minute == 0 and bar.time.second == 0:
            frontier = bar.time
            break
    if frontier is not None and all(decision != frontier for decision, _ in decisions):
        decisions.append((frontier, last_i))

    thresholds = {
        "h1_macd_hist_bps_ge": float(m10p.H1_HIST_GE),
        "h1_macd_line_bps_le": float(m10p.H1_LINE_LE),
        "h1_ret3_bps_ge": float(m10p.H1_RET3_GE),
        "d1_macd_hist_bps_ge": float(m10p.D1_HIST_GE),
    }
    rows: list[dict[str, Any]] = []
    for decision, ih1 in sorted(decisions, key=lambda item: item[0]):
        if decision <= start or decision > cutoff:
            continue
        id1 = bisect.bisect_right(d1_close_times, decision) - 1
        if id1 < 0 or ih1 < 3 or h1_ret3[ih1] is None:
            continue
        values = {
            "h1_macd_hist_bps_ge": float(h1_hist[ih1]),
            "h1_macd_line_bps_le": float(h1_line[ih1]),
            "h1_ret3_bps_ge": float(h1_ret3[ih1]),
            "d1_macd_hist_bps_ge": float(d1_hist[id1]),
        }
        margins = {
            "h1_macd_hist_bps_ge": margin_ge(values["h1_macd_hist_bps_ge"], thresholds["h1_macd_hist_bps_ge"]),
            "h1_macd_line_bps_le": margin_le(values["h1_macd_line_bps_le"], thresholds["h1_macd_line_bps_le"]),
            "h1_ret3_bps_ge": margin_ge(values["h1_ret3_bps_ge"], thresholds["h1_ret3_bps_ge"]),
            "d1_macd_hist_bps_ge": margin_ge(values["d1_macd_hist_bps_ge"], thresholds["d1_macd_hist_bps_ge"]),
        }
        flags = {name: margin >= 0 for name, margin in margins.items()}
        failed = sum(not flag for flag in flags.values())
        deficit = sum(failed_deficit(margins[name], thresholds[name]) for name in margins)
        row: dict[str, Any] = {
            "family": "M10P_C056_G013",
            "decision_time": fmt_time(decision),
            "h1_source_open": fmt_time(h1[ih1].time),
            "d1_source_open": fmt_time(d1[id1].time),
            "failed_condition_count": failed,
            "passed_condition_count": len(flags) - failed,
            "normalized_failed_deficit_sum": deficit,
        }
        for name in thresholds:
            row[f"threshold_{name}"] = thresholds[name]
            row[f"value_{name}"] = values[name]
            row[f"margin_{name}"] = margins[name]
            row[f"pass_{name}"] = flags[name]
        rows.append(row)

    conditions = list(thresholds)
    summary = summarize_rows(
        rows,
        conditions,
        {
            "seed_hist_and_line": ["h1_macd_hist_bps_ge", "h1_macd_line_bps_le"],
            "regime_ret3_and_d1hist": ["h1_ret3_bps_ge", "d1_macd_hist_bps_ge"],
        },
        expected_candidates,
    )
    summary.update({
        "family": "M10P_C056_G013",
        "prospective_start_server_time": fmt_time(start),
        "summary_cutoff_M1": fmt_time(cutoff),
        "thresholds": thresholds,
    })
    return summary, rows, near_misses(rows)


def audit_m10p2(root: Path, start: datetime, cutoff: datetime, expected_candidates: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    contract = load_json(m10p2.CONTRACT)
    fmap = contract["data"]["live_file_map"]
    m1 = m10p2.load_bars_retry(root / fmap["M1"])
    m15 = m10p2.load_bars_retry(root / fmap["M15"])
    h1 = m10p2.load_bars_retry(root / fmap["H1"])
    h4 = m10p2.load_bars_retry(root / fmap["H4"])
    h1_atrp = m10p2.atr_percentile100(h1)
    h4_closes = [float(bar.close) for bar in h4]
    h4_ema20 = frozen.ema(h4_closes, 20)
    h4_ema30 = frozen.ema(h4_closes, 30)
    h1_close_times = [bar.time + timedelta(hours=1) for bar in h1]
    h4_close_times = [bar.time + timedelta(hours=4) for bar in h4]

    decisions: list[datetime] = []
    for i in range(120, len(m15) - 1):
        decision = m15[i + 1].time
        if decision <= cutoff:
            decisions.append(decision)
    nominal = m15[-1].time + timedelta(minutes=15)
    frontier: datetime | None = None
    for bar in m1:
        if bar.time < nominal:
            continue
        if bar.time > cutoff:
            break
        if bar.time.minute % 15 == 0 and bar.time.second == 0:
            frontier = bar.time
            break
    if frontier is not None and frontier not in decisions:
        decisions.append(frontier)

    thresholds = {
        "h4_ema20_30_bps_ge": float(m10p2.H4_EMA20_30_BPS_GE),
        "h1_atr_pct100_ge": float(m10p2.H1_ATR_PCT100_GE),
    }
    rows: list[dict[str, Any]] = []
    for decision in sorted(decisions):
        if decision <= start or decision > cutoff:
            continue
        ih1 = bisect.bisect_right(h1_close_times, decision) - 1
        ih4 = bisect.bisect_right(h4_close_times, decision) - 1
        if ih1 < 0 or ih4 < 0 or h1_atrp[ih1] is None:
            continue
        h4_close = float(h4[ih4].close)
        if h4_close == 0:
            continue
        values = {
            "h4_ema20_30_bps_ge": (float(h4_ema20[ih4]) - float(h4_ema30[ih4])) / abs(h4_close) * 10000.0,
            "h1_atr_pct100_ge": float(h1_atrp[ih1]),
        }
        margins = {name: margin_ge(values[name], thresholds[name]) for name in thresholds}
        flags = {name: margin >= 0 for name, margin in margins.items()}
        failed = sum(not flag for flag in flags.values())
        deficit = sum(failed_deficit(margins[name], thresholds[name]) for name in margins)
        row: dict[str, Any] = {
            "family": "M10P2_C0212",
            "decision_time": fmt_time(decision),
            "h1_source_open": fmt_time(h1[ih1].time),
            "h4_source_open": fmt_time(h4[ih4].time),
            "failed_condition_count": failed,
            "passed_condition_count": len(flags) - failed,
            "normalized_failed_deficit_sum": deficit,
        }
        for name in thresholds:
            row[f"threshold_{name}"] = thresholds[name]
            row[f"value_{name}"] = values[name]
            row[f"margin_{name}"] = margins[name]
            row[f"pass_{name}"] = flags[name]
        rows.append(row)

    conditions = list(thresholds)
    summary = summarize_rows(
        rows,
        conditions,
        {"all_two_conditions": conditions},
        expected_candidates,
    )
    summary.update({
        "family": "M10P2_C0212",
        "prospective_start_server_time": fmt_time(start),
        "summary_cutoff_M1": fmt_time(cutoff),
        "thresholds": thresholds,
    })
    return summary, rows, near_misses(rows)


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = load_json(metadata_path)
    root = Path(str(metadata.get("mt5_files_root", "")))
    point = float(metadata.get("symbols", {}).get("XAUUSD", {}).get("point", "nan"))
    if not root.is_dir() or not math.isfinite(point) or point <= 0:
        raise RuntimeError(f"MT5 root/point unavailable: {root} {point}")

    p_runtime_path = local_root / "m10p_runtime" / "m10p_runtime_manifest.json"
    p2_runtime_path = local_root / "m10p2_runtime" / "m10p2_runtime_manifest.json"
    p_summary_path = local_root / "outputs" / "M10P" / "LATEST" / "01_summary.json"
    p2_summary_path = local_root / "outputs" / "M10P2" / "LATEST" / "01_summary.json"
    for path in (p_runtime_path, p2_runtime_path, p_summary_path, p2_summary_path):
        if not path.is_file():
            raise RuntimeError(f"required source missing: {path}")

    p_runtime = load_json(p_runtime_path)
    p2_runtime = load_json(p2_runtime_path)
    p_summary = load_json(p_summary_path)
    p2_summary = load_json(p2_summary_path)

    # Read-only runtime integrity / current feed checks. Guard modules preserve the
    # weekend-aware observed-M1 freshness semantics already frozen for the shadows.
    m10p_guard.current_feed_guard()
    m10e_path = local_root / "m10e_runtime" / "m10e_runtime_manifest.json"
    m10p.verify_runtime(root, load_json(m10p.CONTRACT), p_runtime, m10e_path)
    p2_snapshots = m10p2.verify_runtime(
        root,
        point,
        load_json(m10p2.CONTRACT),
        p2_runtime,
        p_runtime_path,
    )
    m10p2_guard.observed_feed_health(root, p2_snapshots)

    p_start = parse_time(str(p_runtime["prospective_start_server_time"]))
    p2_start = parse_time(str(p2_runtime["prospective_start_server_time"]))
    if str(p_summary.get("prospective_start_server_time")) != fmt_time(p_start):
        raise RuntimeError("M10P summary/runtime start mismatch")
    if str(p2_summary.get("prospective_start_server_time")) != fmt_time(p2_start):
        raise RuntimeError("M10P2 summary/runtime start mismatch")

    p_cutoff = parse_time(str(p_summary["latest_server_open"]["M1"]))
    p2_cutoff = parse_time(str(p2_summary["latest_server_open"]["M1"]))
    p_expected = int(p_summary.get("metrics", {}).get("candidate_match_count", -1))
    p2_expected = int(p2_summary.get("metrics", {}).get("candidate_match_count", -1))
    if min(p_expected, p2_expected) < 0:
        raise RuntimeError("candidate_match_count missing from current shadow summaries")

    p_result, p_rows, p_near = audit_m10p(root, p_start, p_cutoff, p_expected)
    p2_result, p2_rows, p2_near = audit_m10p2(root, p2_start, p2_cutoff, p2_expected)

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_READ_ONLY_THRESHOLD_ACTIVATION_DISTANCE_AUDIT",
        "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "XAUUSD_GOLD_ONLY",
        "M10P": p_result,
        "M10P2": p2_result,
        "interpretation": {
            "performance_inference_allowed": False,
            "threshold_change_allowed": False,
            "start_change_allowed": False,
            "purpose": "Explain zero-match activation structure only. Near-miss rows are descriptive and must not be used to rescue or refit frozen thresholds from prospective outcomes."
        },
        "guardrails": {
            "audit_only": True,
            "read_only": True,
            "historical_backfill": False,
            "threshold_refit": False,
            "runtime_modified": False,
            "prospective_start_modified": False,
            "M10V_execute": False,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "automatic_live_promotion": False,
        },
    }

    output_root = local_root / "outputs" / "M10W12"
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archive = output_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)
    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M10W12 read-only activation-distance audit for the two frozen GOLD SHORT families. No threshold/start/runtime changes. Near misses are descriptive only.\n",
        encoding="utf-8",
    )
    (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(archive / "02_m10p_decision_ledger.csv", p_rows)
    write_csv(archive / "03_m10p_near_miss.csv", p_near)
    write_csv(archive / "04_m10p2_decision_ledger.csv", p2_rows)
    write_csv(archive / "05_m10p2_near_miss.csv", p2_near)
    (archive / "06_audit.log").write_text("\n".join([
        "status=PASS_READ_ONLY_THRESHOLD_ACTIVATION_DISTANCE_AUDIT",
        f"M10P_decisions={len(p_rows)} all_pass={p_result['all_conditions_pass_count']} expected={p_expected}",
        f"M10P2_decisions={len(p2_rows)} all_pass={p2_result['all_conditions_pass_count']} expected={p2_expected}",
        "threshold_refit=false",
        "start_reset=false",
        "runtime_modified=false",
        "historical_backfill=false",
        "",
    ]), encoding="utf-8")

    latest = output_root / "LATEST"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(archive, latest)
    package = latest / "99_UPLOAD_PACKAGE.zip"
    files = [
        "00_READ_ME_FIRST.txt",
        "01_summary.json",
        "02_m10p_decision_ledger.csv",
        "03_m10p_near_miss.csv",
        "04_m10p2_decision_ledger.csv",
        "05_m10p2_near_miss.csv",
        "06_audit.log",
    ]
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in files:
            zf.write(latest / name, arcname=name)

    print(f"[M10W12 PASS] M10P decisions={len(p_rows)} matches={p_expected}; M10P2 decisions={len(p2_rows)} matches={p2_expected}")
    print(f"[PACKAGE] {package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
