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

from build_latest_signal_payload_from_csv import (
    DEFAULT_HISTORY_CSV,
    PROJECT_ROOT,
    add_indicators,
    build_payload,
    detect_btc_runner,
    detect_gold_abc,
    detect_gold_extra,
    join_h1,
    read_ohlc,
    resolve_path,
)

DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "live_payloads" / "notified_signals_ledger.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "results" / "live_payloads"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def row_time_str(row: pd.Series) -> str:
    value = row.get("time")
    return value.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(value) else ""


def detect_signal_candidates(symbol: str, row: pd.Series) -> list[dict[str, Any]]:
    """Return all signal candidates for one selected M15 bar.

    The final notification still has one primary signal, but overlap candidates are preserved
    because overlapping strategies may imply stronger confirmation.
    """
    if symbol == "BTC":
        signal = detect_btc_runner(row)
        return [signal] if signal is not None else []

    candidates: list[dict[str, Any]] = []
    abc = detect_gold_abc(row)
    if abc is not None:
        candidates.append(abc)
    extra = detect_gold_extra(row)
    if extra is not None:
        candidates.append(extra)
    return candidates


def primary_signal_from_candidates(symbol: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    if symbol == "BTC":
        return candidates[0]

    priority = {
        "GOLD_ABC_V3": 1,
        "GOLD_EXTRA_HIGH_RSI_STOCH": 2,
        "GOLD_EXTRA_BB_BALANCE": 3,
        "GOLD_COUNTER_BUY_ONLY": 4,
    }
    return sorted(candidates, key=lambda x: priority.get(str(x.get("strategy_label")), 99))[0]


def candidate_snapshot(signal: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "strategy_label": signal.get("strategy_label"),
        "signal_model": signal.get("signal_model"),
        "portfolio_rank": signal.get("portfolio_rank"),
        "side": signal.get("side"),
        "rr": signal.get("rr"),
        "risk_atr": signal.get("risk_atr"),
    }
    if signal.get("abc_source"):
        item["abc_source"] = signal.get("abc_source")
    return item


def make_notification_key(symbol: str, signal_time: str, signal: dict[str, Any]) -> str:
    return "|".join(
        [
            symbol,
            signal_time,
            str(signal.get("strategy_label")),
            str(signal.get("side")),
        ]
    )


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


def build_notification_payload(
    *,
    symbol: str,
    row: pd.Series,
    primary: dict[str, Any],
    candidates: list[dict[str, Any]],
    history_csv: Path,
    selection_mode: str,
) -> dict[str, Any]:
    payload = build_payload(symbol, row, primary, history_csv, selection_mode=selection_mode)
    signal_time = payload.get("time", row_time_str(row))
    snapshots = [candidate_snapshot(x) for x in candidates]
    overlap_detected = len(candidates) >= 2
    overlap_labels = [str(x.get("strategy_label")) for x in candidates]

    payload["notification_key"] = make_notification_key(symbol, signal_time, primary)
    payload["overlap_detected"] = overlap_detected
    payload["overlap_signal_count"] = len(candidates)
    payload["overlap_labels"] = overlap_labels
    payload["overlap_candidates"] = snapshots
    payload["confidence_hint"] = "overlap_confirmed" if overlap_detected else "single_signal"
    payload["ai_review_required"] = True
    payload["ai_review_status"] = "not_connected_yet"
    return payload


def format_discord_message(payload: dict[str, Any]) -> str:
    cur = payload.get("current_signal_snapshot", {})
    symbol = payload.get("symbol_group", "")
    time = payload.get("time", "")
    strategy = cur.get("strategy_label", "")
    side = cur.get("side", "")
    rr = cur.get("rr", "")
    risk_atr = cur.get("risk_atr", "")
    priority = payload.get("discord_priority", "normal")
    confidence = payload.get("confidence_hint", "single_signal")
    regime = payload.get("regime_guard", {})
    danger = regime.get("gold_abc_buy_danger_regime", False)
    reason = regime.get("reason", "")

    lines = [
        "📣 Trade Signal",
        f"Symbol: {symbol}",
        f"Time: {time}",
        f"Signal: {strategy} {side}",
        f"RR: {rr} / risk_atr: {risk_atr}",
        f"Priority: {priority}",
        f"Confidence hint: {confidence}",
    ]

    if cur.get("abc_source"):
        lines.append(f"ABC source: {cur.get('abc_source')}")

    if payload.get("overlap_detected"):
        labels = " + ".join(payload.get("overlap_labels", []))
        lines.append(f"Overlap: YES ({labels})")
    else:
        lines.append("Overlap: no")

    if danger:
        lines.append("⚠️ GOLD ABC BUY danger regime: TRUE")
        lines.append(f"Regime reason: {reason}")
    else:
        lines.append(f"Regime guard: {reason}")

    lines.append("AI review: not connected yet")
    return "\n".join(lines)


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


def scan_rows(df: pd.DataFrame, *, scan_recent_bars: int, bar_offset: int) -> range:
    end_idx = len(df) - 1 - bar_offset
    if end_idx < 220:
        raise ValueError(f"Selected end_idx too early for indicators: end_idx={end_idx}")
    start_idx = max(220, end_idx - scan_recent_bars + 1)
    return range(start_idx, end_idx + 1)


def write_payload_json(out_dir: Path, payload: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    key = str(payload.get("notification_key", "signal")).replace("|", "_").replace(":", "").replace(" ", "_")
    path = out_dir / f"notify_payload_{key}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Live CSV signal notifier foundation with duplicate-notification guard.")
    parser.add_argument("--symbol", choices=["GOLD", "BTC"], required=True)
    parser.add_argument("--m15-csv", type=Path, required=True)
    parser.add_argument("--h1-csv", type=Path, required=True)
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY_CSV)
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--scan-recent-bars", type=int, default=20, help="Use a small value in live mode to avoid backfilling old signals.")
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Print notifications without sending Discord or writing ledger unless --mark-dry-run-notified is used.")
    parser.add_argument("--mark-dry-run-notified", action="store_true", help="Write dry-run rows to ledger. Usually keep this off while testing.")
    parser.add_argument("--send-discord", action="store_true", help="Send Discord webhook messages for unnotified signals.")
    parser.add_argument("--discord-webhook-url", default=None, help="Optional. If omitted, DISCORD_WEBHOOK_URL env var is used.")
    parser.add_argument("--max-notifications", type=int, default=5, help="Safety cap for one run.")
    args = parser.parse_args()

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    history_csv = resolve_path(args.history_csv)
    ledger_csv = resolve_path(args.ledger_csv)
    out_dir = resolve_path(args.out_dir)

    m15 = add_indicators(read_ohlc(m15_csv))
    h1 = add_indicators(read_ohlc(h1_csv))
    df = join_h1(m15, h1)
    if len(df) < 250:
        raise ValueError("Not enough rows. Need at least about 250 M15 bars for indicators.")

    notified_keys = load_notified_keys(ledger_csv)
    rows_to_notify: list[tuple[int, pd.Series, dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = []

    for idx in scan_rows(df, scan_recent_bars=args.scan_recent_bars, bar_offset=args.bar_offset):
        row = df.iloc[idx]
        candidates = detect_signal_candidates(args.symbol, row)
        primary = primary_signal_from_candidates(args.symbol, candidates)
        if primary is None:
            continue
        payload = build_notification_payload(
            symbol=args.symbol,
            row=row,
            primary=primary,
            candidates=candidates,
            history_csv=history_csv,
            selection_mode=f"live_scan_recent_bars_{args.scan_recent_bars}",
        )
        key = str(payload.get("notification_key"))
        if key in notified_keys:
            continue
        rows_to_notify.append((idx, row, primary, candidates, payload))

    if args.max_notifications > 0:
        rows_to_notify = rows_to_notify[-args.max_notifications :]

    webhook_url = args.discord_webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if args.send_discord and not webhook_url:
        raise ValueError("--send-discord requires --discord-webhook-url or DISCORD_WEBHOOK_URL environment variable.")

    print("Project root:", PROJECT_ROOT)
    print("Symbol:", args.symbol)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("History CSV:", history_csv)
    print("Ledger CSV:", ledger_csv)
    print("Rows:", len(df))
    print("Scan recent bars:", args.scan_recent_bars)
    print("Already notified keys:", len(notified_keys))
    print("Unnotified signals selected:", len(rows_to_notify))
    print("Dry run:", bool(args.dry_run))
    print("Send Discord:", bool(args.send_discord))

    ledger_rows: list[dict[str, Any]] = []
    for idx, row, primary, candidates, payload in rows_to_notify:
        message = format_discord_message(payload)
        payload_path = write_payload_json(out_dir, payload)
        print("\n" + "=" * 100)
        print("Notification candidate")
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
                    "overlap_detected": payload.get("overlap_detected"),
                    "overlap_signal_count": payload.get("overlap_signal_count"),
                    "overlap_labels": "+".join(payload.get("overlap_labels", [])),
                    "discord_sent": discord_sent,
                    "dry_run": bool(args.dry_run),
                }
            )

    append_ledger_rows(ledger_csv, ledger_rows)
    if ledger_rows:
        print("\nLedger rows appended:", len(ledger_rows))
    else:
        print("\nLedger rows appended: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
