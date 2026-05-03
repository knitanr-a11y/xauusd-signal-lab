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
from build_latest_signal_payload_from_csv import (
    DEFAULT_HISTORY_CSV,
    DEFAULT_OUT_DIR,
    PROJECT_ROOT,
    add_indicators,
    build_payload,
    detect_gold_abc,
    detect_gold_extra,
    join_h1,
    resolve_path,
)
from search_btc_mtf_extra_edges_livecsv import read_ohlc_live_csv

DEFAULT_M15_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_m15.csv"
DEFAULT_H1_CSV = PROJECT_ROOT / "data" / "raw" / "goldsharp_h1.csv"
DEFAULT_LEDGER_CSV = PROJECT_ROOT / "data" / "results" / "live_payloads" / "notified_gold_signals_ledger.csv"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DISCORD_USER_AGENT = "xauusd-signal-lab/1.0 (+https://github.com/knitanr-a11y/xauusd-signal-lab)"
ADOPTED_GOLD_LABELS = {"GOLD_ABC_V3", "GOLD_EXTRA_HIGH_RSI_STOCH", "GOLD_EXTRA_BB_BALANCE"}
EXCLUDED_GOLD_LABELS = {"GOLD_COUNTER_BUY_ONLY"}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_env_file(path: Path) -> None:
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
    return 2 if abs(price) >= 100 else 3


def fmt_price(value: Any, *, digits: int | None = None) -> str:
    number = safe_float(value)
    if number is None:
        return "N/A"
    d = price_digits(number) if digits is None else digits
    return f"{number:.{d}f}"


def make_notification_key(payload: dict[str, Any]) -> str:
    cur = payload.get("current_signal_snapshot", {}) or {}
    return "|".join(["GOLD", str(payload.get("time")), str(cur.get("strategy_label")), str(cur.get("side"))])


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
        "entry_price_estimate",
        "tp_price_estimate",
        "sl_price_estimate",
        "risk_price_distance",
        "reward_price_distance",
        "gold_abc_buy_danger_regime",
        "warning_only",
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
    key = str(payload.get("notification_key", "gold_signal")).replace("|", "_").replace(":", "").replace(" ", "_")
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


def build_trade_plan(cur: dict[str, Any]) -> dict[str, Any] | None:
    side = str(cur.get("side", "")).upper()
    entry = safe_float(cur.get("close"))
    atr14 = safe_float(cur.get("atr14"))
    rr = safe_float(cur.get("rr"))
    risk_atr = safe_float(cur.get("risk_atr"))
    if side not in {"BUY", "SELL"} or entry is None or atr14 is None or rr is None or risk_atr is None:
        return None
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
    return {
        "basis": "signal_close_estimate",
        "note": "確定足終値ベースの目安。実際の約定価格・スプレッドでズレます。",
        "entry_price_estimate": entry,
        "tp_price_estimate": tp,
        "sl_price_estimate": sl,
        "risk_price_distance": risk_distance,
        "reward_price_distance": reward_distance,
    }


def enrich_payload_with_trade_plan(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    cur = dict(out.get("current_signal_snapshot", {}) or {})
    plan = build_trade_plan(cur)
    if plan is not None:
        cur["trade_plan"] = plan
        out["current_signal_snapshot"] = cur
        out["trade_plan"] = plan
    return out


def is_adopted_gold_signal(signal: dict[str, Any]) -> bool:
    label = str(signal.get("strategy_label", ""))
    return label in ADOPTED_GOLD_LABELS and label not in EXCLUDED_GOLD_LABELS


def detect_gold_candidates(row: pd.Series, *, include_excluded: bool = False) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    abc = detect_gold_abc(row)
    extra = detect_gold_extra(row)
    if abc is not None:
        candidates.append(abc)
    if extra is not None:
        candidates.append(extra)
    if include_excluded:
        return candidates
    return [c for c in candidates if is_adopted_gold_signal(c)]


def format_side(side: str) -> str:
    if side == "BUY":
        return "BUY（買い）"
    if side == "SELL":
        return "SELL（売り）"
    return side


def readable_strategy(strategy: str, rank: str, abc_source: str | None = None) -> str:
    if strategy == "GOLD_ABC_V3":
        src = f" / {abc_source}" if abc_source else ""
        return f"GOLD ABC v3（本命候補{src}）"
    if strategy == "GOLD_EXTRA_HIGH_RSI_STOCH":
        return "GOLD EXTRA HIGH（高PF補助候補）"
    if strategy == "GOLD_EXTRA_BB_BALANCE":
        return "GOLD EXTRA STANDARD（補助候補）"
    if strategy == "GOLD_COUNTER_BUY_ONLY":
        return "GOLD COUNTER BUY ONLY（本番除外）"
    return strategy or rank


def format_ai_review_lines(payload: dict[str, Any]) -> list[str]:
    review = payload.get("ai_review") or {}
    if not review:
        return ["AI評価: 未接続"]
    decision = review.get("decision_jp") or payload.get("ai_review_status") or "評価済み"
    confidence = review.get("confidence", "")
    lot = review.get("lot_multiplier_hint", "")
    summary = review.get("summary_jp", "")
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


def format_trade_plan_lines(payload: dict[str, Any]) -> list[str]:
    plan = payload.get("trade_plan") or (payload.get("current_signal_snapshot", {}) or {}).get("trade_plan") or {}
    if not plan:
        return []
    entry = safe_float(plan.get("entry_price_estimate"))
    digits = price_digits(entry)
    return [
        "価格目安: "
        f"Entry {fmt_price(plan.get('entry_price_estimate'), digits=digits)} / "
        f"TP {fmt_price(plan.get('tp_price_estimate'), digits=digits)} / "
        f"SL {fmt_price(plan.get('sl_price_estimate'), digits=digits)}",
        "値幅目安: "
        f"損切り幅 {fmt_price(plan.get('risk_price_distance'), digits=digits)} / "
        f"利確幅 {fmt_price(plan.get('reward_price_distance'), digits=digits)}",
        "価格注記: 確定足終値ベース。実約定・スプレッドでズレあり",
    ]


def regime_display_lines(payload: dict[str, Any]) -> list[str]:
    cur = payload.get("current_signal_snapshot", {}) or {}
    strategy = str(cur.get("strategy_label", ""))
    side = str(cur.get("side", ""))
    regime = payload.get("regime_guard", {}) or {}
    danger = bool(regime.get("gold_abc_buy_danger_regime"))
    if strategy == "GOLD_ABC_V3" and side == "BUY":
        if danger:
            return [
                "",
                "⚠️ GOLD ABC BUY danger regime: TRUE",
                "扱い: 警戒通知のみ / AI評価必須 / ロット低下候補",
                f"理由: {regime.get('reason', '')}",
            ]
        return ["regime guard: GOLD ABC BUY対象 / danger=False"]
    return ["regime guard: 対象外（GOLD ABC BUYのみ判定）"]


def format_discord_message(payload: dict[str, Any]) -> str:
    cur = payload.get("current_signal_snapshot", {}) or {}
    side = str(cur.get("side", ""))
    strategy = str(cur.get("strategy_label", ""))
    rank = str(cur.get("portfolio_rank", ""))
    abc_source = cur.get("abc_source")
    rr = cur.get("rr", "")
    risk_atr = cur.get("risk_atr", "")
    signal_time = payload.get("time", "")
    regime = payload.get("regime_guard", {}) or {}
    danger = bool(regime.get("gold_abc_buy_danger_regime"))
    overlap = bool(payload.get("overlap_detected"))

    icon = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "📣"
    if danger:
        icon = "⚠️"
    lines = [
        f"{icon} **GOLD {format_side(side)} シグナル**",
        "",
        "状態: シグナル確定",
        f"時刻: {signal_time}",
        f"ルール: {readable_strategy(strategy, rank, abc_source)}",
        f"条件: RR {rr} / SL幅 ATR×{risk_atr}",
    ]
    lines.extend(format_trade_plan_lines(payload))
    lines.extend(regime_display_lines(payload))

    if overlap:
        lines.append("重複: あり（" + " + ".join(payload.get("overlap_labels", [])) + "）")
    else:
        lines.append("重複: なし")

    lines.append("")
    lines.extend(format_ai_review_lines(payload))
    lines.append(f"内部名: {strategy}")
    return "\n".join(lines)


def load_gold_context(m15_csv: Path, h1_csv: Path) -> pd.DataFrame:
    m15 = add_indicators(read_ohlc_live_csv(m15_csv))
    h1 = add_indicators(read_ohlc_live_csv(h1_csv))
    return join_h1(m15, h1)


def collect_unnotified_payloads(
    *,
    df: pd.DataFrame,
    history_csv: Path,
    notified_keys: set[str],
    scan_recent_bars: int,
    bar_offset: int,
    include_excluded: bool,
) -> tuple[list[tuple[int, dict[str, Any]]], list[dict[str, Any]]]:
    if df.empty:
        return [], []
    end_idx = len(df) - 1 - bar_offset
    if end_idx < 0:
        return [], []
    start_idx = max(220, end_idx - scan_recent_bars + 1)
    payloads: list[tuple[int, dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    for idx in range(start_idx, end_idx + 1):
        row = df.iloc[idx]
        all_candidates = detect_gold_candidates(row, include_excluded=True)
        if not all_candidates:
            continue
        adopted_candidates = [c for c in all_candidates if is_adopted_gold_signal(c)]
        excluded_candidates = [c for c in all_candidates if not is_adopted_gold_signal(c)]
        for c in excluded_candidates:
            rejected.append(
                {
                    "idx": int(idx),
                    "time": row.get("time"),
                    "strategy_label": c.get("strategy_label"),
                    "side": c.get("side"),
                    "reason": "本番通知対象外",
                }
            )
        candidates = all_candidates if include_excluded else adopted_candidates
        if not candidates:
            continue
        selected = candidates[0]
        payload = build_payload("GOLD", row, selected, history_csv, selection_mode=f"live_gold_scan_{scan_recent_bars}")
        payload = enrich_payload_with_trade_plan(payload)
        payload["notification_type"] = "signal"
        payload["notification_key"] = make_notification_key(payload)
        payload["overlap_detected"] = len(candidates) > 1
        payload["overlap_signal_count"] = len(candidates)
        payload["overlap_labels"] = [str(c.get("strategy_label")) for c in candidates]
        payload["overlap_candidates"] = candidates
        if payload["notification_key"] not in notified_keys:
            payloads.append((idx, payload))
    payloads.sort(key=lambda x: str(x[1].get("time", "")))
    return payloads, rejected


def maybe_apply_ai_review(payload: dict[str, Any], *, enable_ai_review: bool, env_file: Path, ai_model: str | None) -> dict[str, Any]:
    regime = payload.get("regime_guard", {}) or {}
    danger = bool(regime.get("gold_abc_buy_danger_regime"))
    if not enable_ai_review and not danger:
        return payload
    review = evaluate_signal_payload(payload, env_file=env_file, model=ai_model)
    return apply_ai_review(payload, review)


def make_ledger_row(payload: dict[str, Any], *, discord_sent: bool, dry_run: bool) -> dict[str, Any]:
    cur = payload.get("current_signal_snapshot", {}) or {}
    plan = cur.get("trade_plan", {}) or payload.get("trade_plan", {}) or {}
    regime = payload.get("regime_guard", {}) or {}
    ai_review = payload.get("ai_review") or {}
    return {
        "notified_at": now_str(),
        "notification_key": payload.get("notification_key"),
        "symbol_group": "GOLD",
        "time": payload.get("time"),
        "strategy_label": cur.get("strategy_label"),
        "signal_model": cur.get("signal_model"),
        "portfolio_rank": cur.get("portfolio_rank"),
        "side": cur.get("side"),
        "rr": cur.get("rr"),
        "risk_atr": cur.get("risk_atr"),
        "entry_price_estimate": plan.get("entry_price_estimate", ""),
        "tp_price_estimate": plan.get("tp_price_estimate", ""),
        "sl_price_estimate": plan.get("sl_price_estimate", ""),
        "risk_price_distance": plan.get("risk_price_distance", ""),
        "reward_price_distance": plan.get("reward_price_distance", ""),
        "gold_abc_buy_danger_regime": regime.get("gold_abc_buy_danger_regime", ""),
        "warning_only": regime.get("warning_only", ""),
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
    parser = argparse.ArgumentParser(description="Live GOLD CSV notifier with regime guard, AI review, and duplicate guard.")
    parser.add_argument("--m15-csv", type=Path, default=DEFAULT_M15_CSV)
    parser.add_argument("--h1-csv", type=Path, default=DEFAULT_H1_CSV)
    parser.add_argument("--history-csv", type=Path, default=DEFAULT_HISTORY_CSV)
    parser.add_argument("--ledger-csv", type=Path, default=DEFAULT_LEDGER_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--scan-recent-bars", type=int, default=60)
    parser.add_argument("--bar-offset", type=int, default=1)
    parser.add_argument("--include-excluded", action="store_true", help="Debug only: include excluded labels such as GOLD_COUNTER_BUY_ONLY.")
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

    m15_csv = resolve_path(args.m15_csv)
    h1_csv = resolve_path(args.h1_csv)
    history_csv = resolve_path(args.history_csv)
    ledger_csv = resolve_path(args.ledger_csv)
    out_dir = resolve_path(args.out_dir)

    df = load_gold_context(m15_csv, h1_csv)
    notified_keys = load_notified_keys(ledger_csv)
    payloads, rejected = collect_unnotified_payloads(
        df=df,
        history_csv=history_csv,
        notified_keys=notified_keys,
        scan_recent_bars=args.scan_recent_bars,
        bar_offset=args.bar_offset,
        include_excluded=args.include_excluded,
    )
    if args.max_notifications > 0:
        payloads = payloads[-args.max_notifications:]

    webhook_url = args.discord_webhook_url or os.environ.get("DISCORD_WEBHOOK_URL", "")
    if args.send_discord and not webhook_url:
        raise ValueError("--send-discord requires --discord-webhook-url, DISCORD_WEBHOOK_URL environment variable, or DISCORD_WEBHOOK_URL in .env.")

    print("Project root:", PROJECT_ROOT)
    print("Symbol: GOLD")
    print("M15 CSV:", m15_csv)
    print("H1 CSV:", h1_csv)
    print("History CSV:", history_csv)
    print("Ledger CSV:", ledger_csv)
    print("Env file:", env_file, "exists=" + str(env_file.exists()))
    print("Rows:", len(df))
    if not df.empty:
        print("First bar:", df["time"].iloc[0])
        print("Last bar:", df["time"].iloc[-1])
    print("Scan recent bars:", args.scan_recent_bars)
    print("Adopted labels:", sorted(ADOPTED_GOLD_LABELS))
    print("Excluded labels:", sorted(EXCLUDED_GOLD_LABELS))
    print("Include excluded:", bool(args.include_excluded))
    print("AI review enabled:", bool(args.enable_ai_review))
    print("Already notified keys:", len(notified_keys))
    print("Rejected excluded signals:", len(rejected))
    print("Unnotified signals selected:", len(payloads))
    print("Dry run:", bool(args.dry_run))
    print("Send Discord:", bool(args.send_discord))

    if rejected:
        print("\nRejected excluded GOLD signals:")
        for item in rejected[-20:]:
            print(f"  idx={item['idx']} time={item['time']} label={item['strategy_label']} side={item['side']} reason={item['reason']}")

    ledger_rows: list[dict[str, Any]] = []
    for idx, payload in payloads:
        payload = maybe_apply_ai_review(payload, enable_ai_review=args.enable_ai_review, env_file=env_file, ai_model=args.ai_model)
        message = format_discord_message(payload)
        payload_path = write_payload_json(out_dir, payload)
        print("\n" + "=" * 100)
        print("GOLD notification candidate")
        print("=" * 100)
        print("idx:", idx)
        print("payload:", payload_path)
        print(message)

        discord_sent = False
        if args.send_discord:
            send_discord_message(webhook_url, message)
            discord_sent = True
            print("Discord sent: true")

        if args.send_discord or args.mark_dry_run_notified:
            ledger_rows.append(make_ledger_row(payload, discord_sent=discord_sent, dry_run=bool(args.dry_run)))

    append_ledger_rows(ledger_csv, ledger_rows)
    print("\nLedger rows appended:", len(ledger_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
