from __future__ import annotations

import bisect
import json
import math
import os
import shutil
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
M9P_PYTHON = THIS.parents[2] / "m9p" / "python"
if str(M9P_PYTHON) not in sys.path:
    sys.path.insert(0, str(M9P_PYTHON))

import run_gold_dynamic_core_reproduction_audit as m9p

STAGE = "M9U_MULTI_TIMEFRAME_PORTFOLIO_DETERMINISTIC_REPRODUCTION"
TIME_FORMAT = m9p.TIME_FORMAT
EXTRA_COSTS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
PRIORITY = {"M5_S1": 1, "M15_S2": 2, "H1_S3": 3, "H4_S4": 4}

EXPECTED_REFERENCE = {
    "M5_S1": {"count": 1256, "pf": 1.3336981886264172},
    "M15_S2": {"count": 1495, "pf": 1.365884145048126},
    "H1_S3": {"count": 191, "pf": 1.7802349633701025},
    "H4_S4": {"count": 70, "pf": 3.295562620459433},
    "PORTFOLIO": {
        "count": 2241,
        "win_rate": 0.6323070058009818,
        "pf": 1.44465145217794,
        "max_drawdown_bps": 535.4125258246631,
        "max_losing_streak": 8,
    },
}


def window_quantile(values: list[float | None], index: int, window: int, q: float) -> float | None:
    start = index - window + 1
    if start < 0:
        return None
    selected = values[start:index + 1]
    if len(selected) != window or any(value is None or not math.isfinite(float(value)) for value in selected):
        return None
    ordered = sorted(float(value) for value in selected if value is not None)
    return m9p.quantile_sorted(ordered, q)


def selected_closed_index(close_times: list[datetime], decision: datetime) -> int:
    return bisect.bisect_right(close_times, decision) - 1


def macd_bps(bars: list[m9p.Bar]) -> list[float]:
    closes = [bar.close for bar in bars]
    fast = m9p.ema(closes, 6)
    slow = m9p.ema(closes, 13)
    return [(a - b) / abs(close) * 10000.0 for a, b, close in zip(fast, slow, closes)]


def build_timeframe_turns(
    bars: list[m9p.Bar],
    m1: list[m9p.Bar],
    point: float,
    prefix: str,
) -> list[dict[str, Any]]:
    pairs, _ = m9p.replay_m7c(bars)
    rows = m9p.build_first_turns(pairs, m1, point)
    output: list[dict[str, Any]] = []
    for number, row in enumerate(rows, start=1):
        cloned = dict(row)
        cloned["trade_id"] = f"{prefix}_T{number:06d}"
        output.append(cloned)
    return output


def enrich_indices(
    rows: list[dict[str, Any]],
    close_times: dict[str, list[datetime]],
    timeframes: tuple[str, ...],
) -> None:
    for row in rows:
        decision = m9p.parse_time(str(row["turn_entry_time"]))
        for timeframe in timeframes:
            row[f"{timeframe.lower()}_index"] = selected_closed_index(close_times[timeframe], decision)


def select_s1(
    long_m5: list[dict[str, Any]],
    ratio20_m5: list[float | None],
    macd: dict[str, list[float]],
    rci9_h1: list[float | None],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_m5:
        i5 = int(row["m5_index"])
        i15 = int(row["m15_index"])
        ih1 = int(row["h1_index"])

        q_m5_volume = window_quantile(ratio20_m5, i5, 200, 0.50)
        q_m5_macd = window_quantile(macd["M5"], i5, 200, 0.75)
        own_core = (
            q_m5_volume is not None
            and ratio20_m5[i5] is not None
            and float(ratio20_m5[i5]) <= q_m5_volume
        ) or (
            q_m5_macd is not None
            and float(macd["M5"][i5]) >= q_m5_macd
        )

        q_m15 = window_quantile(macd["M15"], i15, 100, 0.75)
        q_h1_macd = window_quantile(macd["H1"], ih1, 100, 0.50)
        q_h1_rci = window_quantile(rci9_h1, ih1, 100, 0.50)
        if (
            own_core
            and q_m15 is not None
            and q_h1_macd is not None
            and q_h1_rci is not None
            and float(macd["M15"][i15]) >= q_m15
            and float(macd["H1"][ih1]) >= q_h1_macd
            and rci9_h1[ih1] is not None
            and float(rci9_h1[ih1]) >= q_h1_rci
        ):
            selected.append({**row, "branch": "M5_S1"})
    return selected


def select_s2(
    long_m15: list[dict[str, Any]],
    ratio20_m5: list[float | None],
    macd_m15: list[float],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_m15:
        i5 = int(row["m5_index"])
        i15 = int(row["m15_index"])
        q1 = window_quantile(ratio20_m5, i5, 200, 0.50)
        q2 = window_quantile(macd_m15, i15, 200, 0.75)
        n1 = q1 is not None and ratio20_m5[i5] is not None and float(ratio20_m5[i5]) <= q1
        n2 = q2 is not None and float(macd_m15[i15]) >= q2
        if n1 or n2:
            selected.append({**row, "branch": "M15_S2", "N1": n1, "N2": n2, "N3": True})
    return selected


def select_s3(
    long_h1: list[dict[str, Any]],
    macd_h4: list[float],
    macd_d1: list[float],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_h1:
        ih4 = int(row["h4_index"])
        id1 = int(row["d1_index"])
        q_h4 = window_quantile(macd_h4, ih4, 100, 0.75)
        q_d1 = window_quantile(macd_d1, id1, 100, 0.50)
        if (
            q_h4 is not None
            and q_d1 is not None
            and float(macd_h4[ih4]) >= q_h4
            and float(macd_d1[id1]) >= q_d1
        ):
            selected.append({**row, "branch": "H1_S3"})
    return selected


def select_s4(
    long_h4: list[dict[str, Any]],
    rci9_d1: list[float | None],
    ema20_d1: list[float],
    ema30_d1: list[float],
    ema40_d1: list[float],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in long_h4:
        id1 = int(row["d1_index"])
        q_d1 = window_quantile(rci9_d1, id1, 100, 0.50)
        if (
            q_d1 is not None
            and rci9_d1[id1] is not None
            and float(rci9_d1[id1]) >= q_d1
            and ema20_d1[id1] > ema30_d1[id1] > ema40_d1[id1]
        ):
            selected.append({**row, "branch": "H4_S4"})
    return selected


def grouped(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        current = m9p.parse_time(str(row["turn_entry_time"]))
        if mode == "year":
            label = str(current.year)
        elif mode == "quarter":
            label = f"{current.year}Q{(current.month - 1) // 3 + 1}"
        else:
            label = f"{current.year}-{current.month:02d}"
        groups.setdefault(label, []).append(row)
    return [{mode: label, **m9p.metrics(group)} for label, group in sorted(groups.items())]


def build_one_position_portfolio(
    branch_rows: dict[str, list[dict[str, Any]]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    for branch, rows in branch_rows.items():
        for row in rows:
            events.append({**row, "branch": branch})
    events.sort(
        key=lambda row: (
            m9p.parse_time(str(row["turn_entry_time"])),
            -PRIORITY[str(row["branch"])],
        )
    )

    accepted: list[dict[str, Any]] = []
    confirmations: list[dict[str, Any]] = []
    active_until: datetime | None = None
    active_trade_id: str | None = None

    for row in events:
        entry = m9p.parse_time(str(row["turn_entry_time"]))
        exit_time = m9p.parse_time(str(row["exit_time"]))
        if active_until is None or entry >= active_until:
            accepted_row = dict(row)
            accepted_row["portfolio_trade_id"] = f"M9U_P{len(accepted) + 1:06d}"
            accepted.append(accepted_row)
            active_until = exit_time
            active_trade_id = str(accepted_row["portfolio_trade_id"])
        else:
            confirmations.append({
                "active_portfolio_trade_id": active_trade_id,
                "confirmation_branch": row["branch"],
                "confirmation_turn_entry_time": row["turn_entry_time"],
                "confirmation_source_trade_id": row["trade_id"],
                "active_until": active_until.strftime(TIME_FORMAT),
            })
    return accepted, confirmations


def assert_close(name: str, actual: float, expected: float, tolerance: float = 1e-9) -> None:
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance):
        raise RuntimeError(f"{name} mismatch actual={actual} expected={expected}")


def main() -> int:
    local_root = Path(os.environ.get("LOCALAPPDATA", "")) / "xauusd_signal_lab" / "mochipoyo_alert_research"
    metadata_path = local_root / "outputs" / "M8B" / "LATEST" / "06_symbol_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}

    data_override = os.environ.get("M9U_GOLD_DATA_ROOT")
    data_root = Path(data_override) if data_override else Path(metadata.get("mt5_files_root", "")) / "gold_v3_2023_2026"
    point_raw = os.environ.get("M9U_POINT")
    point = float(point_raw) if point_raw is not None else float(metadata.get("symbols", {}).get("XAUUSD", {}).get("point", "nan"))

    if not data_root.is_dir() or not math.isfinite(point):
        print(f"[M9U BLOCKED] GOLD data root or XAUUSD point unavailable: {data_root} point={point}")
        return 2

    try:
        paths: dict[str, Path] = {}
        for timeframe, (filename, expected_hash) in m9p.EXPECTED.items():
            path = data_root / filename
            if not path.is_file():
                raise RuntimeError(f"required GOLD file missing: {path}")
            actual_hash = m9p.sha256(path)
            if actual_hash != expected_hash:
                raise RuntimeError(f"SHA256 mismatch for {filename}: {actual_hash}")
            paths[timeframe] = path

        bars = {timeframe: m9p.load_bars(path) for timeframe, path in paths.items()}
        close_times = {
            "M5": [bar.time + timedelta(minutes=5) for bar in bars["M5"]],
            "M15": [bar.time + timedelta(minutes=15) for bar in bars["M15"]],
            "H1": [bar.time + timedelta(hours=1) for bar in bars["H1"]],
            "H4": [bar.time + timedelta(hours=4) for bar in bars["H4"]],
            "D1": [bar.time + timedelta(days=1) for bar in bars["D1"]],
        }

        turns = {
            "M5": build_timeframe_turns(bars["M5"], bars["M1"], point, "M9U_M5"),
            "M15": build_timeframe_turns(bars["M15"], bars["M1"], point, "M9U_M15"),
            "H1": build_timeframe_turns(bars["H1"], bars["M1"], point, "M9U_H1"),
            "H4": build_timeframe_turns(bars["H4"], bars["M1"], point, "M9U_H4"),
        }
        longs = {timeframe: [row for row in rows if row["direction"] == "LONG"] for timeframe, rows in turns.items()}

        enrich_indices(longs["M5"], close_times, ("M5", "M15", "H1"))
        enrich_indices(longs["M15"], close_times, ("M5", "M15"))
        enrich_indices(longs["H1"], close_times, ("H4", "D1"))
        enrich_indices(longs["H4"], close_times, ("D1",))

        ratio20_m5 = m9p.m5_ratio20(bars["M5"])
        macd = {timeframe: macd_bps(bars[timeframe]) for timeframe in ("M5", "M15", "H1", "H4", "D1")}
        rci9_h1 = m9p.rci_series([bar.close for bar in bars["H1"]], 9)
        rci9_d1 = m9p.rci_series([bar.close for bar in bars["D1"]], 9)
        d1_closes = [bar.close for bar in bars["D1"]]
        ema20_d1 = m9p.ema(d1_closes, 20)
        ema30_d1 = m9p.ema(d1_closes, 30)
        ema40_d1 = m9p.ema(d1_closes, 40)

        branches = {
            "M5_S1": select_s1(longs["M5"], ratio20_m5, macd, rci9_h1),
            "M15_S2": select_s2(longs["M15"], ratio20_m5, macd["M15"]),
            "H1_S3": select_s3(longs["H1"], macd["H4"], macd["D1"]),
            "H4_S4": select_s4(longs["H4"], rci9_d1, ema20_d1, ema30_d1, ema40_d1),
        }

        portfolio, confirmations = build_one_position_portfolio(branches)
        branch_metrics = {name: m9p.metrics(rows) for name, rows in branches.items()}
        portfolio_metrics = m9p.metrics(portfolio)

        for branch in ("M5_S1", "M15_S2", "H1_S3", "H4_S4"):
            expected = EXPECTED_REFERENCE[branch]
            if branch_metrics[branch]["count"] != expected["count"]:
                raise RuntimeError(f"{branch} count mismatch")
            assert_close(f"{branch} PF", float(branch_metrics[branch]["profit_factor_bps"]), float(expected["pf"]))

        pexp = EXPECTED_REFERENCE["PORTFOLIO"]
        if portfolio_metrics["count"] != pexp["count"]:
            raise RuntimeError("portfolio count mismatch")
        assert_close("portfolio WR", float(portfolio_metrics["win_rate"]), float(pexp["win_rate"]))
        assert_close("portfolio PF", float(portfolio_metrics["profit_factor_bps"]), float(pexp["pf"]))
        assert_close("portfolio DD", float(portfolio_metrics["max_drawdown_bps"]), float(pexp["max_drawdown_bps"]))
        if portfolio_metrics["max_losing_streak"] != pexp["max_losing_streak"]:
            raise RuntimeError("portfolio losing streak mismatch")

        accepted_by_branch = {branch: sum(str(row["branch"]) == branch for row in portfolio) for branch in PRIORITY}
        cost_rows = [{"extra_cost_bps_per_trade": cost, **m9p.metrics(portfolio, cost)} for cost in EXTRA_COSTS]

    except Exception as exc:
        print(f"[M9U BLOCKED] {exc}")
        return 2

    summary = {
        "project": "MOCHIPOYO_ALERT_RESEARCH",
        "stage": STAGE,
        "status": "PASS_HISTORICAL_DETERMINISTIC_REPRODUCTION_ONLY",
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch_metrics": branch_metrics,
        "portfolio": portfolio_metrics,
        "accepted_by_branch": accepted_by_branch,
        "confirmation_metadata_rows": len(confirmations),
        "portfolio_yearly": grouped(portfolio, "year"),
        "portfolio_quarterly": grouped(portfolio, "quarter"),
        "guardrails": {
            "historical_spread_used": True,
            "commission": "NOT_MODELED",
            "swap": "NOT_MODELED",
            "future_feature_use": False,
            "generic_agreement_score_used": False,
            "pyramiding_used": False,
            "m7c_formula_changed": False,
            "m8c_reset": False,
            "automatic_live_promotion": False,
            "audit_only": True,
        },
    }

    output_override = os.environ.get("M9U_OUTPUT_ROOT")
    out_root = Path(output_override) if output_override else local_root / "outputs" / "M9U"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive = out_root / "archive" / stamp
    archive.mkdir(parents=True, exist_ok=False)

    (archive / "00_READ_ME_FIRST.txt").write_text(
        "M9U deterministically reproduces the M9T canonical GOLD M5/M15/H1/H4 LONG branches and the causal one-position dedup portfolio. "
        "All history is research-exposed; this is not independent validation. Overlapping timeframe signals do not pyramid and generic agreement count is not used as a positive confidence score. "
        "Historical spread is used; commission/swap are not modeled.\n",
        encoding="utf-8",
    )
    m9p.dump_json(archive / "01_summary.json", summary)
    m9p.write_csv(archive / "02_branch_summary.csv", [{"branch": branch, **metrics} for branch, metrics in branch_metrics.items()])
    m9p.write_csv(archive / "03_portfolio_yearly.csv", grouped(portfolio, "year"))
    m9p.write_csv(archive / "04_portfolio_quarterly.csv", grouped(portfolio, "quarter"))
    m9p.write_csv(archive / "05_portfolio_monthly.csv", grouped(portfolio, "month"))
    m9p.write_csv(archive / "06_portfolio_trade_ledger.csv", portfolio)
    m9p.write_csv(archive / "07_confirmation_metadata.csv", confirmations)
    m9p.write_csv(archive / "08_cost_sensitivity.csv", cost_rows)
    m9p.dump_json(
        archive / "09_data_quality.json",
        {
            "data_root": str(data_root),
            "point": point,
            "hashes": {timeframe: {"file": m9p.EXPECTED[timeframe][0], "sha256": m9p.EXPECTED[timeframe][1]} for timeframe in m9p.EXPECTED},
            "closed_bars_only": True,
            "nearest_m1_fallback": False,
        },
    )
    (archive / "10_audit.log").write_text(
        "\n".join([
            "status=PASS_HISTORICAL_DETERMINISTIC_REPRODUCTION_ONLY",
            *(f"{branch}={branch_metrics[branch]['count']}" for branch in ("M5_S1", "M15_S2", "H1_S3", "H4_S4")),
            f"portfolio={portfolio_metrics['count']}",
            f"portfolio_pf={portfolio_metrics['profit_factor_bps']}",
            f"confirmations={len(confirmations)}",
            "generic_agreement_score_used=false",
            "pyramiding_used=false",
            "m7c_formula_changed=false",
            "m8c_reset=false",
            "automatic_live_promotion=false",
            "",
        ]),
        encoding="utf-8",
    )

    names = [
        "00_READ_ME_FIRST.txt",
        "01_summary.json",
        "02_branch_summary.csv",
        "03_portfolio_yearly.csv",
        "04_portfolio_quarterly.csv",
        "05_portfolio_monthly.csv",
        "06_portfolio_trade_ledger.csv",
        "07_confirmation_metadata.csv",
        "08_cost_sensitivity.csv",
        "09_data_quality.json",
        "10_audit.log",
    ]
    with zipfile.ZipFile(archive / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(archive / name, name)

    latest = out_root / "LATEST"
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(archive, latest)

    print(
        f"[M9U PASS] S1={len(branches['M5_S1'])} S2={len(branches['M15_S2'])} "
        f"S3={len(branches['H1_S3'])} S4={len(branches['H4_S4'])} "
        f"PORTFOLIO={len(portfolio)} PF={portfolio_metrics['profit_factor_bps']:.12f}"
    )
    print("[M9U OUTPUT]", latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
