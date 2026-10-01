import csv,json,random
from datetime import date,timedelta
from pathlib import Path
rng=random.Random(42)
p=Path('data');p.mkdir(exist_ok=True)
with (p/'demo.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['date','symbol','return'])
    d=date(2000,1,1)
    for i in range(6000):
        if d.weekday()<5:
            for s in ['EQUITY','BOND','COMMODITY','FX']:
                w.writerow([d,s,rng.gauss(0.00015,0.009)])
        d+=timedelta(days=1)
(p/'demo_manifest.json').write_text(json.dumps({'kind':'synthetic','source':'seed42 generated noise','return_definition':'simple daily synthetic returns','roll_method':'none','currency':'USD','reviewed':False},indent=2))
