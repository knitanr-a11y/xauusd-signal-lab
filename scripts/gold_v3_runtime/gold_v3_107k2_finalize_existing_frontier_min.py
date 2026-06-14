#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, math, time
from datetime import datetime, timezone
import pandas as pd
import gold_v3_107gy_light_non_calendar_subfilter_search_audit as gy

STEP='GOLD_V3_107K2_FINALIZE_EXISTING_FRONTIER_MIN_AUDIT_ONLY'
READY='GOLD_V3_107K2_FINALIZED_READY_AUDIT_ONLY'
BLOCKED='GOLD_V3_107K2_FINALIZED_BLOCKED_AUDIT_ONLY'

def cap(v):
    try:
        x=float(v); return 10.0 if math.isinf(x) else max(0.0,min(x,10.0))
    except Exception: return 0.0

def save(df,p): p.parent.mkdir(parents=True,exist_ok=True); df.to_csv(p,index=False,encoding='utf-8-sig')

def main():
    t0=time.time(); root=gy.mt5_files_dir('')/'FX_OUTPUTS'/'gold_v3'; out=root/'107k2c'; out.mkdir(parents=True,exist_ok=True)
    blocks=[]; findings=[]; fp=out/'gold_v3_107k2_regime_frontier.csv'
    if not fp.exists(): blocks.append({'blocker_id':'missing_regime_frontier','path':str(fp)})
    if not blocks:
        per=pd.read_csv(fp,encoding='utf-8-sig')
        ag=[]
        for key,gp in per.groupby('policy_key'):
            best=gp.sort_values('regime_score',ascending=False).groupby('regime_group').head(1)
            have25=bool((best.regime_group=='2025').any()); have26=bool((best.regime_group=='2026_HIGHVOL').any())
            rec={'policy_key':key,'regime_count':int(best.regime_group.nunique()),'have_2025':have25,'have_2026_highvol':have26,'min_wr':float(best.oos_win_rate.min()),'min_pf':float(best.oos_profit_factor.min()),'min_trades':int(best.oos_trades.min()),'min_unique_days':int(best.oos_unique_trade_days.min()),'max_day_trade_share':float(best.oos_max_day_trade_share.max()),'sum_trades':int(best.oos_trades.sum()),'avg_wr':float(best.oos_win_rate.mean()),'all_regime_pass_60':bool(have25 and have26 and best.regime_pass_60.astype(bool).all()),'all_regime_pass_65':bool(have25 and have26 and best.regime_pass_65.astype(bool).all())}
            rec['balanced_score']=rec['min_wr']*15000+cap(rec['min_pf'])*1000+rec['min_trades']*.5+rec['sum_trades']*.1-rec['max_day_trade_share']*1000
            ag.append(rec)
        bal=pd.DataFrame(ag).sort_values(['all_regime_pass_65','all_regime_pass_60','balanced_score'],ascending=[False,False,False])
        save(bal,out/'gold_v3_107k2_balanced_policy_summary.csv')
        best=bal.iloc[0]
        rows=per[per.policy_key==best.policy_key].sort_values('regime_score',ascending=False).groupby('regime_group').head(1)
        save(rows,out/'gold_v3_107k2_best_policy_regime_rows.csv')
        p65=int(bal.all_regime_pass_65.sum()); p60=int(bal.all_regime_pass_60.sum())
        decision='REGIME_BALANCED_STRICT_65_READY_FOR_REHYDRATION' if p65 else ('REGIME_BALANCED_60_READY_FOR_REVIEW' if p60 else 'NO_REGIME_BALANCED_POLICY_NEED_ADAPTIVE_BASE_CANDIDATE_GENERATION')
        dec=pd.DataFrame([{'decision':decision,'all_regime_pass_65_count':p65,'all_regime_pass_60_count':p60,'best_policy_key':str(best.policy_key),'best_min_wr':float(best.min_wr),'best_min_pf':float(best.min_pf),'best_min_trades':int(best.min_trades),'best_sum_trades':int(best.sum_trades),'best_avg_wr':float(best.avg_wr),'next_stage':'107L_REGIME_REHYDRATION_AND_HEALTH_GATE' if (p65 or p60) else '107L_ADAPTIVE_BASE_CANDIDATE_GENERATION'}])
        save(dec,out/'gold_v3_107k2_next_action_decision.csv')
        findings.append('next_action_decision='+json.dumps(dec.to_dict(orient='records'),ensure_ascii=False,default=str))
        findings.append('best_policy_regime_rows='+json.dumps(rows.to_dict(orient='records'),ensure_ascii=False,default=str))
    status=READY if not blocks else BLOCKED
    summary={'step':STEP,'status':status,'created_at_utc':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),'output_dir':str(out),'audit_only':True,'live_ready':False,'source_csv_mutated':False,'contract_mutated':False,'open_asof_allowed':False,'csv_contract':gy.CONTRACT,'pool_policy':gy.POOL_POLICY,'blocker_count':len(blocks),'elapsed_seconds':round(time.time()-t0,2)}
    if not blocks:
        summary.update({'regime_frontier_rows':int(len(per)),'balanced_policy_rows':int(len(bal)),'all_regime_pass_65_count':p65,'all_regime_pass_60_count':p60,'best_policy_key':str(best.policy_key),'best_min_wr':float(best.min_wr),'best_min_pf':float(best.min_pf),'best_min_trades':int(best.min_trades),'best_sum_trades':int(best.sum_trades),'decision':decision})
    save(pd.DataFrame(blocks),out/'gold_v3_107k2_blocker_matrix.csv')
    (out/'gold_v3_107k2_summary.json').write_text(json.dumps(summary|{'findings':findings},ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    lines=['GOLD V3 107K2 PASTE_ME_FINALIZED_FROM_EXISTING_FRONTIER',f'status: {status}',f'ready: {str(status==READY).lower()}','live_ready: false','source_csv_mutated: false','contract_mutated: false','open_asof_allowed: false','csv_contract: '+gy.CONTRACT,'pool_policy: '+gy.POOL_POLICY,'blocker_count: '+str(len(blocks)),'','KEY_METRICS']+[f'{k}: {v}' for k,v in summary.items()]+['','FINDINGS']+(findings or ['NO_FINDINGS'])
    (out/'paste_me.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'ready':status==READY,'paste_me':str(out/'paste_me.txt')},ensure_ascii=False,indent=2))
    return 0 if status==READY else 2

if __name__=='__main__': raise SystemExit(main())
