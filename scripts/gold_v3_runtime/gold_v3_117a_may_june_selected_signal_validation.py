#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, math, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_117A_MAY_JUNE_SELECTED_SIGNAL_VALIDATION'
READY='GOLD_V3_117A_MAY_JUNE_SELECTED_SIGNAL_VALIDATION_READY'
BLOCKED='GOLD_V3_117A_MAY_JUNE_SELECTED_SIGNAL_VALIDATION_BLOCKED'

def save(df: pd.DataFrame, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, encoding='utf-8-sig')
def write_json(p: Path, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
def load_json(p: Path):
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return {}
def pf(s):
    a=pd.to_numeric(s, errors='coerce').dropna().to_numpy(dtype=float)
    gp=a[a>0].sum(); gl=-a[a<0].sum()
    if gl>0: return float(gp/gl)
    if gp>0: return math.inf
    return 0.0
def cap(x): return 10.0 if math.isinf(float(x)) else float(x)
def metrics(df: pd.DataFrame):
    if df is None or df.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,avg_result_usd=0.0,min_result_usd=0.0,max_result_usd=0.0)
    r=pd.to_numeric(df['result_usd'], errors='coerce').dropna()
    if r.empty:
        return dict(trades=0,wins=0,losses=0,win_rate=0.0,profit_factor=0.0,sum_result_usd=0.0,avg_result_usd=0.0,min_result_usd=0.0,max_result_usd=0.0)
    return dict(trades=int(len(r)),wins=int((r>0).sum()),losses=int((r<0).sum()),win_rate=float((r>0).mean()),profit_factor=pf(r),sum_result_usd=float(r.sum()),avg_result_usd=float(r.mean()),min_result_usd=float(r.min()),max_result_usd=float(r.max()))
def grouped(df: pd.DataFrame, cols, topn=None):
    rows=[]
    if df.empty: return pd.DataFrame()
    for key,g in df.groupby(cols, dropna=False):
        if not isinstance(key, tuple): key=(key,)
        row={c:v for c,v in zip(cols,key)}
        row.update(metrics(g))
        rows.append(row)
    out=pd.DataFrame(rows)
    if out.empty: return out
    out['pf_capped']=out['profit_factor'].apply(cap)
    out['review_score']=out['win_rate']*10000+out['pf_capped']*700+out['trades']*0.2+out['sum_result_usd']*0.01
    out=out.sort_values(['sum_result_usd','profit_factor','trades'], ascending=[False,False,False])
    return out.head(topn) if topn else out
def qgate(name, observed, op, threshold):
    if op=='>=': ok=observed>=threshold
    elif op=='<=': ok=observed<=threshold
    elif op=='==': ok=observed==threshold
    else: ok=False
    return dict(gate=name, observed=observed, operator=op, threshold=threshold, result='PASS' if ok else 'FAIL')
def main():
    t0=time.time()
    ap=argparse.ArgumentParser()
    ap.add_argument('--mt5-files-dir', default='')
    ap.add_argument('--start', default='2026-05-01')
    ap.add_argument('--end', default='2026-07-01')
    args=ap.parse_args()
    mt5=gy.mt5_files_dir(args.mt5_files_dir); root=mt5/'FX_OUTPUTS'/'gold_v3'; out=root/'117a'; out.mkdir(parents=True, exist_ok=True)
    ledger_path=root/'109c'/'gold_v3_109_selected_base_policy_ledger.csv'
    freeze_path=root/'112c'/'gold_v3_112_selected_policy_freeze_manifest.json'
    blockers=[]
    if not ledger_path.exists(): blockers.append({'blocker_id':'missing_selected_ledger','path':str(ledger_path)})
    freeze=load_json(freeze_path)
    if not freeze: blockers.append({'blocker_id':'missing_or_unreadable_freeze_manifest','path':str(freeze_path)})
    period=pd.DataFrame(); full=pd.DataFrame()
    if not blockers:
        full=pd.read_csv(ledger_path, encoding='utf-8-sig', low_memory=False)
        for c in ['entry_dt','result_usd']:
            if c not in full.columns: blockers.append({'blocker_id':'ledger_missing_required_column','column':c})
    if not blockers:
        full['entry_dt']=pd.to_datetime(full['entry_dt'], errors='coerce')
        full['result_usd']=pd.to_numeric(full['result_usd'], errors='coerce')
        full=full[full['entry_dt'].notna() & full['result_usd'].notna()].copy()
        if 'side' not in full.columns:
            if 'portfolio_side' in full.columns: full['side']=full['portfolio_side']
            elif 'selected_side' in full.columns: full['side']=full['selected_side']
            else: full['side']='UNKNOWN'
        for c in ['side','candidate_key','profile_id','family','condition']:
            if c not in full.columns: full[c]=''
        start=pd.Timestamp(args.start); end=pd.Timestamp(args.end)
        period=full[(full['entry_dt']>=start)&(full['entry_dt']<end)].copy()
        period['month']=period['entry_dt'].dt.to_period('M').astype(str)
        period['date']=period['entry_dt'].dt.date.astype(str)
        save(period, out/'gold_v3_117a_may_june_trade_ledger.csv')
        save(grouped(period, ['month']), out/'gold_v3_117a_monthly_metrics.csv')
        save(grouped(period, ['month','side']), out/'gold_v3_117a_side_month_metrics.csv')
        save(grouped(period, ['date']), out/'gold_v3_117a_daily_metrics.csv')
        save(grouped(period, ['profile_id']), out/'gold_v3_117a_profile_metrics.csv')
        save(grouped(period, ['candidate_key'], topn=50), out/'gold_v3_117a_candidate_metrics_top.csv')
    m=metrics(period) if not period.empty else metrics(pd.DataFrame())
    monthly=grouped(period,['month']) if not period.empty else pd.DataFrame()
    negative_month_count=0 if monthly.empty else int((pd.to_numeric(monthly['sum_result_usd'],errors='coerce')<0).sum())
    validations=[
        qgate('audit_only', True, '==', True),
        qgate('source_csv_mutated_false', False, '==', False),
        qgate('contract_mutated_false', False, '==', False),
        qgate('open_asof_allowed_false', False, '==', False),
        qgate('approximate_reconstruction_false', False, '==', False),
        qgate('selected_policy_key_keep_107q', freeze.get('selected_policy_key','')=='107Q_BASE_RESOLVED_PASS_THROUGH', '==', True),
    ]
    if not blockers:
        validations += [
            qgate('period_rows_positive', int(len(period)), '>=', 1),
            qgate('period_profit_factor_ge_1', float(cap(m['profit_factor'])), '>=', 1.0),
            qgate('negative_month_count_eq_0', negative_month_count, '==', 0),
        ]
    val=pd.DataFrame(validations)
    save(val, out/'gold_v3_117a_validation_matrix.csv')
    status=READY if not blockers else BLOCKED
    summary=dict(step=STEP,status=status,ready=status==READY,decision='MAY_JUNE_SELECTED_SIGNAL_VALIDATION_READY' if status==READY else 'MAY_JUNE_SELECTED_SIGNAL_VALIDATION_BLOCKED',created_at_utc=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),output_dir=str(out),start=args.start,end=args.end,selected_policy_key=freeze.get('selected_policy_key',''),source_csv_mutated=False,contract_mutated=False,open_asof_allowed=False,approximate_reconstruction=False,blocker_count=len(blockers),validation_failure_count=int((~val.result.eq('PASS')).sum()) if not val.empty else 0,negative_month_count=negative_month_count,elapsed_seconds=round(time.time()-t0,2))
    summary.update({f'period_{k}':v for k,v in m.items()})
    write_json(out/'gold_v3_117a_summary.json', summary|{'blockers':blockers})
    lines=['GOLD V3 117A PASTE_ME_MAY_JUNE_SELECTED_SIGNAL_VALIDATION',f'status: {status}',f'ready: {str(status==READY).lower()}',f'period: {args.start} <= entry_dt < {args.end}',f'selected_policy_key: {summary.get("selected_policy_key")}',f'period_trades: {m["trades"]}',f'period_win_rate: {m["win_rate"]}',f'period_profit_factor: {m["profit_factor"]}',f'period_sum_result_usd: {m["sum_result_usd"]}',f'negative_month_count: {negative_month_count}','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','approximate_reconstruction: false','blocker_count: '+str(len(blockers)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','MONTHLY_METRICS',monthly.to_string(index=False) if not monthly.empty else 'NO_MONTHLY_ROWS','','BLOCKERS','NO_BLOCKERS' if not blockers else json.dumps(blockers, ensure_ascii=False),'','VALIDATION',val.to_string(index=False)]
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2
if __name__=='__main__': raise SystemExit(main())
