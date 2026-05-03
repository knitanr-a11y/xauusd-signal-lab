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

import numpy as np
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
)
from build_latest_signal_payload_from_csv import DEFAULT_HISTORY_CSV, DEFAULT_OUT_DIR, PROJECT_ROOT, detect_btc_runner
from search_btc_mtf_extra_edges import add_indicators, join_context
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "live_payloads" / "notified_signals_ledger.csv"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DISCORD_USER_AGENT = "xauusd-signal-lab/1.0 (+https://github.com/knitanr-a11y/xauusd-signal-lab)"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_env_file(path: Path) -> None:
    """Minimal .env loader without external dependencies."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def row_number(row: pd.Series, key: str) -> float:
    try:
        value = float(row.get(key, np.nan))
    except Exception:
        return float("nan")
    return value if np.isfinite(value) else float("nan")


def make_notification_key(symbol: str, signal_time: str, signal: dict[str, Any], *, notification_type: str = "signal") -> str:
    prefix = "" if notification_type == "signal" else f"{notification_type.upper()}|"
    return prefix + "|".join([symbol, signal_time, str(signal.get("strategy_label")), str(signal.get("side"))])


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
        "notification_type",
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
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": DISCORD_USER_AGENT,
        },
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


def readable_strategy(strategy: str, source_tf: str) -> str:
    if strategy == "BTC_RUNNER_RR2_RISK1":
        return "BTC RUNNER（高信頼・低頻度）"
    if strategy == "BTC_SCALP_H1_M5_REENTRY_FILTERED_RR2_RISK0.8":
        return "BTC M5追加ルール（高頻度・ロット小さめ候補）"
    if strategy == "BTC_SCALP_H1_M5_REENTRY_FILTERED_STANDBY":
        return "BTC M5追加ルールのスタンバイ"
    return f"{strategy}（{source_tf}）"


def readable_side(side: str) -> str:
    side_upper = str(side).upper()
    if side_upper == "BUY":
        return "BUY（買い）"
    if side_upper == "SELL":
        return "SELL（売り）"
    return side


def format_discord_message(payload: dict[str, Any]) -> str:
    cur = payload.get("current_signal_snapshot", {})
    strategy = str(cur.get("strategy_label", ""))
    side = str(cur.get("side", ""))
    rr = cur.get("rr", "")
    risk_atr = cur.get("risk_atr", "")
    source_tf = str(cur.get("source_tf", payload.get("source_tf", "")))
    signal_time = payload.get("time", "")
    overlap = bool(payload.get("overlap_detected"))
    entry_time = cur.get("entry_time_proxy") or signal_time
    notification_type = str(payload.get("notification_type", "signal"))

    if notification_type == "standby":
        title_icon = "🟡"
        title = f"{title_icon} **BTC {readable_side(side)} スタンバイ**"
        status_line = "状態: あと1条件でシグナル化する可能性"
    else:
        title_icon = "🟢" if side.upper() == "BUY" else "🔴" if side.upper() == "SELL" else "📣"
        title = f"{title_icon} **BTC {readable_side(side)} シグナル**"
        status_line = "状態: シグナル確定"

    risk_note = "ロット小さめ候補" if cur.get("lot_hint") == "reduced_candidate" else "通常候補"
    ai_note = "未接続（次工程で追加）" if payload.get("ai_review_status") == "not_connected_yet" else str(payload.get("ai_review_status", ""))

    lines = [
        title,
        "",
        status_line,
        f"時刻: {signal_time}",
        f"エントリー目安: {entry_time}",
        f"ルール: {readable_strategy(strategy, source_tf)}",
        f"時間足: {source_tf}",
        f"条件: RR {rr} / SL幅 ATR×{risk_atr}",
        f"運用メモ: {risk_note}",
    ]

    if cur.get("entry_hour") is not None:
        lines.append(f"時間フィルタ: {cur.get('entry_hour')}時 → 通過")

    if notification_type == "standby":
        met = cur.get("standby_met_conditions", [])
        missing = cur.get("standby_missing_conditions", [])
        if met:
            lines.append("満たしている条件: " + " / ".join(met))
        if missing:
            lines.append("不足条件: " + " / ".join(missing))
        lines.append("次のM5確定足でシグナル化するか確認")
    else:
        if overlap:
            lines.append("重複: あり（" + " + ".join(payload.get("overlap_labels", [])) + "）")
        else:
            lines.append("重複: なし")

    lines.extend(["", f"AI評価: {ai_note}", f"内部名: {strategy}"])
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


def make_btc_scalp_standby_signal(side: str, *, met: list[str], missing: list[str], exclude_entry_hours: set[int]) -> dict[str, Any]:
    return {
        "side": side,
        "signal_model": "BTC_SCALP_H1_M5_REENTRY_FILTERED_STANDBY",
        "strategy_label": "BTC_SCALP_H1_M5_REENTRY_FILTERED_STANDBY",
        "portfolio_rank": "BTC_SCALP_M5_STANDBY",
        "rr": 2.0,
        "risk_atr": 0.8,
        "base_tf": "M5",
        "ai_review_required": False,
        "ai_review_mode": "standby",
        "ai_risk_profile": "btc_m5_scalp_standby",
        "lot_hint": "reduced_candidate",
        "exclude_entry_hours": sorted(exclude_entry_hours),
        "standby_met_conditions": met,
        "standby_missing_conditions": missing,
    }


def detect_btc_scalp_m5_reentry_standby(row: pd.Series, *, exclude_entry_hours: set[int]) -> dict[str, Any] | None:
    if detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours) is not None:
        return None

    entry_hour_value = row.get("entry_hour")
    if pd.isna(entry_hour_value):
        return None
    entry_hour = int(entry_hour_value)
    if entry_hour in exclude_entry_hours:
        return None

    h1_bull = row_number(row, "h1_ema20") > row_number(row, "h1_ema50") and (row_number(row, "h1_macd_hist") > 0 or row_number(row, "h1_macd_delta3") > 0)
    h1_bear = row_number(row, "h1_ema20") < row_number(row, "h1_ema50") and (row_number(row, "h1_macd_hist") < 0 or row_number(row, "h1_macd_delta3") < 0)
    m15_ok_buy = row_number(row, "m15_close") >= row_number(row, "m15_ema20") - 0.25 * row_number(row, "m15_atr14") and row_number(row, "m15_macd_delta3") > -0.02
    m15_ok_sell = row_number(row, "m15_close") <= row_number(row, "m15_ema20") + 0.25 * row_number(row, "m15_atr14") and row_number(row, "m15_macd_delta3") < 0.02
    not_extended_m5 = abs(row_number(row, "close_change_6_atr")) <= 1.60
    gap_buy = -0.20 <= row_number(row, "close_ema8_gap_atr") <= 0.70
    gap_sell = -0.70 <= row_number(row, "close_ema8_gap_atr") <= 0.20

    checks = {
        "BUY": {
            "direction_ok": h1_bull,
            "m15_ok": m15_ok_buy,
            "not_extended": not_extended_m5,
            "gap_ok": gap_buy,
            "ema8_reclaim": row_number(row, "low") <= row_number(row, "ema8") + 0.30 * row_number(row, "atr14") and row_number(row, "close") > row_number(row, "ema8"),
            "macd_reaccel": row_number(row, "macd_delta") > 0 and row_number(row, "macd_delta3") > 0,
            "rci_turn": row_number(row, "rci9") <= 30 and row_number(row, "rci9_delta") > 0 and row_number(row, "rci26") >= -75,
        },
        "SELL": {
            "direction_ok": h1_bear,
            "m15_ok": m15_ok_sell,
            "not_extended": not_extended_m5,
            "gap_ok": gap_sell,
            "ema8_reclaim": row_number(row, "high") >= row_number(row, "ema8") - 0.30 * row_number(row, "atr14") and row_number(row, "close") < row_number(row, "ema8"),
            "macd_reaccel": row_number(row, "macd_delta") < 0 and row_number(row, "macd_delta3") < 0,
            "rci_turn": row_number(row, "rci9") >= -30 and row_number(row, "rci9_delta") < 0 and row_number(row, "rci26") <= 75,
        },
    }
    labels = {
        "direction_ok": "H1方向",
        "m15_ok": "M15状態",
        "not_extended": "伸びすぎ回避",
        "gap_ok": "EMA8距離",
        "ema8_reclaim": "M5 EMA8再取得",
        "macd_reaccel": "M5 MACD再加速",
        "rci_turn": "M5 RCI反転",
    }

    for side, side_checks in checks.items():
        base_keys = ["direction_ok", "m15_ok", "not_extended", "gap_ok"]
        trigger_keys = ["ema8_reclaim", "macd_reaccel", "rci_turn"]
        if not all(side_checks[k] for k in base_keys):
            continue
        trigger_met = [k for k in trigger_keys if side_checks[k]]
        trigger_missing = [k for k in trigger_keys if not side_checks[k]]
        if len(trigger_met) == 2 and len(trigger_missing) == 1:
            met = [labels[k] for k in base_keys + trigger_met]
            missing = [labels[k] for k in trigger_missing]
            return make_btc_scalp_standby_signal(side, met=met, missing=missing, exclude_entry_hours=exclude_entry_hours)
    return None


def build_standby_payload(row: pd.Series, signal: dict[str, Any], *, notification_type: str) -> dict[str, Any]:
    signal_time = row.get("time").strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row.get("time")) else ""
    entry_time_proxy = row.get("entry_time_proxy").strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row.get("entry_time_proxy")) else signal_time
    current = {
        "symbol_group": "BTC",
        "portfolio_rank": signal["portfolio_rank"],
        "strategy_label": signal["strategy_label"],
        "signal_model": signal["signal_model"],
        "side": signal["side"],
        "entry_time": signal_time,
        "time": signal_time,
        "entry_time_proxy": entry_time_proxy,
        "entry_hour": None if pd.isna(row.get("entry_hour")) else int(row.get("entry_hour")),
        "close": float(row.get("close")),
        "atr14": float(row.get("atr14")),
        "rr": signal["rr"],
        "risk_atr": signal["risk_atr"],
        "source_tf": "M5",
        "lot_hint": signal.get("lot_hint", "reduced_candidate"),
        "ai_review_mode": signal.get("ai_review_mode", "standby"),
        "ai_risk_profile": signal.get("ai_risk_profile", "btc_m5_scalp_standby"),
        "standby_met_conditions": signal.get("standby_met_conditions", []),
        "standby_missing_conditions": signal.get("standby_missing_conditions", []),
    }
    return {
        "payload_type": "latest_btc_mtf_csv_standby_check",
        "notification_type": notification_type,
        "symbol_group": "BTC",
        "signal_found": True,
        "selection_mode": "standby_scan",
        "time": signal_time,
        "source_tf": "M5",
        "current_signal_snapshot": current,
        "ai_review_required": False,
        "ai_review_status": "not_connected_yet",
        "discord_priority": "standby",
        "overlap_detected": False,
        "overlap_signal_count": 1,
        "overlap_labels": [signal["strategy_label"]],
        "overlap_candidates": [candidate_snapshot(signal, source_tf="M5")],
        "confidence_hint": "standby",
    }


def collect_unnotified_payloads(
    *,
    m5_ctx: pd.DataFrame,
    m15_runner_df: pd.DataFrame,
    history_csv: Path,
    notified_keys: set[str],
    scan_recent_m5_bars: int,
    scan_recent_m15_bars: int,
    scan_recent_standby_m5_bars: int,
    bar_offset: int,
    exclude_entry_hours: set[int],
    enable_standby: bool,
) -> list[tuple[int, dict[str, Any]]]:
    payloads: list[tuple[int, dict[str, Any]]] = []

    # M5 scalp confirmed signals.
    m5_end = len(m5_ctx) - 1 - bar_offset
    m5_start = max(300, m5_end - scan_recent_m5_bars + 1)
    for idx in range(m5_start, m5_end + 1):
        row = m5_ctx.iloc[idx]
        signal = detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours)
        if signal is None:
            continue
        payload = build_btc_mtf_payload(row, signal, history_csv, selection_mode=f"live_btc_mtf_m5_scan_{scan_recent_m5_bars}", source_tf="M5")
        payload["notification_type"] = "signal"
        payload["notification_key"] = make_notification_key("BTC", str(payload.get("time")), signal, notification_type="signal")
        payload["overlap_detected"] = False
        payload["overlap_signal_count"] = 1
        payload["overlap_labels"] = [str(signal.get("strategy_label"))]
        payload["overlap_candidates"] = [candidate_snapshot(signal, source_tf="M5")]
        payload["confidence_hint"] = "single_signal"
        if str(payload["notification_key"]) not in notified_keys:
            payloads.append((idx, payload))

    # M5 scalp standby signals.
    if enable_standby:
        standby_start = max(300, m5_end - scan_recent_standby_m5_bars + 1)
        for idx in range(standby_start, m5_end + 1):
            row = m5_ctx.iloc[idx]
            signal = detect_btc_scalp_m5_reentry_standby(row, exclude_entry_hours=exclude_entry_hours)
            if signal is None:
                continue
            payload = build_standby_payload(row, signal, notification_type="standby")
            payload["notification_key"] = make_notification_key("BTC", str(payload.get("time")), signal, notification_type="standby")
            if str(payload["notification_key"]) not in notified_keys:
                payloads.append((idx, payload))

    # M15 BTC RUNNER confirmed signals.
    m15_end = len(m15_runner_df) - 1 - bar_offset
    m15_start = max(220, m15_end - scan_recent_m15_bars + 1)
    for idx in range(m15_start, m15_end + 1):
        row = m15_runner_df.iloc[idx]
        signal = detect_btc_runner(row)
        if signal is None:
            continue
        payload = build_btc_mtf_payload(row, signal, history_csv, selection_mode=f"live_btc_mtf_m15_scan_{scan_recent_m15_bars}", source_tf="M15")
        payload["notification_type"] = "signal"
        payload["notification_key"] = make_notification_key("BTC", str(payload.get("time")), signal, notification_type="signal")
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
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--scan-recent-m5-bars", type=int, default=60)
    parser.add_argument("--scan-recent-m15-bars", type=int, default=20)
    parser.add_argument("--scan-recent-standby-m5-bars", type=int, default=12, help="Standby check range. 12 M5 bars = about 1 hour.")
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--exclude-entry-hours", default="8,13,20,21")
    parser.add_argument("--disable-standby", action="store_true", help="Disable yellow standby notifications.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mark-dry-run-notified", action="store_true")
    parser.add_argument("--send-discord", action="store_true")
    parser.add_argument("--discord-webhook-url", default=None)
    parser.add_argument("--max-notifications", type=int, default=5)
    args = parser.parse_args()

    env_file = resolve_path(args.env_file)
    load_env_file(env_file)

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
        scan_recent_standby_m5_bars=args.scan_recent_standby_m5_bars,
        bar_offset=args.bar_offset,
        exclude_entry_hours=exclude_entry_hours,
        enable_standby=not args.disable_standby,
    )
    if args.max_notifications > 0:
        payloads = payloads[-args.max_notifications :]

    webhook_url = args.discord_webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if args.send_discord and not webhook_url:
        raise ValueError("--send-discord requires --discord-webhook-url, DISCORD_WEBHOOK_URL environment variable, or DISCORD_WEBHOOK_URL in .env.")

    print("Project root:", PROJECT_ROOT)
    print("Symbol: BTC")
    print("M5 CSV:", m5_csv)
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("H4 CSV:", h4_csv)
    print("History CSV:", history_csv)
    print("Ledger CSV:", ledger_csv)
    print("Env file:", env_file, "exists=" + str(env_file.exists()))
    print("Rows:", "M5", len(m5_ctx), "M15", len(m15_runner_df))
    print("Scan recent M5 bars:", args.scan_recent_m5_bars)
    print("Scan recent M15 bars:", args.scan_recent_m15_bars)
    print("Scan recent standby M5 bars:", args.scan_recent_standby_m5_bars)
    print("Standby enabled:", not args.disable_standby)
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
                    "notification_type": payload.get("notification_type", "signal"),
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
