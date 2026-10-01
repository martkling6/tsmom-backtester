"""Fetch adjusted ETF closes; never label these as futures returns."""
import argparse,csv,json,os,urllib.request,urllib.parse
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--symbols',nargs='+',required=True)
for key in ('start','end','out'):ap.add_argument('--'+key,required=True)
a=ap.parse_args();token=os.environ.get('EODHD_API_TOKEN')
if not token:raise SystemExit('Set EODHD_API_TOKEN environment variable')
series={}
for s in a.symbols:
    query=urllib.parse.urlencode({'api_token':token,'fmt':'json','from':a.start,'to':a.end,'period':'d'})
    try:
        with urllib.request.urlopen('https://eodhd.com/api/eod/'+urllib.parse.quote(s,safe='')+'?'+query,timeout=60) as response:
            rows=json.load(response)
    except Exception:
        raise SystemExit('EODHD request failed; check plan, symbol, network and token (URL suppressed)') from None
    if not isinstance(rows,list):raise SystemExit('Unexpected EODHD response')
    prices={r['date']:float(r['adjusted_close']) for r in rows}
    if not prices or any(v<=0 for v in prices.values()):raise SystemExit('Invalid adjusted closes')
    series[s]=prices
common=sorted(set.intersection(*(set(p) for p in series.values())))
if len(common)<2:raise SystemExit('Insufficient overlapping history')
p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
with p.open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['date','symbol','return'])
    for previous,d in zip(common,common[1:]):
        for s,prices in series.items():w.writerow([d,s,prices[d]/prices[previous]-1])
p.with_suffix('.manifest.json').write_text(json.dumps({'kind':'etf_proxy','source':'EODHD adjusted_close','return_definition':'adjusted close simple returns on common calendar','roll_method':'ETF internal holdings; not directly modeled','currency':'USD (user must verify selected symbols)','reviewed':False,'symbols':a.symbols,'start':a.start,'end':a.end},indent=2))
print('Saved ETF proxy dataset; NOT futures replication')
