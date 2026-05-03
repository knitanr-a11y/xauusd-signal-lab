from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from build_latest_btc_mtf_signal_payload_from_csv import (
    DEFAULT_H1_CSV,
    DEFAULT_H4_CSV,
    DEFAULT_M15_CSV,
    DEFAULT_M5_CSV,
    parse_int_set,
    resolve_path,
)
from build_latest_signal_payload_from_csv import DEFAULT_HISTORY_CSV, DEFAULT_OUT_DIR, PROJECT_ROOT
from revalidate_btc_spread_rules import infer_most_frequent_spread_price
from run_live_btc_mtf_notifier_from_csv import (
    DEFAULT_ENV_FILE,
    DEFAULT_LEDGER_CSV,
    append_ledger_rows,
    collect_unnotified_payloads,
    format_discord_message,
    load_contexts,
    load_env_file,
    load_notified_keys,
    maybe_apply_ai_review,
    now_str,
    send_discord_message,
    write_payload_json,
)
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

DEFAULT_BTC_PIP_SIZE = 10.0
DEFAULT_POINT_SIZE = 0.01
DEFAULT_FALLBACK_SPREAD_PRICE = 20.0
DEFAULT_MIN_NET_TP_PIPS = 5.0
DEFAULT_MAX_SPREAD_TO_SL_RATIO = 0.50
DEFAULT_MIN_EFFECTIVE_RR = 1.0


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if pd.isna(number):
        return None
    return number


def resolve_btc_spread_price(
    *,
    m5_csv: Path,
    m15_csv: Path,
    spread_mode: str,
    spread_source: str,
    fixed_spread_price: float | None,
    point_size: float,
    spread_round_digits: int,
    include_zero_spread_in_mode: bool,
) -> tuple[float, dict[str, Any], str]:
    fallback = DEFAULT_FALLBACK_SPREAD_PRICE if fixed_spread_price is None else float(fixed_spread_price)
    if spread_mode == "fixed":
        return fallback, {"ok": True, "reason": "fixed", "mode_spread_price": fallback, "top_counts": []}, "fixed"

    source_csv = m5_csv if spread_source == "m5" else m15_csv
    source_df = read_ohlc_live_csv(source_csv)
    info = infer_most_frequent_spread_price(
        source_df,
        point_size=point_size,
        round_digits=spread_round_digits,
        exclude_zero=not include_zero_spread_in_mode,
    )
    if info.get("ok"):
        return float(info["mode_spread_price"]), info, "csv_mode"
    return fallback, info, f"csv_mode_failed_fallback_fixed:{info.get('reason')}"


def trade_plan_passes_filters(
    payload: dict[str, Any],
    *,
    min_net_tp_pips: float,
    max_spread_to_sl_ratio: float,
    min_effective_rr: float,
) -> tuple[bool, list[str]]:
    cur = payload.get("current_signal_snapshot", {}) or {}
    plan = cur.get("trade_plan") or payload.get("trade_plan") or {}
    reasons: list[str] = []
    if not plan:
        return False, ["trade_planがありません"]

    net_tp_pips = safe_float(plan.get("net_tp_after_spread_pips"))
    spread_to_sl = safe_float(plan.get("spread_to_sl_ratio"))
    effective_rr = safe_float(plan.get("effective_rr_after_spread"))

    if net_tp_pips is None:
        reasons.append("実質TP幅pipsを計算できません")
    elif net_tp_pips < min_net_tp_pips:
        reasons.append(f"実質TP幅 {net_tp_pips:.2f}pips < {min_net_tp_pips:.2f}pips")

    if spread_to_sl is None:
        reasons.append("spread/SL比率を計算できません")
    elif spread_to_sl >= max_spread_to_sl_ratio:
        reasons.append(f"spread/SL {spread_to_sl * 100:.1f}% >= {max_spread_to_sl_ratio * 100:.1f}%")

    if effective_rr is None:
        reasons.append("実質RRを計算できません")
    elif effective_rr < min_effective_rr:
        reasons.append(f"実質RR {effective_rr:.2f} < {min_effective_rr:.2f}")

    return len(reasons) == 0, reasons


def append_rejection_info(payload: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    out = dict(payload)
    out["notification_rejected"] = True
    out["rejection_reasons"] = reasons
    out["discord_priority"] = "skip"
    return out


def make_ledger_row(payload: dict[str, Any], *, discord_sent: bool, dry_run: bool) -> dict[str, Any]:
    cur = payload.get("current_signal_snapshot", {}) or {}
    plan = cur.get("trade_plan", {}) or payload.get("trade_plan", {}) or {}
    ai_review = payload.get("ai_review") or {}
    return {
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
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Live BTC MTF CSV notifier with CSV-mode spread and value-width filters.")
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
    parser.add_argument("--spread-mode", choices=["csv_mode", "fixed"], default="csv_mode")
    parser.add_argument("--spread-source", choices=["m5", "m15"], default="m5")
    parser.add_argument("--fixed-spread-price", type=float, default=None)
    parser.add_argument("--point-size", type=float, default=DEFAULT_POINT_SIZE)
    parser.add_argument("--spread-round-digits", type=int, default=2)
    parser.add_argument("--include-zero-spread-in-mode", action="store_true")
    parser.add_argument("--btc-pip-size", type=float, default=DEFAULT_BTC_PIP_SIZE)
    parser.add_argument("--min-net-tp-pips", type=float, default=DEFAULT_MIN_NET_TP_PIPS)
    parser.add_argument("--max-spread-to-sl-ratio", type=float, default=DEFAULT_MAX_SPREAD_TO_SL_RATIO)
    parser.add_argument("--min-effective-rr", type=float, default=DEFAULT_MIN_EFFECTIVE_RR)
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

    spread_price, spread_info, effective_spread_mode = resolve_btc_spread_price(
        m5_csv=m5_csv,
        m15_csv=m15_csv,
        spread_mode=args.spread_mode,
        spread_source=args.spread_source,
        fixed_spread_price=args.fixed_spread_price,
        point_size=args.point_size,
        spread_round_digits=args.spread_round_digits,
        include_zero_spread_in_mode=args.include_zero_spread_in_mode,
    )

    m5_ctx, m15_runner_df = load_contexts(m5_csv, m15_csv, h1_csv, h4_csv)
    notified_keys = load_notified_keys(ledger_csv)
    raw_payloads = collect_unnotified_payloads(
        m5_ctx=m5_ctx,
        m15_runner_df=m15_runner_df,
        history_csv=history_csv,
        notified_keys=notified_keys,
        scan_recent_m5_bars=args.scan_recent_m5_bars,
        scan_recent_m15_bars=args.scan_recent_m15_bars,
        bar_offset=args.bar_offset,
        exclude_entry_hours=exclude_entry_hours,
        btc_assumed_spread_price=spread_price,
        btc_pip_size=args.btc_pip_size,
    )

    accepted: list[tuple[int, dict[str, Any]]] = []
    rejected: list[tuple[int, dict[str, Any], list[str]]] = []
    for idx, payload in raw_payloads:
        ok, reasons = trade_plan_passes_filters(
            payload,
            min_net_tp_pips=args.min_net_tp_pips,
            max_spread_to_sl_ratio=args.max_spread_to_sl_ratio,
            min_effective_rr=args.min_effective_rr,
        )
        if ok:
            accepted.append((idx, payload))
        else:
            rejected.append((idx, append_rejection_info(payload, reasons), reasons))

    if args.max_notifications > 0:
        accepted = accepted[-args.max_notifications:]

    webhook_url = args.discord_webhook_url or __import__("os").environ.get("DISCORD_WEBHOOK_URL", "")
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
    print("Spread mode:", effective_spread_mode)
    print("Spread source:", args.spread_source)
    print("Spread info:", spread_info)
    print("BTC spread price used:", spread_price)
    print("BTC pip size:", args.btc_pip_size)
    print("Value filters:", f"net_tp_pips>={args.min_net_tp_pips}", f"spread_to_sl<{args.max_spread_to_sl_ratio}", f"effective_rr>={args.min_effective_rr}")
    print("Scan recent M5 bars:", args.scan_recent_m5_bars)
    print("Scan recent M15 bars:", args.scan_recent_m15_bars)
    print("AI review enabled:", bool(args.enable_ai_review))
    print("Exclude entry hours:", sorted(exclude_entry_hours))
    print("Already notified keys:", len(notified_keys))
    print("Raw unnotified signals:", len(raw_payloads))
    print("Rejected by spread/value filters:", len(rejected))
    print("Unnotified signals selected:", len(accepted))
    print("Dry run:", bool(args.dry_run))
    print("Send Discord:", bool(args.send_discord))

    if rejected:
        print("\nRejected BTC signals:")
        for idx, payload, reasons in rejected[-20:]:
            cur = payload.get("current_signal_snapshot", {}) or {}
            plan = cur.get("trade_plan") or payload.get("trade_plan") or {}
            print(
                f"  idx={idx} time={payload.get('time')} label={cur.get('strategy_label')} side={cur.get('side')} "
                f"net_tp_pips={plan.get('net_tp_after_spread_pips')} spread_to_sl={plan.get('spread_to_sl_ratio')} "
                f"effective_rr={plan.get('effective_rr_after_spread')} reasons={' / '.join(reasons)}"
            )
            write_payload_json(out_dir, payload)

    ledger_rows: list[dict[str, Any]] = []
    for idx, payload in accepted:
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

        should_write_ledger = bool(args.send_discord) or bool(args.mark_dry_run_notified)
        if should_write_ledger:
            ledger_rows.append(make_ledger_row(payload, discord_sent=discord_sent, dry_run=bool(args.dry_run)))

    append_ledger_rows(ledger_csv, ledger_rows)
    print("\nLedger rows appended:", len(ledger_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
