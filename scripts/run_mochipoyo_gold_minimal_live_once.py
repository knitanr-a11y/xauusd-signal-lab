#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot GOLD minimal live notification flow.

This is NOT a forever loop.
This is a thin orchestration layer for validating the minimal live flow:

  pair trigger state
    -> scan only should_scan=True GOLD pairs
    -> risk enrich
    -> notification eligibility
    -> filter notifications to the current trigger window
    -> ledger duplicate filter
    -> optional Discord dry-run preview
    -> update trigger state only after successful processing

Safety:
- Default behavior does not send Discord messages.
- No auto-trading.
- Missing initial trigger state is INITIALIZE_ONLY by default.
- Trigger state for SCAN_REQUIRED rows is advanced only after the scan/risk/
  notification/ledger stages complete without errors.
- Historical candidates from a newly scanned pair are not sent.  By default,
  only rows with previous_close_time < signal_close_time <= latest_close_time
  are allowed into the live notification ledger.
- If there are no rows to send, Discord dry-run is skipped and the run can
  still succeed.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.apply_mochipoyo_notification_ledger import (
        build_ledger_append_rows,
        build_state as build_notification_state,
        classify_rows,
        load_existing_ledger,
        append_ledger,
        STATUS_NEW,
    )
    from scripts.apply_mochipoyo_pair_trigger_state import (
        allowed_for_symbol,
        build_updated_state,
        classify_pair,
        get_latest_trigger_close_time,
        read_state,
        state_lookup,
    )
    from scripts.mochipoyo_minimal_config import (
        build_csv_overrides_from_args,
        filter_allowed_slices_for_pair,
        get_pair_config,
    )
    from scripts.mochipoyo_minimal_scanner import errors_frame, reader_metadata_frame, scan_pair_minimal_skeleton
    from scripts.mochipoyo_notification_filter import NotificationEligibilityConfig, apply_notification_eligibility, split_notification_eligible
    from scripts.mochipoyo_risk_enricher import RiskEnrichConfig
except ModuleNotFoundError:
    from apply_mochipoyo_notification_ledger import (  # type: ignore
        build_ledger_append_rows,
        build_state as build_notification_state,
        classify_rows,
        load_existing_ledger,
        append_ledger,
        STATUS_NEW,
    )
    from apply_mochipoyo_pair_trigger_state import (  # type: ignore
        allowed_for_symbol,
        build_updated_state,
        classify_pair,
        get_latest_trigger_close_time,
        read_state,
        state_lookup,
    )
    from mochipoyo_minimal_config import build_csv_overrides_from_args, filter_allowed_slices_for_pair, get_pair_config  # type: ignore
    from mochipoyo_minimal_scanner import errors_frame, reader_metadata_frame, scan_pair_minimal_skeleton  # type: ignore
    from mochipoyo_notification_filter import NotificationEligibilityConfig, apply_notification_eligibility, split_notification_eligible  # type: ignore
    from mochipoyo_risk_enricher import RiskEnrichConfig  # type: ignore


def windows_long_path(path: str | Path) -> str:
    """Return a Windows extended-length path when running on Windows.

    The project often runs under the MT5 roaming profile path, which is already
    long.  Nested dry-loop outputs can exceed the classic MAX_PATH limit and
    pandas/open may raise FileNotFoundError even after the parent directory was
    created.  The \\?\ prefix avoids that Windows path-length edge case.
    """
    p = Path(path)
    if os.name != "nt":
        return str(p)
    text = str(p.resolve())
    if text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(windows_long_path(p), index=False, encoding="utf-8-sig")


def safe_pair_name(pair_name: str) -> str:
    return str(pair_name).lower()


def trigger_decisions(args: argparse.Namespace, csv_overrides: dict[str, str | None]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    state_path = Path(args.trigger_state_csv)
    previous = read_state(state_path)
    lookup = state_lookup(previous)
    allowed = allowed_for_symbol(args.symbol)
    pair_names: list[str] = []
    seen: set[str] = set()
    for row in allowed:
        pair = row["pair_name"]
        if pair not in seen:
            pair_names.append(pair)
            seen.add(pair)

    decisions: list[dict[str, Any]] = []
    for pair_name in pair_names:
        cfg = get_pair_config(pair_name)
        latest, meta = get_latest_trigger_close_time(
            pair_name=pair_name,
            cfg=cfg,
            csv_dir=args.csv_dir,
            csv_overrides=csv_overrides,
            csv_sep=args.csv_sep,
            tail_bars=int(args.trigger_tail_bars),
        )
        decisions.append(
            classify_pair(
                pair_name=pair_name,
                cfg=cfg,
                latest_close_time=latest,
                previous_row=lookup.get(pair_name),
                scan_on_initial_state=bool(args.scan_on_initial_state),
                meta=meta,
            )
        )
    decisions_df = pd.DataFrame(decisions)
    to_scan = decisions_df[decisions_df["should_scan"].fillna(False).astype(bool)].copy() if not decisions_df.empty else pd.DataFrame()
    return previous, decisions_df, to_scan


def tail_overrides(args: argparse.Namespace) -> dict[str, int]:
    values = {
        "M1": args.tail_m1,
        "M5": args.tail_m5,
        "M15": args.tail_m15,
        "H1": args.tail_h1,
        "H4": args.tail_h4,
        "D1": args.tail_d1,
    }
    return {tf: int(v) for tf, v in values.items() if v is not None and int(v) > 0}


def trigger_window_map(to_scan: pd.DataFrame) -> dict[str, dict[str, pd.Timestamp | None]]:
    out: dict[str, dict[str, pd.Timestamp | None]] = {}
    if to_scan.empty:
        return out
    for _, row in to_scan.iterrows():
        pair = str(row.get("pair_name", "")).strip().upper()
        if not pair:
            continue
        prev = pd.to_datetime(row.get("previous_close_time"), errors="coerce")
        latest = pd.to_datetime(row.get("latest_close_time"), errors="coerce")
        out[pair] = {
            "previous_close_time": None if pd.isna(prev) else pd.Timestamp(prev),
            "latest_close_time": None if pd.isna(latest) else pd.Timestamp(latest),
        }
    return out


def filter_to_trigger_window(df: pd.DataFrame, pair_name: str, to_scan: pd.DataFrame, *, enabled: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split notification rows into live-window OK and outside-window rows.

    Default live rule:
      previous_close_time < signal_close_time <= latest_close_time

    If previous_close_time is missing, no row is allowed into live notifications.
    That protects the initial-state case from sending historical candidates.
    """
    if df.empty:
        empty = df.copy()
        return empty, empty.copy()
    if not enabled:
        out = df.copy()
        out["live_window_status"] = "NOT_FILTERED"
        out["live_window_reject_reason"] = "trigger window filter disabled"
        return out, df.iloc[0:0].copy()

    windows = trigger_window_map(to_scan)
    window = windows.get(str(pair_name).strip().upper())
    work = df.copy()
    work["signal_close_time_dt"] = pd.to_datetime(work.get("signal_close_time"), errors="coerce")
    if not window or window.get("previous_close_time") is None or window.get("latest_close_time") is None:
        work["live_window_status"] = "OUTSIDE_TRIGGER_WINDOW"
        work["live_window_reject_reason"] = "missing trigger window"
        return work.iloc[0:0].copy(), work.drop(columns=["signal_close_time_dt"], errors="ignore")

    previous_close = window["previous_close_time"]
    latest_close = window["latest_close_time"]
    assert previous_close is not None
    assert latest_close is not None
    mask = (work["signal_close_time_dt"] > previous_close) & (work["signal_close_time_dt"] <= latest_close)
    accepted = work.loc[mask].copy()
    rejected = work.loc[~mask].copy()
    accepted["live_window_status"] = "IN_TRIGGER_WINDOW"
    accepted["live_window_reject_reason"] = "OK"
    rejected["live_window_status"] = "OUTSIDE_TRIGGER_WINDOW"
    rejected["live_window_reject_reason"] = (
        "requires previous_close_time < signal_close_time <= latest_close_time; "
        f"previous={previous_close.strftime('%Y-%m-%d %H:%M:%S')}; latest={latest_close.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    accepted = accepted.drop(columns=["signal_close_time_dt"], errors="ignore")
    rejected = rejected.drop(columns=["signal_close_time_dt"], errors="ignore")
    return accepted, rejected


def run_scans(args: argparse.Namespace, csv_overrides: dict[str, str | None], to_scan: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[Any]]:
    allowed = allowed_for_symbol(args.symbol)
    risk_config = RiskEnrichConfig(
        rr=float(args.risk_rr),
        gold_min_stop_distance=float(args.gold_min_stop_distance),
        btc_min_stop_distance=float(args.btc_min_stop_distance),
        btc_point_size=float(args.btc_point_size),
        btc_spread_caution_threshold=float(args.btc_spread_caution_threshold),
    )
    notif_config = NotificationEligibilityConfig(
        btc_max_spread_to_sl_ratio=float(args.btc_max_spread_to_sl_ratio),
        btc_min_effective_rr_after_spread=float(args.btc_min_effective_rr_after_spread),
    )

    results = []
    notification_ok_frames: list[pd.DataFrame] = []
    notification_outside_window_frames: list[pd.DataFrame] = []
    notification_marked_frames: list[pd.DataFrame] = []
    out_dir = Path(args.out_dir)
    scan_dir = out_dir / "scan"
    notif_dir = out_dir / "notification"
    scan_dir.mkdir(parents=True, exist_ok=True)
    notif_dir.mkdir(parents=True, exist_ok=True)

    for _, trig in to_scan.iterrows():
        pair_name = str(trig["pair_name"])
        pair_allowed = filter_allowed_slices_for_pair(allowed, pair_name)
        result = scan_pair_minimal_skeleton(
            pair_name,
            csv_dir=args.csv_dir,
            csv_overrides=csv_overrides,
            allowed_slices=pair_allowed,
            tail_bars_override=tail_overrides(args),
            csv_sep=args.csv_sep,
            enable_risk_enrich=True,
            risk_config=risk_config,
        )
        results.append(result)
        safe = safe_pair_name(pair_name)
        if not result.raw_candidates_df.empty:
            write_csv(result.raw_candidates_df, scan_dir / f"minimal_candidates_raw_{safe}.csv")
        if not result.normalized_candidates_df.empty:
            write_csv(result.normalized_candidates_df, scan_dir / f"minimal_candidates_normalized_{safe}.csv")
        if not result.risk_ok_candidates_df.empty:
            write_csv(result.risk_ok_candidates_df, scan_dir / f"minimal_candidates_risk_ok_{safe}.csv")
            marked = apply_notification_eligibility(result.risk_ok_candidates_df, config=notif_config)
            ok_all, ng = split_notification_eligible(marked)
            ok_live, ok_outside_window = filter_to_trigger_window(
                ok_all,
                pair_name,
                to_scan,
                enabled=not bool(args.disable_trigger_window_filter),
            )
            write_csv(marked, notif_dir / f"minimal_candidates_notification_marked_{safe}.csv")
            write_csv(ok_all, notif_dir / f"minimal_candidates_notification_ok_all_{safe}.csv")
            write_csv(ok_live, notif_dir / f"minimal_candidates_notification_ok_live_{safe}.csv")
            write_csv(ok_outside_window, notif_dir / f"minimal_candidates_notification_outside_trigger_window_{safe}.csv")
            write_csv(ng, notif_dir / f"minimal_candidates_notification_ng_{safe}.csv")
            notification_marked_frames.append(marked)
            if not ok_live.empty:
                notification_ok_frames.append(ok_live)
            if not ok_outside_window.empty:
                notification_outside_window_frames.append(ok_outside_window)
        if not result.risk_ng_candidates_df.empty:
            write_csv(result.risk_ng_candidates_df, scan_dir / f"minimal_candidates_risk_ng_{safe}.csv")

    if results:
        summary = pd.DataFrame([
            {
                "pair_name": r.pair_name,
                "scan_status": r.scan_status,
                "raw_candidates": len(r.raw_candidates_df),
                "normalized_candidates": len(r.normalized_candidates_df),
                "risk_ok_candidates": len(r.risk_ok_candidates_df),
                "risk_ng_candidates": len(r.risk_ng_candidates_df),
                "error_count": len(r.errors),
                "errors": ";".join(e.error_reason for e in r.errors),
            }
            for r in results
        ])
        meta = pd.concat([reader_metadata_frame(type("Batch", (), {"results": [r]})()) for r in results], ignore_index=True) if results else pd.DataFrame()
        errs = pd.concat([errors_frame(type("Batch", (), {"results": [r]})()) for r in results], ignore_index=True) if results else pd.DataFrame()
    else:
        summary = pd.DataFrame(columns=["pair_name", "scan_status", "raw_candidates", "normalized_candidates", "risk_ok_candidates", "risk_ng_candidates", "error_count", "errors"])
        meta = pd.DataFrame()
        errs = pd.DataFrame()

    write_csv(summary, scan_dir / "scan_summary.csv")
    write_csv(meta, scan_dir / "reader_metadata.csv")
    write_csv(errs, scan_dir / "scan_errors.csv")

    notification_ok = pd.concat(notification_ok_frames, ignore_index=True, sort=False) if notification_ok_frames else pd.DataFrame()
    notification_outside = pd.concat(notification_outside_window_frames, ignore_index=True, sort=False) if notification_outside_window_frames else pd.DataFrame()
    notification_marked = pd.concat(notification_marked_frames, ignore_index=True, sort=False) if notification_marked_frames else pd.DataFrame()
    write_csv(notification_marked, notif_dir / "notification_marked_all.csv")
    write_csv(notification_ok, notif_dir / "notification_ok_live_all.csv")
    write_csv(notification_outside, notif_dir / "notification_outside_trigger_window_all.csv")
    return summary, notification_ok, notification_outside, results


def apply_ledger(args: argparse.Namespace, notification_ok: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ledger_dir = Path(args.out_dir) / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    source = notification_ok.copy()
    if source.empty:
        classified = pd.DataFrame()
        to_send = pd.DataFrame()
        skipped = pd.DataFrame()
        append_rows = pd.DataFrame()
        write_csv(classified, ledger_dir / "notification_ledger_classified.csv")
        write_csv(to_send, ledger_dir / "notification_ledger_to_send.csv")
        write_csv(skipped, ledger_dir / "notification_ledger_skipped.csv")
        write_csv(append_rows, ledger_dir / "notification_ledger_append_preview.csv")
        return classified, to_send, skipped, append_rows

    ledger_before = load_existing_ledger(args.notification_ledger_csv)
    classified = classify_rows(source, ledger_before)
    append_rows = build_ledger_append_rows(classified, run_id=args.run_id)
    if args.commit_ledger:
        ledger_after = append_ledger(args.notification_ledger_csv, append_rows)
    else:
        ledger_after = ledger_before.copy()
    state = build_notification_state(ledger_after)
    to_send = classified[classified["ledger_status"] == STATUS_NEW].copy()
    skipped = classified[classified["ledger_status"] != STATUS_NEW].copy()
    write_csv(classified, ledger_dir / "notification_ledger_classified.csv")
    write_csv(to_send, ledger_dir / "notification_ledger_to_send.csv")
    write_csv(skipped, ledger_dir / "notification_ledger_skipped.csv")
    write_csv(append_rows, ledger_dir / "notification_ledger_append_preview.csv")
    write_csv(state, ledger_dir / "notification_ledger_state.csv")
    return classified, to_send, skipped, append_rows


def run_discord_dry_run(args: argparse.Namespace, to_send_csv: Path, to_send_rows: int) -> tuple[int, str]:
    if not args.discord_dry_run:
        return 0, "SKIPPED"
    if int(to_send_rows) <= 0:
        preview_dir = Path(args.out_dir) / "discord"
        preview_dir.mkdir(parents=True, exist_ok=True)
        (preview_dir / "discord_dryrun_stdout.txt").write_text("SKIPPED_NO_ROWS\n", encoding="utf-8")
        (preview_dir / "discord_dryrun_stderr.txt").write_text("", encoding="utf-8")
        return 0, "SKIPPED_NO_ROWS"
    preview_dir = Path(args.out_dir) / "discord"
    preview_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "scripts/send_mochipoyo_discord_messages.py",
        "--input-csv", str(to_send_csv),
        "--send-ledger-csv", str(preview_dir / "discord_dryrun_send_ledger.csv"),
        "--preview-txt", str(preview_dir / "discord_dryrun_preview.txt"),
        "--preview-json", str(preview_dir / "discord_dryrun_preview.json"),
        "--symbol", str(args.symbol),
        "--max-rows", str(args.discord_max_rows),
        "--style", str(args.discord_style),
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    (preview_dir / "discord_dryrun_stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (preview_dir / "discord_dryrun_stderr.txt").write_text(proc.stderr, encoding="utf-8")
    return int(proc.returncode), "OK" if proc.returncode == 0 else "ERROR"


def commit_trigger_state_after_success(args: argparse.Namespace, previous_state: pd.DataFrame, decisions_df: pd.DataFrame, success: bool) -> pd.DataFrame:
    if not args.commit_trigger_state:
        return previous_state.copy()
    state_after = build_updated_state(
        previous_state,
        decisions_df,
        commit_initialize_only=True,
        commit_scan_required=bool(success),
    )
    write_csv(state_after, args.trigger_state_csv)
    return state_after


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one GOLD minimal live flow pass.")
    p.add_argument("--csv-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--symbol", default="GOLD")
    p.add_argument("--trigger-state-csv", required=True)
    p.add_argument("--notification-ledger-csv", required=True)
    p.add_argument("--csv-sep", default="auto")
    p.add_argument("--trigger-tail-bars", type=int, default=20)
    p.add_argument("--scan-on-initial-state", action="store_true")
    p.add_argument("--commit-trigger-state", action="store_true")
    p.add_argument("--commit-ledger", action="store_true")
    p.add_argument("--run-id", default=None)
    p.add_argument("--discord-dry-run", action="store_true")
    p.add_argument("--discord-max-rows", type=int, default=5)
    p.add_argument("--discord-style", choices=["compact", "detailed"], default="compact")
    p.add_argument("--disable-trigger-window-filter", action="store_true", help="Unsafe/debug only: allow historical notification_ok rows into ledger.")
    p.add_argument("--tail-m1", type=int, default=12000)
    p.add_argument("--tail-m5", type=int, default=6000)
    p.add_argument("--tail-m15", type=int, default=5000)
    p.add_argument("--tail-h1", type=int, default=1500)
    p.add_argument("--tail-h4", type=int, default=1500)
    p.add_argument("--tail-d1", type=int, default=800)
    p.add_argument("--risk-rr", type=float, default=1.2)
    p.add_argument("--gold-min-stop-distance", type=float, default=1.0)
    p.add_argument("--btc-min-stop-distance", type=float, default=50.0)
    p.add_argument("--btc-point-size", type=float, default=0.01)
    p.add_argument("--btc-spread-caution-threshold", type=float, default=0.07)
    p.add_argument("--btc-max-spread-to-sl-ratio", type=float, default=0.07)
    p.add_argument("--btc-min-effective-rr-after-spread", type=float, default=1.0)
    p.add_argument("--gold-m1-csv")
    p.add_argument("--gold-m5-csv")
    p.add_argument("--gold-m15-csv")
    p.add_argument("--gold-h1-csv")
    p.add_argument("--gold-h4-csv")
    p.add_argument("--gold-d1-csv")
    p.add_argument("--btc-m1-csv")
    p.add_argument("--btc-m5-csv")
    p.add_argument("--btc-m15-csv")
    p.add_argument("--btc-h1-csv")
    p.add_argument("--btc-h4-csv")
    args = p.parse_args()
    if not args.run_id:
        args.run_id = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    return args


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_overrides = build_csv_overrides_from_args(args)

    previous_state, decisions_df, to_scan = trigger_decisions(args, csv_overrides)
    write_csv(decisions_df, out_dir / "pair_trigger_decisions.csv")
    write_csv(to_scan, out_dir / "pair_trigger_to_scan.csv")

    scan_summary, notification_ok, notification_outside, scan_results = run_scans(args, csv_overrides, to_scan)
    classified, to_send, skipped, append_rows = apply_ledger(args, notification_ok)
    to_send_csv = Path(args.out_dir) / "ledger" / "notification_ledger_to_send.csv"
    discord_returncode, discord_status = run_discord_dry_run(args, to_send_csv, to_send_rows=len(to_send))

    scan_errors = int(scan_summary["error_count"].sum()) if not scan_summary.empty and "error_count" in scan_summary.columns else 0
    success = bool(scan_errors == 0 and discord_returncode == 0)
    state_after = commit_trigger_state_after_success(args, previous_state, decisions_df, success=success)
    write_csv(state_after, out_dir / "pair_trigger_state_after.csv")

    summary = pd.DataFrame([
        {
            "run_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "run_id": args.run_id,
            "symbol": args.symbol,
            "pairs_total": int(len(decisions_df)),
            "pairs_to_scan": int(len(to_scan)),
            "scan_errors": scan_errors,
            "notification_ok_live_rows": int(len(notification_ok)),
            "notification_outside_trigger_window_rows": int(len(notification_outside)),
            "ledger_new_candidates": int(len(to_send)),
            "ledger_skipped_rows": int(len(skipped)),
            "ledger_append_rows": int(len(append_rows)),
            "commit_ledger": bool(args.commit_ledger),
            "discord_dry_run": bool(args.discord_dry_run),
            "discord_status": discord_status,
            "discord_returncode": int(discord_returncode),
            "commit_trigger_state": bool(args.commit_trigger_state),
            "trigger_state_advanced": bool(args.commit_trigger_state and success),
            "trigger_window_filter_enabled": not bool(args.disable_trigger_window_filter),
            "success": success,
        }
    ])
    write_csv(summary, out_dir / "minimal_live_once_summary.csv")
    print(summary.to_string(index=False))
    print(f"out_dir: {out_dir}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
