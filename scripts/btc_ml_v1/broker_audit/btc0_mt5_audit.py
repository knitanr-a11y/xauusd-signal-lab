from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

READ_ONLY_AUDIT = True
DEFAULT_OUTPUT_DIR = Path("outputs/btc_ml_v1/btc0_broker_data_audit")
DEFAULT_CSV_ROOT = Path("Files")
BTC_TOKEN = re.compile(r"(?:BTC|XBT|BITCOIN)", re.IGNORECASE)
TIMEFRAME_NAMES = ("M1", "M5", "M15", "H1", "H4", "D1")
SYMBOL_FIELDS = (
    "name",
    "description",
    "path",
    "currency_base",
    "currency_profit",
    "currency_margin",
    "digits",
    "point",
    "trade_contract_size",
    "volume_min",
    "volume_step",
    "volume_max",
    "trade_tick_size",
    "trade_tick_value",
    "trade_tick_value_profit",
    "trade_tick_value_loss",
    "spread",
    "spread_float",
    "trade_stops_level",
    "trade_freeze_level",
    "filling_mode",
    "trade_mode",
    "order_mode",
    "expiration_mode",
    "visible",
    "select",
)


@dataclass(frozen=True)
class AuditPaths:
    root: Path
    contract_json: Path
    symbol_candidates_csv: Path
    history_depth_csv: Path
    spread_distribution_csv: Path
    observed_hours_csv: Path
    csv_inventory_csv: Path


def build_paths(output_dir: Path) -> AuditPaths:
    root = output_dir.resolve()
    return AuditPaths(
        root=root,
        contract_json=root / "btc0_broker_contract.json",
        symbol_candidates_csv=root / "broker_symbol_candidates.csv",
        history_depth_csv=root / "history_depth.csv",
        spread_distribution_csv=root / "spread_distribution.csv",
        observed_hours_csv=root / "observed_trading_hours_utc.csv",
        csv_inventory_csv=root / "existing_btc_csv_inventory.csv",
    )


def _asdict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    method = getattr(value, "_asdict", None)
    if callable(method):
        return dict(method())
    return {
        field: getattr(value, field)
        for field in SYMBOL_FIELDS
        if hasattr(value, field)
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and np.isnan(value):
        return ""
    return str(value).strip()


def _number(value: Any) -> float | None:
    text = _text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return None if number is None else int(number)


def _utc_text(epoch_seconds: Any) -> str:
    seconds = _integer(epoch_seconds)
    if seconds is None or seconds <= 0:
        return ""
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def symbol_record(info: Any) -> dict[str, Any]:
    payload = _asdict(info)
    record = {field: payload.get(field, "") for field in SYMBOL_FIELDS}
    searchable = " ".join(
        _text(record.get(field))
        for field in ("name", "description", "path", "currency_base")
    )
    record["btc_token_match"] = bool(BTC_TOKEN.search(searchable))
    trade_mode = _integer(record.get("trade_mode"))
    record["tradeable_candidate"] = trade_mode is None or trade_mode != 0
    record["candidate_score"] = candidate_score(record)
    return record


def candidate_score(record: dict[str, Any]) -> int:
    name = _text(record.get("name")).upper()
    base = _text(record.get("currency_base")).upper()
    description = _text(record.get("description")).upper()
    score = 0
    if base in {"BTC", "XBT"}:
        score += 100
    if name.startswith(("BTC", "XBT")):
        score += 50
    if "USD" in name:
        score += 20
    if BTC_TOKEN.search(description):
        score += 10
    if bool(record.get("visible")):
        score += 5
    if bool(record.get("select")):
        score += 5
    if record.get("tradeable_candidate"):
        score += 10
    return score


def discover_btc_symbols(symbols: Iterable[Any]) -> pd.DataFrame:
    rows = [symbol_record(info) for info in symbols]
    rows = [row for row in rows if row["btc_token_match"]]
    if not rows:
        return pd.DataFrame(columns=[*SYMBOL_FIELDS, "btc_token_match", "tradeable_candidate", "candidate_score"])
    frame = pd.DataFrame(rows)
    frame = frame.sort_values(
        ["candidate_score", "name"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)
    return frame


def choose_symbol(candidates: pd.DataFrame, requested: str | None) -> str | None:
    if candidates.empty:
        return None
    names = candidates["name"].astype(str)
    if requested:
        matches = candidates[names.str.upper().eq(requested.strip().upper())]
        if len(matches) != 1:
            raise ValueError(f"requested BTC symbol not found uniquely: {requested}")
        return str(matches.iloc[0]["name"])
    tradeable = candidates[candidates["tradeable_candidate"].astype(bool)]
    if len(tradeable) == 1:
        return str(tradeable.iloc[0]["name"])
    return None


def rates_frame(raw_rates: Any) -> pd.DataFrame:
    if raw_rates is None:
        return pd.DataFrame()
    frame = pd.DataFrame(raw_rates)
    if frame.empty or "time" not in frame.columns:
        return pd.DataFrame(columns=list(frame.columns))
    frame = frame.sort_values("time", kind="mergesort").drop_duplicates(
        "time", keep="last"
    )
    # MT5 position 0 is the current/open bar. BTC-0 is read-only and all
    # history statistics use closed rows only, so the newest returned bar is
    # deliberately excluded.
    if len(frame) > 0:
        frame = frame.iloc[:-1].copy()
    if frame.empty:
        return frame
    frame["time_utc"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame.reset_index(drop=True)


def history_record(symbol: str, timeframe: str, frame: pd.DataFrame, requested_bars: int) -> dict[str, Any]:
    if frame.empty:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "closed_rows": 0,
            "first_closed_time_utc": "",
            "last_closed_time_utc": "",
            "requested_bars": requested_bars,
            "terminal_history_cap_reached": False,
            "duplicate_times_after_normalization": 0,
            "latest_row_contract": "CLOSED_ONLY_OPEN_BAR_EXCLUDED",
        }
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "closed_rows": int(len(frame)),
        "first_closed_time_utc": frame["time_utc"].iloc[0].strftime("%Y-%m-%d %H:%M:%S"),
        "last_closed_time_utc": frame["time_utc"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S"),
        "requested_bars": requested_bars,
        "terminal_history_cap_reached": bool(len(frame) >= max(requested_bars - 1, 0)),
        "duplicate_times_after_normalization": int(frame["time"].duplicated().sum()),
        "latest_row_contract": "CLOSED_ONLY_OPEN_BAR_EXCLUDED",
    }


def spread_record(symbol: str, point: float | None, m1: pd.DataFrame) -> dict[str, Any]:
    base = {
        "symbol": symbol,
        "closed_m1_rows": int(len(m1)),
        "spread_rows": 0,
        "spread_points_p50": "",
        "spread_points_p90": "",
        "spread_points_p99": "",
        "spread_points_mean": "",
        "spread_points_max": "",
        "spread_price_p50": "",
        "spread_price_p90": "",
        "spread_price_p99": "",
    }
    if m1.empty or "spread" not in m1.columns:
        return base
    spread = pd.to_numeric(m1["spread"], errors="coerce")
    spread = spread[np.isfinite(spread) & spread.ge(0)]
    if spread.empty:
        return base
    p50, p90, p99 = (float(spread.quantile(q)) for q in (0.50, 0.90, 0.99))
    base.update(
        {
            "spread_rows": int(len(spread)),
            "spread_points_p50": p50,
            "spread_points_p90": p90,
            "spread_points_p99": p99,
            "spread_points_mean": float(spread.mean()),
            "spread_points_max": float(spread.max()),
        }
    )
    if point is not None and point > 0:
        base.update(
            {
                "spread_price_p50": p50 * point,
                "spread_price_p90": p90 * point,
                "spread_price_p99": p99 * point,
            }
        )
    return base


def observed_hours(symbol: str, m1: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "symbol",
        "weekday_utc",
        "hour_utc",
        "closed_m1_bars",
        "observed",
    ]
    if m1.empty or "time_utc" not in m1.columns:
        return pd.DataFrame(columns=columns)
    frame = m1.copy()
    frame["weekday_utc"] = frame["time_utc"].dt.day_name()
    frame["weekday_number_utc"] = frame["time_utc"].dt.weekday
    frame["hour_utc"] = frame["time_utc"].dt.hour
    grouped = (
        frame.groupby(["weekday_number_utc", "weekday_utc", "hour_utc"])
        .size()
        .rename("closed_m1_bars")
        .reset_index()
        .sort_values(["weekday_number_utc", "hour_utc"], kind="mergesort")
    )
    grouped.insert(0, "symbol", symbol)
    grouped["observed"] = True
    return grouped[columns].reset_index(drop=True)


def weekend_summary(m1: pd.DataFrame) -> dict[str, Any]:
    if m1.empty or "time_utc" not in m1.columns:
        return {"weekend_closed_m1_bars": 0, "weekend_trading_observed": False}
    weekend = m1["time_utc"].dt.weekday.isin([5, 6])
    count = int(weekend.sum())
    return {
        "weekend_closed_m1_bars": count,
        "weekend_trading_observed": count > 0,
    }


def audit_csv_files(csv_root: Path) -> pd.DataFrame:
    columns = [
        "path",
        "rows",
        "columns",
        "time_column",
        "first_time",
        "last_time",
        "duplicate_times",
        "latest_row_contract",
        "read_error",
    ]
    if not csv_root.is_dir():
        return pd.DataFrame(columns=columns)
    rows: list[dict[str, Any]] = []
    for path in sorted(csv_root.rglob("*.csv")):
        searchable = f"{path.name} {path.parent}"
        if not BTC_TOKEN.search(searchable):
            continue
        record: dict[str, Any] = {
            "path": str(path.resolve()),
            "rows": 0,
            "columns": "",
            "time_column": "",
            "first_time": "",
            "last_time": "",
            "duplicate_times": 0,
            "latest_row_contract": "CLOSED_BY_EXTERNAL_CSV_CONTRACT",
            "read_error": "",
        }
        try:
            frame = pd.read_csv(path, low_memory=False)
            record["rows"] = int(len(frame))
            record["columns"] = "|".join(map(str, frame.columns))
            time_column = next(
                (column for column in ("time", "datetime", "date", "timestamp") if column in frame.columns),
                "",
            )
            record["time_column"] = time_column
            if time_column:
                values = frame[time_column].astype(str)
                record["first_time"] = values.iloc[0] if len(values) else ""
                record["last_time"] = values.iloc[-1] if len(values) else ""
                record["duplicate_times"] = int(values.duplicated().sum())
        except Exception as exc:
            record["read_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(record)
    return pd.DataFrame(rows, columns=columns)


def _atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8")
    os.replace(temporary, path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, path)


def _mt5_initialize(mt5: Any, args: argparse.Namespace) -> None:
    kwargs: dict[str, Any] = {}
    login = args.login or _integer(os.getenv("BTC0_MT5_LOGIN"))
    password = args.password or os.getenv("BTC0_MT5_PASSWORD")
    server = args.server or os.getenv("BTC0_MT5_SERVER")
    if login is not None:
        kwargs["login"] = login
    if password:
        kwargs["password"] = password
    if server:
        kwargs["server"] = server
    terminal_path = args.terminal_path or os.getenv("BTC0_MT5_TERMINAL_PATH")
    ok = mt5.initialize(terminal_path, **kwargs) if terminal_path else mt5.initialize(**kwargs)
    if not ok:
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")


def _account_summary(mt5: Any) -> dict[str, Any]:
    terminal = _asdict(mt5.terminal_info())
    account = _asdict(mt5.account_info())
    login = _text(account.get("login"))
    return {
        "terminal_company": _text(terminal.get("company")),
        "terminal_name": _text(terminal.get("name")),
        "terminal_path": _text(terminal.get("path")),
        "account_login_masked": f"***{login[-4:]}" if login else "",
        "account_server": _text(account.get("server")),
        "account_company": _text(account.get("company")),
        "account_currency": _text(account.get("currency")),
        "account_leverage": _integer(account.get("leverage")),
        "account_trade_mode": _integer(account.get("trade_mode")),
    }


def _timeframe_constant(mt5: Any, name: str) -> Any:
    return getattr(mt5, f"TIMEFRAME_{name}")


def _current_tick_fields(mt5: Any, symbol: str, point: float | None) -> dict[str, Any]:
    tick = _asdict(mt5.symbol_info_tick(symbol))
    bid = _number(tick.get("bid"))
    ask = _number(tick.get("ask"))
    spread_points = None
    if bid is not None and ask is not None and point is not None and point > 0:
        spread_points = (ask - bid) / point
    return {
        "tick_time_utc": _utc_text(tick.get("time")),
        "bid": bid,
        "ask": ask,
        "last": _number(tick.get("last")),
        "current_spread_points_from_tick": spread_points,
    }


def _minimum_lot_move_risk(mt5: Any, symbol: str, record: dict[str, Any]) -> dict[str, Any]:
    volume_min = _number(record.get("volume_min"))
    tick = _asdict(mt5.symbol_info_tick(symbol))
    ask = _number(tick.get("ask"))
    if volume_min is None or ask is None or volume_min <= 0 or ask <= 0:
        return {
            "min_lot_1pct_down_move_profit_account_ccy": None,
            "min_lot_1pct_down_move_abs_loss_account_ccy": None,
        }
    calculator = getattr(mt5, "order_calc_profit", None)
    order_type_buy = getattr(mt5, "ORDER_TYPE_BUY", None)
    if not callable(calculator) or order_type_buy is None:
        return {
            "min_lot_1pct_down_move_profit_account_ccy": None,
            "min_lot_1pct_down_move_abs_loss_account_ccy": None,
        }
    profit = calculator(order_type_buy, symbol, volume_min, ask, ask * 0.99)
    profit_number = _number(profit)
    return {
        "min_lot_1pct_down_move_profit_account_ccy": profit_number,
        "min_lot_1pct_down_move_abs_loss_account_ccy": (
            abs(profit_number) if profit_number is not None and profit_number < 0 else 0.0
            if profit_number is not None
            else None
        ),
    }


def run_audit(mt5: Any, args: argparse.Namespace) -> dict[str, Any]:
    paths = build_paths(Path(args.output_dir))
    paths.root.mkdir(parents=True, exist_ok=True)
    _mt5_initialize(mt5, args)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        raw_symbols: Sequence[Any] = mt5.symbols_get() or ()
        candidates = discover_btc_symbols(raw_symbols)
        requested_symbol = args.symbol or os.getenv("BTC0_MT5_SYMBOL")
        selected_symbol = choose_symbol(candidates, requested_symbol)

        symbol_rows: list[dict[str, Any]] = []
        history_rows: list[dict[str, Any]] = []
        spread_rows: list[dict[str, Any]] = []
        hour_frames: list[pd.DataFrame] = []
        warnings: list[str] = []

        if candidates.empty:
            warnings.append("BTC/XBT/Bitcoin token matched no MT5 symbols")
        if selected_symbol is None and not candidates.empty:
            warnings.append(
                "multiple or zero tradeable BTC candidates; rerun with --symbol after reviewing broker_symbol_candidates.csv"
            )

        audit_symbols = [selected_symbol] if selected_symbol else candidates["name"].astype(str).tolist()
        for symbol in audit_symbols:
            if not mt5.symbol_select(symbol, True):
                warnings.append(f"symbol_select failed: {symbol} {mt5.last_error()}")
                continue
            info = mt5.symbol_info(symbol)
            record = symbol_record(info)
            point = _number(record.get("point"))
            record.update(_current_tick_fields(mt5, symbol, point))
            record.update(_minimum_lot_move_risk(mt5, symbol, record))
            symbol_rows.append(record)

            m1_closed = pd.DataFrame()
            for timeframe in TIMEFRAME_NAMES:
                raw = mt5.copy_rates_from_pos(
                    symbol,
                    _timeframe_constant(mt5, timeframe),
                    0,
                    int(args.history_bars),
                )
                closed = rates_frame(raw)
                history_rows.append(
                    history_record(symbol, timeframe, closed, int(args.history_bars))
                )
                if timeframe == "M1":
                    m1_closed = closed
            spread = spread_record(symbol, point, m1_closed)
            spread.update(weekend_summary(m1_closed))
            spread_rows.append(spread)
            hour_frames.append(observed_hours(symbol, m1_closed))

        final_candidates = candidates.copy()
        if symbol_rows:
            detailed = pd.DataFrame(symbol_rows)
            detailed = detailed.drop_duplicates("name", keep="last")
            final_candidates = final_candidates.drop(
                columns=[column for column in detailed.columns if column in final_candidates.columns and column != "name"],
                errors="ignore",
            ).merge(detailed, on="name", how="left")

        csv_inventory = audit_csv_files(Path(args.csv_root))
        observed = (
            pd.concat(hour_frames, ignore_index=True)
            if hour_frames
            else observed_hours("", pd.DataFrame())
        )
        history = pd.DataFrame(history_rows)
        spread_frame = pd.DataFrame(spread_rows)

        _atomic_write_csv(paths.symbol_candidates_csv, final_candidates)
        _atomic_write_csv(paths.history_depth_csv, history)
        _atomic_write_csv(paths.spread_distribution_csv, spread_frame)
        _atomic_write_csv(paths.observed_hours_csv, observed)
        _atomic_write_csv(paths.csv_inventory_csv, csv_inventory)

        payload = {
            "schema_version": 1,
            "stage": "BTC-0_BROKER_AND_DATA_CONTRACT_AUDIT",
            "generated_at_utc": generated_at,
            "read_only": READ_ONLY_AUDIT,
            "orders_enabled": False,
            "live_ready": False,
            "final_signal": False,
            "discord_enabled": False,
            "mt5_order_send_available_in_this_script": False,
            "selected_symbol": selected_symbol,
            "requested_symbol": requested_symbol or "",
            "candidate_count": int(len(candidates)),
            "audited_symbol_count": int(len(symbol_rows)),
            "history_bars_requested_per_timeframe": int(args.history_bars),
            "latest_mt5_bar_policy": "OPEN_BAR_EXCLUDED; ALL AUDIT HISTORY ROWS CLOSED",
            "csv_latest_row_policy": "EXISTING BTC CSV LATEST ROW TREATED CLOSED BY CONTRACT",
            "account": _account_summary(mt5),
            "outputs": {
                key: str(value.relative_to(paths.root))
                for key, value in asdict(paths).items()
                if key != "root"
            },
            "warnings": warnings,
        }
        _atomic_write_json(paths.contract_json, payload)
        return payload
    finally:
        mt5.shutdown()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="BTC-0 read-only MT5 broker/data contract audit. Never sends orders."
    )
    parser.add_argument("--symbol", help="Exact broker BTC symbol. Omit to enumerate candidates.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--csv-root", default=str(DEFAULT_CSV_ROOT))
    parser.add_argument("--history-bars", type=int, default=250_000)
    parser.add_argument("--terminal-path")
    parser.add_argument("--login", type=int)
    parser.add_argument("--password")
    parser.add_argument("--server")
    args = parser.parse_args(argv)
    if args.history_bars < 2:
        parser.error("--history-bars must be at least 2 so the open bar can be excluded")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise SystemExit(
            "MetaTrader5 Python package is required on the user PC for BTC-0 audit"
        ) from exc
    payload = run_audit(mt5, args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload["selected_symbol"] is None:
        print(
            "BTC symbol was not selected automatically. Review broker_symbol_candidates.csv and rerun with --symbol."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
