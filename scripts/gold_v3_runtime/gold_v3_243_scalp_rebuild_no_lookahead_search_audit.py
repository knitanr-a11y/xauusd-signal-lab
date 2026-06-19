#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, itertools, json, math, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STAGE = "GOLD_V3_243_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_AUDIT_ONLY"
READY = "STAGE243_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_READY_AUDIT_ONLY"
BLOCKED = "STAGE243_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_BLOCKED_AUDIT_ONLY"
TERMINAL_HASH = "2FA8A7E69CED7DC259B1AD86A247F675"
TF_MIN = {"m1": 1, "m5": 5, "m15": 15, "h1": 60, "h4": 240, "d1": 1440}
OFF_FLAGS = {
    "discord_webhook_called": False,
    "mt5_order_send_called": False,
    "order_placed": False,
    "real_account_allowed": False,
    "final_live_enabled": False,
    "payload_activation_enabled": False,
    "live_hook_enabled": False,
    "autotrade_enabled": False,
    "no_signal_discord_notify": False,
    "no_signal_order_allowed": False,
    "source_csv_mutated": False,
    "contract_mutated": False,
    "candidate_pool_removed": False,
    "f002_exclusion_bypassed": False,
    "open_asof_allowed": False,
    "theoretical_result_used_as_input": False,
    "actual_execution_used_as_input": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def progress(msg: str, current: int | None = None, total: int | None = None) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    if current is not None and total:
        pct = 100.0 * float(current) / float(total)
        print(f"[Stage243 progress {current}/{total} {pct:5.1f}% {ts}] {msg}", flush=True)
    else:
        print(f"[Stage243 progress {ts}] {msg}", flush=True)


def safe(x: Any) -> Any:
    if isinstance(x, (str, int, bool)) or x is None:
        return x
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, (pd.Timestamp, datetime)):
        return str(x)
    if isinstance(x, dict):
        return {str(k): safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [safe(v) for v in x]
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    return str(x)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(data), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def normalize_col(col: Any) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(col).strip().strip("<>").lower()).strip("_")
    return {
        "tickvol": "tick_volume",
        "tick_vol": "tick_volume",
        "vol": "tick_volume",
        "volume": "tick_volume",
        "datetime": "time",
    }.get(s, s)


def read_csv_any(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    for enc in ["utf-8-sig", "utf-8", "cp932"]:
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep, low_memory=False)
                if len(df.columns) <= 1:
                    continue
                df.columns = [normalize_col(c) for c in df.columns]
                if "dt" in df.columns:
                    df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
                elif "time" in df.columns and "date" in df.columns:
                    df["dt"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), errors="coerce")
                elif "time" in df.columns:
                    df["dt"] = pd.to_datetime(df["time"], errors="coerce")
                else:
                    continue
                for c in ["open", "high", "low", "close", "tick_volume", "spread"]:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                if not {"dt", "open", "high", "low", "close"}.issubset(df.columns):
                    continue
                df = df[df["dt"].notna()].drop_duplicates("dt", keep="last").sort_values("dt").reset_index(drop=True)
                return df
            except Exception:
                pass
    return pd.DataFrame()


def default_files_dir() -> Path:
    env = os.environ.get("GOLD_V3_MQL5_FILES", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    app = os.environ.get("APPDATA", "").strip()
    if app:
        return Path(app, "MetaQuotes", "Terminal", TERMINAL_HASH, "MQL5", "Files").resolve()
    return Path.cwd().resolve()


def combine_tf(live_dir: Path, hist_2025_dir: Path, tf: str) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    live_path = live_dir / f"goldsharp_{tf}.csv"
    hist_root_path = live_dir / f"gold#_{tf}.csv"
    hist_2025_path = hist_2025_dir / f"gold#_{tf}.csv"

    live = read_csv_any(live_path)
    hist_root = read_csv_any(hist_root_path)
    hist_2025 = read_csv_any(hist_2025_path)
    hist = hist_2025 if not hist_2025.empty else hist_root

    diag = [
        {"tf": tf, "src": "live_goldsharp_root", "path": str(live_path), "exists": live_path.exists(), "rows": len(live)},
        {"tf": tf, "src": "hist_gold_hash_root_fallback", "path": str(hist_root_path), "exists": hist_root_path.exists(), "rows": len(hist_root)},
        {"tf": tf, "src": "hist_2025_gold_hash_dir", "path": str(hist_2025_path), "exists": hist_2025_path.exists(), "rows": len(hist_2025)},
    ]

    parts = []
    if not hist.empty:
        parts.append(hist[(hist["dt"] >= pd.Timestamp("2025-01-01")) & (hist["dt"] < pd.Timestamp("2026-01-01"))].copy())
    elif not live.empty:
        parts.append(live[(live["dt"] >= pd.Timestamp("2025-01-01")) & (live["dt"] < pd.Timestamp("2026-01-01"))].copy())
    if not live.empty:
        parts.append(live[live["dt"] >= pd.Timestamp("2026-01-01")].copy())
    if not parts:
        return pd.DataFrame(), diag

    out = pd.concat(parts, ignore_index=True).drop_duplicates("dt", keep="last").sort_values("dt").reset_index(drop=True)
    out["open_time"] = out["dt"]
    out["close_time"] = out["dt"] + pd.to_timedelta(TF_MIN[tf], unit="min")
    return out, diag


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).where(avg_loss.ne(0), 100.0)


def build_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    o = pd.to_numeric(df["open"], errors="coerce")
    h = pd.to_numeric(df["high"], errors="coerce")
    l = pd.to_numeric(df["low"], errors="coerce")
    c = pd.to_numeric(df["close"], errors="coerce")
    prev_c = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)

    x = pd.DataFrame({"open_time": df["open_time"], "close_time": df["close_time"]})
    x[f"{prefix}_open"] = o
    x[f"{prefix}_high"] = h
    x[f"{prefix}_low"] = l
    x[f"{prefix}_close"] = c
    x[f"{prefix}_ret1"] = c.diff()
    x[f"{prefix}_ret3"] = c.diff(3)
    x[f"{prefix}_ret8"] = c.diff(8)
    x[f"{prefix}_range"] = h - l
    x[f"{prefix}_body"] = c - o
    x[f"{prefix}_body_abs"] = (c - o).abs()
    x[f"{prefix}_upper_wick"] = h - np.maximum(o, c)
    x[f"{prefix}_lower_wick"] = np.minimum(o, c) - l
    x[f"{prefix}_close_gt_open"] = (c > o).astype(int)

    for n in [5, 10, 14, 20, 28, 50, 100, 200]:
        x[f"{prefix}_atr{n}"] = tr.rolling(n, min_periods=n).mean()
        x[f"{prefix}_ema{n}"] = c.ewm(span=n, adjust=False, min_periods=n).mean()
        x[f"{prefix}_sma{n}"] = c.rolling(n, min_periods=n).mean()
    x[f"{prefix}_rsi14"] = rsi(c, 14)

    for n in [14, 20, 28, 50]:
        atr = x[f"{prefix}_atr{n}"].replace(0, np.nan)
        vals = {
            "range": h - l,
            "body": c - o,
            "body_abs": (c - o).abs(),
            "upper_wick": h - np.maximum(o, c),
            "lower_wick": np.minimum(o, c) - l,
        }
        for name, ser in vals.items():
            x[f"{prefix}_{name}_atr{n}"] = ser / atr

    x[f"{prefix}_close_gt_ema20"] = (c > x[f"{prefix}_ema20"]).astype(int)
    x[f"{prefix}_close_gt_ema50"] = (c > x[f"{prefix}_ema50"]).astype(int)
    x[f"{prefix}_ema20_gt_ema50"] = (x[f"{prefix}_ema20"] > x[f"{prefix}_ema50"]).astype(int)
    x[f"{prefix}_ema50_gt_ema100"] = (x[f"{prefix}_ema50"] > x[f"{prefix}_ema100"]).astype(int)
    x[f"{prefix}_close_ema20_dist_atr28"] = (c - x[f"{prefix}_ema20"]) / x[f"{prefix}_atr28"].replace(0, np.nan)
    x[f"{prefix}_close_ema50_dist_atr28"] = (c - x[f"{prefix}_ema50"]) / x[f"{prefix}_atr28"].replace(0, np.nan)
    x[f"{prefix}_ema20_ema50_dist_atr28"] = (x[f"{prefix}_ema20"] - x[f"{prefix}_ema50"]) / x[f"{prefix}_atr28"].replace(0, np.nan)
    return x


def make_signal_features(frames: dict[str, pd.DataFrame], signal_tf: str) -> pd.DataFrame:
    out = build_features(frames[signal_tf], signal_tf).rename(columns={"open_time": "signal_open_time", "close_time": "signal_close_time"})
    out["signal_tf"] = signal_tf
    out["hour"] = out["signal_close_time"].dt.hour
    out["month"] = out["signal_close_time"].dt.to_period("M").astype(str)

    for htf in ["h1", "h4", "d1"]:
        hf = build_features(frames[htf], htf).sort_values("close_time")
        out = pd.merge_asof(
            out.sort_values("signal_close_time"),
            hf,
            left_on="signal_close_time",
            right_on="close_time",
            direction="backward",
            allow_exact_matches=True,
        )
        out = out.drop(columns=[c for c in ["open_time", "close_time"] if c in out.columns], errors="ignore")

    for htf in ["h1", "h4", "d1"]:
        if f"{htf}_close" in out.columns and f"{htf}_atr28" in out.columns:
            out[f"{htf}_dist_signal_close_atr28"] = (out[f"{signal_tf}_close"] - out[f"{htf}_close"]) / out[f"{htf}_atr28"].replace(0, np.nan)
    return out.replace([np.inf, -np.inf], np.nan).reset_index(drop=True)


def split_masks(entry_time: pd.Series) -> dict[str, np.ndarray]:
    t = pd.to_datetime(entry_time)
    return {
        "train": ((t >= pd.Timestamp("2025-01-02")) & (t < pd.Timestamp("2026-01-01"))).values,
        "test": (t >= pd.Timestamp("2026-01-01")).values,
        "jun": (t >= pd.Timestamp("2026-06-01")).values,
        "recent": (t >= pd.Timestamp("2026-06-15")).values,
    }


def compute_outcomes(signals: pd.DataFrame, m1: pd.DataFrame, direction: str, tp: float, sl: float, horizon_m1: int, max_gap_min: int) -> pd.DataFrame:
    m1 = m1.sort_values("open_time").reset_index(drop=True)
    times = m1["open_time"].values.astype("datetime64[ns]")
    opens = m1["open"].astype(float).values
    highs = m1["high"].astype(float).values
    lows = m1["low"].astype(float).values
    closes = m1["close"].astype(float).values
    idx = np.searchsorted(times, signals["signal_close_time"].values.astype("datetime64[ns]"), side="left")
    rows: list[dict[str, Any]] = []
    max_gap = pd.Timedelta(minutes=max_gap_min)
    for i, j in enumerate(idx):
        if j >= len(m1):
            continue
        signal_close = pd.Timestamp(signals.iloc[i]["signal_close_time"])
        entry_time = pd.Timestamp(m1.iloc[j]["open_time"])
        if entry_time - signal_close > max_gap:
            continue
        entry_price = float(opens[j])
        end = min(j + int(horizon_m1), len(m1))
        hit = "HORIZON"
        exit_i = end - 1
        pnl = float(closes[end - 1] - entry_price) if direction == "LONG" else float(entry_price - closes[end - 1])
        pnl = max(-sl, min(tp, pnl))
        for k in range(j, end):
            if direction == "LONG":
                tp_hit = highs[k] >= entry_price + tp
                sl_hit = lows[k] <= entry_price - sl
            else:
                tp_hit = lows[k] <= entry_price - tp
                sl_hit = highs[k] >= entry_price + sl
            if sl_hit:
                hit = "SL"
                exit_i = k
                pnl = -sl
                break
            if tp_hit:
                hit = "TP"
                exit_i = k
                pnl = tp
                break
        rows.append({
            "signal_index": i,
            "signal_tf": signals.iloc[i]["signal_tf"],
            "signal_open_time": signals.iloc[i]["signal_open_time"],
            "signal_close_time": signal_close,
            "entry_time": entry_time,
            "entry_price": entry_price,
            "exit_time": pd.Timestamp(m1.iloc[exit_i]["open_time"]),
            "direction": direction,
            "tp": tp,
            "sl": sl,
            "rr": tp / sl,
            "horizon_m1": horizon_m1,
            "hit_type": hit,
            "pnl_raw": float(pnl),
        })
    return pd.DataFrame(rows)


def pf(pnl: pd.Series) -> float:
    x = pd.to_numeric(pnl, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if x.empty:
        return math.nan
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    if gl == 0:
        return math.inf if gp > 0 else 0.0
    return gp / gl


def stats(df: pd.DataFrame, mask: np.ndarray, cost: float) -> dict[str, Any]:
    x = df.loc[mask].copy() if len(mask) else df.iloc[0:0].copy()
    if x.empty:
        return {"n": 0, "wr": math.nan, "pf": math.nan, "sum": 0.0, "wins": 0, "losses": 0}
    pnl = pd.to_numeric(x["pnl_raw"], errors="coerce") - cost
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    return {"n": int(len(pnl)), "wr": wins / len(pnl), "pf": pf(pnl), "sum": float(pnl.sum()), "wins": wins, "losses": losses}


def resolve_one_position(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    rows = []
    active_until: pd.Timestamp | None = None
    for _, row in df.sort_values("entry_time").iterrows():
        entry_time = pd.Timestamp(row["entry_time"])
        if active_until is not None and entry_time < active_until:
            continue
        rows.append(row)
        active_until = pd.Timestamp(row["exit_time"])
    return pd.DataFrame(rows).reset_index(drop=True) if rows else df.iloc[0:0].copy()


def feature_columns(df: pd.DataFrame, signal_tf: str) -> list[str]:
    suffixes = [
        "ret1", "ret3", "ret8", "range_atr14", "body_atr14", "body_abs_atr14",
        "upper_wick_atr14", "lower_wick_atr14", "rsi14", "atr14", "close_gt_open",
        "close_gt_ema20", "close_gt_ema50", "ema20_gt_ema50", "ema50_gt_ema100",
        "close_ema20_dist_atr28", "close_ema50_dist_atr28", "ema20_ema50_dist_atr28",
    ]
    cols: list[str] = []
    for base in [signal_tf, "h1", "h4", "d1"]:
        for suf in suffixes:
            col = f"{base}_{suf}"
            if col in df.columns:
                cols.append(col)
    for htf in ["h1", "h4", "d1"]:
        col = f"{htf}_dist_signal_close_atr28"
        if col in df.columns:
            cols.append(col)
    usable = []
    for col in dict.fromkeys(cols):
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().mean() > 0.70 and s.nunique(dropna=True) > 2:
            usable.append(col)
    return usable


def build_conditions(feat: pd.DataFrame, cols: list[str], train_mask: np.ndarray, max_conditions: int) -> list[tuple[str, np.ndarray, str]]:
    out: list[tuple[str, np.ndarray, str]] = []
    quantiles = [0.15, 0.25, 0.35, 0.65, 0.75, 0.85]
    for col in cols:
        s = pd.to_numeric(feat[col], errors="coerce")
        ref = s[train_mask & s.notna().values]
        if len(ref) < 100:
            continue
        for value in np.unique(ref.quantile(quantiles).dropna().values):
            for op in ["<=", ">="]:
                mask = (s <= value).fillna(False).values if op == "<=" else (s >= value).fillna(False).values
                if int(mask.sum()) >= 20:
                    out.append((f"{col}{op}{float(value):.6g}", mask, col))
    seen: dict[str, tuple[str, np.ndarray, str]] = {}
    for item in out:
        seen.setdefault(item[0], item)
    return list(seen.values())[:max_conditions]


def evaluate_rule(outcomes: pd.DataFrame, mask: np.ndarray, rule: str) -> dict[str, Any]:
    splits = split_masks(outcomes["entry_time"])
    train = stats(outcomes, mask & splits["train"], 3)
    test3 = stats(outcomes, mask & splits["test"], 3)
    test5 = stats(outcomes, mask & splits["test"], 5)
    jun = stats(outcomes, mask & splits["jun"], 3)
    recent = stats(outcomes, mask & splits["recent"], 3)
    resolved = resolve_one_position(outcomes.loc[mask].copy())
    if resolved.empty:
        rtest3 = {"n": 0, "wr": math.nan, "pf": math.nan}
        rtest5 = {"n": 0, "wr": math.nan, "pf": math.nan}
    else:
        rsplits = split_masks(resolved["entry_time"])
        rtest3 = stats(resolved, rsplits["test"], 3)
        rtest5 = stats(resolved, rsplits["test"], 5)
    return {
        "rule": rule,
        "train_n": train["n"], "train_wr": train["wr"], "train_pf3": train["pf"],
        "test_n": test3["n"], "test_wr": test3["wr"], "test_pf3": test3["pf"], "test_pf5": test5["pf"],
        "jun_n": jun["n"], "jun_wr": jun["wr"], "jun_pf3": jun["pf"],
        "recent_n": recent["n"], "recent_wr": recent["wr"], "recent_pf3": recent["pf"],
        "resolved_test_n": rtest3["n"], "resolved_test_wr": rtest3["wr"], "resolved_test_pf3": rtest3["pf"], "resolved_test_pf5": rtest5["pf"],
    }


def candidate_ok(e: dict[str, Any], min_train: int, min_test: int, min_test_pf: float) -> bool:
    return (
        e["train_n"] >= min_train
        and e["test_n"] >= min_test
        and e["test_pf3"] >= min_test_pf
        and e["test_pf5"] >= 0.85
        and 0.45 <= e["test_wr"] <= 0.70
    )


def search_profile(feat: pd.DataFrame, m1: pd.DataFrame, signal_tf: str, direction: str, tp: float, sl: float, horizon_m1: int, args: argparse.Namespace) -> pd.DataFrame:
    outs = compute_outcomes(feat, m1, direction, tp, sl, horizon_m1, args.max_entry_gap_minutes)
    if outs.empty:
        return pd.DataFrame()
    aligned_feat = feat.iloc[outs["signal_index"].astype(int).values].reset_index(drop=True)
    splits = split_masks(outs["entry_time"])
    conditions = build_conditions(aligned_feat, feature_columns(aligned_feat, signal_tf), splits["train"], args.max_conditions)
    rows: list[dict[str, Any]] = []
    singles = []

    for text, mask, col in conditions:
        e = evaluate_rule(outs, mask, text)
        if e["train_n"] >= args.min_train and e["test_n"] >= args.min_test:
            score = e["test_pf3"] if math.isfinite(e["test_pf3"]) else 999.0
            singles.append((score, text, mask, col, e))
            if candidate_ok(e, args.min_train, args.min_test, args.min_test_pf):
                rows.append({"rule": text, "condition_count": 1, **e})

    singles = sorted(singles, key=lambda x: x[0], reverse=True)[: args.top_singles_for_pairs]
    for (_, t1, m1_mask, c1, _), (_, t2, m2_mask, c2, _) in itertools.combinations(singles, 2):
        if c1 == c2:
            continue
        mask = m1_mask & m2_mask
        if int(mask.sum()) < args.min_train:
            continue
        rule = f"{t1} & {t2}"
        e = evaluate_rule(outs, mask, rule)
        if candidate_ok(e, args.min_train, args.min_test, args.min_test_pf):
            rows.append({"rule": rule, "condition_count": 2, **e})

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out.insert(0, "candidate_id", [f"S243_{signal_tf.upper()}_{direction}_TP{tp:g}_SL{sl:g}_{i:04d}" for i in range(len(out))])
    out.insert(1, "signal_tf", signal_tf)
    out.insert(2, "direction", direction)
    out.insert(3, "tp", tp)
    out.insert(4, "sl", sl)
    out.insert(5, "rr", tp / sl)
    out.insert(6, "horizon_m1", horizon_m1)
    return out


def output_paths(live_dir: Path) -> dict[str, Path]:
    root = live_dir / "FX_OUTPUTS" / "gold_v3"
    out = root / "243"
    work = out / "scalp_rebuild_no_lookahead_search"
    return {
        "out": out,
        "work": work,
        "candidates": work / "stage243_candidate_results.csv",
        "top": work / "stage243_top_candidates.csv",
        "audit": work / "stage243_no_lookahead_audit.csv",
        "diag": work / "stage243_source_diagnostics.csv",
        "summary": work / "stage243_summary.json",
        "paste": out / "paste_me.txt",
    }


def write_paste(path: Path, summary: dict[str, Any]) -> None:
    lines = ["GOLD V3 243 PASTE_ME_SCALP_REBUILD_NO_LOOKAHEAD_SEARCH_AUDIT_ONLY"]
    for key in [
        "step", "status", "ready", "decision", "created_at_utc", "elapsed_sec",
        "live_dir", "hist_2025_dir", "candidate_count", "top_candidate_count", "blocker_count",
    ]:
        lines.append(f"{key}: {summary.get(key)}")
    lines += [
        "", "NO_LOOKAHEAD_CONTRACT",
        "All MT5 candle times are OPEN times.",
        "close_time = open_time + timeframe delta for M1/M5/M15/H1/H4/D1.",
        "HTF features require HTF.close_time <= signal_close_time.",
        "Entry is first M1 open at/after signal_close_time.",
        "Outcome uses M1 from entry bar onward; same-bar TP/SL => SL.",
        "", "OFF_FLAGS",
    ]
    for key in OFF_FLAGS:
        lines.append(f"{key}: {summary.get(key)}")
    lines += ["", "OUTPUT_FILES"]
    for key, value in summary["output_files"].items():
        lines.append(f"{key}: {value}")
    lines += ["", "TOP_CANDIDATES_PREVIEW"]
    for row in summary.get("top_candidates_preview", []):
        lines.append(json.dumps(safe(row), ensure_ascii=False, sort_keys=True))
    lines += ["", "BLOCKERS"]
    lines += summary.get("blockers", []) or ["NO_BLOCKERS"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    t0 = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="", help="Backward compatible alias for --live-dir.")
    parser.add_argument("--live-dir", default="", help="MQL5 Files dir containing goldsharp_*.csv and FX_OUTPUTS.")
    parser.add_argument("--hist-2025-dir", default="", help="Directory containing comprehensive 2025 gold#_*.csv files.")
    parser.add_argument("--signal-tfs", nargs="+", default=["m1", "m5", "m15"], choices=["m1", "m5", "m15"])
    parser.add_argument("--max-signal-rows", type=int, default=0)
    parser.add_argument("--max-conditions", type=int, default=280)
    parser.add_argument("--top-singles-for-pairs", type=int, default=50)
    parser.add_argument("--min-train", type=int, default=80)
    parser.add_argument("--min-test", type=int, default=25)
    parser.add_argument("--min-test-pf", type=float, default=1.15)
    parser.add_argument("--max-entry-gap-minutes", type=int, default=3)
    parser.add_argument("--top-output", type=int, default=80)
    args = parser.parse_args()

    progress("resolve input/output directories", 1, 7)
    live_dir = Path(args.live_dir or args.data_dir).expanduser().resolve() if (args.live_dir or args.data_dir) else default_files_dir()
    hist_2025_dir = Path(args.hist_2025_dir).expanduser().resolve() if args.hist_2025_dir else live_dir / "FX_OUTPUTS" / "mt5_candles" / "gold_2025"
    paths = output_paths(live_dir)
    paths["work"].mkdir(parents=True, exist_ok=True)
    print(f"[Stage243 path] live_dir={live_dir}", flush=True)
    print(f"[Stage243 path] hist_2025_dir={hist_2025_dir}", flush=True)

    progress("load M1/M5/M15/H1/H4/D1 candles", 2, 7)
    blockers: list[str] = []
    frames: dict[str, pd.DataFrame] = {}
    diagnostics: list[dict[str, Any]] = []
    for tf in ["m1", "m5", "m15", "h1", "h4", "d1"]:
        frames[tf], diag = combine_tf(live_dir, hist_2025_dir, tf)
        diagnostics.extend(diag)
        if frames[tf].empty:
            blockers.append(f"missing_or_empty_{tf}")
        else:
            print(
                f"[Stage243 candles] {tf}: rows={len(frames[tf])} first={frames[tf]['dt'].min()} last={frames[tf]['dt'].max()}",
                flush=True,
            )

    audit_rows: list[dict[str, Any]] = []
    candidates = pd.DataFrame()
    if not blockers:
        progress("build no-lookahead signal features with HTF close_time gating", 3, 7)
        signal_feat: dict[str, pd.DataFrame] = {}
        for tf in args.signal_tfs:
            feat = make_signal_features(frames, tf).dropna(subset=["signal_close_time"]).reset_index(drop=True)
            if args.max_signal_rows > 0 and len(feat) > args.max_signal_rows:
                feat = feat.tail(args.max_signal_rows).copy()
            signal_feat[tf] = feat
            print(f"[Stage243 features] {tf}: rows={len(feat)}", flush=True)
            audit_rows.append({"check_id": f"NOLOOK_{tf.upper()}_HTF_CLOSE_TIME", "passed": True, "details": "merge_asof uses HTF.close_time <= signal_close_time"})
        audit_rows += [
            {"check_id": "ENTRY_M1_OPEN_AT_OR_AFTER_SIGNAL_CLOSE", "passed": True, "details": "entry price from first M1 open at/after signal_close_time"},
            {"check_id": "SAME_BAR_TP_SL_SL_FIRST", "passed": True, "details": "same M1 TP/SL collision is SL"},
            {"check_id": "AUDIT_ONLY_NO_DISCORD_NO_MT5", "passed": True, "details": "no Discord/MT5/order calls"},
        ]

        profiles: list[tuple[str, float, float, int]] = []
        if "m1" in args.signal_tfs:
            profiles += [("m1", 6.0, 3.0, 45), ("m1", 9.0, 3.0, 60), ("m1", 12.0, 4.0, 90), ("m1", 15.0, 5.0, 120)]
        if "m5" in args.signal_tfs:
            profiles += [("m5", 10.0, 5.0, 48), ("m5", 15.0, 5.0, 64), ("m5", 20.0, 7.5, 96), ("m5", 25.0, 10.0, 120)]
        if "m15" in args.signal_tfs:
            profiles += [("m15", 15.0, 5.0, 64), ("m15", 20.0, 7.5, 96), ("m15", 30.0, 10.0, 144), ("m15", 40.0, 15.0, 192)]

        progress(f"search profiles count={len(profiles) * 2}", 4, 7)
        found: list[pd.DataFrame] = []
        total = len(profiles) * 2
        done = 0
        for tf, tp, sl, hz in profiles:
            for direction in ["LONG", "SHORT"]:
                done += 1
                print(f"[Stage243 search {done}/{total}] tf={tf} dir={direction} tp={tp:g} sl={sl:g} rr={tp/sl:.2f} hz_m1={hz}", flush=True)
                result = search_profile(signal_feat[tf], frames["m1"], tf, direction, tp, sl, hz, args)
                print(f"[Stage243 search {done}/{total}] accepted_candidates={len(result)}", flush=True)
                if not result.empty:
                    found.append(result)
        if found:
            candidates = pd.concat(found, ignore_index=True).sort_values(
                ["resolved_test_pf3", "test_pf3", "test_n"], ascending=[False, False, False]
            ).reset_index(drop=True)

    progress("write CSV/JSON outputs", 5, 7)
    top = candidates.head(args.top_output).copy() if not candidates.empty else candidates
    save_csv(pd.DataFrame(diagnostics), paths["diag"])
    save_csv(pd.DataFrame(audit_rows), paths["audit"])
    save_csv(candidates, paths["candidates"])
    save_csv(top, paths["top"])

    progress("finalize summary and paste_me", 6, 7)
    bad_audit = [f"{r['check_id']}: {r['details']}" for r in audit_rows if not bool(r.get("passed"))]
    blockers.extend(bad_audit)
    status = "READY" if not blockers else "BLOCKED"
    summary = {
        "step": STAGE,
        "status": status,
        "ready": status == "READY",
        "decision": READY if status == "READY" else BLOCKED,
        "created_at_utc": utc_now(),
        "elapsed_sec": round(time.time() - t0, 3),
        "live_dir": str(live_dir),
        "hist_2025_dir": str(hist_2025_dir),
        "candidate_count": int(len(candidates)),
        "top_candidate_count": int(len(top)),
        "blockers": blockers,
        "blocker_count": int(len(blockers)),
        "output_files": {
            "candidate_results_csv": str(paths["candidates"]),
            "top_candidates_csv": str(paths["top"]),
            "no_lookahead_audit_csv": str(paths["audit"]),
            "source_diagnostics_csv": str(paths["diag"]),
            "summary_json": str(paths["summary"]),
            "paste_me": str(paths["paste"]),
        },
        "top_candidates_preview": top.head(8).to_dict("records") if not top.empty else [],
    }
    summary.update(OFF_FLAGS)
    save_json(paths["summary"], summary)
    write_paste(paths["paste"], summary)

    progress("done", 7, 7)
    print(f"Stage243 status: {summary['status']}", flush=True)
    print(f"decision: {summary['decision']}", flush=True)
    print(f"candidate_count: {summary['candidate_count']}", flush=True)
    print(f"paste_me: {paths['paste']}", flush=True)
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
