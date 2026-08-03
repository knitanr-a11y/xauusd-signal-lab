#!/usr/bin/env python3
"""Download and audit Binance BTCUSDT spot 1-minute monthly archives."""
from __future__ import annotations
import argparse,csv,datetime as dt,gzip,hashlib,io,json,shutil,sys,urllib.error,urllib.request,zipfile
from pathlib import Path
BASE_URL='https://data.binance.vision/data/spot/monthly/klines'
SYMBOL='BTCUSDT';INTERVAL='1m'
HEADER=['open_time_ms','open','high','low','close','volume','close_time_ms','quote_volume','trades','taker_buy_base_volume','taker_buy_quote_volume','ignore']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''):h.update(c)
 return h.hexdigest()
def dl(url,p):
 p.parent.mkdir(parents=True,exist_ok=True)
 req=urllib.request.Request(url,headers={'User-Agent':'btc-ai-v1-research/1.0'})
 with urllib.request.urlopen(req,timeout=120) as r,p.open('wb') as o:shutil.copyfileobj(r,o,1<<20)
def checksum(p):return p.read_text().strip().split()[0].lower()
def iso(ms):return dt.datetime.fromtimestamp(ms/1000,tz=dt.timezone.utc).isoformat() if ms is not None else None
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--year',type=int,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();y=a.year;o=a.output_dir;o.mkdir(parents=True,exist_ok=True);w=o/'_work';w.mkdir(exist_ok=True)
 merged=o/f'{SYMBOL}_SPOT_1m_{y}.csv.gz';records=[];rows=0;first=last=None;dups=rev=gaps=maxgap=0;mn=mx=None;vol=qvol=taker=0.0;trades=0
 with gzip.open(merged,'wt',encoding='utf-8',newline='',compresslevel=6) as gz:
  wr=csv.writer(gz);wr.writerow(HEADER)
  for m in range(1,13):
   ym=f'{y}-{m:02d}';fn=f'{SYMBOL}-{INTERVAL}-{ym}.zip';url=f'{BASE_URL}/{SYMBOL}/{INTERVAL}/{fn}';zp=w/fn;cp=w/(fn+'.CHECKSUM')
   print('[spot]',ym,flush=True);dl(url,zp);dl(url+'.CHECKSUM',cp);actual=sha(zp);expected=checksum(cp)
   if actual!=expected:raise RuntimeError(f'checksum mismatch {fn}')
   mr=0;mf=ml=None
   with zipfile.ZipFile(zp) as z:
    names=[n for n in z.namelist() if n.lower().endswith('.csv')]
    if len(names)!=1:raise RuntimeError(f'expected one csv {fn}')
    with z.open(names[0]) as raw:
     for row in csv.reader(io.TextIOWrapper(raw,encoding='utf-8',newline='')):
      if not row:continue
      try:ts=int(row[0])
      except ValueError:continue
      if ts>10_000_000_000_000:
       ts//=1000;row[0]=str(ts);row[6]=str(int(row[6])//1000)
      row=row[:12]
      if last is not None:
       d=ts-last
       if d==0:dups+=1
       elif d<0:rev+=1
       elif d>60000:gaps+=1;maxgap=max(maxgap,d//60000-1)
      if first is None:first=ts
      last=ts;mf=ts if mf is None else mf;ml=ts
      lo=float(row[3]);hi=float(row[2]);mn=lo if mn is None else min(mn,lo);mx=hi if mx is None else max(mx,hi)
      vol+=float(row[5]);qvol+=float(row[7]);trades+=int(float(row[8]));taker+=float(row[9]);wr.writerow(row);rows+=1;mr+=1
   records.append({'month':ym,'rows':mr,'first_open_utc':iso(mf),'last_open_utc':iso(ml),'archive_sha256':actual,'checksum_verified':True,'source_url':url});zp.unlink();cp.unlink()
 with (o/f'monthly_manifest_{y}.csv').open('w',encoding='utf-8',newline='') as f:
  cw=csv.DictWriter(f,fieldnames=list(records[0]));cw.writeheader();cw.writerows(records)
 expected=int((dt.datetime(y+1,1,1,tzinfo=dt.timezone.utc)-dt.datetime(y,1,1,tzinfo=dt.timezone.utc)).total_seconds()//60)
 audit={'research_track':'BTC_AI_V1_BINANCE_SPOT_EXTERNAL_VALIDATION','source':'Binance public data archive','market':'spot','symbol':SYMBOL,'interval':'1m','calendar_year':y,'time_semantics':'UTC','rows':rows,'expected_calendar_minutes':expected,'calendar_minute_coverage':rows/expected,'first_open_utc':iso(first),'last_open_utc':iso(last),'duplicate_timestamps':dups,'non_ascending_timestamps':rev,'gap_count':gaps,'max_missing_minutes_between_rows':maxgap,'min_price':mn,'max_price':mx,'total_base_volume':vol,'total_quote_volume':qvol,'total_trades':trades,'taker_buy_base_share':taker/vol if vol else None,'merged_file':merged.name,'merged_file_sha256':sha(merged),'monthly_archives':records,'trading_authorized':False}
 (o/f'audit_manifest_{y}.json').write_text(json.dumps(audit,indent=2,sort_keys=True),encoding='utf-8')
 if dups or rev:raise RuntimeError('timestamp integrity failure')
 print(json.dumps(audit,indent=2),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:print('ERROR',e,file=sys.stderr);raise
