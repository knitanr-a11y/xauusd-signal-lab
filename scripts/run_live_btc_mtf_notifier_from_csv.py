from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from build_latest_btc_mtf_signal_payload_from_csv import (
    DEFAULT_H1_CSV,
    DEFAULT_H4_CSV,
    DEFAULT_M15_CSV,
    DEFAULT_M5_CSV,
    add_entry_hour,
    build_btc_mtf_payload,
    build_m15_runner_df,
    detect_btc_scalp_m5_reentry_filtered,
    parse_int_set,
    resolve_path,
    signal_item,
)
from build_latest_signal_payload_from_csv import DEFAULT_HISTORY_CSV, DEFAULT_OUT_DIR, PROJECT_ROOT, detect_btc_runner
from search_btc_mtf_extra_edges import add_indicators, join_context
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "live_payloads" / "notified_signals_ledger.csv"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_notification_key(symbol: str, signal_time: str, signal: dict[str, Any]) -> str:
    return "|".join([symbol, signal_time, str(signal.get("strategy_label")), str(signal.get("side"))])


def load_notified_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    if "notification_key" not in df.columns:
        return set()
    return set(df["notification_key"].dropna().astype(str).tolist())


def append_ledger_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fieldnames = [
        "notified_at",
        "notification_key",
        "symbol_group",
        "time",
        "strategy_label",
        "signal_model",
        "portfolio_rank",
        "side",
        "rr",
        "risk_atr",
        "source_tf",
        "overlap_detected",
        "overlap_signal_count",
        "overlap_labels",
        "discord_sent",
        "dry_run",
    ]
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_payload_json(out_dir: Path, payload: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    key = str(payload.get("notification_key", "signal")).replace("|", "_").replace(":", "").replace(" ", "_")
    path = out_dir / f"notify_payload_{key}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return path


def send_discord_message(webhook_url: str, content: str) -> None:
    data = json.dumps({"content": content}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = getattr(response, "status", None)
            if status is not None and not (200 <= int(status) < 300):
                raise RuntimeError(f"Discord webhook returned status={status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord webhook HTTPError status={exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Discord webhook URLError: {exc}") from exc


def candidate_snapshot(signal: dict[str, Any], *, source_tf: str) -> dict[str, Any]:
    return {
        "strategy_label": signal.get("strategy_label"),
        "signal_model": signal.get("signal_model"),
        "portfolio_rank": signal.get("portfolio_rank"),
        "side": signal.get("side"),
        "rr": signal.get("rr"),
        "risk_atr": signal.get("risk_atr"),
        "source_tf": source_tf,
    }


def format_discord_message(payload: dict[str, Any]) -> str:
    cur = payload.get("current_signal_snapshot", {})
    strategy = cur.get("strategy_label", "")
    side = cur.get("side", "")
    rr = cur.get("rr", "")
    risk_atr = cur.get("risk_atr", "")
    source_tf = cur.get("source_tf", payload.get("source_tf", ""))
    confidence = payload.get("confidence_hint", "single_signal")

    lines = [
        "📣 BTC Trade Signal",
        f"Time: {payload.get('time', '')}",
        f"Signal: {strategy} {side}",
        f"Source TF: {source_tf}",
        f"RR: {rr} / risk_atr: {risk_atr}",
        f"Confidence hint: {confidence}",
    ]

    if cur.get("entry_hour") is not None:
        lines.append(f"Entry hour: {cur.get('entry_hour')}")
    if cur.get("entry_time_proxy"):
        lines.append(f"Entry time proxy: {cur.get('entry_time_proxy')}")
    if cur.get("lot_hint"):
        lines.append(f"Lot hint: {cur.get('lot_hint')}")
    if cur.get("ai_risk_profile"):
        lines.append(f"AI risk profile: {cur.get('ai_risk_profile')}")

    if payload.get("overlap_detected"):
        lines.append("Overlap: YES (" + " + ".join(payload.get("overlap_labels", [])) + ")")
    else:
        lines.append("Overlap: no")

    lines.append("AI review: not connected yet")
    return "\n".join(lines)


def load_contexts(m5_csv: Path, m15_csv: Path, h1_csv: Path, h4_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    m5 = add_indicators(read_ohlc_live_csv(m5_csv))
    m15 = add_indicators(read_ohlc_live_csv(m15_csv))
    h1 = add_indicators(read_ohlc_live_csv(h1_csv))
    h4 = add_indicators(read_ohlc_live_csv(h4_csv))
    m5_ctx = join_context(m5, [(m15, "m15"), (h1, "h1"), (h4, "h4")])
    m5_ctx = add_entry_hour(m5_ctx)
    m15_runner_df = build_m15_runner_df(m15, h1)
    return m5_ctx, m15_runner_df


def collect_unnotified_payloads(
    *,
    m5_ctx: pd.DataFrame,
    m15_runner_df: pd.DataFrame,
    history_csv: Path,
    notified_keys: set[str],
    scan_recent_m5_bars: int,
    scan_recent_m15_bars: int,
    bar_offset: int,
    exclude_entry_hours: set[int],
) -> list[tuple[int, dict[str, Any]]]:
    payloads: list[tuple[int, dict[str, Any]]] = []

    # M5 scalp candidates.
    m5_end = len(m5_ctx) - 1 - bar_offset
    m5_start = max(300, m5_end - scan_recent_m5_bars + 1)
    for idx in range(m5_start, m5_end + 1):
        row = m5_ctx.iloc[idx]
        signal = detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours)
        if signal is None:
            continue
        payload = build_btc_mtf_payload(row, signal, history_csv, selection_mode=f"live_btc_mtf_m5_scan_{scan_recent_m5_bars}", source_tf="M5")
        payload["notification_key"] = make_notification_key("BTC", str(payload.get("time")), signal)
        payload["overlap_detected"] = False
        payload["overlap_signal_count"] = 1
        payload["overlap_labels"] = [str(signal.get("strategy_label"))]
        payload["overlap_candidates"] = [candidate_snapshot(signal, source_tf="M5")]
        payload["confidence_hint"] = "single_signal"
        if str(payload["notification_key"]) not in notified_keys:
            payloads.append((idx, payload))

    # M15 BTC RUNNER candidates.
    m15_end = len(m15_runner_df) - 1 - bar_offset
    m15_start = max(220, m15_end - scan_recent_m15_bars + 1)
    for idx in range(m15_start, m15_end + 1):
        row = m15_runner_df.iloc[idx]
        signal = detect_btc_runner(row)
        if signal is None:
            continue
        payload = build_btc_mtf_payload(row, signal, history_csv, selection_mode=f"live_btc_mtf_m15_scan_{scan_recent_m15_bars}", source_tf="M15")
        payload["notification_key"] = make_notification_key("BTC", str(payload.get("time")), signal)
        payload["overlap_detected"] = False
        payload["overlap_signal_count"] = 1
        payload["overlap_labels"] = [str(signal.get("strategy_label"))]
        payload["overlap_candidates"] = [candidate_snapshot(signal, source_tf="M15")]
        payload["confidence_hint"] = "single_signal"
        if str(payload["notification_key"]) not in notified_keys:
            payloads.append((idx, payload))

    payloads.sort(key=lambda x: str(x[1].get("time", "")))
    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(description="Live BTC MTF CSV notifier with duplicate-notification guard.")
    parser.add_argument("--m5-csv", type=Path, default=DEFAULT_M5_CSV)
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--h4-csv", type=Path, default=DEFAULT_H4_CSV)
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY_CSV)
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--scan-recent-m5-bars", type=int, default=60, help="Use a small value in live mode to avoid backfilling old M5 signals.")
    parser.add_argument("--scan-recent-m15-bars", type=int, default=20, help="Use a small value in live mode to avoid backfilling old M15 signals.")
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--exclude-entry-hours", default="8,13,20,21")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mark-dry-run-notified", action="store_true")
    parser.add_argument("--send-discord", action="store_true")
    parser.add_argument("--discord-webhook-url", default=None)
    parser.add_argument("--max-notifications", type=int, default=5)
    args = parser.parse_args()

    m5_csv = resolve_path(args.m5_csv)
    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    h4_csv = resolve_path(args.h4_csv)
    history_csv = resolve_path(args.history_csv)
    ledger_csv = resolve_path(args.ledger_csv)
    out_dir = resolve_path(args.out_dir)
    exclude_entry_hours = parse_int_set(args.exclude_entry_hours)

    m5_ctx, m15_runner_df = load_contexts(m5_csv, m15_csv, h1_csv, h4_csv)
    notified_keys = load_notified_keys(ledger_csv)
    payloads = collect_unnotified_payloads(
        m5_ctx=m5_ctx,
        m15_runner_df=m15_runner_df,
        history_csv=history_csv,
        notified_keys=notified_keys,
        scan_recent_m5_bars=args.scan_recent_m5_bars,
        scan_recent_m15_bars=args.scan_recent_m15_bars,
        bar_offset=args.bar_offset,
        exclude_entry_hours=exclude_entry_hours,
    )
    if args.max_notifications > 0:
        payloads = payloads[-args.max_notifications :]

    webhook_url = args.discord_webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if args.send_discord and not webhook_url:
        raise ValueError("--send-discord requires --discord-webhook-url or DISCORD_WEBHOOK_URL environment variable.")

    print("Project root:", PROJECT_ROOT)
    print("Symbol: BTC")
    print("M5 CSV:", m5_csv)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("H4 CSV:", h4_csv)
    print("History CSV:", history_csv)
    print("Ledger CSV:", ledger_csv)
    print("Rows:", "M5", len(m5_ctx), "M15", len(m15_runner_df))
    print("Scan recent M5 bars:", args.scan_recent_m5_bars)
    print("Scan recent M15 bars:", args.scan_recent_m15_bars)
    print("Exclude entry hours:", sorted(exclude_entry_hours))
    print("Already notified keys:", len(notified_keys))
    print("Unnotified signals selected:", len(payloads))
    print("Dry run:", bool(args.dry_run))
    print("Send Discord:", bool(args.send_discord))

    ledger_rows: list[dict[str, Any]] = []
    for idx, payload in payloads:
        message = format_discord_message(payload)
        payload_path = write_payload_json(out_dir, payload)
        print("\n" + "=" * 100)
        print("BTC notification candidate")
        print("=" * 100)
        print("idx:", idx)
        print("payload:", payload_path)
        print(message)

        discord_sent = False
        if args.send_discord:
            send_discord_message(webhook_url, message)
            discord_sent = True
            print("Discord sent: true")

        cur = payload.get("current_signal_snapshot", {})
        should_write_ledger = bool(args.send_discord) or bool(args.mark_dry_run_notified)
        if should_write_ledger:
            ledger_rows.append(
                {
                    "notified_at": now_str(),
                    "notification_key": payload.get("notification_key"),
                    "symbol_group": payload.get("symbol_group"),
                    "time": payload.get("time"),
                    "strategy_label": cur.get("strategy_label"),
                    "signal_model": cur.get("signal_model"),
                    "portfolio_rank": cur.get("portfolio_rank"),
                    "side": cur.get("side"),
                    "rr": cur.get("rr"),
                    "risk_atr": cur.get("risk_atr"),
                    "source_tf": cur.get("source_tf"),
                    "overlap_detected": payload.get("overlap_detected"),
                    "overlap_signal_count": payload.get("overlap_signal_count"),
                    "overlap_labels": "+".join(payload.get("overlap_labels", [])),
                    "discord_sent": discord_sent,
                    "dry_run": bool(args.dry_run),
                }
            )

    append_ledger_rows(ledger_csv, ledger_rows)
    print("\nLedger rows appended:", len(ledger_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
