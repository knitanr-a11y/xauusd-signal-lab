from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from stage55_shadow_features import COST, exact_m1_index

FEATURES = [
    "distance_entry_atr", "setup_atr", "cost_r", "close_from_entry_r", "max_fav_r", "max_adv_r",
    "distance_remaining_r", "confirmed_so_far", "signal_count_7d", "m5_close_ema20_r", "m5_body_atr",
    "m5_close_pos", "m5_slope", "m5_adx", "m5_eff", "m5_ret3", "m5_ret6", "m5_range5",
    "m15_close_ema20_r", "m15_body_atr", "m15_close_pos", "m15_slope", "m15_adx", "m15_eff",
    "h4_close_ema20_r", "h4_slope", "h4_adx", "h4_eff",
]

def frozen_model_score(feature_row: dict[str, Any], artifact: dict[str, Any]) -> float:
    x = np.array([float(feature_row[name]) for name in artifact["features"]], dtype=float)
    med = np.asarray(artifact["imputer_median"], dtype=float)
    mean = np.asarray(artifact["scaler_mean"], dtype=float)
    scale = np.asarray(artifact["scaler_scale"], dtype=float)
    coef = np.asarray(artifact["coef"], dtype=float)
    x = np.where(np.isfinite(x), x, med)
    scale = np.where(scale == 0, 1.0, scale)
    z = float(np.dot((x - mean) / scale, coef) + float(artifact["intercept"]))
    return float(1.0 / (1.0 + math.exp(-max(min(z, 700.0), -700.0))))


def checkpoint_features(tr: pd.Series, checkpoint: pd.Timestamp, source_ledger: pd.DataFrame,
                        m5: pd.DataFrame, m15: pd.DataFrame, h4: pd.DataFrame) -> dict[str, Any] | None:
    m5ct = pd.DatetimeIndex(m5.close_time); m15ct = pd.DatetimeIndex(m15.close_time); h4ct = pd.DatetimeIndex(h4.close_time)
    mi = int(m5ct.searchsorted(checkpoint, side="right") - 1); m15i = int(m15ct.searchsorted(checkpoint, side="right") - 1); h4i = int(h4ct.searchsorted(checkpoint, side="right") - 1)
    if min(mi, m15i, h4i) < 0: return None
    entry_mi = int(m5ct.searchsorted(tr.decision_time, side="right") - 1)
    if entry_mi < 0 or mi < entry_mi: return None
    seg = m5.iloc[entry_mi:mi + 1]; setup_atr = float(tr.setup_atr)
    close = float(m5.close.iloc[mi]); entry = float(tr.entry_price); level = float(tr.breakout_level)
    start_m15 = max(0, int(m15ct.searchsorted(tr.decision_time, side="right")))
    confirmed = bool((m15.iloc[start_m15:m15i + 1].close > level).any())
    di = pd.DatetimeIndex(source_ledger.decision_time)
    prior7 = int(di.searchsorted(tr.decision_time, side="left") - di.searchsorted(tr.decision_time - pd.Timedelta(days=7), side="left"))
    row = {
        "distance_entry_atr": float(tr.distance_to_level_atr), "setup_atr": setup_atr, "cost_r": COST / setup_atr,
        "close_from_entry_r": (close - entry) / setup_atr, "max_fav_r": (float(seg.high.max()) - entry) / setup_atr,
        "max_adv_r": (entry - float(seg.low.min())) / setup_atr, "distance_remaining_r": (level - close) / setup_atr,
        "confirmed_so_far": int(confirmed), "signal_count_7d": prior7,
        "m5_close_ema20_r": (close - float(m5.ema20.iloc[mi])) / float(m5.atr14.iloc[mi]),
        "m5_body_atr": float(m5.body_atr.iloc[mi]), "m5_close_pos": float(m5.close_pos.iloc[mi]), "m5_slope": float(m5.slope.iloc[mi]),
        "m5_adx": float(m5.adx14.iloc[mi]), "m5_eff": float(m5.eff20.iloc[mi]), "m5_ret3": float(m5.ret3_atr.iloc[mi]),
        "m5_ret6": float(m5.ret6_atr.iloc[mi]), "m5_range5": float(m5.range5_atr.iloc[mi]),
        "m15_close_ema20_r": (float(m15.close.iloc[m15i]) - float(m15.ema20.iloc[m15i])) / float(m15.atr14.iloc[m15i]),
        "m15_body_atr": float(m15.body_atr.iloc[m15i]), "m15_close_pos": float(m15.close_pos.iloc[m15i]), "m15_slope": float(m15.slope.iloc[m15i]),
        "m15_adx": float(m15.adx14.iloc[m15i]), "m15_eff": float(m15.eff20.iloc[m15i]),
        "h4_close_ema20_r": (float(h4.close.iloc[h4i]) - float(h4.ema20.iloc[h4i])) / float(h4.atr14.iloc[h4i]),
        "h4_slope": float(h4.slope.iloc[h4i]), "h4_adx": float(h4.adx14.iloc[h4i]), "h4_eff": float(h4.eff20.iloc[h4i]),
    }
    if any(not np.isfinite(v) for v in row.values()): return None
    return row


def find_m1_confirmation(alert: pd.Timestamp, m1: pd.DataFrame) -> tuple[pd.Timestamp, int] | None:
    ct = pd.DatetimeIndex(m1.close_time)
    start = int(ct.searchsorted(alert, side="right")); end = int(ct.searchsorted(alert + pd.Timedelta(minutes=15), side="right"))
    for i in range(start, min(end, len(m1))):
        if pd.notna(m1.ema20.iloc[i]) and m1.close.iloc[i] < m1.ema20.iloc[i] and m1.body_atr.iloc[i] <= -0.10:
            return pd.Timestamp(m1.close_time.iloc[i]), i
    return None


def find_m5_bearish(alert: pd.Timestamp, m5: pd.DataFrame) -> tuple[pd.Timestamp, int] | None:
    ct = pd.DatetimeIndex(m5.close_time)
    start = int(ct.searchsorted(alert, side="right")); end = int(ct.searchsorted(alert + pd.Timedelta(minutes=30), side="right"))
    for i in range(max(1, start), min(end, len(m5))):
        if (m5.close.iloc[i] < m5.open.iloc[i] and m5.close.iloc[i - 1] > m5.open.iloc[i - 1] and
                m5.close.iloc[i] < m5.open.iloc[i - 1] and m5.body_atr.iloc[i] <= -0.10):
            return pd.Timestamp(m5.close_time.iloc[i]), i
    return None


def simulate_short(m1: pd.DataFrame, entry_idx: int, stop: float, max_minutes: int) -> dict[str, Any]:
    entry = float(m1.open.iloc[entry_idx])
    if not np.isfinite(stop) or stop <= entry:
        return {"status": "INVALID", "reason": "INVALID_STOP", "pnl": np.nan, "exit_time": pd.NaT, "exit_price": np.nan}
    risk = stop - entry; target = entry - 2 * risk; latest = len(m1) - 1; intended_end = entry_idx + max_minutes
    scan_end = min(intended_end, latest)
    for j in range(entry_idx, scan_end + 1):
        if m1.high.iloc[j] >= stop:
            return {"status": "CLOSED", "reason": "SL", "pnl": entry - stop - COST, "exit_time": m1.time.iloc[j], "exit_price": stop, "risk": risk}
        if m1.low.iloc[j] <= target:
            return {"status": "CLOSED", "reason": "TP", "pnl": entry - target - COST, "exit_time": m1.time.iloc[j], "exit_price": target, "risk": risk}
    if intended_end <= latest:
        px = float(m1.close.iloc[intended_end])
        return {"status": "CLOSED", "reason": "MAX", "pnl": entry - px - COST, "exit_time": m1.time.iloc[intended_end], "exit_price": px, "risk": risk}
    return {"status": "OPEN", "reason": "OPEN", "pnl": np.nan, "exit_time": pd.NaT, "exit_price": np.nan, "risk": risk}


def build_short_candidates(m1_src: pd.DataFrame, m5_src: pd.DataFrame, model_artifact: dict[str, Any],
                           h4: pd.DataFrame, m15: pd.DataFrame, m5: pd.DataFrame, m1: pd.DataFrame,
                           candidate_after: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for _, tr in m1_src.iterrows():
        if pd.Timestamp(tr.decision_time) <= candidate_after: continue
        checkpoint = pd.Timestamp(tr.decision_time) + pd.Timedelta(minutes=30)
        if tr.source_status == "CLOSED" and pd.Timestamp(tr.source_exit_time) <= checkpoint: continue
        if checkpoint > m1.close_time.iloc[-1]: continue
        feat = checkpoint_features(tr, checkpoint, m1_src, m5, m15, h4)
        if feat is None: continue
        score = frozen_model_score(feat, model_artifact); threshold = float(model_artifact["threshold"])
        if score < threshold: continue
        conf = find_m1_confirmation(checkpoint, m1)
        if conf is None: continue
        ctime, _ = conf; ei = exact_m1_index(m1, ctime)
        if ei < 0: continue
        m5ct = pd.DatetimeIndex(m5.close_time); mi = int(m5ct.searchsorted(ctime, side="right") - 1)
        recent = m5.iloc[max(0, mi - 4):mi + 1]; stop = float(recent.high.max() + 0.10 * m5.atr14.iloc[mi])
        rows.append({"family": "M1_FALSE_LONG_REVERSAL_SHORT", "source_decision_time": tr.decision_time, "alert_time": checkpoint,
                     "confirmation_time": ctime, "entry_time": m1.time.iloc[ei], "entry_idx": ei, "entry_price": float(m1.open.iloc[ei]),
                     "stop_price": stop, "max_minutes": 240, "detector_score": score, "detector_threshold": threshold,
                     "detector_train_n": int(model_artifact["train_n"]), "candidate_key": f"M1|{pd.Timestamp(tr.decision_time).isoformat()}"})
    m5ct = pd.DatetimeIndex(m5.close_time)
    for _, tr in m5_src.iterrows():
        if pd.Timestamp(tr.decision_time) <= candidate_after: continue
        alert = None; entry_mi = int(m5ct.searchsorted(tr.decision_time, side="right") - 1)
        for cp in (15, 30):
            checkpoint = pd.Timestamp(tr.decision_time) + pd.Timedelta(minutes=cp)
            if tr.source_status == "CLOSED" and pd.Timestamp(tr.source_exit_time) <= checkpoint: continue
            mi = int(m5ct.searchsorted(checkpoint, side="right") - 1)
            if mi < entry_mi or checkpoint > m5.close_time.iloc[-1]: continue
            seg = m5.iloc[entry_mi:mi + 1]; reached = float(seg.high.max()) >= float(tr.breakout_level) - 0.05 * float(tr.setup_atr)
            if reached and m5.close.iloc[mi] <= float(tr.breakout_level) - 0.10 * float(tr.setup_atr) and m5.body_atr.iloc[mi] < 0:
                alert = checkpoint; break
        if alert is None: continue
        conf = find_m5_bearish(alert, m5)
        if conf is None: continue
        ctime, cmi = conf; ei = exact_m1_index(m1, ctime)
        if ei < 0: continue
        seg = m5.iloc[entry_mi:cmi + 1]; stop = float(seg.high.max() + 0.10 * m5.atr14.iloc[cmi])
        rows.append({"family": "M5_LEVEL_REJECTION_REVERSAL_SHORT", "source_decision_time": tr.decision_time, "alert_time": alert,
                     "confirmation_time": ctime, "entry_time": m1.time.iloc[ei], "entry_idx": ei, "entry_price": float(m1.open.iloc[ei]),
                     "stop_price": stop, "max_minutes": 480, "detector_score": np.nan, "detector_threshold": np.nan,
                     "detector_train_n": 0, "candidate_key": f"M5|{pd.Timestamp(tr.decision_time).isoformat()}"})
    out = pd.DataFrame(rows)
    if out.empty: return out
    kept = []
    for family, group in out.groupby("family"):
        blocked = pd.Timestamp.min
        for _, row in group.sort_values("entry_time").iterrows():
            if pd.Timestamp(row.entry_time) <= blocked: continue
            sim = simulate_short(m1, int(row.entry_idx), float(row.stop_price), int(row.max_minutes))
            rec = row.to_dict(); rec.update(sim); kept.append(rec)
            blocked = pd.Timestamp(sim["exit_time"]) if sim["status"] == "CLOSED" else pd.Timestamp.max
    return pd.DataFrame(kept).sort_values(["entry_time", "family"]).reset_index(drop=True)
