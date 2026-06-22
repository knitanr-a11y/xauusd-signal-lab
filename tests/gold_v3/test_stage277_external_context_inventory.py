from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import sys


MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "gold_v3"
    / "stage277_audit_external_context_inventory.py"
)
SPEC = importlib.util.spec_from_file_location("stage277_audit", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
stage277 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stage277
SPEC.loader.exec_module(stage277)

PREFIX = "gold_v3_stage277_external_context_inventory"


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_fixture(root: Path, *, server: str = "XMTrading-MT5 3", unsafe: bool = False) -> None:
    symbol_fields = [
        "captured_at_server",
        "broker_company",
        "account_server",
        "terminal_build",
        "symbol",
        "source_group_candidate",
        "match_basis",
        "explicit_symbol_requested",
        "selected_before",
        "selected_after",
        "path",
        "description",
        "currency_base",
        "currency_profit",
        "currency_margin",
        "digits",
        "point",
        "trade_tick_size",
        "trade_tick_value",
        "trade_contract_size",
        "trade_calc_mode",
        "trade_mode",
        "current_spread_points",
        "spread_float",
        "spread_price_formula",
        "selection_contract",
        "audit_only",
    ]
    symbols = [
        {
            "captured_at_server": "2026.06.22 12:00:00",
            "broker_company": "XM Global Limited",
            "account_server": server,
            "terminal_build": "5000",
            "symbol": "GOLD#",
            "source_group_candidate": "GOLD_BASELINE",
            "match_basis": "exact_baseline_symbol",
            "explicit_symbol_requested": "false",
            "selected_before": "true",
            "selected_after": "true",
            "path": "Metals",
            "description": "Gold",
            "currency_base": "XAU",
            "currency_profit": "USD",
            "currency_margin": "USD",
            "digits": "2",
            "point": "0.01",
            "trade_tick_size": "0.01",
            "trade_tick_value": "1",
            "trade_contract_size": "100",
            "trade_calc_mode": "SYMBOL_CALC_MODE_CFD",
            "trade_mode": "SYMBOL_TRADE_MODE_FULL",
            "current_spread_points": "30",
            "spread_float": "true",
            "spread_price_formula": "spread_price=spread_points*point",
            "selection_contract": "candidate only",
            "audit_only": "true",
        },
        {
            "captured_at_server": "2026.06.22 12:00:00",
            "broker_company": "XM Global Limited",
            "account_server": server,
            "terminal_build": "5000",
            "symbol": "SILVER#",
            "source_group_candidate": "XAGUSD",
            "match_basis": "name_or_description_token:XAGUSD|SILVER",
            "explicit_symbol_requested": "false",
            "selected_before": "false",
            "selected_after": "true",
            "path": "Metals",
            "description": "Silver",
            "currency_base": "XAG",
            "currency_profit": "USD",
            "currency_margin": "USD",
            "digits": "3",
            "point": "0.001",
            "trade_tick_size": "0.001",
            "trade_tick_value": "5",
            "trade_contract_size": "5000",
            "trade_calc_mode": "SYMBOL_CALC_MODE_CFD",
            "trade_mode": "SYMBOL_TRADE_MODE_FULL",
            "current_spread_points": "30",
            "spread_float": "true",
            "spread_price_formula": "spread_price=spread_points*point",
            "selection_contract": "candidate only",
            "audit_only": "true",
        },
        {
            "captured_at_server": "2026.06.22 12:00:00",
            "broker_company": "XM Global Limited",
            "account_server": server,
            "terminal_build": "5000",
            "symbol": "USDJPY#",
            "source_group_candidate": "USDJPY",
            "match_basis": "symbol_token:USDJPY",
            "explicit_symbol_requested": "false",
            "selected_before": "false",
            "selected_after": "true",
            "path": "Forex",
            "description": "US Dollar vs Japanese Yen",
            "currency_base": "USD",
            "currency_profit": "JPY",
            "currency_margin": "USD",
            "digits": "3",
            "point": "0.001",
            "trade_tick_size": "0.001",
            "trade_tick_value": "1",
            "trade_contract_size": "100000",
            "trade_calc_mode": "SYMBOL_CALC_MODE_FOREX",
            "trade_mode": "SYMBOL_TRADE_MODE_FULL",
            "current_spread_points": "15",
            "spread_float": "true",
            "spread_price_formula": "spread_price=spread_points*point",
            "selection_contract": "candidate only",
            "audit_only": "true",
        },
    ]
    write_csv(root / f"{PREFIX}_symbols.csv", symbol_fields, symbols)

    coverage_fields = [
        "captured_at_server",
        "broker_company",
        "account_server",
        "terminal_build",
        "symbol",
        "source_group",
        "match_basis",
        "timeframe",
        "timeframe_seconds",
        "requested_from_server_inclusive",
        "requested_to_server_exclusive",
        "effective_to_server_exclusive",
        "rows_total",
        "first_bar_open_time",
        "last_bar_open_time",
        "rows_2023",
        "first_2023",
        "last_2023",
        "rows_2024",
        "first_2024",
        "last_2024",
        "rows_2025",
        "first_2025",
        "last_2025",
        "rows_2026",
        "first_2026",
        "last_2026",
        "duplicate_count",
        "non_monotonic_count",
        "raw_gap_intervals_gt_one_period",
        "max_raw_gap_seconds",
        "copy_errors",
        "empty_chunks",
        "chunks",
        "status",
        "csv_time_semantics",
        "closed_bar_rule",
        "source_close_availability_rule",
        "gap_fill_applied",
        "nearest_future_applied",
        "fallback_source_applied",
        "audit_only",
    ]
    seconds = stage277.TIMEFRAME_SECONDS
    coverage: list[dict[str, object]] = []
    for symbol, group in (("GOLD#", "GOLD_BASELINE"), ("SILVER#", "XAGUSD"), ("USDJPY#", "USDJPY")):
        for tf in stage277.TIMEFRAMES:
            has_rows = not (symbol == "USDJPY#" and tf in {"M1", "D1"})
            rows_total = 100 if has_rows else 0
            coverage.append(
                {
                    "captured_at_server": "2026.06.22 12:00:00",
                    "broker_company": "XM Global Limited",
                    "account_server": server,
                    "terminal_build": "5000",
                    "symbol": symbol,
                    "source_group": group,
                    "match_basis": "fixture",
                    "timeframe": tf,
                    "timeframe_seconds": seconds[tf],
                    "requested_from_server_inclusive": "2023.01.01 00:00:00",
                    "requested_to_server_exclusive": "2027.01.01 00:00:00",
                    "effective_to_server_exclusive": "2026.06.22 12:00:01",
                    "rows_total": rows_total,
                    "first_bar_open_time": "2023.01.02 00:00:00" if has_rows else "",
                    "last_bar_open_time": "2026.06.20 00:00:00" if has_rows else "",
                    "rows_2023": 25 if has_rows else 0,
                    "first_2023": "2023.01.02 00:00:00" if has_rows else "",
                    "last_2023": "2023.12.29 20:00:00" if has_rows else "",
                    "rows_2024": 25 if has_rows else 0,
                    "first_2024": "2024.01.02 00:00:00" if has_rows else "",
                    "last_2024": "2024.12.31 20:00:00" if has_rows else "",
                    "rows_2025": 25 if has_rows else 0,
                    "first_2025": "2025.01.02 00:00:00" if has_rows else "",
                    "last_2025": "2025.12.31 20:00:00" if has_rows else "",
                    "rows_2026": 25 if has_rows else 0,
                    "first_2026": "2026.01.02 00:00:00" if has_rows else "",
                    "last_2026": "2026.06.20 00:00:00" if has_rows else "",
                    "duplicate_count": 0,
                    "non_monotonic_count": 0,
                    "raw_gap_intervals_gt_one_period": 10,
                    "max_raw_gap_seconds": 172800,
                    "copy_errors": 0,
                    "empty_chunks": 0,
                    "chunks": 43,
                    "status": "AVAILABLE" if has_rows else "NO_RATES_RETURNED",
                    "csv_time_semantics": "broker_server_bar_open_time",
                    "closed_bar_rule": "bar_open_time+timeframe_seconds<=captured_at_server",
                    "source_close_availability_rule": "source_close_time<=decision_time",
                    "gap_fill_applied": "false",
                    "nearest_future_applied": "false",
                    "fallback_source_applied": "false",
                    "audit_only": "true",
                }
            )
    write_csv(root / f"{PREFIX}_timeframe_coverage.csv", coverage_fields, coverage)

    session_fields = [
        "captured_at_server",
        "broker_company",
        "account_server",
        "symbol",
        "source_group_candidate",
        "weekday",
        "session_index",
        "from_hhmm",
        "to_hhmm",
        "source_name",
        "holiday_exceptions_included",
        "audit_only",
    ]
    sessions = [
        {
            "captured_at_server": "2026.06.22 12:00:00",
            "broker_company": "XM Global Limited",
            "account_server": server,
            "symbol": symbol,
            "source_group_candidate": group,
            "weekday": "MONDAY",
            "session_index": 0,
            "from_hhmm": "00:05",
            "to_hhmm": "23:55",
            "source_name": "MT5_SymbolInfoSessionTrade",
            "holiday_exceptions_included": "false",
            "audit_only": "true",
        }
        for symbol, group in (("GOLD#", "GOLD_BASELINE"), ("SILVER#", "XAGUSD"), ("USDJPY#", "USDJPY"))
    ]
    write_csv(root / f"{PREFIX}_sessions.csv", session_fields, sessions)

    run_fields = [
        "captured_at_server",
        "broker_company",
        "account_server",
        "terminal_build",
        "baseline_symbol",
        "requested_from_server_inclusive",
        "requested_to_server_exclusive",
        "effective_to_server_exclusive",
        "symbols_total_server",
        "symbols_inventory_rows",
        "symbols_probed",
        "timeframes_requested",
        "csv_time_semantics",
        "closed_only",
        "gap_fill_applied",
        "nearest_future_applied",
        "fallback_source_applied",
        "performance_grid_run",
        "candidate_created",
        "router_changed",
        "live_ready",
        "final_signal",
        "mt5_order",
        "discord_notify",
        "partial_close",
        "audit_only",
    ]
    run = {
        "captured_at_server": "2026.06.22 12:00:00",
        "broker_company": "XM Global Limited",
        "account_server": server,
        "terminal_build": "5000",
        "baseline_symbol": "GOLD#",
        "requested_from_server_inclusive": "2023.01.01 00:00:00",
        "requested_to_server_exclusive": "2027.01.01 00:00:00",
        "effective_to_server_exclusive": "2026.06.22 12:00:01",
        "symbols_total_server": 100,
        "symbols_inventory_rows": 3,
        "symbols_probed": 3,
        "timeframes_requested": 6,
        "csv_time_semantics": "broker_server_bar_open_time",
        "closed_only": "true",
        "gap_fill_applied": "false",
        "nearest_future_applied": "false",
        "fallback_source_applied": "true" if unsafe else "false",
        "performance_grid_run": "false",
        "candidate_created": "false",
        "router_changed": "false",
        "live_ready": "false",
        "final_signal": "false",
        "mt5_order": "false",
        "discord_notify": "false",
        "partial_close": "false",
        "audit_only": "true",
    }
    write_csv(root / f"{PREFIX}_run_metadata.csv", run_fields, [run])


def test_partial_inventory_outputs_and_contracts(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    build_fixture(input_dir)

    summary = stage277.run_audit(
        stage277.AuditConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            prefix=PREFIX,
            expected_server="XMTrading-MT5 3",
            expected_company="XM Global Limited",
            expected_baseline_symbol="GOLD#",
        )
    )

    assert summary["classification"] == "PARTIAL"
    assert summary["status"] == stage277.STATUS_PARTIAL
    assert summary["performance_grid_run"] is False
    assert summary["specialist_health_router_v3_changed"] is False
    assert summary["live_ready"] is False
    assert summary["phase2_hv_retest_state"] == "SHADOW_ONLY_UNCHANGED"

    source_rows = list(csv.DictReader((output_dir / "stage277_source_inventory.csv").open(encoding="utf-8")))
    xag = [row for row in source_rows if row["source_group"] == "XAGUSD"]
    assert len(xag) == 1
    assert xag[0]["exact_symbol"] == "SILVER#"
    assert xag[0]["selection_status"] == "INVENTORY_CANDIDATE_ONLY_NOT_AUTO_SELECTED"

    econ = [row for row in source_rows if row["source_group"] == "ECONOMIC_CALENDAR"]
    assert econ[0]["availability_status"] == "BLOCKED_SEPARATE_NON_SYMBOL_SOURCE_NOT_AUDITED"

    contract_rows = list(csv.DictReader((output_dir / "stage277_causal_availability_contract.csv").open(encoding="utf-8")))
    assert {row["timeframe"] for row in contract_rows} == set(stage277.TIMEFRAMES)
    assert all(row["decision_join_rule"] == "source_close_time<=decision_time" for row in contract_rows)
    assert all(row["forming_bar_allowed"] == "False" for row in contract_rows)


def test_server_mismatch_is_blocked(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    build_fixture(input_dir, server="OTHER-SERVER")

    summary = stage277.run_audit(
        stage277.AuditConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            prefix=PREFIX,
            expected_server="XMTrading-MT5 3",
            expected_company=None,
            expected_baseline_symbol="GOLD#",
        )
    )

    assert summary["classification"] == "BLOCKED"
    assert summary["status"] == stage277.STATUS_BLOCKED
    assert any("expected exact account_server" in issue for issue in summary["validation_issues"])


def test_unsafe_fallback_flag_is_blocked(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    build_fixture(input_dir, unsafe=True)

    summary = stage277.run_audit(
        stage277.AuditConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            prefix=PREFIX,
            expected_server="XMTrading-MT5 3",
            expected_company=None,
            expected_baseline_symbol="GOLD#",
        )
    )

    assert summary["classification"] == "BLOCKED"
    assert any("fallback_source_applied" in issue for issue in summary["validation_issues"])


def test_mql5_inventory_is_read_only_and_closed_only() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "mt5"
        / "ExportGoldV3ExternalContextInventory.mq5"
    ).read_text(encoding="utf-8")

    banned_calls = (
        "OrderSend(",
        "PositionClose(",
        "PositionModify(",
        "CTrade ",
        "WebRequest(",
    )
    assert not any(call in source for call in banned_calls)
    assert "bar_time+(datetime)result.timeframe_seconds>captured_server_now" in source
    assert "source_close_time=bar_open_time+%d_seconds" in source
    assert "fallback_source_applied" in source
    assert "performance_grid_run" in source
    assert "candidate_created" in source
    assert "router_changed" in source
