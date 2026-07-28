from __future__ import annotations

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
for directory in (MR / "m10a" / "python", MR / "m10w25" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import frozen_core as c
import run_m10w25_neither_prefix_causal_live_parity_audit as parity

STAGE = "M10W25B_H4_S4_BOUNDARY_AND_CAUSAL_NEITHER_COHORT_CORRECTION_AUDIT_ONLY"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10w25b_h4_s4_boundary_and_causal_neither_cohort_correction_contract_20260728.json"
TIME_FORMAT = c.TIME_FORMAT
EXPECTED_FULL_GRID = 81329
EXPECTED_TARGET = 8648
EXPECTED_HIST_NEITHER = 5917
EXPECTED_CAUSAL_NEITHER = 5913
EXPECTED_FULL_H4_MISMATCH = 21
EXPECTED_TARGET_H4_MISMATCH = 7
EXPECTED_REMOVED = 4


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return payload


def load_csv(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"required CSV missing: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"required CSV empty: {path}")
    return rows


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


def assert_preentry_columns(rows: list[dict[str, Any]], label: str) -> None:
    fields = set(rows[0])
    forbidden = {
        "actual_return_bps", "fixed0p20_return_bps", "trade_id", "status",
        "scheduled_exit_time", "exit_time", "profit_factor", "net_bps",
        "win_rate", "pnl", "outcome", "label",
    }
    found = sorted(fields & forbidden)
    if found:
        raise RuntimeError(f"{label} contains forbidden outcome/trade columns: {found}")


def reconstruct_h4_selected_turns(bars: dict[str, list[c.Bar]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    m1 = bars["M1"]
    m1_index = {bar.time: i for i, bar in enumerate(m1)}
    events = parity.primary_events(bars["H4"])
    ctx = parity.build_branch_context(bars)
    event_cursor = 0
    state = "IDLE"
    signal_bid: float | None = None
    entry_m1_index: int | None = None
    raw_consumed = False
    active_episode: dict[str, Any] | None = None
    long_episodes: list[dict[str, Any]] = []
    selected_by_window: dict[str, dict[str, Any]] = {}

    for decision_index, decision_bar in enumerate(m1):
        decision = decision_bar.time
        while event_cursor < len(events) and events[event_cursor]["time"] <= decision:
            event = events[event_cursor]
            event_time = event["time"]
            if state == "IDLE":
                if bool(event["turn_up"]) and bool(event["bullish"]):
                    state = "ACTIVE_LONG"
                    ep = m1_index.get(event_time)
                    active_episode = {
                        "primary_entry_time": parity.ft(event_time),
                        "primary_entry_m1_present": ep is not None,
                        "primary_exit_time": None,
                        "primary_exit_m1_present": None,
                        "raw_first_turn_time": None,
                        "selected_H4_S4_turn_time": None,
                        "selected_m15_window": None,
                    }
                    long_episodes.append(active_episode)
                    if ep is None:
                        signal_bid = None
                        entry_m1_index = None
                    else:
                        signal_bid = float(m1[ep].open)
                        entry_m1_index = ep
                    raw_consumed = False
                elif bool(event["turn_down"]) and bool(event["bearish"]):
                    state = "ACTIVE_SHORT"
                    signal_bid = None
                    entry_m1_index = None
                    active_episode = None
                    raw_consumed = False
            elif state == "ACTIVE_LONG" and float(event["current_rci9"]) >= c.LONG_EXIT_RCI9:
                if active_episode is None:
                    raise RuntimeError("ACTIVE_LONG exit without episode")
                active_episode["primary_exit_time"] = parity.ft(event_time)
                active_episode["primary_exit_m1_present"] = event_time in m1_index
                state = "IDLE"
                signal_bid = None
                entry_m1_index = None
                active_episode = None
                raw_consumed = False
            elif state == "ACTIVE_SHORT" and float(event["current_rci9"]) <= c.SHORT_EXIT_RCI9:
                state = "IDLE"
                signal_bid = None
                entry_m1_index = None
                active_episode = None
                raw_consumed = False
            event_cursor += 1

        if state != "ACTIVE_LONG" or active_episode is None or raw_consumed or signal_bid is None or entry_m1_index is None:
            continue
        current_index = decision_index - 1
        if current_index < entry_m1_index + 1 or current_index <= 0:
            continue
        history = m1[max(0, current_index - c.TURN_LOOKBACK):current_index]
        if len(history) < c.TURN_LOOKBACK:
            continue
        previous = m1[current_index - 1]
        current = m1[current_index]
        candidate = previous.low <= min(bar.low for bar in history) and previous.low < signal_bid and current.close > previous.close
        if not candidate:
            continue
        raw_consumed = True
        active_episode["raw_first_turn_time"] = parity.ft(decision)
        if parity.branch_pass("H4", decision, ctx):
            window = parity.floor_m15(decision)
            key = parity.ft(window)
            active_episode["selected_H4_S4_turn_time"] = parity.ft(decision)
            active_episode["selected_m15_window"] = key
            if key in selected_by_window:
                raise RuntimeError(f"multiple causal H4_S4 selected turns in one M15 window: {key}")
            selected_by_window[key] = active_episode

    return long_episodes, selected_by_window


def classify_h4_mismatch(
    mismatch: dict[str, Any],
    episode: dict[str, Any],
    pair_by_entry: dict[str, dict[str, Any]],
    m1_times: set[datetime],
) -> str:
    entry_text = str(episode["primary_entry_time"])
    pair = pair_by_entry.get(entry_text)
    if pair is None:
        if episode.get("primary_exit_time") in (None, ""):
            return "TERMINAL_UNCOMPLETED_EPISODE"
        return "OTHER_LOGIC_MISMATCH"
    entry = pair["entry_time"]
    exit_time = pair["exit_time"]
    if entry not in m1_times:
        return "EXACT_M1_PRIMARY_ENTRY_MISSING"
    if exit_time not in m1_times:
        return "EXACT_M1_PRIMARY_EXIT_MISSING"
    turn = parity.pt(str(episode["selected_H4_S4_turn_time"]))
    if turn >= exit_time:
        return "SAME_TIMESTAMP_EXIT_PRECEDENCE"
    return "OTHER_LOGIC_MISMATCH"


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    output_root = local_root / "outputs" / "M10W25B"
    try:
        contract = load_json(CONTRACT)
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_NOT_EXECUTED":
            raise RuntimeError("unexpected M10W25B contract")

        m10w25_root = local_root / "outputs" / "M10W25" / "LATEST"
        summary25 = load_json(m10w25_root / "01_summary.json")
        if summary25.get("stage") != "M10W25_NEITHER_PREFIX_CAUSAL_LIVE_PARITY_AUDIT_ONLY" or summary25.get("status") != "COMPLETE_TARGET_NEITHER_PREFIX_CAUSAL_MISMATCH_REQUIRES_CORRECTION_AUDIT_ONLY":
            raise RuntimeError("unexpected M10W25 result status")
        if summary25.get("sources", {}).get("outcome_files_read") is not False:
            raise RuntimeError("M10W25 was not outcome-blind")

        comparison = load_csv(m10w25_root / "02_causal_coverage_grid_comparison.csv")
        if len(comparison) != EXPECTED_FULL_GRID:
            raise RuntimeError(f"M10W25 comparison row drift: {len(comparison)}")
        comparison_by_time = {str(row["decision_time"]): row for row in comparison}
        if len(comparison_by_time) != len(comparison):
            raise RuntimeError("duplicate decision_time in M10W25 comparison")

        full_h4_mismatches = [row for row in comparison if parity.parse_bool(row["mismatch_LONG_H4_S4"])]
        target_h4_mismatches = [row for row in full_h4_mismatches if parity.parse_bool(row["target_high_atr_bullish"])]
        if len(full_h4_mismatches) != EXPECTED_FULL_H4_MISMATCH or len(target_h4_mismatches) != EXPECTED_TARGET_H4_MISMATCH:
            raise RuntimeError("M10W25 H4 mismatch count drift")
        for row in full_h4_mismatches:
            other = [name for name in parity.FAMILIES if name != "LONG_H4_S4" and parity.parse_bool(row[f"mismatch_{name}"])]
            if other or parity.parse_bool(row["historical_LONG_H4_S4"]) or not parity.parse_bool(row["causal_LONG_H4_S4"]):
                raise RuntimeError(f"unexpected mismatch structure at {row['decision_time']}: other={other}")

        data_root = parity.resolve_data_root(local_root)
        bars, hashes = parity.verify_and_load(data_root)
        long_episodes, selected_by_window = reconstruct_h4_selected_turns(bars)
        historical_pairs = [pair for pair in c.replay_m7c(bars["H4"]) if pair["direction"] == "LONG"]
        pair_by_entry = {parity.ft(pair["entry_time"]): pair for pair in historical_pairs}
        if len(pair_by_entry) != len(historical_pairs):
            raise RuntimeError("duplicate H4 historical LONG primary entry_time")
        m1_times = {bar.time for bar in bars["M1"]}

        root_rows: list[dict[str, Any]] = []
        root_counts: dict[str, int] = {}
        for row in sorted(full_h4_mismatches, key=lambda item: str(item["decision_time"])):
            decision = str(row["decision_time"])
            episode = selected_by_window.get(decision)
            if episode is None:
                raise RuntimeError(f"no causal selected H4 episode detail for mismatch window: {decision}")
            classification = classify_h4_mismatch(row, episode, pair_by_entry, m1_times)
            root_counts[classification] = root_counts.get(classification, 0) + 1
            root_rows.append({
                "decision_time": decision,
                "target_high_atr_bullish": parity.parse_bool(row["target_high_atr_bullish"]),
                "historical_coverage_class": row["historical_coverage_class"],
                "causal_coverage_class": row["causal_coverage_class"],
                "root_cause_classification": classification,
                **episode,
            })

        broad_path = local_root / "outputs" / "M10W22" / "LATEST" / "02_target_regime_causal_feature_rows.csv"
        historical_path = local_root / "outputs" / "M10W24B" / "LATEST" / "02_corrected_neither_feature_rows.csv"
        broad_rows = load_csv(broad_path)
        historical_neither_rows = load_csv(historical_path)
        assert_preentry_columns(broad_rows, "M10W22 broader pre-entry features")
        assert_preentry_columns(historical_neither_rows, "M10W24B historical NEITHER pre-entry features")
        if len(broad_rows) != EXPECTED_TARGET or len(historical_neither_rows) != EXPECTED_HIST_NEITHER:
            raise RuntimeError("pre-entry source row count drift")

        broad_times = [str(row["decision_time"]) for row in broad_rows]
        historical_times = {str(row["decision_time"]) for row in historical_neither_rows}
        if len(set(broad_times)) != len(broad_times) or len(historical_times) != len(historical_neither_rows):
            raise RuntimeError("duplicate decision_time in pre-entry sources")

        causal_rows: list[dict[str, Any]] = []
        for row in broad_rows:
            decision = str(row["decision_time"])
            comparison_row = comparison_by_time.get(decision)
            if comparison_row is None or not parity.parse_bool(comparison_row["target_high_atr_bullish"]):
                raise RuntimeError(f"M10W22 target decision missing/non-target in M10W25 comparison: {decision}")
            if str(comparison_row["causal_coverage_class"]) == "NEITHER":
                causal_rows.append(row)

        causal_times = {str(row["decision_time"]) for row in causal_rows}
        if len(causal_rows) != EXPECTED_CAUSAL_NEITHER or len(causal_times) != len(causal_rows):
            raise RuntimeError(f"causal target NEITHER row drift: {len(causal_rows)}")
        removed = sorted(historical_times - causal_times)
        added = sorted(causal_times - historical_times)
        if len(removed) != EXPECTED_REMOVED or added:
            raise RuntimeError(f"unexpected causal cohort diff removed={len(removed)} added={len(added)}")

        removed_rows: list[dict[str, Any]] = []
        for decision in removed:
            row = comparison_by_time[decision]
            mismatch_names = [name for name in parity.FAMILIES if parity.parse_bool(row[f"mismatch_{name}"])]
            if str(row["historical_coverage_class"]) != "NEITHER" or str(row["causal_coverage_class"]) != "LONG_ONLY" or mismatch_names != ["LONG_H4_S4"]:
                raise RuntimeError(f"unexpected removed-row reason at {decision}: {mismatch_names}")
            removed_rows.append({
                "decision_time": decision,
                "historical_coverage_class": row["historical_coverage_class"],
                "causal_coverage_class": row["causal_coverage_class"],
                "historical_LONG_H4_S4": row["historical_LONG_H4_S4"],
                "causal_LONG_H4_S4": row["causal_LONG_H4_S4"],
                "correction_action": "REMOVE_FROM_CAUSAL_NEITHER_COHORT",
            })

        other_count = int(root_counts.get("OTHER_LOGIC_MISMATCH", 0))
        pass_cohort = len(causal_rows) == EXPECTED_CAUSAL_NEITHER and len(removed) == EXPECTED_REMOVED and not added
        pass_root = other_count == 0
        status = "PASS_H4_BOUNDARY_CLASSIFIED_CAUSAL_NEITHER_COHORT_FROZEN_AUDIT_ONLY" if pass_cohort and pass_root else "BLOCKED_UNRESOLVED_H4_ROOT_CAUSE_AUDIT_ONLY"
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": status,
            "built_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": "XAUUSD_GOLD_ONLY",
            "verified_sha256": hashes,
            "outcome_files_read": False,
            "future_return_computed": False,
            "root_cause": {
                "full_H4_S4_mismatch_count": len(full_h4_mismatches),
                "target_H4_S4_mismatch_count": len(target_h4_mismatches),
                "classification_counts": root_counts,
                "other_logic_mismatch_count": other_count,
                "all_mismatches_explained": pass_root,
            },
            "causal_cohort": {
                "broader_target_preentry_rows": len(broad_rows),
                "historical_NEITHER_preentry_rows": len(historical_neither_rows),
                "causal_NEITHER_preentry_rows": len(causal_rows),
                "removed_historical_only_rows": len(removed),
                "added_causal_only_rows": len(added),
                "removed_decision_times": removed,
                "join_unmatched_rows": 0,
                "outcome_columns_read": False,
            },
            "decision": {
                "causal_cohort_frozen_for_exact_formula_reevaluation": bool(pass_cohort and pass_root),
                "M10W25C_authorized": bool(pass_cohort and pass_root),
                "M10W26_fresh_start_authorized_now": False,
                "next": "If PASS, re-evaluate exact frozen M10W23 formulas on 02_causal_neither_preentry_feature_rows.csv in M10W25C without tuning. Fresh start remains forbidden until review.",
            },
            "guardrails": contract["safety"],
        }

        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10W25B outcome-blind H4_S4 boundary/root-cause and causal NEITHER pre-entry cohort correction. No trade outcomes, PF/PnL, future returns, threshold changes, monitor changes, or fresh start creation.\n",
            encoding="utf-8",
        )
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_causal_neither_preentry_feature_rows.csv", causal_rows)
        write_csv(archive / "03_removed_historical_neither_rows.csv", removed_rows)
        write_csv(archive / "04_h4_s4_boundary_root_cause.csv", root_rows)
        (archive / "05_audit.log").write_text("\n".join([
            f"status={status}",
            f"full_H4_S4_mismatches={len(full_h4_mismatches)}",
            f"target_H4_S4_mismatches={len(target_h4_mismatches)}",
            f"root_cause_counts={json.dumps(root_counts, sort_keys=True)}",
            f"other_logic_mismatch_count={other_count}",
            f"broader_target_preentry_rows={len(broad_rows)}",
            f"historical_neither_preentry_rows={len(historical_neither_rows)}",
            f"causal_neither_preentry_rows={len(causal_rows)}",
            f"removed_historical_only_rows={len(removed)}",
            f"added_causal_only_rows={len(added)}",
            "outcome_files_read=false",
            "future_return_computed=false",
            "formula_application=false",
            "threshold_refit=false",
            "new_prospective_start_created=false",
            "existing_forward_modified=false",
            "",
        ]), encoding="utf-8")

        latest = output_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = ["00_READ_ME_FIRST.txt", "01_summary.json", "02_causal_neither_preentry_feature_rows.csv", "03_removed_historical_neither_rows.csv", "04_h4_s4_boundary_root_cause.csv", "05_audit.log"]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)

        if not (pass_cohort and pass_root):
            print(f"[M10W25B BLOCKED] unresolved root cause or cohort mismatch; root={root_counts}")
            print(f"[PACKAGE] {package}")
            return 2
        print(f"[M10W25B PASS] causal_neither={len(causal_rows)} removed={len(removed)} root={root_counts}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10W25B BLOCKED] {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[SAFE] No outcome evaluation, threshold/start/runtime/monitor change was attempted.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
