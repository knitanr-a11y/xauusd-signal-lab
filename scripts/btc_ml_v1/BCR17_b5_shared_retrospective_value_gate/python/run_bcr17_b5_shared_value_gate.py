from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
import shutil
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

EXPECTED_INPUT_SHA256 = "b8de00d117a119f9bf2f417b6228fe0ca0779c88f71a80b134bb9244d6768148"
EXPECTED_INPUT_ROWS = 30_661
EXPECTED_BCR16_PACKAGE_SHA256 = "c469be9455bd5639de336684e0fdcaebf6a72dc6f0bae623acefa5e0cb506653"
DEFAULT_INPUT = Path(r"C:\Users\regen\AppData\Roaming\MetaQuotes\Terminal\2FA8A7E69CED7DC259B1AD86A247F675\MQL5\Files\btcusdsharp_m15.csv")
PACKAGE_NAME = "BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE_20260731.zip"
FIXED_ZIP_DT = (2026, 7, 31, 0, 0, 0)
POINT = 0.01
C2_SLIPPAGE_FRACTION_PER_FILL = 0.25
M15 = pd.Timedelta(minutes=15)

MACHINES = (
    "TRACK_B_B5_R06_B075_W08_H1_IMPULSE_M15_RECLAIM",
    "TRACK_B_B5_R06_B075_W16_H1_IMPULSE_M15_RECLAIM",
    "TRACK_B_B5_R06_B100_W08_H1_IMPULSE_M15_RECLAIM",
    "TRACK_B_B5_R06_B100_W16_H1_IMPULSE_M15_RECLAIM",
    "TRACK_B_B5_R12_B075_W08_H1_IMPULSE_M15_RECLAIM",
    "TRACK_B_B5_R12_B075_W16_H1_IMPULSE_M15_RECLAIM",
    "TRACK_B_B5_R12_B100_W08_H1_IMPULSE_M15_RECLAIM",
    "TRACK_B_B5_R12_B100_W16_H1_IMPULSE_M15_RECLAIM",
)
EXPECTED_BCR16_MEMBERS = {
    "bcr16_episode_ledger.csv",
    "bcr16_event_counts.csv",
    "bcr16_gate_checks.csv",
    "bcr16_machine_metrics.csv",
    "bcr16_monthly_entries.csv",
    "bcr16_summary.json",
    "bcr16_transition_ledger.csv",
    "manifest.json",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _prefix_candidates(raw: bytes, expected_rows: int) -> Iterable[bytes]:
    lines = raw.splitlines(keepends=True)
    need = expected_rows + 1
    if len(lines) < need:
        return ()
    prefix = b"".join(lines[:need])
    candidates = [prefix]
    if prefix.endswith(b"\r\n"):
        candidates.append(prefix[:-2])
    elif prefix.endswith((b"\n", b"\r")):
        candidates.append(prefix[:-1])
    return candidates


def resolve_frozen_input(source: Path, work_dir: Path, allow_prefix_rehydrate: bool) -> tuple[Path, dict[str, Any]]:
    if not source.exists():
        raise FileNotFoundError(f"BCR17 input not found: {source}")
    actual_sha = sha256_file(source)
    if actual_sha == EXPECTED_INPUT_SHA256:
        return source, {
            "source_path": str(source),
            "source_sha256": actual_sha,
            "frozen_sha256": actual_sha,
            "prefix_rehydrated": False,
        }
    if not allow_prefix_rehydrate:
        raise ValueError("Input SHA mismatch and prefix rehydration was not enabled")
    raw = source.read_bytes()
    work_dir.mkdir(parents=True, exist_ok=True)
    for candidate in _prefix_candidates(raw, EXPECTED_INPUT_ROWS):
        if sha256_bytes(candidate) == EXPECTED_INPUT_SHA256:
            out = work_dir / "frozen_btc_m15_snapshot.csv"
            out.write_bytes(candidate)
            return out, {
                "source_path": str(source),
                "source_sha256": actual_sha,
                "frozen_sha256": EXPECTED_INPUT_SHA256,
                "prefix_rehydrated": True,
                "prefix_rows": EXPECTED_INPUT_ROWS,
            }
    raise ValueError(
        "Input SHA mismatch and no byte-exact 30,661-row prefix reproduced the frozen SHA; "
        "no alternate file, sorting, repair, nearest/next, or interpolation is permitted"
    )


def read_value_m15(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [str(c).strip().lower().lstrip("\ufeff") for c in df.columns]
    aliases = {"datetime": "time", "date_time": "time", "timestamp": "time"}
    df = df.rename(columns={c: aliases.get(c, c) for c in df.columns})
    required = ["time", "open", "high", "low", "close", "spread"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required value-gate columns: {missing}; got {list(df.columns)}")
    df = df[required].copy()
    df["time"] = pd.to_datetime(df["time"], errors="raise")
    if getattr(df["time"].dt, "tz", None) is not None:
        raise ValueError("BCR17 requires naive MT5 broker-server timestamps")
    for c in ["open", "high", "low", "close", "spread"]:
        df[c] = pd.to_numeric(df[c], errors="raise").astype(float)
    if len(df) != EXPECTED_INPUT_ROWS:
        raise ValueError(f"Frozen row-count mismatch: expected {EXPECTED_INPUT_ROWS}, got {len(df)}")
    if df["time"].duplicated().any():
        raise ValueError("Duplicate M15 open timestamp")
    if not df["time"].is_monotonic_increasing:
        raise ValueError("M15 rows are not strictly increasing; implicit sorting is forbidden")
    if (df["spread"] < 0).any():
        raise ValueError("Negative spread points")
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("OHLC integrity failure: high")
    if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("OHLC integrity failure: low")
    df["spread_price"] = df["spread"] * POINT
    return df


def validate_contract(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["frozen_input"]["BTC_M15_sha256"] != EXPECTED_INPUT_SHA256:
        raise ValueError("BCR17 contract frozen input SHA mismatch")
    if int(payload["frozen_input"]["rows"]) != EXPECTED_INPUT_ROWS:
        raise ValueError("BCR17 contract frozen row count mismatch")
    if payload["source_capability_package"]["sha256"] != EXPECTED_BCR16_PACKAGE_SHA256:
        raise ValueError("BCR17 contract BCR16 package SHA mismatch")
    if tuple(payload["machine_inventory"]) != MACHINES:
        raise ValueError("BCR17 contract machine inventory mismatch")
    c = payload["execution_cost_contract"]
    if float(c["point"]) != POINT or float(c["C2_slippage_fraction_of_spread_per_fill"]) != C2_SLIPPAGE_FRACTION_PER_FILL:
        raise ValueError("BCR17 execution/cost constants mismatch")
    return payload


def load_bcr16_package(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], dict[str, Any]]:
    actual_sha = sha256_file(path)
    if actual_sha != EXPECTED_BCR16_PACKAGE_SHA256:
        raise ValueError(f"BCR16 package SHA mismatch: {actual_sha}")
    with zipfile.ZipFile(path, "r") as zf:
        bad = zf.testzip()
        if bad is not None:
            raise ValueError(f"BCR16 package CRC failure: {bad}")
        names = set(zf.namelist())
        if names != EXPECTED_BCR16_MEMBERS:
            raise ValueError(f"BCR16 package members mismatch: {sorted(names)}")
        summary = json.loads(zf.read("bcr16_summary.json"))
        manifest = json.loads(zf.read("manifest.json"))
        episodes = pd.read_csv(zf.open("bcr16_episode_ledger.csv"))
        metrics = pd.read_csv(zf.open("bcr16_machine_metrics.csv"))
    if summary.get("input_rows") != EXPECTED_INPUT_ROWS:
        raise ValueError("BCR16 summary input row mismatch")
    if summary.get("input", {}).get("frozen_sha256") != EXPECTED_INPUT_SHA256:
        raise ValueError("BCR16 summary frozen input SHA mismatch")
    if summary.get("all_eight_reported") is not True or summary.get("capability_pass_count") != 8:
        raise ValueError("BCR16 package is not the accepted eight-survivor capability result")
    if summary.get("outcome_fields_opened") is not False or summary.get("value_evaluation_performed") is not False:
        raise ValueError("BCR16 source package unexpectedly opened value outcomes")
    if set(metrics["machine_id"]) != set(MACHINES) or len(metrics) != 8:
        raise ValueError("BCR16 machine metrics inventory mismatch")
    if not metrics["capability_pass"].astype(str).str.lower().eq("true").all():
        raise ValueError("BCR16 source includes a non-passing machine")
    if set(episodes["machine_id"]) != set(MACHINES):
        raise ValueError("BCR16 episode inventory mismatch")
    if episodes["endpoint_open"].astype(str).str.lower().eq("true").any():
        raise ValueError("BCR17 requires closed BCR16 episodes only")
    expected_counts = metrics.set_index("machine_id")["closed_episodes"].astype(int).to_dict()
    actual_counts = episodes.groupby("machine_id").size().to_dict()
    if actual_counts != expected_counts:
        raise ValueError(f"BCR16 episode count mismatch: {actual_counts} vs {expected_counts}")
    if episodes.duplicated(["machine_id", "entry_time"]).any():
        raise ValueError("Duplicate BCR16 machine entry timestamp")
    return episodes, metrics, summary, manifest


def _fill_prices(direction: str, entry_bid: float, exit_bid: float, entry_spread: float, exit_spread: float) -> dict[str, float]:
    if direction == "LONG":
        entry_c0 = entry_bid + entry_spread
        exit_c0 = exit_bid
        entry_c2 = entry_c0 + C2_SLIPPAGE_FRACTION_PER_FILL * entry_spread
        exit_c2 = exit_c0 - C2_SLIPPAGE_FRACTION_PER_FILL * exit_spread
        pnl_c0 = exit_c0 - entry_c0
        pnl_c2 = exit_c2 - entry_c2
    elif direction == "SHORT":
        entry_c0 = entry_bid
        exit_c0 = exit_bid + exit_spread
        entry_c2 = entry_c0 - C2_SLIPPAGE_FRACTION_PER_FILL * entry_spread
        exit_c2 = exit_c0 + C2_SLIPPAGE_FRACTION_PER_FILL * exit_spread
        pnl_c0 = entry_c0 - exit_c0
        pnl_c2 = entry_c2 - exit_c2
    else:
        raise ValueError(f"Unknown direction: {direction}")
    return {
        "entry_price_c0": entry_c0,
        "exit_price_c0": exit_c0,
        "pnl_c0_usd_1lot": pnl_c0,
        "entry_price_c2": entry_c2,
        "exit_price_c2": exit_c2,
        "pnl_c2_usd_1lot": pnl_c2,
    }


def _path_excursions(
    direction: str,
    m15: pd.DataFrame,
    entry_idx: int,
    exit_idx: int,
    entry_bid: float,
    entry_spread: float,
    exit_bid: float,
    exit_spread: float,
) -> dict[str, float]:
    if exit_idx <= entry_idx:
        raise ValueError("Exit must be after entry")
    path = m15.iloc[entry_idx:exit_idx]
    if path.empty:
        raise ValueError("Empty holding path")
    if direction == "LONG":
        entry_c0 = entry_bid + entry_spread
        favorable_c0 = list(path["high"] - entry_c0) + [exit_bid - entry_c0]
        adverse_c0 = list(path["low"] - entry_c0) + [exit_bid - entry_c0]
        entry_c2 = entry_c0 + C2_SLIPPAGE_FRACTION_PER_FILL * entry_spread
        favorable_c2 = list(path["high"] - C2_SLIPPAGE_FRACTION_PER_FILL * path["spread_price"] - entry_c2)
        adverse_c2 = list(path["low"] - C2_SLIPPAGE_FRACTION_PER_FILL * path["spread_price"] - entry_c2)
        favorable_c2.append(exit_bid - C2_SLIPPAGE_FRACTION_PER_FILL * exit_spread - entry_c2)
        adverse_c2.append(exit_bid - C2_SLIPPAGE_FRACTION_PER_FILL * exit_spread - entry_c2)
    else:
        entry_c0 = entry_bid
        ask_low = path["low"] + path["spread_price"]
        ask_high = path["high"] + path["spread_price"]
        favorable_c0 = list(entry_c0 - ask_low) + [entry_c0 - (exit_bid + exit_spread)]
        adverse_c0 = list(entry_c0 - ask_high) + [entry_c0 - (exit_bid + exit_spread)]
        entry_c2 = entry_c0 - C2_SLIPPAGE_FRACTION_PER_FILL * entry_spread
        ask_low_c2 = path["low"] + path["spread_price"] + C2_SLIPPAGE_FRACTION_PER_FILL * path["spread_price"]
        ask_high_c2 = path["high"] + path["spread_price"] + C2_SLIPPAGE_FRACTION_PER_FILL * path["spread_price"]
        favorable_c2 = list(entry_c2 - ask_low_c2)
        adverse_c2 = list(entry_c2 - ask_high_c2)
        exit_ask_c2 = exit_bid + exit_spread + C2_SLIPPAGE_FRACTION_PER_FILL * exit_spread
        favorable_c2.append(entry_c2 - exit_ask_c2)
        adverse_c2.append(entry_c2 - exit_ask_c2)
    return {
        "mfe_c0_usd_1lot": max(favorable_c0),
        "mae_c0_usd_1lot": min(adverse_c0),
        "mfe_c2_usd_1lot": max(favorable_c2),
        "mae_c2_usd_1lot": min(adverse_c2),
    }


def build_trade_ledger(m15: pd.DataFrame, episodes: pd.DataFrame) -> list[dict[str, Any]]:
    time_to_idx = {pd.Timestamp(t): i for i, t in enumerate(pd.to_datetime(m15["time"]))}
    rows: list[dict[str, Any]] = []
    for e in episodes.to_dict("records"):
        entry_t = pd.Timestamp(e["entry_time"])
        exit_t = pd.Timestamp(e["exit_time"])
        entry_idx = time_to_idx.get(entry_t)
        exit_idx = time_to_idx.get(exit_t)
        if entry_idx is None or exit_idx is None:
            raise ValueError(f"Missing exact entry/exit M15 row: {entry_t} / {exit_t}")
        if exit_idx <= entry_idx:
            raise ValueError("Non-positive episode ordering")
        holding = int(round((exit_t - entry_t).total_seconds() / 900.0))
        if holding != int(e["holding_bars"]):
            raise ValueError(f"Holding-bar mismatch for {e['machine_id']} {entry_t}")
        entry = m15.iloc[entry_idx]
        exit_ = m15.iloc[exit_idx]
        fills = _fill_prices(
            str(e["direction"]),
            float(entry["open"]),
            float(exit_["open"]),
            float(entry["spread_price"]),
            float(exit_["spread_price"]),
        )
        excursions = _path_excursions(
            str(e["direction"]), m15, entry_idx, exit_idx,
            float(entry["open"]), float(entry["spread_price"]),
            float(exit_["open"]), float(exit_["spread_price"]),
        )
        same_date = entry_t.date() == exit_t.date()
        row = {
            "machine_id": e["machine_id"],
            "direction": e["direction"],
            "impulse_h1_open": e["impulse_h1_open"],
            "pullback_time": e["pullback_time"],
            "reclaim_time": e["reclaim_time"],
            "entry_time": entry_t.isoformat(sep=" "),
            "exit_time": exit_t.isoformat(sep=" "),
            "holding_bars": holding,
            "exit_reason": e["exit_reason"],
            "entry_bid_open": float(entry["open"]),
            "exit_bid_open": float(exit_["open"]),
            "entry_spread_points": float(entry["spread"]),
            "exit_spread_points": float(exit_["spread"]),
            "entry_spread_price": float(entry["spread_price"]),
            "exit_spread_price": float(exit_["spread_price"]),
            **fills,
            **excursions,
            "win_loss_c0": "WIN" if fills["pnl_c0_usd_1lot"] > 0 else ("LOSS" if fills["pnl_c0_usd_1lot"] < 0 else "FLAT"),
            "win_loss_c2": "WIN" if fills["pnl_c2_usd_1lot"] > 0 else ("LOSS" if fills["pnl_c2_usd_1lot"] < 0 else "FLAT"),
            "entry_month": entry_t.strftime("%Y-%m"),
            "same_server_date": same_date,
            "rollover_exposed": not same_date,
            "financing_status": "FULL_KNOWN_COST_NO_ROLLOVER" if same_date else "PRE_SWAP_ONLY",
        }
        rows.append(row)
    rows.sort(key=lambda r: (r["machine_id"], r["entry_time"]))
    return rows


def _profit_factor(values: Iterable[float]) -> float | None:
    values = list(float(x) for x in values)
    gp = sum(x for x in values if x > 0)
    gl = -sum(x for x in values if x < 0)
    if gl == 0:
        return None if gp == 0 else math.inf
    return gp / gl


def _max_drawdown(values: Iterable[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for v in values:
        equity += float(v)
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd


def _summary(values: Iterable[float]) -> dict[str, Any]:
    a = np.asarray(list(values), dtype=float)
    wins = int((a > 0).sum())
    losses = int((a < 0).sum())
    flats = int((a == 0).sum())
    return {
        "trades": int(len(a)),
        "wins": wins,
        "losses": losses,
        "flats": flats,
        "win_rate": float(wins / len(a)) if len(a) else None,
        "gross_profit": float(a[a > 0].sum()) if len(a) else 0.0,
        "gross_loss_abs": float(-a[a < 0].sum()) if len(a) else 0.0,
        "profit_factor": _profit_factor(a),
        "net_usd_1lot": float(a.sum()),
        "expectancy_usd_1lot": float(a.mean()) if len(a) else None,
        "median_usd_1lot": float(np.median(a)) if len(a) else None,
        "max_drawdown_usd_1lot": _max_drawdown(a),
    }


def _rankdata_average(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    k = 0
    while k < len(order):
        j = k + 1
        while j < len(order) and values[order[j]] == values[order[k]]:
            j += 1
        avg = ((k + 1) + j) / 2.0
        for p in range(k, j):
            ranks[order[p]] = avg
        k = j
    return ranks


def exact_wilcoxon_greater(values: Iterable[float]) -> dict[str, Any]:
    xs = [float(x) for x in values if float(x) != 0.0]
    n = len(xs)
    if n == 0:
        return {"n_nonzero": 0, "w_plus": 0.0, "p_one_sided_greater": 1.0}
    ranks = _rankdata_average([abs(x) for x in xs])
    observed = sum(r for x, r in zip(xs, ranks) if x > 0)
    total = 1 << n
    extreme = 0
    for mask in range(total):
        w = 0.0
        for i, r in enumerate(ranks):
            if mask & (1 << i):
                w += r
        if w >= observed - 1e-12:
            extreme += 1
    return {
        "n_nonzero": n,
        "w_plus": observed,
        "p_one_sided_greater": extreme / total,
    }


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    items = sorted(pvalues.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        value = min(1.0, (m - rank) * float(p))
        running = max(running, value)
        adjusted[name] = running
    return adjusted


def _classification(c0: dict[str, Any], c2: dict[str, Any], c2_holm_p: float) -> str:
    c0_positive = c0["net_usd_1lot"] > 0 and (c0["profit_factor"] or 0) > 1.0
    c2_positive = c2["net_usd_1lot"] > 0 and (c2["profit_factor"] or 0) > 1.0
    if c0_positive and c2_positive and c2_holm_p <= 0.05:
        return "VALUE_SUPPORTED_RETROSPECTIVE"
    if c0_positive and c2_positive:
        return "VALUE_PROMISING_RETROSPECTIVE"
    if c0_positive:
        return "HOLD_COST_SENSITIVE"
    return "REJECT_RETROSPECTIVE_VALUE"


def summarize_trades(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    df = pd.DataFrame(rows)
    machine_base: dict[str, dict[str, Any]] = {}
    monthly_rows: list[dict[str, Any]] = []
    direction_rows: list[dict[str, Any]] = []
    rollover_rows: list[dict[str, Any]] = []
    reason_rows: list[dict[str, Any]] = []
    raw_p_c0: dict[str, float] = {}
    raw_p_c2: dict[str, float] = {}
    wilcoxon: dict[str, dict[str, Any]] = {}
    for machine in MACHINES:
        g = df[df["machine_id"] == machine].sort_values("entry_time")
        c0 = _summary(g["pnl_c0_usd_1lot"])
        c2 = _summary(g["pnl_c2_usd_1lot"])
        monthly_c0 = g.groupby("entry_month")["pnl_c0_usd_1lot"].sum().sort_index()
        monthly_c2 = g.groupby("entry_month")["pnl_c2_usd_1lot"].sum().sort_index()
        w0 = exact_wilcoxon_greater(monthly_c0.values)
        w2 = exact_wilcoxon_greater(monthly_c2.values)
        raw_p_c0[machine] = w0["p_one_sided_greater"]
        raw_p_c2[machine] = w2["p_one_sided_greater"]
        wilcoxon[machine] = {"c0": w0, "c2": w2}
        machine_base[machine] = {
            "machine_id": machine,
            **{f"c0_{k}": v for k, v in c0.items()},
            **{f"c2_{k}": v for k, v in c2.items()},
            "entry_months": int(g["entry_month"].nunique()),
            "same_server_date_trades": int(g["same_server_date"].sum()),
            "rollover_exposed_trades": int(g["rollover_exposed"].sum()),
            "mean_mfe_c0": float(g["mfe_c0_usd_1lot"].mean()),
            "mean_mae_c0": float(g["mae_c0_usd_1lot"].mean()),
            "median_mfe_c0": float(g["mfe_c0_usd_1lot"].median()),
            "median_mae_c0": float(g["mae_c0_usd_1lot"].median()),
        }
        all_months = sorted(set(monthly_c0.index) | set(monthly_c2.index))
        for month in all_months:
            mg = g[g["entry_month"] == month]
            monthly_rows.append({
                "machine_id": machine,
                "entry_month": month,
                "trades": len(mg),
                "c0_net_usd_1lot": float(mg["pnl_c0_usd_1lot"].sum()),
                "c2_net_usd_1lot": float(mg["pnl_c2_usd_1lot"].sum()),
            })
        for direction in ("LONG", "SHORT"):
            dg = g[g["direction"] == direction]
            s0, s2 = _summary(dg["pnl_c0_usd_1lot"]), _summary(dg["pnl_c2_usd_1lot"])
            direction_rows.append({
                "machine_id": machine, "direction": direction,
                **{f"c0_{k}": v for k, v in s0.items()},
                **{f"c2_{k}": v for k, v in s2.items()},
            })
        for label, mask in (
            ("FULL_KNOWN_COST_NO_ROLLOVER", g["same_server_date"]),
            ("PRE_SWAP_ONLY_ROLLOVER_EXPOSED", g["rollover_exposed"]),
        ):
            rg = g[mask]
            s0, s2 = _summary(rg["pnl_c0_usd_1lot"]), _summary(rg["pnl_c2_usd_1lot"])
            rollover_rows.append({
                "machine_id": machine, "subset": label,
                **{f"c0_{k}": v for k, v in s0.items()},
                **{f"c2_{k}": v for k, v in s2.items()},
            })
        for reason, rg in g.groupby("exit_reason", sort=True):
            s0, s2 = _summary(rg["pnl_c0_usd_1lot"]), _summary(rg["pnl_c2_usd_1lot"])
            reason_rows.append({
                "machine_id": machine, "exit_reason": reason,
                **{f"c0_{k}": v for k, v in s0.items()},
                **{f"c2_{k}": v for k, v in s2.items()},
            })
    adj0 = holm_adjust(raw_p_c0)
    adj2 = holm_adjust(raw_p_c2)
    machine_rows: list[dict[str, Any]] = []
    testing_rows: list[dict[str, Any]] = []
    empty_summary_keys = _summary({}).keys()
    for machine in MACHINES:
        base = machine_base[machine]
        base.update({
            "c0_monthly_wilcoxon_n": wilcoxon[machine]["c0"]["n_nonzero"],
            "c0_monthly_wilcoxon_w_plus": wilcoxon[machine]["c0"]["w_plus"],
            "c0_monthly_wilcoxon_raw_p": raw_p_c0[machine],
            "c0_monthly_wilcoxon_holm_p": adj0[machine],
            "c2_monthly_wilcoxon_n": wilcoxon[machine]["c2"]["n_nonzero"],
            "c2_monthly_wilcoxon_w_plus": wilcoxon[machine]["c2"]["w_plus"],
            "c2_monthly_wilcoxon_raw_p": raw_p_c2[machine],
            "c2_monthly_wilcoxon_holm_p": adj2[machine],
        })
        c0 = {k[3:]: v for k, v in base.items() if k.startswith("c0_") and k[3:] in empty_summary_keys}
        c2 = {k[3:]: v for k, v in base.items() if k.startswith("c2_") and k[3:] in empty_summary_keys}
        base["classification"] = _classification(c0, c2, adj2[machine])
        machine_rows.append(base)
        testing_rows.extend([
            {"machine_id": machine, "cost": "C0", **wilcoxon[machine]["c0"], "raw_p": raw_p_c0[machine], "holm_adjusted_p": adj0[machine]},
            {"machine_id": machine, "cost": "C2", **wilcoxon[machine]["c2"], "raw_p": raw_p_c2[machine], "holm_adjusted_p": adj2[machine]},
        ])
    return {
        "machine": machine_rows,
        "monthly": monthly_rows,
        "direction": direction_rows,
        "rollover": rollover_rows,
        "reason": reason_rows,
        "testing": testing_rows,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None if math.isnan(value) else ("INF" if value > 0 else "-INF")
        return round(value, 12)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_normalize(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _deterministic_zip(output_dir: Path, members: list[Path]) -> Path:
    zip_path = output_dir / PACKAGE_NAME
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(members, key=lambda p: p.name):
            info = zipfile.ZipInfo(path.name, date_time=FIXED_ZIP_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return zip_path


def build_once(
    input_path: Path,
    bcr16_package: Path,
    contract_path: Path,
    output_dir: Path,
    allow_prefix_rehydrate: bool,
) -> dict[str, Any]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    contract = validate_contract(contract_path)
    episodes, metrics, bcr16_summary, _ = load_bcr16_package(bcr16_package)
    with tempfile.TemporaryDirectory(prefix="bcr17_input_") as td:
        frozen_path, input_meta = resolve_frozen_input(input_path, Path(td), allow_prefix_rehydrate)
        m15 = read_value_m15(frozen_path)
    trade_rows = build_trade_ledger(m15, episodes)
    summaries = summarize_trades(trade_rows)
    _write_csv(output_dir / "bcr17_trade_ledger.csv", trade_rows)
    _write_csv(output_dir / "bcr17_machine_summary.csv", summaries["machine"])
    _write_csv(output_dir / "bcr17_direction_summary.csv", summaries["direction"])
    _write_csv(output_dir / "bcr17_monthly_summary.csv", summaries["monthly"])
    _write_csv(output_dir / "bcr17_rollover_summary.csv", summaries["rollover"])
    _write_csv(output_dir / "bcr17_exit_reason_summary.csv", summaries["reason"])
    _write_csv(output_dir / "bcr17_multiple_testing.csv", summaries["testing"])
    classifications = defaultdict(int)
    for row in summaries["machine"]:
        classifications[row["classification"]] += 1
    summary = {
        "project": "BTC_CANDIDATE_RESEARCH_REDESIGN",
        "stage": "BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE",
        "status": "BCR17_RETROSPECTIVE_VALUE_OUTPUT_BUILT_NO_AUTOMATIC_PROMOTION",
        "branch": "feature/btc-fresh-forward-research",
        "input": input_meta,
        "input_rows": len(m15),
        "input_first_time": m15["time"].iloc[0].isoformat(sep=" "),
        "input_last_time": m15["time"].iloc[-1].isoformat(sep=" "),
        "bcr16_package_sha256": EXPECTED_BCR16_PACKAGE_SHA256,
        "bcr16_episode_rows": len(episodes),
        "machine_count": len(MACHINES),
        "all_eight_reported": len(summaries["machine"]) == 8,
        "execution_cost_contract": contract["execution_cost_contract"],
        "multiple_testing": contract["multiple_testing"],
        "classification_counts": dict(sorted(classifications.items())),
        "machine_results": summaries["machine"],
        "commission_included": False,
        "swap_included": False,
        "rollover_exposed_rows_labeled_pre_swap_only": True,
        "candidate_promoted": False,
        "portfolio_selected": False,
        "prospective_start_set": False,
        "shadow_started": False,
        "discord_sent": False,
        "mt5_order_sent": False,
    }
    _json_dump(output_dir / "bcr17_summary.json", summary)
    manifest_files = []
    for path in sorted(output_dir.glob("bcr17_*")):
        manifest_files.append({"name": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "stage": "BCR17_B5_SHARED_RETROSPECTIVE_VALUE_GATE",
        "source_input_sha256": EXPECTED_INPUT_SHA256,
        "source_bcr16_package_sha256": EXPECTED_BCR16_PACKAGE_SHA256,
        "contract_sha256": sha256_file(contract_path),
        "files": manifest_files,
        "deterministic_zip_timestamp": FIXED_ZIP_DT,
    }
    _json_dump(output_dir / "manifest.json", manifest)
    members = [p for p in output_dir.iterdir() if p.is_file() and p.name != PACKAGE_NAME]
    zip_path = _deterministic_zip(output_dir, members)
    package_sha = sha256_file(zip_path)
    (output_dir / "package_sha256.txt").write_text(f"{package_sha}  {PACKAGE_NAME}\n", encoding="ascii")
    return {"package_path": str(zip_path), "package_sha256": package_sha, "summary": summary}


def build_with_repeat(
    input_path: Path,
    bcr16_package: Path,
    contract_path: Path,
    output_dir: Path,
    allow_prefix_rehydrate: bool,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="bcr17_repeat_") as td:
        root = Path(td)
        first = build_once(input_path, bcr16_package, contract_path, root / "run_a", allow_prefix_rehydrate)
        second = build_once(input_path, bcr16_package, contract_path, root / "run_b", allow_prefix_rehydrate)
        if first["package_sha256"] != second["package_sha256"]:
            raise RuntimeError("BCR17 deterministic repeat package SHA mismatch")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(root / "run_a", output_dir)
        repeat = {
            "deterministic_repeat_match": True,
            "package_sha256_run_a": first["package_sha256"],
            "package_sha256_run_b": second["package_sha256"],
        }
        _json_dump(output_dir / "deterministic_repeat.json", repeat)
        return {**first, **repeat, "published_output_dir": str(output_dir)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BCR17 B5 shared retrospective value gate")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--bcr16-package", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-prefix-rehydrate", action="store_true")
    parser.add_argument("--repeat-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeat_check:
        result = build_with_repeat(args.input, args.bcr16_package, args.contract, args.output_dir, args.allow_prefix_rehydrate)
    else:
        result = build_once(args.input, args.bcr16_package, args.contract, args.output_dir, args.allow_prefix_rehydrate)
    print(json.dumps(_normalize(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
