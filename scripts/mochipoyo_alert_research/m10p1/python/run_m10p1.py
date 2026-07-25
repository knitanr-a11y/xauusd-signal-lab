from __future__ import annotations

import csv
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
ROOT = THIS.parents[4]
MR = THIS.parents[2]
for rel in ("m10a/python", "m10j/python"):
    path = MR / rel
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import frozen_core as c
import run_m10j as m10j

STAGE = "M10P1_C0212_DETERMINISTIC_REPRODUCTION"
CONTRACT = ROOT / "config" / "mochipoyo_alert_research" / "m10p1_c0212_deterministic_reproduction_contract_20260725.json"
POINT = c.POINT
H4_EMA20_30_BPS_GE = 37.61355979
H1_ATR_PCT100_GE = 0.8
HORIZON_MINUTES = 240
FIXED_SPREAD_USD = 0.20


class AuditError(RuntimeError):
    pass


def local_root() -> Path:
    base = os.environ.get("LOCALAPPDATA", "").strip() or os.environ.get("TEMP", "").strip()
    if not base:
        raise AuditError("LOCALAPPDATA/TEMP unavailable")
    return Path(base) / "xauusd_signal_lab" / "mochipoyo_alert_research"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_candidate_rows(bars: dict[str, list[c.Bar]]) -> list[dict[str, Any]]:
    rows = m10j.build_feature_rows(bars)
    selected = [
        row
        for row in rows
        if float(row["h4_ema20_30_bps"]) >= H4_EMA20_30_BPS_GE
        and float(row["h1_atr_pct100"]) >= H1_ATR_PCT100_GE
    ]
    selected.sort(key=lambda row: row["decision"])
    return selected


def build_trade_ledger(
    rows: list[dict[str, Any]],
    m1: list[c.Bar],
    allowed_years: set[int] | None,
    id_prefix: str,
) -> list[dict[str, Any]]:
    """Mirror original M10J selected_returns one-position semantics exactly.

    Each split is evaluated independently. Rows outside allowed_years do not
    consume the one-position block for that split.
    """
    by_time = {bar.time: bar for bar in m1}
    trades: list[dict[str, Any]] = []
    blocked_until: datetime | None = None
    for row in rows:
        if allowed_years is not None and int(row["year"]) not in allowed_years:
            continue
        decision = row["decision"]
        if blocked_until is not None and decision < blocked_until:
            continue
        entry = by_time.get(decision)
        exit_time = decision + timedelta(minutes=HORIZON_MINUTES)
        exit_bar = by_time.get(exit_time)
        if entry is None or exit_bar is None:
            continue
        entry_bid = float(entry.open)
        actual_exit_ask = float(exit_bar.open) + float(exit_bar.spread) * POINT
        fixed_exit_ask = float(exit_bar.open) + FIXED_SPREAD_USD
        trades.append(
            {
                "trade_id": f"{id_prefix}_T{len(trades) + 1:06d}",
                "entry_time": decision.strftime(c.TIME_FORMAT),
                "exit_time": exit_time.strftime(c.TIME_FORMAT),
                "year": int(row["year"]),
                "entry_bid": entry_bid,
                "exit_open": float(exit_bar.open),
                "exit_spread_points": int(exit_bar.spread),
                "actual_exit_ask": actual_exit_ask,
                "fixed0p20_exit_ask": fixed_exit_ask,
                "return_bps": c.directional_return("SHORT", entry_bid, actual_exit_ask),
                "fixed0p20_return_bps": c.directional_return("SHORT", entry_bid, fixed_exit_ask),
                "h4_ema20_30_bps": float(row["h4_ema20_30_bps"]),
                "h1_atr_pct100": float(row["h1_atr_pct100"]),
            }
        )
        blocked_until = exit_time
    return trades


def split_ledgers(rows: list[dict[str, Any]], m1: list[c.Bar]) -> dict[str, list[dict[str, Any]]]:
    specs: dict[str, set[int] | None] = {
        "train": {2023, 2024},
        "val2025": {2025},
        "test2026": {2026},
        "all": {2023, 2024, 2025, 2026},
    }
    return {
        name: build_trade_ledger(rows, m1, years, f"M10P1_{name.upper()}")
        for name, years in specs.items()
    }


def split_metrics(ledgers: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, trades in ledgers.items():
        actual = c.metrics_from_values([float(row["return_bps"]) for row in trades])
        fixed = c.metrics_from_values([float(row["fixed0p20_return_bps"]) for row in trades])
        output[name] = {"actual": actual, "fixed0p20": fixed}
    return output


def check_close(label: str, actual: Any, expected: Any, tolerance: float) -> dict[str, Any]:
    if actual is None or expected is None:
        passed = actual == expected
        diff = None
    else:
        diff = abs(float(actual) - float(expected))
        passed = math.isfinite(float(actual)) and diff <= tolerance
    return {"field": label, "expected": expected, "actual": actual, "abs_diff": diff, "pass": passed}


def assert_reference(metrics: dict[str, dict[str, Any]], reference: dict[str, Any], tolerance: float) -> list[dict[str, Any]]:
    mapping = {
        "train": reference["train_2023_2024"],
        "val2025": reference["validation_2025"],
        "test2026": reference["test_2026"],
        "all": reference["all"],
    }
    checks: list[dict[str, Any]] = []
    for split, expected in mapping.items():
        actual = metrics[split]["actual"]
        checks.append(
            {
                "split": split,
                "field": "count",
                "expected": int(expected["count"]),
                "actual": int(actual["count"]),
                "abs_diff": abs(int(actual["count"]) - int(expected["count"])),
                "pass": int(actual["count"]) == int(expected["count"]),
            }
        )
        pf_check = check_close("pf", actual["profit_factor_bps"], expected["pf"], tolerance)
        pf_check["split"] = split
        checks.append(pf_check)

    all_actual = metrics["all"]["actual"]
    all_fixed = metrics["all"]["fixed0p20"]
    for field, actual, expected in (
        ("all_max_dd_bps", all_actual["max_drawdown_bps"], reference["all"]["max_dd_bps"]),
        ("all_payoff_ratio", all_actual["payoff_ratio"], reference["all"]["payoff_ratio"]),
        ("all_fixed0p20_pf", all_fixed["profit_factor_bps"], reference["all"]["fixed0p20_pf"]),
    ):
        row = check_close(field, actual, expected, tolerance)
        row["split"] = "all"
        checks.append(row)

    failed = [row for row in checks if not bool(row["pass"])]
    if failed:
        raise AuditError(f"C0212 deterministic reproduction mismatch: {failed}")
    return checks


def main() -> int:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        if contract.get("stage") != STAGE or contract.get("status") != "DESIGN_FROZEN_HISTORICAL_AUDIT_ONLY":
            raise AuditError("unexpected M10P1 contract")
        candidate = contract.get("candidate", {})
        formula = candidate.get("formula", {})
        if (
            float(formula.get("h4_ema20_30_bps_ge", math.nan)) != H4_EMA20_30_BPS_GE
            or float(formula.get("h1_atr_pct100_ge", math.nan)) != H1_ATR_PCT100_GE
            or int(candidate.get("horizon_minutes", -1)) != HORIZON_MINUTES
            or candidate.get("direction") != "SHORT"
            or candidate.get("one_position") is not True
        ):
            raise AuditError("C0212 frozen formula mismatch")

        local = local_root()
        data_root = m10j.resolve_data_root(local)
        paths: dict[str, Path] = {}
        hashes: dict[str, str] = {}
        for tf, (filename, expected_hash) in c.EXPECTED_FILES.items():
            path = data_root / filename
            if not path.is_file():
                raise AuditError(f"missing frozen GOLD file: {path}")
            actual_hash = c.sha256(path)
            if actual_hash != expected_hash:
                raise AuditError(f"SHA256 mismatch for {filename}: {actual_hash}")
            paths[tf] = path
            hashes[tf] = actual_hash

        bars = {tf: c.load_bars(path) for tf, path in paths.items()}
        candidate_rows = build_candidate_rows(bars)
        ledgers = split_ledgers(candidate_rows, bars["M1"])
        metrics = split_metrics(ledgers)
        tolerance = float(contract["reproduction_rules"]["metric_tolerance"])
        checks = assert_reference(metrics, contract["reference"], tolerance)
        all_trades = ledgers["all"]

        out_root = local / "outputs" / "M10P1"
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive = out_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)
        (archive / "00_READ_ME_FIRST.txt").write_text(
            "M10P1 deterministic reproduction of M10J_C0212 from frozen raw GOLD data. Historical audit-only. M10P continues independently and is not modified.\n",
            encoding="utf-8",
        )
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": STAGE,
            "status": "PASS_DETERMINISTIC_REPRODUCTION_AUDIT_ONLY",
            "run_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidate_id": "M10J_C0212",
            "candidate_row_count_before_one_position": len(candidate_rows),
            "trade_count_after_one_position": len(all_trades),
            "split_trade_counts": {name: len(rows) for name, rows in ledgers.items()},
            "metrics": metrics,
            "reference_checks": checks,
            "frozen_hashes": hashes,
            "guardrails": contract["safety"],
        }
        (archive / "01_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_csv(archive / "02_reproduced_trade_ledger.csv", all_trades)
        write_csv(archive / "03_reference_checks.csv", checks)
        (archive / "04_data_quality.json").write_text(
            json.dumps(
                {
                    "frozen_hashes": hashes,
                    "newest_row_contract": "CLOSED",
                    "time_basis": "MT5 server time",
                    "decision_timeframe": "M15",
                    "split_one_position_recomputed_independently": True,
                    "exact_m1_entry_and_exit_only": True,
                    "nearest_m1_fallback": False,
                    "actual_spread_at_short_exit": True,
                    "fixed_spread_sensitivity_usd": FIXED_SPREAD_USD,
                    "reads_m10j_or_m10m_result_csv_for_trade_generation": False,
                    "m10p_modified": False,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (archive / "05_audit.log").write_text(
            "\n".join(
                [
                    "status=PASS_DETERMINISTIC_REPRODUCTION_AUDIT_ONLY",
                    f"candidate_rows={len(candidate_rows)}",
                    f"all_trades={len(all_trades)}",
                    f"train_trades={len(ledgers['train'])}",
                    f"val2025_trades={len(ledgers['val2025'])}",
                    f"test2026_trades={len(ledgers['test2026'])}",
                    "all_reference_checks_pass=true",
                    "split_one_position_recomputed_independently=true",
                    "m10p_modified=false",
                    "discord_send=false",
                    "mt5_order=false",
                    "live_ready=false",
                    "final_signal=false",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        latest = out_root / "LATEST"
        if latest.exists():
            shutil.rmtree(latest)
        shutil.copytree(archive, latest)
        package = latest / "99_UPLOAD_PACKAGE.zip"
        names = [
            "00_READ_ME_FIRST.txt",
            "01_summary.json",
            "02_reproduced_trade_ledger.csv",
            "03_reference_checks.csv",
            "04_data_quality.json",
            "05_audit.log",
        ]
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name in names:
                zf.write(latest / name, arcname=name)

        max_diff = max((float(row["abs_diff"]) for row in checks if row.get("abs_diff") is not None), default=0.0)
        print("[M10P1 PASS] Deterministic C0212 reproduction completed")
        print(f"[RESULT] trades={len(all_trades)} all_pf={metrics['all']['actual']['profit_factor_bps']} max_abs_diff={max_diff}")
        print(f"[PACKAGE] {package}")
        return 0
    except Exception as exc:
        print(f"[M10P1 BLOCKED] {type(exc).__name__}: {exc}")
        print("[SAFE] M10P and all existing forward monitors/frozen starts were not modified.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
