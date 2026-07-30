from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

STAGE = "BCR08_MT5_SYMBOL_AND_COST_PROVENANCE"
VERSION = "1.0.0"
EXPECTED_MEMBERS = [
    "00_READ_ME_FIRST.txt",
    "01_bcr08_summary.json",
    "02_terminal_info.json",
    "03_account_context_redacted.json",
    "04_symbol_candidates.csv",
    "05_target_symbol_info.json",
    "06_target_tick_snapshot.json",
    "07_csv_spread_observation.json",
    "08_cost_field_interpretation.json",
    "09_runtime_integrity.json",
    "10_output_manifest.json",
    "11_error.json",
]

ACCOUNT_ALLOWLIST = (
    "server",
    "company",
    "currency",
    "currency_digits",
    "leverage",
    "trade_mode",
    "margin_mode",
    "fifo_close",
    "trade_allowed",
    "trade_expert",
)

TERMINAL_ALLOWLIST = (
    "community_account",
    "community_connection",
    "connected",
    "dlls_allowed",
    "trade_allowed",
    "tradeapi_disabled",
    "email_enabled",
    "ftp_enabled",
    "notifications_enabled",
    "mqid",
    "build",
    "maxbars",
    "codepage",
    "name",
    "company",
    "language",
    "path",
    "data_path",
    "commondata_path",
)

SYMBOL_SUMMARY_FIELDS = (
    "name",
    "description",
    "path",
    "select",
    "visible",
    "digits",
    "point",
    "spread",
    "spread_float",
    "trade_tick_size",
    "trade_tick_value",
    "trade_tick_value_profit",
    "trade_tick_value_loss",
    "trade_contract_size",
    "trade_calc_mode",
    "trade_mode",
    "trade_exemode",
    "trade_stops_level",
    "trade_freeze_level",
    "filling_mode",
    "order_mode",
    "volume_min",
    "volume_max",
    "volume_step",
    "volume_limit",
    "currency_base",
    "currency_profit",
    "currency_margin",
    "bid",
    "ask",
    "last",
    "time",
)

FORBIDDEN_ACCOUNT_FIELDS = {
    "login",
    "name",
    "balance",
    "credit",
    "profit",
    "equity",
    "margin",
    "margin_free",
    "margin_level",
    "assets",
    "liabilities",
    "commission_blocked",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    return str(value)


def namedtuple_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "_asdict"):
        return {str(k): jsonable(v) for k, v in value._asdict().items()}
    raise TypeError(f"Expected namedtuple-like value, got {type(value)!r}")


def select_fields(source: dict[str, Any], names: Iterable[str]) -> dict[str, Any]:
    return {name: source.get(name) for name in names if name in source}


def normalize_path(value: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(value)))


def tasklist_terminal64_running() -> tuple[bool, str]:
    if os.name != "nt":
        return False, "BCR08 must run on Windows with the existing MT5 terminal."
    try:
        cp = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/FO", "CSV", "/NH"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        text = (cp.stdout or "").strip()
        running = "terminal64.exe" in text.lower()
        return running, text
    except Exception as exc:  # pragma: no cover - Windows environment dependent
        return False, f"tasklist failed: {exc}"


def percentile_linear(values: list[float], q: float) -> float | None:
    if not values:
        return None
    data = sorted(values)
    if len(data) == 1:
        return data[0]
    pos = (len(data) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(data) - 1)
    frac = pos - lo
    return data[lo] * (1.0 - frac) + data[hi] * frac


def inspect_csv(path: Path, frozen_sha256: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "frozen_sha256_expected": frozen_sha256,
    }
    if not path.is_file():
        return result

    result["bytes"] = path.stat().st_size
    current_sha = sha256_file(path)
    result["current_sha256"] = current_sha
    result["matches_frozen_sha256"] = current_sha.lower() == frozen_sha256.lower()

    spreads: list[float] = []
    row_count = 0
    latest_time = None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        result["columns"] = reader.fieldnames or []
        if not reader.fieldnames or "spread" not in reader.fieldnames:
            result["spread_column_found"] = False
            return result
        result["spread_column_found"] = True
        for row in reader:
            row_count += 1
            latest_time = row.get("time") or latest_time
            raw = row.get("spread")
            try:
                if raw not in (None, ""):
                    spreads.append(float(raw))
            except ValueError:
                pass

    result["row_count"] = row_count
    result["latest_time"] = latest_time
    result["spread_numeric_count"] = len(spreads)
    if spreads:
        result["spread_observed"] = {
            "min": min(spreads),
            "q10": percentile_linear(spreads, 0.10),
            "median": median(spreads),
            "q90": percentile_linear(spreads, 0.90),
            "q99": percentile_linear(spreads, 0.99),
            "max": max(spreads),
            "latest": spreads[-1],
        }
    return result


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_candidates_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(SYMBOL_SUMMARY_FIELDS)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})


def build_cost_interpretation(
    symbol: dict[str, Any], tick: dict[str, Any], csv_observation: dict[str, Any]
) -> dict[str, Any]:
    point = symbol.get("point")
    tick_size = symbol.get("trade_tick_size")
    digits = symbol.get("digits")
    static_spread = symbol.get("spread")
    bid = tick.get("bid", symbol.get("bid"))
    ask = tick.get("ask", symbol.get("ask"))

    result: dict[str, Any] = {
        "digits": digits,
        "point": point,
        "trade_tick_size": tick_size,
        "trade_tick_value": symbol.get("trade_tick_value"),
        "trade_tick_value_profit": symbol.get("trade_tick_value_profit"),
        "trade_tick_value_loss": symbol.get("trade_tick_value_loss"),
        "trade_contract_size": symbol.get("trade_contract_size"),
        "currency_base": symbol.get("currency_base"),
        "currency_profit": symbol.get("currency_profit"),
        "currency_margin": symbol.get("currency_margin"),
        "trade_calc_mode": symbol.get("trade_calc_mode"),
        "symbol_info_spread_points": static_spread,
        "bid": bid,
        "ask": ask,
        "csv_spread_column_semantics": "UNRESOLVED_UNTIL_POINT_AND_LIVE_TICK_COMPARISON_IS_AUDITED",
        "commission_model": "UNRESOLVED_NOT_EXPOSED_BY_SYMBOL_INFO_AND_ACCOUNT_HISTORY_NOT_QUERIED",
        "history_orders_or_deals_queried": False,
    }

    if isinstance(point, (int, float)) and point > 0:
        if isinstance(static_spread, (int, float)):
            result["symbol_info_spread_price_if_points"] = static_spread * point
        if isinstance(tick_size, (int, float)):
            result["trade_tick_size_in_points"] = tick_size / point
        if isinstance(bid, (int, float)) and isinstance(ask, (int, float)) and ask >= bid:
            live_price_spread = ask - bid
            result["tick_snapshot_spread_price"] = live_price_spread
            result["tick_snapshot_spread_points"] = live_price_spread / point

        spread_stats = csv_observation.get("spread_observed") or {}
        result["csv_spread_price_if_points"] = {
            key: value * point
            for key, value in spread_stats.items()
            if isinstance(value, (int, float))
        }

    required = {
        "digits": isinstance(digits, int) and digits >= 0,
        "point": isinstance(point, (int, float)) and point > 0,
        "trade_tick_size": isinstance(tick_size, (int, float)) and tick_size > 0,
        "trade_contract_size": isinstance(symbol.get("trade_contract_size"), (int, float))
        and symbol.get("trade_contract_size") > 0,
        "currency_profit": bool(symbol.get("currency_profit")),
    }
    result["required_field_checks"] = required
    result["minimum_symbol_cost_fields_ready"] = all(required.values())
    return result


def make_readme(status: str, expected_symbol: str, output_zip: Path) -> str:
    return f"""BCR08 - MT5 SYMBOL AND COST PROVENANCE

status: {status}
expected symbol hypothesis: {expected_symbol}
output ZIP: {output_zip}

READ-ONLY FUNCTIONS ONLY:
- initialize / shutdown
- terminal_info
- account_info with redacted allowlist
- symbols_get / symbol_info / symbol_info_tick

NOT USED:
- order_send / order_check
- positions_get / orders_get
- history_orders_get / history_deals_get
- symbol_select
- Collector/M7C/GOLD changes

Upload this first ZIP and do not rerun automatically.
"""


def finalize_package(run_dir: Path, latest_dir: Path) -> Path:
    manifest: dict[str, Any] = {"stage": STAGE, "version": VERSION, "files": {}}
    for name in EXPECTED_MEMBERS:
        if name == "10_output_manifest.json":
            continue
        file_path = run_dir / name
        if not file_path.exists():
            raise RuntimeError(f"Required output member missing before manifest: {name}")
        manifest["files"][name] = {
            "sha256": sha256_file(file_path),
            "bytes": file_path.stat().st_size,
        }
    write_json(run_dir / "10_output_manifest.json", manifest)

    zip_path = run_dir / "99_UPLOAD_PACKAGE.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in EXPECTED_MEMBERS:
            zf.write(run_dir / name, arcname=name)

    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    latest_dir.mkdir(parents=True, exist_ok=True)
    for name in EXPECTED_MEMBERS:
        shutil.copy2(run_dir / name, latest_dir / name)
    shutil.copy2(zip_path, latest_dir / zip_path.name)
    return latest_dir / zip_path.name


def main() -> int:
    parser = argparse.ArgumentParser(description=STAGE)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--expected-data-path", required=True)
    parser.add_argument("--expected-symbol", required=True)
    parser.add_argument("--csv-path", required=True)
    parser.add_argument("--frozen-csv-sha256", required=True)
    args = parser.parse_args()

    output_root = Path(args.output_root).expanduser().resolve()
    run_id = datetime.now(timezone.utc).strftime("BCR08_%Y%m%dT%H%M%SZ")
    run_dir = output_root / "RUNS" / run_id
    latest_dir = output_root / "LATEST"
    run_dir.mkdir(parents=True, exist_ok=False)

    status = "BLOCKED_OR_FAILED"
    error: dict[str, Any] | None = None
    mt5 = None
    initialized = False
    terminal_payload: dict[str, Any] = {}
    account_payload: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []
    target_payload: dict[str, Any] = {}
    tick_payload: dict[str, Any] = {}
    csv_observation = inspect_csv(Path(args.csv_path), args.frozen_csv_sha256)
    cost_payload: dict[str, Any] = {}
    runtime_integrity: dict[str, Any] = {
        "generated_at_utc": now_utc(),
        "stage": STAGE,
        "version": VERSION,
        "read_only_intent": True,
        "orders_sent": False,
        "orders_checked": False,
        "positions_queried": False,
        "orders_queried": False,
        "history_orders_queried": False,
        "history_deals_queried": False,
        "symbol_select_called": False,
        "collector_or_m7c_modified": False,
        "gold_or_mochipoyo_modified": False,
        "account_identity_or_balance_exported": False,
    }

    try:
        running, tasklist_text = tasklist_terminal64_running()
        runtime_integrity["terminal64_running_before_initialize"] = running
        runtime_integrity["tasklist_observation"] = tasklist_text
        if not running:
            raise RuntimeError("terminal64.exe was not already running; BCR08 refuses to launch MT5.")

        try:
            import MetaTrader5 as mt5_module  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"MetaTrader5 Python package import failed: {exc}") from exc
        mt5 = mt5_module
        runtime_integrity["MetaTrader5_python_package_version"] = getattr(mt5, "__version__", None)

        if not mt5.initialize():
            raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
        initialized = True

        terminal_raw = namedtuple_dict(mt5.terminal_info())
        if not terminal_raw:
            raise RuntimeError(f"terminal_info unavailable: {mt5.last_error()}")
        terminal_payload = select_fields(terminal_raw, TERMINAL_ALLOWLIST)
        observed_data_path = str(terminal_payload.get("data_path") or "")
        runtime_integrity["expected_data_path"] = args.expected_data_path
        runtime_integrity["observed_data_path"] = observed_data_path
        runtime_integrity["data_path_exact_match"] = (
            bool(observed_data_path)
            and normalize_path(observed_data_path) == normalize_path(args.expected_data_path)
        )
        if not runtime_integrity["data_path_exact_match"]:
            raise RuntimeError(
                "Connected MT5 data_path does not match the frozen BTC CSV terminal data path."
            )

        account_raw = namedtuple_dict(mt5.account_info())
        account_payload = select_fields(account_raw, ACCOUNT_ALLOWLIST)
        leaked = sorted(FORBIDDEN_ACCOUNT_FIELDS.intersection(account_payload))
        if leaked:
            raise RuntimeError(f"Forbidden account fields entered export allowlist: {leaked}")

        symbol_values = mt5.symbols_get(group="*BTC*")
        if symbol_values is None:
            raise RuntimeError(f"symbols_get('*BTC*') failed: {mt5.last_error()}")
        for item in symbol_values:
            row = namedtuple_dict(item)
            candidates.append(select_fields(row, SYMBOL_SUMMARY_FIELDS))
        candidates.sort(key=lambda row: str(row.get("name") or ""))

        exact_info = mt5.symbol_info(args.expected_symbol)
        runtime_integrity["expected_symbol"] = args.expected_symbol
        runtime_integrity["expected_symbol_found_exactly"] = exact_info is not None
        if exact_info is None:
            raise RuntimeError(
                f"Expected exact symbol {args.expected_symbol!r} was not found. Candidate list is included."
            )
        target_payload = namedtuple_dict(exact_info)

        tick_value = mt5.symbol_info_tick(args.expected_symbol)
        tick_payload = namedtuple_dict(tick_value) if tick_value is not None else {}
        runtime_integrity["tick_snapshot_available"] = bool(tick_payload)

        cost_payload = build_cost_interpretation(target_payload, tick_payload, csv_observation)
        if not cost_payload.get("minimum_symbol_cost_fields_ready"):
            raise RuntimeError("Required symbol cost fields are incomplete or invalid.")

        status = "READY_MT5_SYMBOL_COST_PROVENANCE_COMMISSION_UNRESOLVED"
    except Exception as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "mt5_last_error": jsonable(mt5.last_error()) if mt5 is not None else None,
        }
    finally:
        if initialized and mt5 is not None:
            try:
                mt5.shutdown()
                runtime_integrity["mt5_shutdown_called"] = True
            except Exception as exc:  # pragma: no cover - environment dependent
                runtime_integrity["mt5_shutdown_called"] = False
                runtime_integrity["mt5_shutdown_error"] = str(exc)
        else:
            runtime_integrity["mt5_shutdown_called"] = False

    summary = {
        "stage": STAGE,
        "version": VERSION,
        "run_id": run_id,
        "generated_at_utc": now_utc(),
        "status": status,
        "expected_symbol_hypothesis": args.expected_symbol,
        "expected_data_path": args.expected_data_path,
        "candidate_symbol_count": len(candidates),
        "target_symbol_found": bool(target_payload),
        "minimum_symbol_cost_fields_ready": bool(cost_payload.get("minimum_symbol_cost_fields_ready")),
        "commission_model": "UNRESOLVED",
        "csv_matches_frozen_sha256": csv_observation.get("matches_frozen_sha256"),
        "safe_to_compute_pnl": False,
        "next_gate": "AUDIT_PACKAGE_THEN_FREEZE_COMMISSION_AND_SHARED_EXECUTION_COST_CONTRACT",
    }

    output_zip_hint = latest_dir / "99_UPLOAD_PACKAGE.zip"
    (run_dir / "00_READ_ME_FIRST.txt").write_text(
        make_readme(status, args.expected_symbol, output_zip_hint), encoding="utf-8"
    )
    write_json(run_dir / "01_bcr08_summary.json", summary)
    write_json(run_dir / "02_terminal_info.json", terminal_payload)
    write_json(run_dir / "03_account_context_redacted.json", account_payload)
    write_candidates_csv(run_dir / "04_symbol_candidates.csv", candidates)
    write_json(run_dir / "05_target_symbol_info.json", target_payload)
    write_json(run_dir / "06_target_tick_snapshot.json", tick_payload)
    write_json(run_dir / "07_csv_spread_observation.json", csv_observation)
    write_json(run_dir / "08_cost_field_interpretation.json", cost_payload)
    write_json(run_dir / "09_runtime_integrity.json", runtime_integrity)
    write_json(run_dir / "11_error.json", error)

    package_path = finalize_package(run_dir, latest_dir)
    print(json.dumps({"status": status, "package": str(package_path)}, ensure_ascii=False))
    return 0 if status.startswith("READY_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
