from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIVE_DIR = PROJECT_ROOT / "data" / "results" / "live_payloads"
DEFAULT_GOLD_LEDGER = DEFAULT_LIVE_DIR / "notified_gold_signals_ledger.csv"
DEFAULT_BTC_LEDGER = DEFAULT_LIVE_DIR / "notified_btc_signals_ledger.csv"

DEFAULT_GOLD_M15_CSV = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_m15.csv")
DEFAULT_GOLD_M5_CSV = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\goldsharp_m5.csv")
DEFAULT_BTC_M5_CSV = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m5.csv")
DEFAULT_BTC_M15_CSV = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def parse_dt(value: Any) -> pd.Timestamp | pd.NaT:
    if value is None or pd.isna(value):
        return pd.NaT
    return pd.to_datetime(str(value), errors="coerce")


def read_ohlc(path: Path) -> pd.DataFrame:
    path = resolve_path(path)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty or "time" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time", kind="mergesort").reset_index(drop=True)
    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def payload_path_for_key(out_dir: Path, notification_key: str) -> Path:
    key = str(notification_key).replace("|", "_").replace(":", "").replace(" ", "_")
    return out_dir / f"notify_payload_{key}.json"


def load_payload(out_dir: Path, notification_key: str) -> dict[str, Any] | None:
    path = payload_path_for_key(out_dir, notification_key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def safe_float(value: Any) -> float | None:
    try:
        x = float(value)
    except Exception:
        return None
    if pd.isna(x):
        return None
    return x


def load_ledger(path: Path, *, symbol: str, out_dir: Path, server_to_jst_hours: int, start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.DataFrame:
    path = resolve_path(path)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["symbol_group"] = df.get("symbol_group", symbol)
    df["notified_at_dt"] = df.get("notified_at", pd.Series(dtype=str)).map(parse_dt)
    df["signal_server_dt"] = df.get("time", pd.Series(dtype=str)).map(parse_dt)
    df["signal_jst_dt"] = df["signal_server_dt"] + pd.to_timedelta(server_to_jst_hours, unit="h")
    df["lag_min"] = (df["notified_at_dt"] - df["signal_jst_dt"]).dt.total_seconds() / 60.0
    df["lag_flag"] = "OK"
    df.loc[df["lag_min"] > 10, "lag_flag"] = "STALE_GT_10M"
    df.loc[df["lag_min"] > 20, "lag_flag"] = "STALE_GT_20M"
    df.loc[df["lag_min"] > 60, "lag_flag"] = "STALE_GT_60M"
    df.loc[df["lag_min"] < -5, "lag_flag"] = "NEGATIVE_LAG_CHECK_TZ"

    if start is not None:
        df = df[df["notified_at_dt"] >= start]
    if end is not None:
        df = df[df["notified_at_dt"] <= end]

    extras: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        key = str(row.get("notification_key", ""))
        payload = load_payload(out_dir, key)
        cur = (payload or {}).get("current_signal_snapshot", {}) if payload else {}
        plan = cur.get("trade_plan") or (payload or {}).get("trade_plan") or {}
        extras.append(
            {
                "payload_exists": payload is not None,
                "payload_file": str(payload_path_for_key(out_dir, key)) if payload_path_for_key(out_dir, key).exists() else "",
                "payload_time": (payload or {}).get("time", "") if payload else "",
                "payload_source_tf": cur.get("source_tf", row.get("source_tf", "")) if isinstance(cur, dict) else row.get("source_tf", ""),
                "payload_entry_time_proxy": cur.get("entry_time_proxy", "") if isinstance(cur, dict) else "",
                "payload_jst_hour": cur.get("jst_hour", "") if isinstance(cur, dict) else "",
                "payload_server_to_jst_hours": cur.get("server_to_jst_hours", "") if isinstance(cur, dict) else "",
                "entry_price": safe_float(plan.get("entry_price_estimate", row.get("entry_price_estimate", None))) if isinstance(plan, dict) else safe_float(row.get("entry_price_estimate", None)),
                "tp_price": safe_float(plan.get("tp_price_estimate", row.get("tp_price_estimate", None))) if isinstance(plan, dict) else safe_float(row.get("tp_price_estimate", None)),
                "sl_price": safe_float(plan.get("sl_price_estimate", row.get("sl_price_estimate", None))) if isinstance(plan, dict) else safe_float(row.get("sl_price_estimate", None)),
            }
        )
    if extras:
        df = pd.concat([df.reset_index(drop=True), pd.DataFrame(extras)], axis=1)
    return df


def first_touch_outcome(
    ohlc: pd.DataFrame,
    *,
    signal_time: pd.Timestamp,
    side: str,
    tp: float | None,
    sl: float | None,
    horizon_bars: int,
    inbar_priority: str,
) -> dict[str, Any]:
    if ohlc.empty or pd.isna(signal_time) or tp is None or sl is None:
        return {
            "outcome": "UNKNOWN",
            "outcome_reason": "missing_ohlc_or_prices",
            "touch_time": "",
            "bars_to_touch": "",
            "max_favorable": "",
            "max_adverse": "",
        }

    side = str(side).upper()
    idx_list = ohlc.index[ohlc["time"] > signal_time].tolist()
    if not idx_list:
        return {
            "outcome": "OPEN_OR_NO_FUTURE_BARS",
            "outcome_reason": "no bars after signal_time",
            "touch_time": "",
            "bars_to_touch": "",
            "max_favorable": "",
            "max_adverse": "",
        }
    start = int(idx_list[0])
    end = min(len(ohlc), start + max(1, horizon_bars))
    window = ohlc.iloc[start:end].copy()
    if window.empty:
        return {
            "outcome": "OPEN_OR_NO_FUTURE_BARS",
            "outcome_reason": "empty future window",
            "touch_time": "",
            "bars_to_touch": "",
            "max_favorable": "",
            "max_adverse": "",
        }

    # Conservative first-touch. If TP and SL are hit within the same OHLC bar, use inbar_priority.
    for n, (_, bar) in enumerate(window.iterrows(), start=1):
        high = float(bar.get("high"))
        low = float(bar.get("low"))
        if side == "BUY":
            hit_tp = high >= tp
            hit_sl = low <= sl
        else:
            hit_tp = low <= tp
            hit_sl = high >= sl
        if hit_tp and hit_sl:
            outcome = "SL" if inbar_priority.upper() == "SL" else "TP"
            return {
                "outcome": outcome,
                "outcome_reason": "both_hit_same_bar_" + inbar_priority.upper(),
                "touch_time": bar.get("time"),
                "bars_to_touch": n,
                "max_favorable": calc_max_favorable(window.iloc[:n], side, signal_time, tp, sl),
                "max_adverse": calc_max_adverse(window.iloc[:n], side, signal_time, tp, sl),
            }
        if hit_tp:
            return {
                "outcome": "TP",
                "outcome_reason": "tp_first",
                "touch_time": bar.get("time"),
                "bars_to_touch": n,
                "max_favorable": calc_max_favorable(window.iloc[:n], side, signal_time, tp, sl),
                "max_adverse": calc_max_adverse(window.iloc[:n], side, signal_time, tp, sl),
            }
        if hit_sl:
            return {
                "outcome": "SL",
                "outcome_reason": "sl_first",
                "touch_time": bar.get("time"),
                "bars_to_touch": n,
                "max_favorable": calc_max_favorable(window.iloc[:n], side, signal_time, tp, sl),
                "max_adverse": calc_max_adverse(window.iloc[:n], side, signal_time, tp, sl),
            }

    return {
        "outcome": "NO_TOUCH",
        "outcome_reason": f"no_tp_sl_within_{horizon_bars}_bars",
        "touch_time": "",
        "bars_to_touch": "",
        "max_favorable": calc_max_favorable(window, side, signal_time, tp, sl),
        "max_adverse": calc_max_adverse(window, side, signal_time, tp, sl),
    }


def calc_max_favorable(window: pd.DataFrame, side: str, signal_time: pd.Timestamp, tp: float | None, sl: float | None) -> float | str:
    if window.empty:
        return ""
    # In price units from entry proxy. The entry proxy is not directly passed; use TP/SL midpoint approximation only as rough diagnostic.
    return ""


def calc_max_adverse(window: pd.DataFrame, side: str, signal_time: pd.Timestamp, tp: float | None, sl: float | None) -> float | str:
    if window.empty:
        return ""
    return ""


def attach_outcomes(df: pd.DataFrame, *, gold_ohlc: pd.DataFrame, btc_ohlc: pd.DataFrame, gold_horizon_bars: int, btc_horizon_bars: int, inbar_priority: str) -> pd.DataFrame:
    if df.empty:
        return df
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol_group", "")).upper()
        ohlc = btc_ohlc if symbol == "BTC" else gold_ohlc
        horizon = btc_horizon_bars if symbol == "BTC" else gold_horizon_bars
        result = first_touch_outcome(
            ohlc,
            signal_time=row.get("signal_server_dt"),
            side=str(row.get("side", "")),
            tp=safe_float(row.get("tp_price")),
            sl=safe_float(row.get("sl_price")),
            horizon_bars=horizon,
            inbar_priority=inbar_priority,
        )
        rows.append(result)
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit live notification timing and first-touch outcomes.")
    parser.add_argument("--gold-ledger", type=Path, default=DEFAULT_GOLD_LEDGER)
    parser.add_argument("--btc-ledger", type=Path, default=DEFAULT_BTC_LEDGER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_LIVE_DIR)
    parser.add_argument("--gold-ohlc", type=Path, default=DEFAULT_GOLD_M15_CSV, help="GOLD outcome OHLC. Use M5 if available; default is M15.")
    parser.add_argument("--btc-ohlc", type=Path, default=DEFAULT_BTC_M5_CSV, help="BTC outcome OHLC. Default is M5.")
    parser.add_argument("--server-to-jst-hours", type=int, default=6)
    parser.add_argument("--start", default="")
    parser.add_argument("--end", default="")
    parser.add_argument("--gold-horizon-bars", type=int, default=32, help="Default M15 32 bars = 8 hours if gold-ohlc is M15.")
    parser.add_argument("--btc-horizon-bars", type=int, default=96, help="Default M5 96 bars = 8 hours.")
    parser.add_argument("--inbar-priority", choices=["SL", "TP"], default="SL")
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_LIVE_DIR / "live_notification_outcome_audit.csv")
    args = parser.parse_args()

    start = parse_dt(args.start) if args.start else None
    end = parse_dt(args.end) if args.end else None
    out_dir = resolve_path(args.out_dir)

    gold = load_ledger(args.gold_ledger, symbol="GOLD", out_dir=out_dir, server_to_jst_hours=args.server_to_jst_hours, start=start, end=end)
    btc = load_ledger(args.btc_ledger, symbol="BTC", out_dir=out_dir, server_to_jst_hours=args.server_to_jst_hours, start=start, end=end)
    frames = [x for x in [gold, btc] if not x.empty]
    if not frames:
        print("No ledger rows found for selected range.")
        return 0

    df = pd.concat(frames, ignore_index=True)
    gold_ohlc = read_ohlc(args.gold_ohlc)
    btc_ohlc = read_ohlc(args.btc_ohlc)
    df = attach_outcomes(
        df,
        gold_ohlc=gold_ohlc,
        btc_ohlc=btc_ohlc,
        gold_horizon_bars=args.gold_horizon_bars,
        btc_horizon_bars=args.btc_horizon_bars,
        inbar_priority=args.inbar_priority,
    )
    df = df.sort_values(["notified_at_dt", "symbol_group"], kind="mergesort")

    keep = [
        "notified_at",
        "time",
        "signal_jst_dt",
        "lag_min",
        "lag_flag",
        "symbol_group",
        "strategy_label",
        "side",
        "entry_price",
        "tp_price",
        "sl_price",
        "outcome",
        "outcome_reason",
        "touch_time",
        "bars_to_touch",
        "notification_key",
        "payload_file",
    ]
    view = df[[c for c in keep if c in df.columns]].copy()
    if "lag_min" in view.columns:
        view["lag_min"] = view["lag_min"].round(2)

    pd.set_option("display.max_columns", 80)
    pd.set_option("display.width", 260)
    print(view.to_string(index=False))

    csv_out = resolve_path(args.csv_out)
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    view.to_csv(csv_out, index=False, encoding="utf-8-sig")
    print("\nWrote:", csv_out)

    print("\nSummary:")
    print(view.groupby(["symbol_group", "outcome"], dropna=False).size().to_string())
    print("\nLag summary:")
    print(view.groupby(["symbol_group", "lag_flag"], dropna=False).size().to_string())
    print("\nNotes:")
    print("- time is MT5/server candle time. signal_jst_dt is time + server-to-JST offset.")
    print("- outcome uses first touch after the signal candle, with same-bar priority set by --inbar-priority.")
    print("- GOLD defaults to M15 outcome if goldsharp_m5.csv is unavailable; M15 is coarser than M5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
