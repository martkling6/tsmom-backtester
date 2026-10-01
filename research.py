"""Predeclared grid. Reports all configurations without selecting a winner."""
import argparse,json
from pathlib import Path
from backtest import load,simulate,metrics,write_csv
p=argparse.ArgumentParser();p.add_argument('--data',required=True);p.add_argument('--out',required=True);a=p.parse_args()
dates,symbols,panel=load(a.data);base=json.loads(Path('configs/baseline.json').read_text());rows=[]
reference,_=simulate(dates,symbols,panel,base)
base['evaluation_start']=reference[0]['date']
for lb in (1,3,6,12):
 for cost in (0,5,10,20):
  cfg={**base,'lookback_months':lb,'cost_bps':cost}
  records,_=simulate(dates,symbols,panel,cfg)
  m=metrics(records,base['annual_days'])
  rows.append({'lookback_months':lb,'cost_bps':cost,**{k:v for k,v in m.items() if k!='yearly_returns'}})
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise SystemExit('Output already exists')
write_csv(out,rows)
print('Saved all 16 variants; compare identical date windows before ranking')
