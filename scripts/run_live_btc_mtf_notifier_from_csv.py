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

from ai_signal_review import apply_ai_review, evaluate_signal_payload
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
DEFAULT_BTC_ASSUMED_SPREAD_PRICE = 20.0
DEFAULT_BTC_PIP_SIZE = 10.0


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_env_file(path: Path) -> None:
    """Minimal .env loader without external dependencies.

    Existing environment variables are not overwritten.
    Supported format:
      DISCORD_WEBHOOK_URL=https://...
      KEY="quoted value"
    """
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
        "entry_price_estimate",
        "tp_price_estimate",
        "sl_price_estimate",
        "risk_price_distance",
        "reward_price_distance",
        "btc_assumed_spread_price",
        "btc_pip_size",
        "gross_tp_pips",
        "gross_sl_pips",
        "net_tp_after_spread_price",
        "sl_with_spread_price",
        "net_tp_after_spread_pips",
        "sl_with_spread_pips",
        "spread_to_sl_ratio",
        "spread_to_tp_ratio",
        "effective_rr_after_spread",
        "overlap_detected",
        "overlap_signal_count",
        "overlap_labels",
        "ai_review_status",
        "ai_decision",
        "ai_confidence",
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


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if pd.isna(number):
        return None
    return number


def price_digits(price: float | None) -> int:
    if price is None:
        return 2
    if abs(price) >= 1000:
        return 2
    if abs(price) >= 100:
        return 3
    return 5


def fmt_price(value: Any, *, digits: int | None = None) -> str:
    number = safe_float(value)
    if number is None:
        return "N/A"
    d = price_digits(number) if digits is None else digits
    return f"{number:.{d}f}"


def fmt_ratio(value: Any) -> str:
    number = safe_float(value)
    if number is None:
        return "N/A"
    return f"{number * 100:.1f}%"


def build_trade_plan(cur: dict[str, Any], *, btc_assumed_spread_price: float, btc_pip_size: float) -> dict[str, Any] | None:
    side = str(cur.get("side", "")).upper()
    entry = safe_float(cur.get("close"))
    atr14 = safe_float(cur.get("atr14"))
    rr = safe_float(cur.get("rr"))
    risk_atr = safe_float(cur.get("risk_atr"))
    spread_price = safe_float(btc_assumed_spread_price)
    pip_size = safe_float(btc_pip_size)
    if side not in {"BUY", "SELL"} or entry is None or atr14 is None or rr is None or risk_atr is None:
        return None
    if spread_price is None or spread_price < 0:
        spread_price = 0.0
    if pip_size is None or pip_size <= 0:
        pip_size = DEFAULT_BTC_PIP_SIZE

    risk_distance = atr14 * risk_atr
    if risk_distance <= 0:
        return None
    reward_distance = risk_distance * rr
    if side == "BUY":
        sl = entry - risk_distance
        tp = entry + reward_distance
    else:
        sl = entry + risk_distance
        tp = entry - reward_distance

    net_tp_after_spread = reward_distance - spread_price
    sl_with_spread = risk_distance + spread_price
    effective_rr_after_spread = net_tp_after_spread / sl_with_spread if sl_with_spread > 0 else None
    spread_to_sl_ratio = spread_price / risk_distance if risk_distance > 0 else None
    spread_to_tp_ratio = spread_price / reward_distance if reward_distance > 0 else None

    warnings: list[str] = []
    if spread_to_sl_ratio is not None and spread_to_sl_ratio >= 0.50:
        warnings.append("想定スプレッドがSL幅の50%以上で重い")
    if net_tp_after_spread <= 0:
        warnings.append("スプレッド控除後の実質TP幅が0以下")
    elif effective_rr_after_spread is not None and effective_rr_after_spread < 1.0:
        warnings.append("スプレッド控除後の実質RRが1.0未満")

    return {
        "basis": "signal_close_estimate",
        "note": "確定足終値ベースの目安。実際の約定価格・スプレッドでズレます。",
        "entry_price_estimate": entry,
        "tp_price_estimate": tp,
        "sl_price_estimate": sl,
        "risk_price_distance": risk_distance,
        "reward_price_distance": reward_distance,
        "btc_assumed_spread_price": spread_price,
        "btc_pip_size": pip_size,
        "spread_pips": spread_price / pip_size,
        "gross_tp_pips": reward_distance / pip_size,
        "gross_sl_pips": risk_distance / pip_size,
        "net_tp_after_spread_price": net_tp_after_spread,
        "sl_with_spread_price": sl_with_spread,
        "net_tp_after_spread_pips": net_tp_after_spread / pip_size,
        "sl_with_spread_pips": sl_with_spread / pip_size,
        "spread_to_sl_ratio": spread_to_sl_ratio,
        "spread_to_tp_ratio": spread_to_tp_ratio,
        "effective_rr_after_spread": effective_rr_after_spread,
        "spread_warnings": warnings,
    }


def enrich_payload_with_trade_plan(payload: dict[str, Any], *, btc_assumed_spread_price: float, btc_pip_size: float) -> dict[str, Any]:
    out = dict(payload)
    cur = dict(out.get("current_signal_snapshot", {}) or {})
    plan = build_trade_plan(cur, btc_assumed_spread_price=btc_assumed_spread_price, btc_pip_size=btc_pip_size)
    if plan is not None:
        cur["trade_plan"] = plan
        out["current_signal_snapshot"] = cur
        out["trade_plan"] = plan
    return out


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
    return f"{strategy}（{source_tf}）"


def readable_side(side: str) -> str:
    side_upper = str(side).upper()
    if side_upper == "BUY":
        return "BUY（買い）"
    if side_upper == "SELL":
        return "SELL（売り）"
    return side


def format_ai_review_lines(payload: dict[str, Any]) -> list[str]:
    review = payload.get("ai_review") or {}
    if not review:
        return ["AI評価: 未接続（次工程で追加）"]
    decision = review.get("decision_jp") or payload.get("ai_review_status") or "評価済み"
    confidence = review.get("confidence", "")
    summary = review.get("summary_jp", "")
    lot = review.get("lot_multiplier_hint", "")
    lines = [f"AI評価: {decision} / 信頼度 {confidence}"]
    if lot != "":
        lines.append(f"AIロット目安: 通常比 {lot}")
    if summary:
        lines.append(f"AI要約: {summary}")
    reasons = review.get("reasons_jp") or []
    warnings = review.get("warnings_jp") or []
    if reasons:
        lines.append("AI理由: " + " / ".join(str(x) for x in reasons[:3]))
    if warnings:
        lines.append("AI注意: " + " / ".join(str(x) for x in warnings[:2]))
    return lines


def format_trade_plan_line(payload: dict[str, Any]) -> list[str]:
    cur = payload.get("current_signal_snapshot", {}) or {}
    plan = cur.get("trade_plan") or payload.get("trade_plan") or {}
    if not plan:
        return []
    entry = safe_float(plan.get("entry_price_estimate"))
    digits = price_digits(entry)
    lines = [
        "価格目安: "
        f"Entry {fmt_price(plan.get('entry_price_estimate'), digits=digits)} / "
        f"TP {fmt_price(plan.get('tp_price_estimate'), digits=digits)} / "
        f"SL {fmt_price(plan.get('sl_price_estimate'), digits=digits)}",
        "理論値幅: "
        f"TP幅 {fmt_price(plan.get('reward_price_distance'), digits=digits)}ドル（約{fmt_price(plan.get('gross_tp_pips'), digits=2)}pips） / "
        f"SL幅 {fmt_price(plan.get('risk_price_distance'), digits=digits)}ドル（約{fmt_price(plan.get('gross_sl_pips'), digits=2)}pips）",
        "スプレッド考慮: "
        f"想定 {fmt_price(plan.get('btc_assumed_spread_price'), digits=digits)}ドル（約{fmt_price(plan.get('spread_pips'), digits=2)}pips） / "
        f"実質TP幅 {fmt_price(plan.get('net_tp_after_spread_price'), digits=digits)}ドル（約{fmt_price(plan.get('net_tp_after_spread_pips'), digits=2)}pips） / "
        f"実質SL負担 {fmt_price(plan.get('sl_with_spread_price'), digits=digits)}ドル（約{fmt_price(plan.get('sl_with_spread_pips'), digits=2)}pips）",
        "コスト比率: "
        f"spread/SL {fmt_ratio(plan.get('spread_to_sl_ratio'))} / "
        f"spread/TP {fmt_ratio(plan.get('spread_to_tp_ratio'))} / "
        f"実質RR {fmt_price(plan.get('effective_rr_after_spread'), digits=2)}",
        "価格注記: 確定足終値ベース。実約定・スプレッドでズレあり",
    ]
    warnings = plan.get("spread_warnings") or []
    if warnings:
        lines.append("スプレッド注意: " + " / ".join(str(x) for x in warnings))
    return lines


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

    title_icon = "🟢" if side.upper() == "BUY" else "🔴" if side.upper() == "SELL" else "📣"
    risk_note = "ロット小さめ候補" if cur.get("lot_hint") == "reduced_candidate" else "通常候補"

    lines = [
        f"{title_icon} **BTC {readable_side(side)} シグナル**",
        "",
        "状態: シグナル確定",
        f"時刻: {signal_time}",
        f"エントリー目安: {entry_time}",
        f"ルール: {readable_strategy(strategy, source_tf)}",
        f"時間足: {source_tf}",
        f"条件: RR {rr} / SL幅 ATR×{risk_atr}",
    ]
    lines.extend(format_trade_plan_line(payload))
    lines.append(f"運用メモ: {risk_note}")

    if cur.get("entry_hour") is not None:
        lines.append(f"時間フィルタ: {cur.get('entry_hour')}時 → 通過")

    if overlap:
        lines.append("重複: あり（" + " + ".join(payload.get("overlap_labels", [])) + "）")
    else:
        lines.append("重複: なし")

    lines.append("")
    lines.extend(format_ai_review_lines(payload))
    lines.append(f"内部名: {strategy}")
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
    btc_assumed_spread_price: float,
    btc_pip_size: float,
) -> list[tuple[int, dict[str, Any]]]:
    payloads: list[tuple[int, dict[str, Any]]] = []

    # BTC M5 scalp confirmed signals.
    m5_end = len(m5_ctx) - 1 - bar_offset
    m5_start = max(300, m5_end - scan_recent_m5_bars + 1)
    for idx in range(m5_start, m5_end + 1):
        row = m5_ctx.iloc[idx]
        signal = detect_btc_scalp_m5_reentry_filtered(row, exclude_entry_hours=exclude_entry_hours)
        if signal is None:
            continue
        payload = build_btc_mtf_payload(row, signal, history_csv, selection_mode=f"live_btc_mtf_m5_scan_{scan_recent_m5_bars}", source_tf="M5")
        payload = enrich_payload_with_trade_plan(payload, btc_assumed_spread_price=btc_assumed_spread_price, btc_pip_size=btc_pip_size)
        payload["notification_type"] = "signal"
        payload["notification_key"] = make_notification_key("BTC", str(payload.get("time")), signal)
        payload["overlap_detected"] = False
        payload["overlap_signal_count"] = 1
        payload["overlap_labels"] = [str(signal.get("strategy_label"))]
        payload["overlap_candidates"] = [candidate_snapshot(signal, source_tf="M5")]
        payload["confidence_hint"] = "single_signal"
        if str(payload["notification_key"]) not in notified_keys:
            payloads.append((idx, payload))

    # BTC RUNNER confirmed signals.
    m15_end = len(m15_runner_df) - 1 - bar_offset
    m15_start = max(220, m15_end - scan_recent_m15_bars + 1)
    for idx in range(m15_start, m15_end + 1):
        row = m15_runner_df.iloc[idx]
        signal = detect_btc_runner(row)
        if signal is None:
            continue
        payload = build_btc_mtf_payload(row, signal, history_csv, selection_mode=f"live_btc_mtf_m15_scan_{scan_recent_m15_bars}", source_tf="M15")
        payload = enrich_payload_with_trade_plan(payload, btc_assumed_spread_price=btc_assumed_spread_price, btc_pip_size=btc_pip_size)
        payload["notification_type"] = "signal"
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


def maybe_apply_ai_review(payload: dict[str, Any], *, enable_ai_review: bool, env_file: Path, ai_model: str | None) -> dict[str, Any]:
    if not enable_ai_review:
        return payload
    review = evaluate_signal_payload(payload, env_file=env_file, model=ai_model)
    return apply_ai_review(payload, review)


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
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--exclude-entry-hours", default="8,13,20,21")
    parser.add_argument("--btc-assumed-spread-price", type=float, default=DEFAULT_BTC_ASSUMED_SPREAD_PRICE)
    parser.add_argument("--btc-pip-size", type=float, default=DEFAULT_BTC_PIP_SIZE)
    parser.add_argument("--enable-ai-review", action="store_true")
    parser.add_argument("--ai-model", default=None)
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
        bar_offset=args.bar_offset,
        exclude_entry_hours=exclude_entry_hours,
        btc_assumed_spread_price=args.btc_assumed_spread_price,
        btc_pip_size=args.btc_pip_size,
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
    print("Standby enabled: False")
    print("AI review enabled:", bool(args.enable_ai_review))
    print("BTC assumed spread price:", args.btc_assumed_spread_price)
    print("BTC pip size:", args.btc_pip_size)
    print("Exclude entry hours:", sorted(exclude_entry_hours))
    print("Already notified keys:", len(notified_keys))
    print("Unnotified signals selected:", len(payloads))
    print("Dry run:", bool(args.dry_run))
    print("Send Discord:", bool(args.send_discord))

    ledger_rows: list[dict[str, Any]] = []
    for idx, payload in payloads:
        payload = maybe_apply_ai_review(payload, enable_ai_review=args.enable_ai_review, env_file=env_file, ai_model=args.ai_model)
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
        plan = cur.get("trade_plan", {}) or payload.get("trade_plan", {}) or {}
        ai_review = payload.get("ai_review") or {}
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
                    "entry_price_estimate": plan.get("entry_price_estimate", ""),
                    "tp_price_estimate": plan.get("tp_price_estimate", ""),
                    "sl_price_estimate": plan.get("sl_price_estimate", ""),
                    "risk_price_distance": plan.get("risk_price_distance", ""),
                    "reward_price_distance": plan.get("reward_price_distance", ""),
                    "btc_assumed_spread_price": plan.get("btc_assumed_spread_price", ""),
                    "btc_pip_size": plan.get("btc_pip_size", ""),
                    "gross_tp_pips": plan.get("gross_tp_pips", ""),
                    "gross_sl_pips": plan.get("gross_sl_pips", ""),
                    "net_tp_after_spread_price": plan.get("net_tp_after_spread_price", ""),
                    "sl_with_spread_price": plan.get("sl_with_spread_price", ""),
                    "net_tp_after_spread_pips": plan.get("net_tp_after_spread_pips", ""),
                    "sl_with_spread_pips": plan.get("sl_with_spread_pips", ""),
                    "spread_to_sl_ratio": plan.get("spread_to_sl_ratio", ""),
                    "spread_to_tp_ratio": plan.get("spread_to_tp_ratio", ""),
                    "effective_rr_after_spread": plan.get("effective_rr_after_spread", ""),
                    "overlap_detected": payload.get("overlap_detected"),
                    "overlap_signal_count": payload.get("overlap_signal_count"),
                    "overlap_labels": "+".join(payload.get("overlap_labels", [])),
                    "ai_review_status": payload.get("ai_review_status", ""),
                    "ai_decision": ai_review.get("decision", ""),
                    "ai_confidence": ai_review.get("confidence", ""),
                    "discord_sent": discord_sent,
                    "dry_run": bool(args.dry_run),
                }
            )

    append_ledger_rows(ledger_csv, ledger_rows)
    print("\nLedger rows appended:", len(ledger_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
