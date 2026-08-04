from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd

DELTAS={'M15':pd.Timedelta(minutes=15),'H1':pd.Timedelta(hours=1),'H4':pd.Timedelta(hours=4)}
SCALES=[('M15_K080','M15',0.80,0.18),('M15_K140','M15',1.40,0.14),('H1_K080','H1',0.80,0.20),('H1_K140','H1',1.40,0.20),('H4_K060','H4',0.60,0.14),('H4_K100','H4',1.00,0.14)]
STATE_COLS=['trend','impulse_early','impulse_mid','impulse_late','correction_early','correction_mid','correction_late','reversal_risk','unknown','cycle_favorable','cycle_top_risk','structure_confidence']
def atr14(d: pd.DataFrame) -> np.ndarray:
    prev = d['close'].shift(1)
    tr = pd.concat([(d.high-d.low), (d.high-prev).abs(), (d.low-prev).abs()], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=14).mean().to_numpy(float)


def clip01(x: float) -> float:
    if not np.isfinite(x): return 0.0
    return float(min(1.0, max(0.0, x)))


def trap(x: float, a: float, b: float, c: float, d: float) -> float:
    if not np.isfinite(x) or x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return clip01((x-a)/(b-a)) if b>a else 1.0
    return clip01((d-x)/(d-c)) if d>c else 1.0


def stage_scores(progress: float, kind: str) -> tuple[float,float,float]:
    if kind == 'impulse':
        return (
            trap(progress, -0.05, 0.05, 0.50, 0.85),
            trap(progress, 0.45, 0.80, 1.40, 2.00),
            clip01((progress-1.35)/1.25),
        )
    return (
        trap(progress, -0.05, 0.05, 0.30, 0.55),
        trap(progress, 0.30, 0.55, 0.85, 1.15),
        trap(progress, 0.75, 1.00, 1.75, 2.80),
    )


@dataclass
class Pivot:
    idx: int
    price: float
    typ: int  # +1 high, -1 low
    confirm_idx: int


def transformed_grammar(pivots: list[Pivot], price: float, idx: int, side: int, atr: float) -> dict[str,float]:
    z = {k: 0.0 for k in STATE_COLS}
    if len(pivots) < 3 or not np.isfinite(atr) or atr <= 0:
        z['unknown'] = 1.0
        return z
    pp = pivots[-12:]
    q = np.array([side*p.price for p in pp], dtype=float)
    ty = np.array([side*p.typ for p in pp], dtype=int)
    ix = np.array([p.idx for p in pp], dtype=int)
    cur = side*price

    # Generic trend score from path efficiency plus higher-high/higher-low structure.
    if len(q) >= 5:
        variation = np.abs(np.diff(q[-5:])).sum()
        eff = (q[-1]-q[-5]) / variation if variation > 1e-12 else 0.0
        eff_score = clip01((eff+0.05)/0.55)
    else:
        eff_score = 0.0
    highs = q[ty == 1]
    lows = q[ty == -1]
    hh = 0.5
    hl = 0.5
    if len(highs) >= 2: hh = 1.0 if highs[-1] > highs[-2] else 0.0
    if len(lows) >= 2: hl = 1.0 if lows[-1] > lows[-2] else 0.0
    structural_trend = 0.5*(hh+hl)
    trend = clip01(0.55*eff_score + 0.45*structural_trend)
    z['trend'] = trend

    last = q[-1]
    current_dir = int(np.sign(cur-last))
    completed_moves = np.diff(q)
    completed_durs = np.diff(ix)

    # Typical completed legs in the transformed positive and negative directions.
    pos = completed_moves > 0
    neg = completed_moves < 0
    typ_up_move = np.median(completed_moves[pos][-4:]) if pos.any() else np.nan
    typ_dn_move = np.median(-completed_moves[neg][-4:]) if neg.any() else np.nan
    typ_up_dur = np.median(completed_durs[pos][-4:]) if pos.any() else np.nan
    typ_dn_dur = np.median(completed_durs[neg][-4:]) if neg.any() else np.nan
    cur_move = abs(cur-last)
    cur_dur = max(1, idx-ix[-1])

    # Generic impulse/correction memberships.
    if current_dir > 0 and np.isfinite(typ_up_move) and typ_up_move > 0:
        move_ratio = cur_move/typ_up_move
        dur_ratio = cur_dur/typ_up_dur if np.isfinite(typ_up_dur) and typ_up_dur>0 else move_ratio
        prog = 0.75*move_ratio + 0.25*dur_ratio
        e,m,l = stage_scores(prog, 'impulse')
        base = trend
        z['impulse_early'] = max(z['impulse_early'], base*e)
        z['impulse_mid'] = max(z['impulse_mid'], base*m)
        z['impulse_late'] = max(z['impulse_late'], base*l)
    elif current_dir < 0:
        prior_impulse = completed_moves[-1] if len(completed_moves) and completed_moves[-1] > 0 else typ_up_move
        if np.isfinite(prior_impulse) and prior_impulse > 0:
            retr = cur_move/prior_impulse
            dur_ratio = cur_dur/typ_dn_dur if np.isfinite(typ_dn_dur) and typ_dn_dur>0 else retr
            prog = 0.80*retr + 0.20*dur_ratio
            e,m,l = stage_scores(prog, 'correction')
            base = trend
            z['correction_early'] = max(z['correction_early'], base*e)
            z['correction_mid'] = max(z['correction_mid'], base*m)
            z['correction_late'] = max(z['correction_late'], base*l)
            z['reversal_risk'] = max(z['reversal_risk'], trend*clip01((retr-0.80)/0.55))

    w3_struct = 0.0
    w5_struct = 0.0
    c_struct = 0.0

    # Fuzzy wave-3 candidate: low-high-higher-low-current advance.
    if len(q) >= 3 and tuple(ty[-3:]) == (-1,1,-1) and current_dir > 0:
        p0,p1,p2 = q[-3:]
        w1 = p1-p0
        if w1 > 0:
            retr2 = (p1-p2)/w1
            no_invalidation = trap((p2-p0)/max(w1,1e-9), -0.02, 0.00, 0.80, 3.0)
            retr_fit = trap(retr2, 0.08, 0.25, 0.80, 0.98)
            w3_struct = math.sqrt(max(0.0, no_invalidation*retr_fit))
            progress = (cur-p2)/w1
            e,m,l = stage_scores(progress, 'impulse')
            z['impulse_early'] = max(z['impulse_early'], w3_struct*e)
            z['impulse_mid'] = max(z['impulse_mid'], w3_struct*m)
            z['impulse_late'] = max(z['impulse_late'], w3_struct*l)

    # Fuzzy wave-5 candidate: low-high-higher-low-higher-high-higher-low-current advance.
    if len(q) >= 5 and tuple(ty[-5:]) == (-1,1,-1,1,-1) and current_dir > 0:
        p0,p1,p2,p3,p4 = q[-5:]
        w1 = p1-p0; w3 = p3-p2
        if w1 > 0 and w3 > 0:
            retr2 = (p1-p2)/w1
            ext3 = w3/w1
            retr4 = (p3-p4)/w3
            structure = [
                1.0 if p2>p0 else 0.0,
                1.0 if p3>p1 else 0.0,
                1.0 if p4>p2 else 0.0,
                trap(retr2,0.08,0.25,0.80,0.98),
                trap(ext3,0.60,0.90,2.80,4.50),
                trap(retr4,0.03,0.12,0.58,0.85),
            ]
            w5_struct = float(np.mean(structure))
            progress = (cur-p4)/max(np.median([w1,w3]),1e-9)
            e,m,l = stage_scores(progress, 'impulse')
            # Fifth-wave status is deliberately down-weighted for new entries.
            z['impulse_early'] = max(z['impulse_early'], 0.55*w5_struct*e)
            z['impulse_mid'] = max(z['impulse_mid'], 0.65*w5_struct*m)
            z['impulse_late'] = max(z['impulse_late'], w5_struct*l)

    # Fuzzy ABC correction: high-low-retracement-high-current C decline.
    if len(q) >= 3 and tuple(ty[-3:]) == (1,-1,1) and current_dir < 0:
        p0,p1,p2 = q[-3:]
        A = p0-p1
        if A > 0:
            B = (p2-p1)/A
            C = (p2-cur)/A
            bfit = trap(B,0.10,0.25,0.85,1.10)
            c_struct = bfit
            e,m,l = stage_scores(C, 'correction')
            z['correction_early'] = max(z['correction_early'], trend*c_struct*e)
            z['correction_mid'] = max(z['correction_mid'], trend*c_struct*m)
            z['correction_late'] = max(z['correction_late'], trend*c_struct*l)
            z['reversal_risk'] = max(z['reversal_risk'], trend*c_struct*clip01((C-1.15)/0.85))

    z['structure_confidence'] = max(trend, w3_struct, w5_struct, c_struct)

    # Cycle estimate from past transformed trough-to-trough spacing, not future extrema.
    low_idx = ix[ty == -1]
    if len(low_idx) >= 3:
        periods = np.diff(low_idx)
        period = float(np.median(periods[-4:]))
        if period > 0:
            phase = (idx-low_idx[-1])/period
            if current_dir >= 0:
                z['cycle_favorable'] = trap(phase,-0.05,0.02,0.48,0.78)
            else:
                z['cycle_favorable'] = trap(phase,0.62,0.82,1.16,1.42)
            z['cycle_top_risk'] = trap(phase,0.35,0.50,0.72,0.95)

    best = max(z['impulse_early'],z['impulse_mid'],z['impulse_late'],
               z['correction_early'],z['correction_mid'],z['correction_late'])
    z['unknown'] = clip01(1.0 - 0.70*best - 0.30*z['structure_confidence'])
    return z


def build_scale_features(d: pd.DataFrame, tf: str, k: float, name: str, target_times: pd.DatetimeIndex) -> pd.DataFrame:
    """Build causal pivot stream on all bars, but score only requested signal times."""
    atr = atr14(d)
    close = d.close.to_numpy(float)
    n = len(d)
    closed = (d.time + DELTAS[tf]).to_numpy('datetime64[ns]')
    tt = pd.DatetimeIndex(target_times).to_numpy('datetime64[ns]')
    target_idx = np.searchsorted(closed, tt, side='right') - 1
    index_to_pos: dict[int, list[int]] = {}
    for pos, ix0 in enumerate(target_idx):
        if ix0 >= 0:
            index_to_pos.setdefault(int(ix0), []).append(pos)
    out = {'entry_time': pd.DatetimeIndex(target_times)}
    for side_name in ['long','short']:
        for c in STATE_COLS:
            out[f'{name}_{side_name}_{c}'] = np.full(len(tt), np.nan, dtype=np.float32)
    pivots: list[Pivot] = []
    direction = 0
    hi = lo = np.nan
    hi_idx = lo_idx = -1
    last_needed = max(index_to_pos) if index_to_pos else -1
    for i in range(min(n, last_needed+1)):
        p = close[i]
        a = atr[i]
        if not np.isfinite(p) or not np.isfinite(a) or a <= 0:
            continue
        threshold = k*a
        if not np.isfinite(hi):
            hi=lo=p; hi_idx=lo_idx=i
        if direction == 0:
            if p > hi: hi=p; hi_idx=i
            if p < lo: lo=p; lo_idx=i
            up = p-lo >= threshold
            dn = hi-p >= threshold
            if up and not dn:
                pivots.append(Pivot(lo_idx,lo,-1,i)); direction=1; hi=p; hi_idx=i
            elif dn and not up:
                pivots.append(Pivot(hi_idx,hi,1,i)); direction=-1; lo=p; lo_idx=i
        elif direction == 1:
            if p >= hi:
                hi=p; hi_idx=i
            elif hi-p >= threshold:
                pivots.append(Pivot(hi_idx,hi,1,i)); direction=-1; lo=p; lo_idx=i
        else:
            if p <= lo:
                lo=p; lo_idx=i
            elif p-lo >= threshold:
                pivots.append(Pivot(lo_idx,lo,-1,i)); direction=1; hi=p; hi_idx=i
        if len(pivots)>40:
            pivots=pivots[-40:]
        if i in index_to_pos:
            for side,side_name in [(1,'long'),(-1,'short')]:
                z=transformed_grammar(pivots,p,i,side,a)
                for pos in index_to_pos[i]:
                    for c,v in z.items():
                        out[f'{name}_{side_name}_{c}'][pos]=v
    return pd.DataFrame(out)

def build_wave_ledger(router_ledger: pd.DataFrame, data_by_tf: dict[str,pd.DataFrame], omit_scale: str | None=None) -> pd.DataFrame:
    sig=router_ledger.copy().sort_values(['entry_time','origin_id']).reset_index(drop=True)
    target=pd.DatetimeIndex(sig.entry_time)
    active=[s for s in SCALES if s[0]!=omit_scale]
    for name,tf,k,w in active:
        sf=build_scale_features(data_by_tf[tf],tf,k,name,target)
        sig=sig.merge(sf,on='entry_time',how='left',validate='one_to_one')
    for c in STATE_COLS:
        vals=[];weights=[]
        for name,tf,k,w in active:
            lv=sig[f'{name}_long_{c}'].to_numpy(float);sv=sig[f'{name}_short_{c}'].to_numpy(float)
            vals.append(np.where(sig.chosen_side.to_numpy()=='LONG',lv,sv));weights.append(w)
        V=np.vstack(vals);W=np.asarray(weights)[:,None];ok=np.isfinite(V)
        sig[f'wave_{c}']=np.nansum(np.where(ok,V,0)*W,axis=0)/np.maximum(np.sum(ok*W,axis=0),1e-12)
    names=['impulse_early','impulse_mid','impulse_late','correction_early','correction_mid','correction_late']
    M=sig[[f'wave_{x}' for x in names]].to_numpy(float);idx=np.nanargmax(np.where(np.isfinite(M),M,-1),axis=1);mx=np.nanmax(M,axis=1);labels=np.array([names[i].upper() for i in idx],dtype=object);labels[(mx<0.24)|(sig.wave_unknown.to_numpy()>0.72)]='UNKNOWN';sig['wave_state']=labels
    sig['gap_from_prev_min']=sig.entry_time.diff().dt.total_seconds()/60
    return sig
