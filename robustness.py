"""Declared ETF cost/exposure sensitivity; report every scenario, no winner selection."""
import argparse, hashlib, json
from pathlib import Path
from backtest import load, simulate, metrics, write_csv

p=argparse.ArgumentParser()
for key in ('data','manifest','out'):p.add_argument('--'+key,required=True)
a=p.parse_args()
manifest=json.loads(Path(a.manifest).read_text())
if manifest.get('kind')!='etf_proxy':raise SystemExit('This study is for ETF proxies only')
dates,symbols,panel=load(a.data)
base=json.loads(Path('configs/baseline.json').read_text())
reference,_=simulate(dates,symbols,panel,base)
base['evaluation_start']=reference[0]['date']
out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
periods=[('full',None,None),('2006-2015','2006-01-01','2015-12-31'),('2016-2025','2016-01-01','2025-12-31'),('2006-2010','2006-01-01','2010-12-31'),('2011-2015','2011-01-01','2015-12-31'),('2016-2020','2016-01-01','2020-12-31'),('2021-2025','2021-01-01','2025-12-31')]
rows=[];configs={}
for lb in (6,12):
 for cap in (1.0,1.5):
  for financing in (0.0,0.04,0.08):
   for borrow in (0.0,0.02):
    for mode in ('momentum','passive_vol'):
     cfg={**base,'lookback_months':lb,'gross_cap':cap,'financing_rate':financing,'borrow_rate':borrow,'mode':mode}
     name=f'{mode}_{lb}m_cap{cap}_fin{financing}_borrow{borrow}'
     configs[name]=cfg
     records,logs=simulate(dates,symbols,panel,cfg)
     # Preserve full detail for central stress scenario, with both benchmarks.
     if financing==0.04 and borrow==0.02:
      dest=out/name;dest.mkdir()
      write_csv(dest/'daily.csv',records);write_csv(dest/'weights.csv',logs)
     for label,start,end in periods:
      segment=[dict(x) for x in records if (not start or x['date']>=start) and (not end or x['date']<=end)]
      if len(segment)<2:continue
      equity=peak=10000.0
      for x in segment:
       equity*=1+x['net_return'];peak=max(peak,equity);x['drawdown']=equity/peak-1;x['equity']=equity
      m=metrics(segment,cfg['annual_days'])
      rows.append({'scenario':name,'mode':mode,'lookback_months':lb,'gross_cap':cap,'financing_rate':financing,'borrow_rate':borrow,'cost_bps':cfg['cost_bps'],'period':label,'start':segment[0]['date'],'end':segment[-1]['date'],**{k:v for k,v in m.items() if k!='yearly_returns'}})
# Additional monthly equal-weight long-only passive benchmark, gross exposure 100%.
cfg={**base,'mode':'passive_equal','gross_cap':1.0}
records,logs=simulate(dates,symbols,panel,cfg)
write_csv(out/'passive_equal_daily.csv',records)
m=metrics(records,cfg['annual_days'])
rows.append({'scenario':'passive_equal','mode':'passive_equal','lookback_months':12,'gross_cap':1.0,'financing_rate':0,'borrow_rate':0,'cost_bps':cfg['cost_bps'],'period':'full','start':records[0]['date'],'end':records[-1]['date'],**{k:v for k,v in m.items() if k!='yearly_returns'}})
write_csv(out/'comparison.csv',rows)
(out/'study.json').write_text(json.dumps({'data_sha256':hashlib.sha256(Path(a.data).read_bytes()).hexdigest(),'manifest':manifest,'configs':configs,'periods':periods,'limitations':['Rates are declared sensitivity assumptions, not historical broker costs.','Financing conservatively charged on gross exposure above 100%; no collateral/short proceeds interest.','Passive volatility weights have same per-asset absolute exposure, not identical realized portfolio volatility.','Subperiods are retrospective stability checks, not untouched out-of-sample validation.','Partial periods are retained with actual start/end dates; compare complete periods.','Constant exposure research weights, no integer contracts.']},indent=2))
print(f'Saved {len(rows)} comparisons to {out}')
