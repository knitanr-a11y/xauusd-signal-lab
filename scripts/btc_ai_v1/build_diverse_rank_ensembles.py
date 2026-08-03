from pathlib import Path
import json,numpy as np
ROOT=Path('/mnt/data/btc_ai_v1_cycle3');OUT=ROOT/'model_scores';MODELS=['XGB_D3','CAT_D4','EXTRA_D8','HGB_L15'];FOLDS=['2024H1','2024H2','2025H1','2025H2']
def pct_rank(ref,x):
 s=np.sort(ref);return np.searchsorted(s,x,side='right')/len(s)
def main():
 for fs in ['MTF_CONTEXT','FULL_CAUSAL']:
  for side in ['LONG','SHORT']:
   zs=[np.load(OUT/f'{m}__{fs}__{side}.npz') for m in MODELS];arr={};di=[]
   for f in FOLDS:
    cal=[];val=[]
    for z in zs:
     c=z[f'{f}_cal_score'];v=z[f'{f}_val_score'];cal.append(pct_rank(c,c));val.append(pct_rank(c,v))
    cs=np.mean(cal,axis=0).astype(np.float32);vs=np.mean(val,axis=0).astype(np.float32);arr[f'{f}_cal_score']=cs;arr[f'{f}_val_score']=vs;arr[f'{f}_val_idx']=zs[0][f'{f}_val_idx']
    di.append({'fold':f,'calibration_rows':len(cs),'validation_rows':len(vs),'members':MODELS})
   tag=f'RANK_ENSEMBLE__{fs}__{side}';np.savez_compressed(OUT/f'{tag}.npz',**arr);(OUT/f'{tag}.json').write_text(json.dumps({'tag':tag,'model_id':'RANK_ENSEMBLE','feature_set':fs,'direction':side,'diagnostics':di},indent=2));print('DONE',tag)
if __name__=='__main__':main()
