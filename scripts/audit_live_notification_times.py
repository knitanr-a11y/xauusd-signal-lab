from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER_DIR = PROJECT_ROOT / "data" / "results" / "live_payloads"
DEFAULT_GOLD_LEDGER = DEFAULT_LEDGER_DIR / "notified_gold_signals_ledger.csv"
DEFAULT_BTC_LEDGER = DEFAULT_LEDGER_DIR / "notified_btc_signals_ledger.csv"


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_dt(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or pd.isna(value):
        return pd.NaT
    return pd.to_datetime(str(value), errors="coerce")


def payload_path_for_key(out_dir: Path, notification_key: str) -> Path:
    key = str(notification_key).replace("|", "_").replace(":", "").replace(" ", "_")
    return out_dir / f"notify_payload_{key}.json"


def load_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def audit_one_ledger(path: Path, *, symbol: str, out_dir: Path, start: pd.Timestamp | None, end: pd.Timestamp | None, server_to_jst_hours: int) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame()

    df["notified_at_dt"] = df.get("notified_at", pd.Series(dtype=str)).map(parse_dt)
    df["signal_server_dt"] = df.get("time", pd.Series(dtype=str)).map(parse_dt)
    df["signal_jst_plus_config_dt"] = df["signal_server_dt"] + pd.to_timedelta(server_to_jst_hours, unit="h")
    df["signal_jst_plus6_dt"] = df["signal_server_dt"] + pd.to_timedelta(6, unit="h")
    df["signal_jst_plus7_dt"] = df["signal_server_dt"] + pd.to_timedelta(7, unit="h")
    df["lag_min_plus_config"] = (df["notified_at_dt"] - df["signal_jst_plus_config_dt"]).dt.total_seconds() / 60.0
    df["lag_min_plus6"] = (df["notified_at_dt"] - df["signal_jst_plus6_dt"]).dt.total_seconds() / 60.0
    df["lag_min_plus7"] = (df["notified_at_dt"] - df["signal_jst_plus7_dt"]).dt.total_seconds() / 60.0
    df["symbol_group"] = df.get("symbol_group", symbol)

    if start is not None:
        df = df[df["notified_at_dt"] >= start]
    if end is not None:
        df = df[df["notified_at_dt"] <= end]

    payload_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        notification_key = str(row.get("notification_key", ""))
        payload_path = payload_path_for_key(out_dir, notification_key)
        payload = load_payload(payload_path)
        cur = (payload or {}).get("current_signal_snapshot", {}) if payload else {}
        trade_plan = cur.get("trade_plan") or (payload or {}).get("trade_plan") or {}
        payload_rows.append(
            {
                "payload_exists": payload is not None,
                "payload_file": str(payload_path) if payload_path.exists() else "",
                "payload_time": (payload or {}).get("time", "") if payload else "",
                "payload_entry_time": cur.get("entry_time", "") if isinstance(cur, dict) else "",
                "payload_jst_hour": cur.get("jst_hour", "") if isinstance(cur, dict) else "",
                "payload_server_to_jst_hours": cur.get("server_to_jst_hours", "") if isinstance(cur, dict) else "",
                "entry_price_estimate": trade_plan.get("entry_price_estimate", "") if isinstance(trade_plan, dict) else "",
                "tp_price_estimate": trade_plan.get("tp_price_estimate", "") if isinstance(trade_plan, dict) else "",
                "sl_price_estimate": trade_plan.get("sl_price_estimate", "") if isinstance(trade_plan, dict) else "",
            }
        )
    if payload_rows:
        df = pd.concat([df.reset_index(drop=True), pd.DataFrame(payload_rows)], axis=1)

    keep_cols = [
        "notified_at",
        "time",
        "signal_jst_plus_config_dt",
        "signal_jst_plus6_dt",
        "signal_jst_plus7_dt",
        "lag_min_plus_config",
        "lag_min_plus6",
        "lag_min_plus7",
        "symbol_group",
        "strategy_label",
        "side",
        "notification_key",
        "payload_exists",
        "payload_jst_hour",
        "payload_server_to_jst_hours",
        "entry_price_estimate",
        "tp_price_estimate",
        "sl_price_estimate",
        "payload_file",
    ]
    return df[[c for c in keep_cols if c in df.columns]].sort_values("notified_at")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit live notification ledger times and server-to-JST conversion.")
    parser.add_argument("--gold-ledger", type=Path, default=DEFAULT_GOLD_LEDGER)
    parser.add_argument("--btc-ledger", type=Path, default=DEFAULT_BTC_LEDGER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--start", default="", help="Filter notified_at >= this local time, e.g. 2026-05-04 00:00")
    parser.add_argument("--end", default="", help="Filter notified_at <= this local time, e.g. 2026-05-05 23:59")
    parser.add_argument("--server-to-jst-hours", type=int, default=6)
    parser.add_argument("--csv-out", type=Path, default=None)
    args = parser.parse_args()

    start = parse_dt(args.start) if args.start else None
    end = parse_dt(args.end) if args.end else None
    out_dir = resolve_path(args.out_dir)

    frames = []
    frames.append(audit_one_ledger(resolve_path(args.gold_ledger), symbol="GOLD", out_dir=out_dir, start=start, end=end, server_to_jst_hours=args.server_to_jst_hours))
    frames.append(audit_one_ledger(resolve_path(args.btc_ledger), symbol="BTC", out_dir=out_dir, start=start, end=end, server_to_jst_hours=args.server_to_jst_hours))
    df = pd.concat([x for x in frames if not x.empty], ignore_index=True) if any(not x.empty for x in frames) else pd.DataFrame()

    if df.empty:
        print("No notification ledger rows found for the selected range.")
        return 0

    pd.set_option("display.max_columns", 50)
    pd.set_option("display.width", 240)
    print(df.to_string(index=False))

    if args.csv_out is not None:
        csv_out = resolve_path(args.csv_out)
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_out, index=False, encoding="utf-8-sig")
        print("\nWrote:", csv_out)

    print("\nNotes:")
    print("- time is the raw MT5/server candle time stored in the payload/ledger.")
    print("- signal_jst_plus6_dt is the expected JST time if server time is JST-6.")
    print("- lag_min_plus6 shows how many minutes after that signal candle the Discord notification was sent.")
    print("- If lag_min_plus6 is around 60 minutes, this is not timezone conversion; it means an older unnotified signal was sent later.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
