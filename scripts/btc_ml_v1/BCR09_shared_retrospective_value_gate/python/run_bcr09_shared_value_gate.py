from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

M15_SHA = "b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148"
BCR07_SHA = "7b2643a00179aaa3b09c2854fa52e10e4bbad6ed9ff69d0a58e3d279ea7cb0f4"
BCR08_SHA = "2b5df4bcdf0f2c07c0d246a3cfe057f05ef4751f7ab3e3c71e8f993cd24cbbf7"
RECORDED_AT = "2026-07-30T19:50:00+09:00"
CONTRACT_COMMIT = "4808bdeeed7ff0b906428c7427f3eccf4bc525fb"
CORRECTION_COMMIT = "11cb7c46e60d09dc041d0e7e1b0000899ec5fd43"

SCENARIOS = {
    "C0_OBSERVED_SPREAD": 0.0,
    "C1_10PCT_SPREAD_PER_FILL": 0.1,
    "C2_25PCT_SPREAD_PER_FILL": 0.25,
    "C3_50PCT_SPREAD_PER_FILL": 0.5,
}

TRACK_A = {
    "TRACK_A_F1_COVERAGE_FIRST": dict(long_entry="E0Z1P0", short_entry="E0Z1P1", long_exit="T70M0P1"),
    "TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE": dict(long_entry="E0Z1P0", short_entry="E1Z1P1", long_exit="T70M0P1"),
    "TRACK_A_F3_STATE_FIDELITY": dict(long_entry="E1Z2P0", short_entry="E1Z2P0", long_exit="T70M0P1"),
    "TRACK_A_F4_MINIMUM_EXTRA_PARETO": dict(long_entry="E1Z2P0", short_entry="E1Z2P0", long_exit="T70M1P0"),
}

TRACK_A_EXPECTED = {
    "TRACK_A_F1_COVERAGE_FIRST": {"LONG": 801, "SHORT": 761},
    "TRACK_A_F2_HIGH_COVERAGE_INTERMEDIATE": {"LONG": 892, "SHORT": 337},
    "TRACK_A_F3_STATE_FIDELITY": {"LONG": 412, "SHORT": 400},
    "TRACK_A_F4_MINIMUM_EXTRA_PARETO": {"LONG": 416, "SHORT": 352},
}

EXPECTED_BCR07 = {
    "TRACK_B_B1_E0_EMA30_CROSS": (1980, 1980, 0),
    "TRACK_B_B1_E1_STACK_BREAK": (519, 519, 0),
    "TRACK_B_B4_E0_EMA20_TOUCH": (774, 773, 1),
    "TRACK_B_B4_E1_EXTENSION_CONTRACT": (833, 832, 1),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rci(values: np.ndarray) -> float:
    n = len(values)
    ranks = pd.Series(values).rank(method="average").to_numpy(float)
    d = np.arange(1, n + 1, dtype=float) - ranks
    return float((1 - 6 * np.square(d).sum() / (n * (n * n - 1))) * 100)


def build_features(m15: pd.DataFrame) -> pd.DataFrame:
    c = m15.copy().sort_values("server_open").reset_index(drop=True)
    cl, hi, lo = c["close"], c["high"], c["low"]
    for n in (9, 14, 18):
        c[f"rci{n}"] = cl.rolling(n, min_periods=n).apply(rci, raw=True)
        c[f"rci{n}_delta1"] = c[f"rci{n}"].diff()
        prev = c[f"rci{n}_delta1"].shift()
        c[f"rci{n}_turn_up"] = c[f"rci{n}_delta1"].gt(0) & prev.le(0)
        c[f"rci{n}_turn_down"] = c[f"rci{n}_delta1"].lt(0) & prev.ge(0)
    for n in (20, 30, 40):
        c[f"ema{n}"] = cl.ewm(span=n, adjust=False).mean()
    c["ema_alignment"] = np.select(
        [(c.ema20 > c.ema30) & (c.ema30 > c.ema40),
         (c.ema20 < c.ema30) & (c.ema30 < c.ema40)],
        ["BULLISH_STACK", "BEARISH_STACK"], default="MIXED")
    prev_close = cl.shift()
    tr = pd.concat([hi - lo, (hi - prev_close).abs(), (lo - prev_close).abs()], axis=1).max(axis=1)
    c["atr14"] = tr.rolling(14, min_periods=14).mean()
    c["atr50"] = tr.rolling(50, min_periods=50).mean()
    for h in (1, 4, 8, 16):
        c[f"ret{h}_bps"] = (cl / cl.shift(h) - 1) * 10000
    c["ema20_slope4"] = c["ema20"] - c["ema20"].shift(4)
    c["ema30_slope4"] = c["ema30"] - c["ema30"].shift(4)
    c["prev_exact"] = c["server_open"].diff().eq(pd.Timedelta(minutes=15))
    c["segment_id"] = (~c["prev_exact"]).cumsum()
    c["segment_pos"] = c.groupby("segment_id").cumcount() + 1

    prev_cols = [
        "close", "rci9", "rci9_turn_up", "rci9_turn_down",
        "ema20", "ema30", "ema40", "ema_alignment", "atr14", "atr50",
        "ret1_bps", "ret4_bps", "ret8_bps", "ret16_bps",
        "ema20_slope4", "ema30_slope4",
    ]
    for col in prev_cols:
        c[f"p_{col}"] = c[col].shift(1)

    c["common_eligible"] = (
        c.index.to_series().ge(500)
        & c["prev_exact"]
        & c["segment_pos"].ge(51)
        & c[["p_rci9", "p_ema40", "p_atr14"]].notna().all(axis=1)
    )
    return c


def long_entry(row, code: str) -> bool:
    if not row.common_eligible:
        return False
    if code == "E0Z1P0":
        return bool(row.p_rci9_turn_up) and row.p_rci9 <= 0
    if code == "E1Z2P0":
        return bool(row.p_rci9_turn_up) and row.p_ema_alignment == "BULLISH_STACK" and row.p_rci9 <= -40
    raise ValueError(code)


def short_entry(row, code: str) -> bool:
    if not row.common_eligible:
        return False
    if code == "E0Z1P1":
        return bool(row.p_rci9_turn_down) and row.p_rci9 >= 0 and row.p_ret1_bps < 0
    if code == "E1Z1P1":
        return bool(row.p_rci9_turn_down) and row.p_ema_alignment == "BEARISH_STACK" and row.p_rci9 >= 0 and row.p_ret1_bps < 0
    if code == "E1Z2P0":
        return bool(row.p_rci9_turn_down) and row.p_ema_alignment == "BEARISH_STACK" and row.p_rci9 >= 40
    raise ValueError(code)


def long_exit(row, code: str) -> bool:
    if not row.common_eligible:
        return False
    if code == "T70M0P1":
        return row.p_rci9 >= 70 and row.open > row.p_ema20
    if code == "T70M1P0":
        return row.p_rci9 >= 70 and row.p_ema30_slope4 > 0
    raise ValueError(code)


def replay_track_a(features: pd.DataFrame, machine_id: str) -> pd.DataFrame:
    spec = TRACK_A[machine_id]
    state, entry = "IDLE", None
    episodes: list[dict] = []
    for row in features.itertuples(index=False):
        if state == "ACTIVE_LONG":
            if long_exit(row, spec["long_exit"]):
                episodes.append(dict(machine_id=machine_id, direction="LONG",
                                     entry_server_open=entry, exit_server_open=row.server_open, closed=True))
                state, entry = "IDLE", None
        elif state == "ACTIVE_SHORT":
            if row.common_eligible and row.p_rci9 <= -70:
                episodes.append(dict(machine_id=machine_id, direction="SHORT",
                                     entry_server_open=entry, exit_server_open=row.server_open, closed=True))
                state, entry = "IDLE", None
        else:
            le = long_entry(row, spec["long_entry"])
            se = short_entry(row, spec["short_entry"])
            if le and not se:
                state, entry = "ACTIVE_LONG", row.server_open
            elif se and not le:
                state, entry = "ACTIVE_SHORT", row.server_open
    if state != "IDLE":
        episodes.append(dict(machine_id=machine_id,
                             direction="LONG" if state == "ACTIVE_LONG" else "SHORT",
                             entry_server_open=entry, exit_server_open=pd.NaT, closed=False))
    return pd.DataFrame(episodes)


def max_drawdown(values: np.ndarray) -> float:
    equity = np.concatenate([[0.0], np.cumsum(values)])
    return float((np.maximum.accumulate(equity) - equity).max())


def max_losing_streak(values: np.ndarray) -> int:
    best = run = 0
    for value in values:
        if value < 0:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def metrics(group: pd.DataFrame, scenario: str) -> dict:
    pnl_col = f"pnl_{scenario}"
    g = group.sort_values(["exit_server_open", "entry_server_open"])
    vals = g[pnl_col].to_numpy(float)
    pos, neg = vals[vals > 0], vals[vals < 0]
    gp, gl = pos.sum(), -neg.sum()
    monthly = g.groupby("exit_month")[pnl_col].sum()
    top = np.sort(pos)[::-1]
    return {
        "closed_trades": len(g),
        "closed_long": int(g.direction.eq("LONG").sum()),
        "closed_short": int(g.direction.eq("SHORT").sum()),
        "wins": int((vals > 0).sum()),
        "losses": int((vals < 0).sum()),
        "breakeven": int((vals == 0).sum()),
        "win_rate": float((vals > 0).mean()) if len(vals) else np.nan,
        "gross_profit": float(gp),
        "gross_loss": float(gl),
        "pf": float(gp / gl) if gl > 0 else (float("inf") if gp > 0 else np.nan),
        "net_usd_per_1lot": float(vals.sum()),
        "net_usd_per_0p01lot": float(vals.sum() * 0.01),
        "expectancy": float(vals.mean()) if len(vals) else np.nan,
        "median_trade": float(np.median(vals)) if len(vals) else np.nan,
        "average_win": float(pos.mean()) if len(pos) else np.nan,
        "average_loss": float(neg.mean()) if len(neg) else np.nan,
        "max_drawdown": max_drawdown(vals) if len(vals) else np.nan,
        "max_losing_streak": max_losing_streak(vals),
        "active_months": len(monthly),
        "positive_month_share": float(monthly.gt(0).mean()) if len(monthly) else np.nan,
        "top1_gross_profit_share": float(top[:1].sum() / gp) if gp > 0 else np.nan,
        "top5_gross_profit_share": float(top[:5].sum() / gp) if gp > 0 else np.nan,
        "top10_gross_profit_share": float(top[:10].sum() / gp) if gp > 0 else np.nan,
        "no_rollover_trades": int(g.same_server_date.sum()),
        "rollover_exposed_trades": int(g.rollover_exposed.sum()),
        "no_rollover_net": float(g.loc[g.same_server_date, pnl_col].sum()),
        "rollover_exposed_net_pre_swap": float(g.loc[g.rollover_exposed, pnl_col].sum()),
        "cost_total": float(g[f"cost_{scenario}"].sum()),
    }


def holm_adjust(p_values: np.ndarray) -> np.ndarray:
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values))
    running = 0.0
    for rank, original_index in enumerate(order):
        running = max(running, (len(p_values) - rank) * p_values[original_index])
        adjusted[original_index] = min(1.0, running)
    return adjusted


def write_deterministic_zip(directory: Path, target: Path) -> None:
    fixed = (2026, 7, 30, 10, 50, 0)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(directory.iterdir()):
            info = zipfile.ZipInfo(path.name, date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            zf.writestr(info, path.read_bytes())


def run(m15_path: Path, bcr07_path: Path, bcr08_path: Path, output_root: Path) -> Path:
    if sha256_file(m15_path) != M15_SHA:
        raise RuntimeError("M15 SHA mismatch")
    if sha256_file(bcr07_path) != BCR07_SHA:
        raise RuntimeError("BCR07 SHA mismatch")
    if sha256_file(bcr08_path) != BCR08_SHA:
        raise RuntimeError("BCR08 SHA mismatch")

    m15 = pd.read_csv(m15_path, encoding="utf-8-sig")
    m15["server_open"] = pd.to_datetime(m15["time"])
    for col in ("open", "high", "low", "close", "spread"):
        m15[col] = pd.to_numeric(m15[col], errors="raise")
    features = build_features(m15)

    episode_parts = [replay_track_a(features, machine_id) for machine_id in TRACK_A]
    with zipfile.ZipFile(bcr07_path) as zf:
        track_b = pd.read_csv(zf.open("03_episode_ledger_no_price_outcomes.csv"))
    track_b = track_b[["machine_id", "direction", "entry_server_open", "exit_server_open", "closed"]]
    track_b["closed"] = track_b["closed"].astype(bool)
    episode_parts.append(track_b)
    episodes = pd.concat(episode_parts, ignore_index=True)
    episodes["entry_server_open"] = pd.to_datetime(episodes["entry_server_open"])
    episodes["exit_server_open"] = pd.to_datetime(episodes["exit_server_open"])

    for machine_id, expected in TRACK_A_EXPECTED.items():
        subset = episodes.loc[episodes.machine_id.eq(machine_id)]
        observed = subset.direction.value_counts().to_dict()
        if observed.get("LONG", 0) != expected["LONG"] or observed.get("SHORT", 0) != expected["SHORT"]:
            raise RuntimeError(f"Track A count parity failed: {machine_id} {observed}")

    for machine_id, (entries, closed_n, open_n) in EXPECTED_BCR07.items():
        subset = episodes.loc[episodes.machine_id.eq(machine_id)]
        if len(subset) != entries or int(subset.closed.sum()) != closed_n or int((~subset.closed).sum()) != open_n:
            raise RuntimeError(f"BCR07 episode parity failed: {machine_id}")

    prices = features.set_index("server_open")
    trades = episodes.loc[episodes.closed].copy()
    for side in ("entry", "exit"):
        timestamp = f"{side}_server_open"
        trades[f"{side}_open"] = trades[timestamp].map(prices["open"])
        trades[f"{side}_spread"] = trades[timestamp].map(prices["spread"])
    if trades[["entry_open", "entry_spread", "exit_open", "exit_spread"]].isna().any().any():
        raise RuntimeError("Missing exact execution row")

    trades["entry_spread_price"] = trades.entry_spread * 0.01
    trades["exit_spread_price"] = trades.exit_spread * 0.01
    trades["same_server_date"] = trades.entry_server_open.dt.date == trades.exit_server_open.dt.date
    trades["rollover_exposed"] = ~trades.same_server_date
    trades["exit_month"] = trades.exit_server_open.dt.to_period("M").astype(str)
    trades["holding_bars"] = ((trades.exit_server_open - trades.entry_server_open) / pd.Timedelta(minutes=15)).astype(int)

    for scenario, fraction in SCENARIOS.items():
        entry_slip = fraction * trades.entry_spread_price
        exit_slip = fraction * trades.exit_spread_price
        long_pnl = (trades.exit_open - exit_slip) - (trades.entry_open + trades.entry_spread_price + entry_slip)
        short_pnl = (trades.entry_open - entry_slip) - (trades.exit_open + trades.exit_spread_price + exit_slip)
        trades[f"pnl_{scenario}"] = np.where(trades.direction.eq("LONG"), long_pnl, short_pnl)
        trades[f"cost_{scenario}"] = np.where(
            trades.direction.eq("LONG"),
            trades.entry_spread_price + entry_slip + exit_slip,
            trades.exit_spread_price + entry_slip + exit_slip,
        )

    machine_rows, direction_rows, rollover_rows = [], [], []
    for machine_id, group in trades.groupby("machine_id"):
        for scenario in SCENARIOS:
            machine_rows.append({"machine_id": machine_id, "scenario": scenario, **metrics(group, scenario)})
        for direction, direction_group in group.groupby("direction"):
            for scenario in SCENARIOS:
                direction_rows.append({"machine_id": machine_id, "direction": direction,
                                       "scenario": scenario, **metrics(direction_group, scenario)})
        for scenario in SCENARIOS:
            for subset_name, subset in (
                ("NO_ROLLOVER_FULL_KNOWN_COST", group.loc[group.same_server_date]),
                ("ROLLOVER_EXPOSED_PRE_SWAP", group.loc[group.rollover_exposed]),
            ):
                rollover_rows.append({"machine_id": machine_id, "scenario": scenario,
                                      "subset": subset_name, **metrics(subset, scenario)})
    machine_metrics = pd.DataFrame(machine_rows)
    direction_metrics = pd.DataFrame(direction_rows)
    rollover_metrics = pd.DataFrame(rollover_rows)

    pnl_columns = [f"pnl_{scenario}" for scenario in SCENARIOS]
    id_columns = [column for column in trades.columns if not column.startswith("pnl_")]
    long_form = trades.melt(id_vars=id_columns, value_vars=pnl_columns,
                            var_name="pnl_scenario", value_name="pnl")
    long_form["scenario"] = long_form.pnl_scenario.str.replace("pnl_", "", regex=False)
    monthly = long_form.groupby(["machine_id", "scenario", "exit_month"], as_index=False).agg(
        trades=("pnl", "size"), net_usd_per_1lot=("pnl", "sum"))
    monthly["positive"] = monthly.net_usd_per_1lot.gt(0)

    stat_rows = []
    for scenario in ("C0_OBSERVED_SPREAD", "C2_25PCT_SPREAD_PER_FILL"):
        for machine_id in machine_metrics.machine_id.unique():
            values = monthly.loc[(monthly.machine_id.eq(machine_id)) & (monthly.scenario.eq(scenario))] \
                            .sort_values("exit_month").net_usd_per_1lot.to_numpy()
            result = wilcoxon(values, alternative="greater", zero_method="wilcox",
                              correction=False, method="auto")
            stat_rows.append(dict(machine_id=machine_id, scenario=scenario, active_months=len(values),
                                  wilcoxon_stat=float(result.statistic), p_value=float(result.pvalue)))
    stats = pd.DataFrame(stat_rows)
    stats["holm_p"] = np.nan
    for scenario, group in stats.groupby("scenario"):
        stats.loc[group.index, "holm_p"] = holm_adjust(group.p_value.to_numpy())

    c0 = machine_metrics.loc[machine_metrics.scenario.eq("C0_OBSERVED_SPREAD")].set_index("machine_id")
    c2 = machine_metrics.loc[machine_metrics.scenario.eq("C2_25PCT_SPREAD_PER_FILL")].set_index("machine_id")
    no_roll = rollover_metrics.loc[
        rollover_metrics.scenario.eq("C0_OBSERVED_SPREAD")
        & rollover_metrics.subset.eq("NO_ROLLOVER_FULL_KNOWN_COST")
    ].set_index("machine_id")

    classification_rows = []
    for machine_id in c0.index:
        base, stress, known = c0.loc[machine_id], c2.loc[machine_id], no_roll.loc[machine_id]
        supported = (
            base.closed_trades >= 50 and base.closed_long >= 20 and base.closed_short >= 20
            and base.active_months >= 6 and base.pf >= 1.20
            and base.net_usd_per_1lot > 0 and base.expectancy > 0
            and base.positive_month_share >= 0.60
            and base.top5_gross_profit_share <= 0.50
            and known.closed_trades >= 30 and known.pf >= 1.05
            and stress.pf >= 1.00 and stress.net_usd_per_1lot >= 0
        )
        promising = (
            base.closed_trades >= 50 and base.pf >= 1.10
            and base.net_usd_per_1lot > 0 and base.expectancy > 0
            and base.positive_month_share >= 0.50 and stress.pf >= 0.95
            and base.top1_gross_profit_share <= 0.35
        )
        if supported:
            label = "VALUE_SUPPORTED_RETROSPECTIVE"
        elif promising:
            label = "VALUE_PROMISING_RETROSPECTIVE"
        elif base.net_usd_per_1lot > 0 and base.pf > 1 and stress.net_usd_per_1lot < 0:
            label = "HOLD_INSUFFICIENT_OR_COST_SENSITIVE"
        elif base.pf <= 1.0 or base.net_usd_per_1lot <= 0:
            label = "REJECT_RETROSPECTIVE_VALUE"
        else:
            label = "HOLD_INSUFFICIENT_OR_COST_SENSITIVE"
        classification_rows.append({
            "machine_id": machine_id,
            "classification": label,
            "c0_pf": base.pf,
            "c0_net": base.net_usd_per_1lot,
            "c0_expectancy": base.expectancy,
            "c0_positive_month_share": base.positive_month_share,
            "c2_pf": stress.pf,
            "c2_net": stress.net_usd_per_1lot,
            "c2_expectancy": stress.expectancy,
            "no_rollover_c0_trades": int(known.closed_trades),
            "no_rollover_c0_pf": known.pf,
            "no_rollover_c0_net": known.net_usd_per_1lot,
            "rollover_exposed_count": int(base.rollover_exposed_trades),
            "top1_gross_profit_share": base.top1_gross_profit_share,
            "top5_gross_profit_share": base.top5_gross_profit_share,
            "notes": "C0 positive but fixed C2 stress negative" if label.startswith("HOLD") else "",
        })
    classification = pd.DataFrame(classification_rows)

    integrity = {
        "frozen_m15_sha256": sha256_file(m15_path),
        "frozen_m15_rows": len(m15),
        "bcr07_package_sha256": sha256_file(bcr07_path),
        "bcr08_package_sha256": sha256_file(bcr08_path),
        "track_a_entry_count_parity": {
            machine_id: {
                "LONG_observed": int(episodes.loc[episodes.machine_id.eq(machine_id)].direction.eq("LONG").sum()),
                "LONG_expected": expected["LONG"],
                "SHORT_observed": int(episodes.loc[episodes.machine_id.eq(machine_id)].direction.eq("SHORT").sum()),
                "SHORT_expected": expected["SHORT"],
                "match": True,
            }
            for machine_id, expected in TRACK_A_EXPECTED.items()
        },
        "track_b_episode_ledger_used_authoritatively": True,
        "missing_entry_or_exit_price_rows": 0,
        "current_high_low_close_used_for_signal": False,
        "nearest_next_interpolation_used": False,
        "commission_round_trip": 0.0,
        "swap_included": False,
        "rollover_exposed_labeled": True,
        "invalid_initial_run_accepted": False,
    }

    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / "BCR09_20260730T105000Z"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir()
    summary = {
        "stage": "BCR09_SHARED_EXECUTION_COST_RETROSPECTIVE_VALUE_GATE",
        "recorded_at": RECORDED_AT,
        "status": "READY_CORRECTED_RETROSPECTIVE_VALUE_RESULT_NO_SUPPORTED_MACHINE",
        "input_m15_sha256": M15_SHA,
        "bcr07_package_sha256": BCR07_SHA,
        "bcr08_package_sha256": BCR08_SHA,
        "contract_commit": CONTRACT_COMMIT,
        "warmup_correction_commit": CORRECTION_COMMIT,
        "machine_count": 8,
        "closed_trade_rows": int(len(trades)),
        "endpoint_open_episodes": int((~episodes.closed).sum()),
        "classification_counts": classification.classification.value_counts().to_dict(),
        "supported_machines": classification.loc[classification.classification.eq("VALUE_SUPPORTED_RETROSPECTIVE"), "machine_id"].tolist(),
        "promising_machines": classification.loc[classification.classification.eq("VALUE_PROMISING_RETROSPECTIVE"), "machine_id"].tolist(),
        "hold_machines": classification.loc[classification.classification.eq("HOLD_INSUFFICIENT_OR_COST_SENSITIVE"), "machine_id"].tolist(),
        "rejected_machines": classification.loc[classification.classification.eq("REJECT_RETROSPECTIVE_VALUE"), "machine_id"].tolist(),
        "best_c0_machine": machine_metrics.loc[machine_metrics.loc[machine_metrics.scenario.eq("C0_OBSERVED_SPREAD"), "pf"].idxmax(), "machine_id"],
        "best_c0_pf": float(machine_metrics.loc[machine_metrics.scenario.eq("C0_OBSERVED_SPREAD"), "pf"].max()),
        "commission": 0.0,
        "swap_included": False,
        "rollover_exposed_results": "PRE_SWAP_ONLY",
        "invalid_initial_local_output_accepted": False,
        "portfolio_selected": False,
        "shadow_authorized": False,
    }
    readme = (
        "BCR09 - SHARED RETROSPECTIVE VALUE GATE\n\n"
        f"status: {summary['status']}\n"
        "IMPORTANT: retrospective only; swap excluded; no candidate promoted.\n"
        "The initial local run with an incorrect common warm-up is invalid audit history.\n"
    )
    (run_dir / "00_READ_ME_FIRST.txt").write_text(readme, encoding="utf-8")
    (run_dir / "01_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    episode_output = episodes.copy()
    for col in ("entry_server_open", "exit_server_open"):
        episode_output[col] = episode_output[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    episode_output["holding_bars"] = (
        (pd.to_datetime(episode_output.exit_server_open) - pd.to_datetime(episode_output.entry_server_open))
        / pd.Timedelta(minutes=15)
    )
    episode_output.to_csv(run_dir / "02_common_episode_ledger.csv", index=False, encoding="utf-8-sig")

    trade_columns = [
        "machine_id", "direction", "entry_server_open", "exit_server_open", "holding_bars",
        "entry_open", "entry_spread", "entry_spread_price",
        "exit_open", "exit_spread", "exit_spread_price",
        "same_server_date", "rollover_exposed", "exit_month",
    ]
    for scenario in SCENARIOS:
        trade_columns.extend([f"cost_{scenario}", f"pnl_{scenario}"])
    trade_output = trades[trade_columns].copy()
    for col in ("entry_server_open", "exit_server_open"):
        trade_output[col] = trade_output[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    trade_output.to_csv(run_dir / "03_trade_ledger_cost_enriched.csv", index=False, encoding="utf-8-sig")
    machine_metrics.to_csv(run_dir / "04_machine_metrics.csv", index=False, encoding="utf-8-sig")
    direction_metrics.to_csv(run_dir / "05_direction_metrics.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(run_dir / "06_monthly_metrics.csv", index=False, encoding="utf-8-sig")
    rollover_metrics.to_csv(run_dir / "07_rollover_subset_metrics.csv", index=False, encoding="utf-8-sig")
    stats.to_csv(run_dir / "08_monthly_wilcoxon_holm.csv", index=False, encoding="utf-8-sig")
    classification.to_csv(run_dir / "09_classification.csv", index=False, encoding="utf-8-sig")
    (run_dir / "10_integrity_checks.json").write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {}
    for path in sorted(run_dir.iterdir()):
        manifest[path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    (run_dir / "11_file_sha256_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    package = output_root / "BCR09_SHARED_RETROSPECTIVE_VALUE_GATE_20260730.zip"
    if package.exists():
        package.unlink()
    write_deterministic_zip(run_dir, package)
    return package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--m15", type=Path, required=True)
    parser.add_argument("--bcr07", type=Path, required=True)
    parser.add_argument("--bcr08", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    package = run(args.m15, args.bcr07, args.bcr08, args.output_root)
    print(package)
    print(sha256_file(package))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
