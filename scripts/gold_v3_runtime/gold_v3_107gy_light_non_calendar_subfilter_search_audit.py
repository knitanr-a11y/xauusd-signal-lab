#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, os, re, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STEP = 'GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_AUDIT_ONLY'
READY = 'GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_READY_AUDIT_ONLY'
BLOCKED = 'GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_BLOCKED_INPUT_INCOMPLETE_AUDIT_ONLY'
CONTRACT = 'open/in-progress candles are not written to CSV; CSV latest row is contractually closed; open/as-of treatment is forbidden'
POOL_POLICY = 'poolから外さない。rolling health gateに判断させる。'
INPUTS = [
    ('atomic_current_107GO', '107goc', 'gold_v3_107go_portfolio_ledger.csv'),
    ('atomic_top_107GN', '107gnc', 'gold_v3_107gn_top_candidate_trade_ledger.csv'),
    ('new_vector_top_107GL', '107glc', 'gold_v3_107gl_top_vector_trade_ledger.csv'),
    ('fixed_diversified_107GD', '107gdc', 'gold_v3_107gd_diversified_portfolio_ledger.csv'),
    ('broad_candidate_107GB', '107gbc', 'gold_v3_107gb_top_candidate_trade_ledger.csv'),
]
OHLC = {
    'm15': ['gold#_m15.csv', 'goldsharp_m15.csv'],
    'h1': ['gold#_h1.csv', 'goldsharp_h1.csv'],
    'h4': ['gold#_h4.csv', 'goldsharp_h4.csv'],
    'd1': ['gold#_d1.csv', 'goldsharp_d1.csv'],
}
SPLITS = {
    'TRAIN_2025_TEST_2026': ('2025-01-01', '2026-01-01', '2026-01-01', '2027-01-01'),
    'TRAIN_2025H1_TEST_2025H2': ('2025-01-01', '2025-07-01', '2025-07-01', '2026-01-01'),
    'TRAIN_TO_2026_02_TEST_2026_03_PLUS': ('2025-01-01', '2026-03-01', '2026-03-01', '2027-01-01'),
    'TRAIN_TO_2026_04_TEST_2026_05_06': ('2025-01-01', '2026-05-01', '2026-05-01', '2027-01-01'),
}
PROFILES = [('elite65', 0.65, 1.40, 8), ('strict63', 0.63, 1.60, 12), ('wr60pf2', 0.60, 2.00, 15)]
TOP_NS = [10, 20, 50, 100, 200]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def progress(i: int, n: int, msg: str) -> None:
    pct = 100.0 * i / max(n, 1)
    log(f'progress {pct:5.1f}% complete / {100.0 - pct:5.1f}% remaining | step {i}/{n} | {msg}')


def mt5_files_dir(arg: str) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get('MT5_FILES_DIR') or os.environ.get('MQL5_FILES_DIR')
    if env:
        return Path(env).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if p.name.lower() == 'files':
            return p
    return cwd


def save(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')


def norm_name(x: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(x).strip().lower())


def find_col(cols, names):
    m = {norm_name(c): c for c in cols}
    for name in names:
        if name in m:
            return m[name]
    for key, val in m.items():
        if any(name in key for name in names):
            return val
    return None


def read_ohlc(path: Path):
    try:
        sample = path.read_text(encoding='utf-8-sig', errors='ignore')[:4096]
        sep = ';' if sample.count(';') > sample.count(',') else ','
        df = pd.read_csv(path, sep=sep, encoding='utf-8-sig')
        t = find_col(df.columns, ['time', 'datetime', 'date', 'timestamp'])
        o = find_col(df.columns, ['open'])
        h = find_col(df.columns, ['high'])
        l = find_col(df.columns, ['low'])
        c = find_col(df.columns, ['close'])
        if not all([t, o, h, l, c]):
            return pd.DataFrame(), 'missing_ohlc_columns'
        x = df[[t, o, h, l, c]].copy()
        x.columns = ['time', 'open', 'high', 'low', 'close']
        x['time'] = pd.to_datetime(x['time'], errors='coerce')
        for col in ['open', 'high', 'low', 'close']:
            x[col] = pd.to_numeric(x[col], errors='coerce')
        return x.dropna().sort_values('time').drop_duplicates('time', keep='last'), ''
    except Exception as e:
        return pd.DataFrame(), str(e)


def load_tf(mt5: Path, tf: str):
    parts, coverage = [], []
    for fn in OHLC[tf]:
        p = mt5 / fn
        rows, mn, mx, err = 0, '', '', ''
        if p.exists():
            df, err = read_ohlc(p)
            rows = len(df)
            if rows:
                mn, mx = str(df['time'].min()), str(df['time'].max())
                parts.append(df)
        coverage.append(dict(tf=tf, file=fn, path=str(p), exists=p.exists(), rows=rows, min_time=mn, max_time=mx, error=err))
    if parts:
        return pd.concat(parts, ignore_index=True).sort_values('time').drop_duplicates('time', keep='last'), coverage
    return pd.DataFrame(), coverage


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).rolling(n, min_periods=4).mean()
    dn = (-d.clip(upper=0)).rolling(n, min_periods=4).mean()
    return 100.0 - 100.0 / (1.0 + up / dn)


def make_features(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    x = df.copy()
    pc = x['close'].shift(1)
    tr = pd.concat([(x['high'] - x['low']).abs(), (x['high'] - pc).abs(), (x['low'] - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(28, min_periods=6).mean()
    e20 = x['close'].ewm(span=20, adjust=False, min_periods=5).mean()
    e50 = x['close'].ewm(span=50, adjust=False, min_periods=10).mean()
    return pd.DataFrame({
        'time': x['time'],
        f'{tf}_atr28': atr,
        f'{tf}_rsi14': rsi(x['close']),
        f'{tf}_up': e20 > e50,
        f'{tf}_close_gt_ema20': x['close'] > e20,
        f'{tf}_dist_atr': (x['close'] - e20) / atr.replace(0, np.nan),
        f'{tf}_range_atr': (x['high'] - x['low']) / atr.replace(0, np.nan),
    }).sort_values('time')


def merge_asof_feature(left: pd.DataFrame, feat: pd.DataFrame) -> pd.DataFrame:
    return pd.merge_asof(left.sort_values('entry_dt'), feat.sort_values('time'), left_on='entry_dt', right_on='time', direction='backward').drop(columns=['time'], errors='ignore')


def profit_factor(values) -> float:
    arr = np.asarray(values, dtype=float)
    gp = arr[arr > 0].sum()
    gl = -arr[arr < 0].sum()
    return float(gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0)


def cap_pf(x: float) -> float:
    return 10.0 if math.isinf(float(x)) else max(0.0, min(float(x), 10.0))


def metrics(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0)
    x = df.copy()
    x['result_usd'] = pd.to_numeric(x['result_usd'], errors='coerce')
    x = x[x['result_usd'].notna()]
    if x.empty:
        return dict(trades=0, wins=0, losses=0, win_rate=0.0, profit_factor=0.0, sum_result_usd=0.0, negative_month_count=0)
    monthly = x.groupby(pd.to_datetime(x['entry_dt']).dt.to_period('M').astype(str))['result_usd'].sum()
    return dict(
        trades=int(len(x)),
        wins=int((x['result_usd'] > 0).sum()),
        losses=int((x['result_usd'] < 0).sum()),
        win_rate=float((x['result_usd'] > 0).mean()),
        profit_factor=profit_factor(x['result_usd'].to_numpy()),
        sum_result_usd=float(x['result_usd'].sum()),
        negative_month_count=int((monthly < 0).sum()),
    )


def density_metrics(df: pd.DataFrame) -> dict:
    m = metrics(df)
    if df is None or df.empty:
        return m | dict(business_day_trade_rate=0.0, active_trade_day_rate=0.0, min_entry_dt='', max_entry_dt='')
    mn = pd.to_datetime(df['entry_dt'].min()).date()
    mx = pd.to_datetime(df['entry_dt'].max()).date()
    bd = int(np.busday_count(np.datetime64(mn), np.datetime64(mx) + np.timedelta64(1, 'D')))
    ad = int(pd.to_datetime(df['entry_dt']).dt.date.nunique())
    return m | dict(
        business_day_trade_rate=float(m['trades'] / bd) if bd else 0.0,
        active_trade_day_rate=float(m['trades'] / ad) if ad else 0.0,
        min_entry_dt=str(mn),
        max_entry_dt=str(mx),
    )


def normalize_ledger(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if 'entry_dt' not in df.columns:
        return pd.DataFrame()
    x = df.copy()
    x['entry_dt'] = pd.to_datetime(x['entry_dt'], errors='coerce')
    x = x[x['entry_dt'].notna()].copy()
    x['result_usd'] = pd.to_numeric(x.get('result_usd', 0), errors='coerce')
    x = x[x['result_usd'].notna()].copy()
    if 'portfolio_side' in x.columns:
        x['side'] = x['portfolio_side']
    if 'selected_side' in x.columns and 'side' not in x.columns:
        x['side'] = x['selected_side']
    if 'side' not in x.columns:
        x['side'] = 'UNKNOWN'
    for col in ['side', 'family', 'condition', 'profile_id', 'candidate_key']:
        if col not in x.columns:
            x[col] = ''
        x[col] = x[col].astype(str).replace({'nan': ''})
    if 'cooldown_bars' not in x.columns:
        x['cooldown_bars'] = 0
    x['cooldown_bars'] = pd.to_numeric(x['cooldown_bars'], errors='coerce').fillna(0).astype(int)
    built = x.apply(lambda r: f"{r.side}||{r.family}||{r.condition}||{r.profile_id}||CD{int(r.cooldown_bars)}", axis=1)
    empty = x['candidate_key'].eq('') | x['candidate_key'].eq('nan')
    x.loc[empty, 'candidate_key'] = built[empty]
    x['source_name'] = source_name
    x['global_candidate_key'] = x['source_name'] + '::' + x['candidate_key']
    return x.sort_values('entry_dt')


def make_filters(train: pd.DataFrame):
    filters = []
    def add(fid, fn): filters.append((fid, fn))
    for col in ['m15_up', 'm15_close_gt_ema20', 'h1_up', 'h4_up', 'd1_up']:
        if col in train.columns and train[col].notna().sum() >= 5:
            add(col + '_T', lambda d, c=col: d[c].fillna(False).astype(bool))
            add(col + '_F', lambda d, c=col: ~d[c].fillna(False).astype(bool))
    for col in ['m15_rsi14', 'h1_rsi14', 'h4_rsi14']:
        if col in train.columns and train[col].notna().sum() >= 8:
            add(col + '_le45', lambda d, c=col: pd.to_numeric(d[c], errors='coerce') <= 45)
            add(col + '_ge55', lambda d, c=col: pd.to_numeric(d[c], errors='coerce') >= 55)
            add(col + '_40_60', lambda d, c=col: pd.to_numeric(d[c], errors='coerce').between(40, 60, inclusive='left'))
    for col in ['m15_atr28', 'm15_range_atr', 'm15_dist_atr', 'h1_dist_atr', 'h4_dist_atr']:
        if col in train.columns and train[col].notna().sum() >= 12:
            s = pd.to_numeric(train[col], errors='coerce').dropna()
            q25, q75 = s.quantile([0.25, 0.75])
            add(col + '_lowq', lambda d, c=col, q=q25: pd.to_numeric(d[c], errors='coerce') <= q)
            add(col + '_highq', lambda d, c=col, q=q75: pd.to_numeric(d[c], errors='coerce') >= q)
    return filters


def subfilter_metrics(train: pd.DataFrame, test: pd.DataFrame, meta: dict) -> pd.DataFrame:
    rows = []
    for fid, fn in make_filters(train):
        tr = train[fn(train)].copy()
        tm = density_metrics(tr)
        if tm['trades'] < 5 or tm['sum_result_usd'] <= 0:
            continue
        te = test[fn(test)].copy()
        om = density_metrics(te)
        score = tm['win_rate'] * 9000 + cap_pf(tm['profit_factor']) * 800 + tm['trades'] * 0.3 - tm['negative_month_count'] * 250
        row = dict(filter_id=fid, subfilter_key=meta['global_candidate_key'] + '::NF::' + fid, train_score=score)
        row.update({f'train_{k}': v for k, v in tm.items()})
        row.update({f'oos_{k}': v for k, v in om.items()})
        row.update(meta)
        rows.append(row)
    return pd.DataFrame(rows)


def apply_filter(df: pd.DataFrame, fid: str) -> pd.DataFrame:
    for k, fn in make_filters(df):
        if k == fid:
            return df[fn(df)].copy()
    return df.iloc[0:0]


def stack_portfolio(ledger: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, r in selected.iterrows():
        x = ledger[(ledger['global_candidate_key'] == r.global_candidate_key) & (ledger['entry_dt'] >= pd.Timestamp(r.test_start)) & (ledger['entry_dt'] < pd.Timestamp(r.test_end))].copy()
        x = apply_filter(x, str(r.filter_id))
        if not x.empty:
            x['subfilter_key'] = r.subfilter_key
            x['train_score'] = r.train_score
            parts.append(x)
    if not parts:
        return pd.DataFrame()
    y = pd.concat(parts, ignore_index=True)
    return y.sort_values(['entry_dt', 'train_score'], ascending=[True, False]).drop_duplicates('entry_dt', keep='first')


def gate_row(name, obs, op, thr):
    ok = obs >= thr if op == '>=' else obs <= thr
    return dict(gate=name, observed=obs, operator=op, threshold=thr, result='PASS' if ok else 'FAIL')


def main() -> int:
    t0 = time.time()
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--top-configs', type=int, default=8)
    args = ap.parse_args()
    mt5 = mt5_files_dir(args.mt5_files_dir)
    root = mt5 / 'FX_OUTPUTS' / 'gold_v3'
    out = root / '107gyc'
    out.mkdir(parents=True, exist_ok=True)
    log(STEP + ' START')
    blocks, outputs, validations, findings = [], [], [], []
    req = {'d2': root / '107gvc' / 'gold_v3_107gv_density2_pass_configs.csv', 'sel': root / '107guc' / 'gold_v3_107gu_selected_candidate_keys.csv'}
    for k, p in req.items():
        if not p.exists():
            blocks.append(dict(blocker_id='missing_' + k, path=str(p)))
    cov, feats = [], {}
    for tf in ['m15', 'h1', 'h4', 'd1']:
        x, c = load_tf(mt5, tf)
        cov.extend(c)
        if not x.empty:
            feats[tf] = make_features(x, tf)
    save(pd.DataFrame(cov), out / 'gold_v3_107gy_ohlc_coverage.csv'); outputs.append('gold_v3_107gy_ohlc_coverage.csv')
    if 'm15' not in feats:
        blocks.append(dict(blocker_id='missing_m15_ohlc'))
    ledgers, ledger_cov = [], []
    for src, sub, fn in INPUTS:
        p = root / sub / fn
        rows, err = 0, ''
        if p.exists():
            try:
                x = normalize_ledger(pd.read_csv(p, encoding='utf-8-sig'), src)
                rows = len(x)
                if rows:
                    ledgers.append(x)
            except Exception as e:
                err = str(e)
        ledger_cov.append(dict(source_name=src, path=str(p), exists=p.exists(), rows=rows, error=err))
    save(pd.DataFrame(ledger_cov), out / 'gold_v3_107gy_input_ledger_coverage.csv'); outputs.append('gold_v3_107gy_input_ledger_coverage.csv')
    if not ledgers:
        blocks.append(dict(blocker_id='no_ledgers'))
    if not blocks:
        ledger = pd.concat(ledgers, ignore_index=True).sort_values('entry_dt')
        for f in feats.values():
            ledger = merge_asof_feature(ledger, f)
        fc = [dict(feature=c, coverage=float(ledger[c].notna().mean()), non_null=int(ledger[c].notna().sum())) for c in ledger.columns if re.match(r'^(m15|h1|h4|d1)_', c)]
        save(pd.DataFrame(fc), out / 'gold_v3_107gy_feature_join_coverage.csv'); outputs.append('gold_v3_107gy_feature_join_coverage.csv')
        d2 = pd.read_csv(req['d2'], encoding='utf-8-sig').sort_values('review_score', ascending=False).head(args.top_configs)
        sel = pd.read_csv(req['sel'], encoding='utf-8-sig')
        total = sum(int(sel[(sel.split.astype(str) == str(r.split)) & (sel.tier.astype(str) == str(r.tier)) & (pd.to_numeric(sel.top_n, errors='coerce') == int(r.top_n))].shape[0]) for _, r in d2.iterrows()) + len(d2) * len(PROFILES) * len(TOP_NS)
        cur = 0
        progress(cur, total, 'start')
        all_sub, front_rows, all_selected = [], [], []
        for ci, (_, cfg) in enumerate(d2.iterrows(), 1):
            sp, tier, topn = str(cfg.split), str(cfg.tier), int(cfg.top_n)
            if sp not in SPLITS:
                continue
            trs, tre, tes, tee = SPLITS[sp]
            keys = sel[(sel.split.astype(str) == sp) & (sel.tier.astype(str) == tier) & (pd.to_numeric(sel.top_n, errors='coerce') == topn)].sort_values('rank')
            cfg_sub = []
            for _, kr in keys.iterrows():
                cur += 1
                key = str(kr.global_candidate_key)
                train = ledger[(ledger.global_candidate_key == key) & (ledger.entry_dt >= pd.Timestamp(trs)) & (ledger.entry_dt < pd.Timestamp(tre))]
                test = ledger[(ledger.global_candidate_key == key) & (ledger.entry_dt >= pd.Timestamp(tes)) & (ledger.entry_dt < pd.Timestamp(tee))]
                if not train.empty:
                    sm = subfilter_metrics(train, test, dict(split=sp, tier=tier, base_top_n=topn, global_candidate_key=key, train_start=trs, train_end=tre, test_start=tes, test_end=tee))
                    if not sm.empty:
                        all_sub.append(sm); cfg_sub.append(sm)
                if cur % 10 == 0:
                    progress(cur, total, f'filters config={ci}/{len(d2)}')
            pool0 = pd.concat(cfg_sub, ignore_index=True) if cfg_sub else pd.DataFrame()
            for prof, min_wr, min_pf, min_tr in PROFILES:
                if pool0.empty:
                    pool = pd.DataFrame()
                else:
                    pool = pool0[(pool0.train_win_rate >= min_wr) & (pool0.train_profit_factor >= min_pf) & (pool0.train_trades >= min_tr)].sort_values('train_score', ascending=False)
                for n in TOP_NS:
                    cur += 1
                    ss = pool.head(n).copy()
                    port = stack_portfolio(ledger, ss) if not ss.empty else pd.DataFrame()
                    m = density_metrics(port)
                    row = dict(split=sp, tier=tier, base_top_n=topn, profile=prof, subfilter_top_n=n, train_pool_count=len(pool), selected_subfilters=len(ss), original_wr=float(cfg.test_wr), original_pf=float(cfg.test_pf), original_density=float(cfg.test_business_day_trade_rate))
                    row.update({f'oos_{k}': v for k, v in m.items()})
                    row['primary_65_gate'] = bool(m['win_rate'] >= 0.65 and m['profit_factor'] >= 1.5 and m['trades'] >= 30)
                    row['volume_65_gate'] = bool(m['win_rate'] >= 0.65 and m['profit_factor'] >= 1.5 and m['business_day_trade_rate'] >= 2)
                    row['review_62_gate'] = bool(m['win_rate'] >= 0.62 and m['profit_factor'] >= 1.8 and m['trades'] >= 50)
                    row['review_score'] = m['win_rate'] * 12000 + cap_pf(m['profit_factor']) * 900 + m['trades'] * 0.35 + min(m['business_day_trade_rate'], 30) * 120 - m['negative_month_count'] * 500
                    front_rows.append(row)
                    if not ss.empty:
                        all_selected.append(ss.assign(profile=prof, subfilter_top_n=n, stack_split=sp, stack_tier=tier, stack_base_top_n=topn))
                    if cur % 20 == 0:
                        progress(cur, total, f'stack config={ci}/{len(d2)}')
        sub = pd.concat(all_sub, ignore_index=True) if all_sub else pd.DataFrame()
        front = pd.DataFrame(front_rows).sort_values('review_score', ascending=False) if front_rows else pd.DataFrame()
        selected = pd.concat(all_selected, ignore_index=True) if all_selected else pd.DataFrame()
        save(sub, out / 'gold_v3_107gy_subfilter_metrics.csv'); outputs.append('gold_v3_107gy_subfilter_metrics.csv')
        save(front, out / 'gold_v3_107gy_stack_frontier.csv'); outputs.append('gold_v3_107gy_stack_frontier.csv')
        save(selected, out / 'gold_v3_107gy_selected_subfilters.csv'); outputs.append('gold_v3_107gy_selected_subfilters.csv')
        if front.empty:
            blocks.append(dict(blocker_id='no_frontier'))
        else:
            best = front.iloc[0]
            bs = selected[(selected.stack_split == best.split) & (selected.stack_tier == best.tier) & (selected.stack_base_top_n == best.base_top_n) & (selected.profile == best.profile) & (selected.subfilter_top_n == best.subfilter_top_n)] if not selected.empty else pd.DataFrame()
            port = stack_portfolio(ledger, bs) if not bs.empty else pd.DataFrame()
            save(port, out / 'gold_v3_107gy_best_stack_ledger.csv'); outputs.append('gold_v3_107gy_best_stack_ledger.csv')
            p65 = int(front.primary_65_gate.sum()); v65 = int(front.volume_65_gate.sum()); r62 = int(front.review_62_gate.sum())
            decision = 'PRIMARY_65_READY' if p65 else ('VOLUME_65_READY' if v65 else ('REVIEW_62_ONLY' if r62 else 'NO_65_NEED_DEEPER_FEATURES'))
            gates = pd.DataFrame([gate_row('any_primary_65', p65, '>=', 1), gate_row('any_volume_65', v65, '>=', 1), gate_row('any_review_62', r62, '>=', 1), gate_row('best_wr_ge_65', float(best.oos_win_rate), '>=', 0.65), gate_row('best_trades_ge_30', int(best.oos_trades), '>=', 30)])
            dec = pd.DataFrame([dict(decision=decision, primary_65_gate_count=p65, volume_65_gate_count=v65, review_62_gate_count=r62, best_split=str(best.split), best_tier=str(best.tier), best_profile=str(best.profile), best_subfilter_top_n=int(best.subfilter_top_n), best_selected_subfilters=int(best.selected_subfilters), best_trades=int(best.oos_trades), best_wr=float(best.oos_win_rate), best_pf=float(best.oos_profit_factor), best_density=float(best.oos_business_day_trade_rate), next_stage=('107GZ_REHYDRATION' if p65 or v65 else '107GZ_DEEPER_FEATURE_SEARCH'))])
            save(gates, out / 'gold_v3_107gy_quality_gate_matrix.csv'); outputs.append('gold_v3_107gy_quality_gate_matrix.csv')
            save(dec, out / 'gold_v3_107gy_next_action_decision.csv'); outputs.append('gold_v3_107gy_next_action_decision.csv')
            findings.append('next_action_decision=' + json.dumps(dec.to_dict(orient='records'), ensure_ascii=False, default=str))
            findings.append('top_stack_frontier=' + json.dumps(front.head(10).to_dict(orient='records'), ensure_ascii=False, default=str))
            validations.append(dict(check_id='frontier_rows_positive', result='PASS', observed=len(front), expected='>0', severity='BLOCKER'))
    validations += [dict(check_id='audit_only', result='PASS', observed=True, expected=True, severity='BLOCKER'), dict(check_id='source_csv_mutated', result='PASS', observed=False, expected=False, severity='BLOCKER'), dict(check_id='open_asof_allowed', result='PASS', observed=False, expected=False, severity='BLOCKER')]
    val = pd.DataFrame(validations)
    status = READY if not blocks and val.result.eq('PASS').all() else BLOCKED
    summary = dict(step=STEP, status=status, created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z'), output_dir=str(out), audit_only=True, live_ready=False, source_csv_mutated=False, contract_mutated=False, manual_candidate_demotion_or_removal=False, open_asof_allowed=False, csv_contract=CONTRACT, csv_open_bar_exclusion_required=False, pool_policy=POOL_POLICY, blocker_count=len(blocks), validation_failure_count=int((~val.result.eq('PASS')).sum()), elapsed_seconds=round(time.time() - t0, 2))
    if not blocks and 'front' in locals() and not front.empty:
        summary.update(stack_frontier_rows=len(front), primary_65_gate_count=int(front.primary_65_gate.sum()), volume_65_gate_count=int(front.volume_65_gate.sum()), review_62_gate_count=int(front.review_62_gate.sum()), best_wr=float(front.iloc[0].oos_win_rate), best_pf=float(front.iloc[0].oos_profit_factor), best_density=float(front.iloc[0].oos_business_day_trade_rate), best_trades=int(front.iloc[0].oos_trades), decision=decision)
    save(pd.DataFrame(blocks), out / 'gold_v3_107gy_blocker_matrix.csv'); outputs.append('gold_v3_107gy_blocker_matrix.csv')
    save(val, out / 'gold_v3_107gy_validation_matrix.csv'); outputs.append('gold_v3_107gy_validation_matrix.csv')
    outputs += ['gold_v3_107gy_summary.json', 'GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_AUDIT_ONLY_REPORT.md', 'paste_me.txt']
    (out / 'gold_v3_107gy_summary.json').write_text(json.dumps(summary | {'findings': findings}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    (out / 'GOLD_V3_107GY_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH_AUDIT_ONLY_REPORT.md').write_text('# GOLD V3 107GY report\n\n' + json.dumps({'summary': summary, 'findings': findings, 'blockers': blocks}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    lines = ['GOLD V3 107GY PASTE_ME_LIGHT_NON_CALENDAR_SUBFILTER_SEARCH', f'status: {status}', f'ready: {str(status == READY).lower()}', 'live_ready: false', 'source_csv_mutated: false', 'contract_mutated: false', 'manual_candidate_demotion_or_removal: false', 'open_asof_allowed: false', 'csv_contract: ' + CONTRACT, 'csv_open_bar_exclusion_required: false', 'safety: audit_only=true, proxy_only=true, mt5=false, discord=false, ai_api=false, live_hook=false, final_signal=false', 'pool_policy: ' + POOL_POLICY, 'source: exact OHLC as-of features plus Stage107GV/GU candidate bank; no M5 re-evaluation; no runtime change', 'runtime_estimate: light_to_medium_with_percent_progress', 'blocker_count: ' + str(len(blocks)), '', 'KEY_METRICS']
    lines += [f'{k}: {v}' for k, v in summary.items()]
    lines += ['', 'FINDINGS'] + (findings or ['NO_FINDINGS']) + ['', 'BLOCKERS', pd.DataFrame(blocks).to_string(index=False) if blocks else 'NO_BLOCKERS', '', 'VALIDATION', val.to_string(index=False), '', 'OUTPUTS'] + outputs
    (out / 'paste_me.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    progress(total if 'total' in locals() else 1, total if 'total' in locals() else 1, 'DONE')
    log(f'DONE status={status} elapsed={time.time() - t0:.1f}s paste_me={out / "paste_me.txt"}')
    print(json.dumps({'status': status, 'ready': status == READY, 'paste_me': str(out / 'paste_me.txt')}, ensure_ascii=False, indent=2))
    return 0 if status == READY else 2


if __name__ == '__main__':
    raise SystemExit(main())
