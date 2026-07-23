from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_FILES = {"XAUUSD": "goldsharp_m1.csv", "BTCUSD": "btcusdsharp_m1.csv"}
EXPECTED_SKELETON_SHA256 = "f42ce896f00b717320662ff1b64991718bf3e1ce7dfe0d671c62f362731f7acc"
SPREAD_MULTIPLIERS = (1.0, 1.5, 2.0)
EXPECTED_EXTRA_ENTRY_COUNT = 18
TIME_FORMAT = "%Y.%m.%d %H:%M:%S"


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def dump_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def find_mt5_files_root(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if all((p / name).is_file() for name in EXPECTED_FILES.values()):
            return p
        raise RuntimeError(f"explicit MT5 Files root lacks required M1 CSVs: {p}")

    env = os.environ.get("MOCHIPOYO_MT5_FILES_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if all((p / name).is_file() for name in EXPECTED_FILES.values()):
            return p
        raise RuntimeError(f"MOCHIPOYO_MT5_FILES_ROOT lacks required M1 CSVs: {p}")

    appdata = os.environ.get("APPDATA", "").strip()
    if not appdata:
        raise RuntimeError("APPDATA is unavailable; cannot locate MetaTrader Files root")
    terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
    candidates: list[Path] = []
    if terminal_root.is_dir():
        for p in terminal_root.glob("*/MQL5/Files"):
            if all((p / name).is_file() for name in EXPECTED_FILES.values()):
                candidates.append(p.resolve())
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RuntimeError("no MT5 Files folder contains both goldsharp_m1.csv and btcusdsharp_m1.csv")
    raise RuntimeError("multiple MT5 Files roots matched; set MOCHIPOYO_MT5_FILES_ROOT explicitly: " + "; ".join(map(str, candidates)))


def load_m1(path: Path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    rows = load_csv(path)
    if not rows:
        raise RuntimeError(f"empty M1 CSV: {path}")
    expected = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    if list(rows[0].keys()) != expected:
        raise RuntimeError(f"unexpected M1 header: {path.name}")
    by_time: dict[str, dict[str, str]] = {}
    for row in rows:
        t = row["time"]
        if t in by_time:
            raise RuntimeError(f"duplicate M1 time {t} in {path.name}")
        for k in ("open", "high", "low", "close"):
            v = float(row[k])
            if not math.isfinite(v):
                raise RuntimeError(f"nonfinite {k} at {t} in {path.name}")
        s = int(row["spread"])
        if s < 0:
            raise RuntimeError(f"negative spread at {t} in {path.name}")
        by_time[t] = row
    return by_time, rows[-1]


def resolve_symbol_metadata(csv_latest: dict[str, dict[str, str]], metadata_json: str | None) -> dict[str, Any]:
    if metadata_json:
        payload = json.loads(Path(metadata_json).read_text(encoding="utf-8"))
        return payload

    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        raise RuntimeError("MetaTrader5 Python package is required to capture SYMBOL_POINT safely") from exc

    if not mt5.initialize():
        raise RuntimeError(f"MetaTrader5 initialize() failed: {mt5.last_error()}")
    try:
        all_symbols = list(mt5.symbols_get() or [])
        if not all_symbols:
            raise RuntimeError("MetaTrader5 symbols_get() returned no symbols")

        overrides = {
            "XAUUSD": os.environ.get("MOCHIPOYO_XAU_MT5_SYMBOL", "").strip(),
            "BTCUSD": os.environ.get("MOCHIPOYO_BTC_MT5_SYMBOL", "").strip(),
        }
        result: dict[str, Any] = {
            "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "symbols": {},
        }
        for ticker in ("XAUUSD", "BTCUSD"):
            latest_close = float(csv_latest[ticker]["close"])
            if overrides[ticker]:
                candidates = [s for s in all_symbols if s.name == overrides[ticker]]
                if len(candidates) != 1:
                    raise RuntimeError(f"configured {ticker} MT5 symbol not found: {overrides[ticker]}")
            else:
                if ticker == "XAUUSD":
                    candidates = [s for s in all_symbols if ("XAU" in s.name.upper() or "GOLD" in s.name.upper())]
                else:
                    candidates = [s for s in all_symbols if "BTC" in s.name.upper()]
                scored = []
                for s in candidates:
                    tick = mt5.symbol_info_tick(s.name)
                    if tick is None:
                        continue
                    px = float(tick.bid or tick.last or tick.ask or 0.0)
                    if px <= 0:
                        continue
                    rel = abs(px - latest_close) / max(abs(latest_close), 1e-12)
                    if rel <= 0.03:
                        scored.append((rel, s.name, s))
                scored.sort(key=lambda x: (x[0], x[1]))
                if not scored:
                    names = [s.name for s in candidates[:30]]
                    raise RuntimeError(f"cannot auto-resolve {ticker} MT5 symbol near CSV price; candidates={names}")
                best_rel = scored[0][0]
                near = [x for x in scored if x[0] <= max(0.001, best_rel * 1.25)]
                exact = [x for x in near if x[1].upper() == ticker]
                if len(exact) == 1:
                    candidates = [exact[0][2]]
                elif len(near) == 1:
                    candidates = [near[0][2]]
                else:
                    env_name = "MOCHIPOYO_XAU_MT5_SYMBOL" if ticker == "XAUUSD" else "MOCHIPOYO_BTC_MT5_SYMBOL"
                    raise RuntimeError(f"ambiguous {ticker} MT5 symbol. Set {env_name}; near-price={[x[1] for x in near]}")

            info = mt5.symbol_info(candidates[0].name)
            if info is None:
                raise RuntimeError(f"symbol_info failed: {candidates[0].name}")
            point = float(info.point)
            if point <= 0 or not math.isfinite(point):
                raise RuntimeError(f"invalid SYMBOL_POINT for {candidates[0].name}: {point}")
            chart_mode = int(info.chart_mode)
            if chart_mode != 0:
                raise RuntimeError(f"{candidates[0].name} chart_mode={chart_mode}; M8B V1 requires BID chart mode")
            result["symbols"][ticker] = {
                "mt5_symbol": candidates[0].name,
                "point": point,
                "digits": int(info.digits),
                "chart_mode": chart_mode,
                "trade_tick_size": float(info.trade_tick_size),
                "trade_contract_size": float(info.trade_contract_size),
                "volume_min": float(info.volume_min),
                "volume_step": float(info.volume_step),
                "latest_csv_time": csv_latest[ticker]["time"],
                "latest_csv_close": latest_close,
            }
        return result
    finally:
        mt5.shutdown()


def calc_trade(row: dict[str, str], entry_bar: dict[str, str], exit_bar: dict[str, str], point: float, mult: float) -> dict[str, Any]:
    direction = row["direction"]
    entry_bid = float(entry_bar["open"])
    exit_bid = float(exit_bar["open"])
    entry_spread_pts = int(entry_bar["spread"])
    exit_spread_pts = int(exit_bar["spread"])
    if direction == "LONG":
        entry_exec = entry_bid + entry_spread_pts * point * mult
        exit_exec = exit_bid
        gross_bps = (exit_bid - entry_bid) / entry_bid * 10000.0
        net_bps = (exit_exec - entry_exec) / entry_exec * 10000.0
    elif direction == "SHORT":
        entry_exec = entry_bid
        exit_exec = exit_bid + exit_spread_pts * point * mult
        gross_bps = (entry_bid - exit_bid) / entry_bid * 10000.0
        net_bps = (entry_exec - exit_exec) / entry_exec * 10000.0
    else:
        raise RuntimeError(f"unknown direction {direction}")
    e = datetime.strptime(row["entry_server_open"], TIME_FORMAT)
    x = datetime.strptime(row["exit_server_open"], TIME_FORMAT)
    hold_minutes = int((x - e).total_seconds() // 60)
    return {
        "entry_bid_open": entry_bid,
        "exit_bid_open": exit_bid,
        "entry_spread_points": entry_spread_pts,
        "exit_spread_points": exit_spread_pts,
        "spread_multiplier": mult,
        "entry_exec_price": entry_exec,
        "exit_exec_price": exit_exec,
        "gross_return_bps": gross_bps,
        "spread_adjusted_return_bps": net_bps,
        "outcome": "WIN" if net_bps > 0 else ("LOSS" if net_bps < 0 else "FLAT"),
        "holding_minutes": hold_minutes,
    }


def metrics(rows: list[dict[str, Any]], key: str = "spread_adjusted_return_bps") -> dict[str, Any]:
    vals = [float(r[key]) for r in rows]
    wins = [v for v in vals if v > 0]
    losses = [v for v in vals if v < 0]
    flat = len(vals) - len(wins) - len(losses)
    pf = None if not losses else sum(wins) / abs(sum(losses))
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    losing = 0
    max_losing = 0
    for r in sorted(rows, key=lambda x: x["exit_decision_time_utc"]):
        v = float(r[key])
        cum += v
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
        if v < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        elif v > 0:
            losing = 0
    if rows:
        first = min(datetime.fromisoformat(r["entry_decision_time_utc"].replace("Z", "+00:00")) for r in rows)
        last = max(datetime.fromisoformat(r["exit_decision_time_utc"].replace("Z", "+00:00")) for r in rows)
        days = max((last - first).total_seconds() / 86400.0, 1.0 / 96.0)
    else:
        days = 0.0
    return {
        "trade_count": len(vals),
        "wins": len(wins),
        "losses": len(losses),
        "flat": flat,
        "win_rate": (len(wins) / len(vals) if vals else None),
        "profit_factor_bps": pf,
        "net_return_bps_sum": sum(vals),
        "average_return_bps": (statistics.fmean(vals) if vals else None),
        "median_return_bps": (statistics.median(vals) if vals else None),
        "max_drawdown_bps": max_dd,
        "maximum_losing_streak": max_losing,
        "calendar_span_days": days,
        "trades_per_calendar_day": (len(vals) / days if days else None),
    }


def split_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, fn in {
        "by_ticker": lambda r: r["ticker"],
        "by_direction": lambda r: r["direction"],
        "by_ticker_direction": lambda r: f"{r['ticker']}|{r['direction']}",
        "by_entry_exit_origin": lambda r: f"{r['entry_origin']}|{r['exit_origin']}",
    }.items():
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            groups[fn(r)].append(r)
        out[label] = {k: metrics(v) for k, v in sorted(groups.items())}
    return out


def package(folder: Path) -> None:
    names = [
        "00_READ_ME_FIRST.txt", "01_summary.json", "02_status.json",
        "03_extra_entry_trades.csv", "04_extra_exit_actions.csv",
        "05_cost_sensitivity.csv", "06_symbol_metadata.json", "07_audit.log",
    ]
    with zipfile.ZipFile(folder / "99_UPLOAD_PACKAGE.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(folder / name, name)


def main() -> int:
    ap = argparse.ArgumentParser(description="M8B frozen extra-entry outcome audit")
    ap.add_argument("--trade-skeleton", required=True)
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--mt5-files-root")
    ap.add_argument("--symbol-metadata-json")
    ap.add_argument("--commit", default="")
    args = ap.parse_args()

    skeleton = Path(args.trade_skeleton).resolve()
    if not skeleton.is_file():
        print(f"[M8B BLOCKED] missing skeleton: {skeleton}")
        return 2
    if sha256(skeleton) != EXPECTED_SKELETON_SHA256:
        print("[M8B BLOCKED] frozen trade skeleton SHA256 mismatch")
        return 2

    all_trades = load_csv(skeleton)
    extra_trades = [r for r in all_trades if r["entry_origin"] == "EXTRA_CANDIDATE"]
    if len(extra_trades) != EXPECTED_EXTRA_ENTRY_COUNT:
        print(f"[M8B BLOCKED] expected {EXPECTED_EXTRA_ENTRY_COUNT} extra-entry trades, got {len(extra_trades)}")
        return 2

    try:
        files_root = find_mt5_files_root(args.mt5_files_root)
        m1_by_ticker: dict[str, dict[str, dict[str, str]]] = {}
        latest: dict[str, dict[str, str]] = {}
        for ticker, filename in EXPECTED_FILES.items():
            m1_by_ticker[ticker], latest[ticker] = load_m1(files_root / filename)
        meta = resolve_symbol_metadata(latest, args.symbol_metadata_json)

        errors: list[str] = []
        evaluated_by_mult: dict[float, list[dict[str, Any]]] = {m: [] for m in SPREAD_MULTIPLIERS}
        for r in extra_trades:
            ticker = r["ticker"]
            ebar = m1_by_ticker[ticker].get(r["entry_server_open"])
            xbar = m1_by_ticker[ticker].get(r["exit_server_open"])
            if ebar is None:
                errors.append(f"missing exact M1 entry row {ticker} {r['entry_server_open']}")
                continue
            if xbar is None:
                errors.append(f"missing exact M1 exit row {ticker} {r['exit_server_open']}")
                continue
            point = float(meta["symbols"][ticker]["point"])
            for mult in SPREAD_MULTIPLIERS:
                x = dict(r)
                x.update(calc_trade(r, ebar, xbar, point, mult))
                evaluated_by_mult[mult].append(x)

        if errors:
            raise RuntimeError("; ".join(errors))
        if any(len(v) != EXPECTED_EXTRA_ENTRY_COUNT for v in evaluated_by_mult.values()):
            raise RuntimeError("not all frozen extra-entry trades resolved")

        primary_rows = evaluated_by_mult[1.0]
        summary = {
            "project": "MOCHIPOYO_ALERT_RESEARCH",
            "stage": "M8B_EXTRA_SIGNAL_OUTCOME_AUDIT",
            "status": "PASS",
            "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "audit_only": True,
            "candidate_scope": {
                "finalized_extra_signals": 36,
                "extra_entry_trades_evaluated": 18,
                "extra_exit_actions_not_double_counted_as_trades": 18,
                "pending_grace_excluded": 2,
                "frozen_trade_skeleton_sha256": EXPECTED_SKELETON_SHA256,
            },
            "cost_contract": {
                "primary_spread_multiplier": 1.0,
                "sensitivity_spread_multipliers": [1.5, 2.0],
                "commission_mode": "NOT_MODELED_IN_M8B_V1",
                "swap_mode": "NOT_MODELED_IN_M8B_V1",
                "monetary_pnl": "DEFERRED_TO_M8D_SIZING_CONTRACT",
            },
            "primary_metrics_spread_x1_0": metrics(primary_rows),
            "primary_splits_spread_x1_0": split_metrics(primary_rows),
            "sensitivity": {str(m): metrics(evaluated_by_mult[m]) for m in SPREAD_MULTIPLIERS},
            "interpretation_guardrails": {
                "this_is_not_exact_mochipoyo_replication": True,
                "source_coverage_is_reference_not_final_objective": True,
                "same_sample_gate_reoptimization_claim_forbidden": True,
                "m8c_requires_new_forward_or_independent_validation_for_performance_claim": True,
            },
        }
        status = {
            "status": "PASS",
            "exact_m1_rows_required": True,
            "nearest_bar_fallback_used": False,
            "intrabar_high_low_close_used": False,
            "future_information_used_for_candidate_creation": False,
            "future_prices_used_only_for_post_freeze_outcome_evaluation": True,
            "discord_send": False,
            "mt5_order": False,
            "live_ready": False,
            "final_signal": False,
            "entry_gate_enabled": False,
            "m7c_formula_changed": False,
            "m7c_threshold_changed": False,
            "m7c_runtime_manifest_changed": False,
            "next_stage": "M8C_EXTRA_LOSS_REDUCTION_GATE_DESIGN_AND_FORWARD_SHADOW",
        }

        output_root = Path(args.output_root).resolve()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive = output_root / "archive" / stamp
        archive.mkdir(parents=True, exist_ok=False)

        dump_json(archive / "01_summary.json", summary)
        dump_json(archive / "02_status.json", status)
        fields = list(primary_rows[0].keys())
        write_csv(archive / "03_extra_entry_trades.csv", primary_rows, fields)

        exit_rows: list[dict[str, Any]] = []
        for r in all_trades:
            if r["exit_origin"] != "EXTRA_CANDIDATE":
                continue
            exit_rows.append({
                "ticker": r["ticker"],
                "direction": r["direction"],
                "parent_trade_id": r["trade_id"],
                "parent_entry_origin": r["entry_origin"],
                "exit_decision_time_utc": r["exit_decision_time_utc"],
                "exit_server_open": r["exit_server_open"],
                "exit_transition": r["exit_transition"],
                "classification": "EXTRA_EXIT_ACTION_NOT_STANDALONE_TRADE",
                "included_in_wr_pf": False,
            })
        write_csv(archive / "04_extra_exit_actions.csv", exit_rows, list(exit_rows[0].keys()))

        sens_rows = []
        for m in SPREAD_MULTIPLIERS:
            mm = metrics(evaluated_by_mult[m])
            sens_rows.append({"spread_multiplier": m, **mm})
        write_csv(archive / "05_cost_sensitivity.csv", sens_rows, list(sens_rows[0].keys()))
        meta["mt5_files_root"] = str(files_root)
        dump_json(archive / "06_symbol_metadata.json", meta)

        audit_lines = [
            "status=PASS",
            f"trade_skeleton_sha256={EXPECTED_SKELETON_SHA256}",
            f"extra_entry_trade_count={len(primary_rows)}",
            f"extra_exit_action_count={len(exit_rows)}",
            "exact_m1_only=true",
            "nearest_bar_fallback=false",
            "commission_mode=NOT_MODELED_IN_M8B_V1",
            "swap_mode=NOT_MODELED_IN_M8B_V1",
            f"primary_metrics={json.dumps(summary['primary_metrics_spread_x1_0'], sort_keys=True)}",
        ]
        (archive / "07_audit.log").write_text("\n".join(audit_lines) + "\n", encoding="utf-8")
        readme = (
            "MOCHIPOYO M8B Extra Signal Outcome Audit\n"
            "Stage: M8B_EXTRA_SIGNAL_OUTCOME_AUDIT\n"
            f"Run UTC: {summary['run_at_utc']}\n"
            f"Commit: {args.commit or 'not supplied'}\n\n"
            "Result: PASS\n"
            "Primary population: 18 frozen extra-entry trades.\n"
            "Extra EXIT actions are listed separately and are not double-counted as trades.\n"
            "Primary cost view uses historical M1 spread x1.0; x1.5/x2.0 are sensitivity views.\n"
            "Commission and swap are not modeled in M8B V1. Monetary sizing is deferred to M8D.\n"
            "Do not tune a gate on these outcomes and claim the same sample as validation.\n"
            "Normal submission: 99_UPLOAD_PACKAGE.zip\n"
        )
        (archive / "00_READ_ME_FIRST.txt").write_text(readme, encoding="utf-8")
        package(archive)
        latest_dir = output_root / "LATEST"
        if latest_dir.exists():
            shutil.rmtree(latest_dir)
        shutil.copytree(archive, latest_dir)

        mm = summary["primary_metrics_spread_x1_0"]
        pf_text = "INF" if mm["profit_factor_bps"] is None else f"{mm['profit_factor_bps']:.4f}"
        print(
            "[M8B PASS] "
            f"trades={mm['trade_count']} WR={mm['win_rate']:.4f} "
            f"PF={pf_text} net_bps={mm['net_return_bps_sum']:.2f} "
            f"trades_per_day={mm['trades_per_calendar_day']:.2f}"
        )
        print(f"[M8B OUTPUT] {latest_dir}")
        print(f"[M8B UPLOAD] {latest_dir / '99_UPLOAD_PACKAGE.zip'}")
        return 0
    except Exception as exc:
        print(f"[M8B BLOCKED] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
