"""Monthly TSMOM research engine; standard library only."""
import argparse, calendar, csv, hashlib, json, math, statistics, subprocess
from datetime import date
from pathlib import Path


def load(path):
    panel = {}
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            d = date.fromisoformat(row['date'])
            s = row['symbol']
            r = float(row['return'])
            if not s or not math.isfinite(r) or r <= -1:
                raise ValueError('Invalid symbol or simple return')
            if s in panel.setdefault(d, {}):
                raise ValueError('Duplicate date/symbol')
            panel[d][s] = r
    dates = sorted(panel)
    if not dates:
        raise ValueError('Empty data')
    symbols = sorted(set().union(*(set(x) for x in panel.values())))
    if any(set(panel[d]) != set(symbols) for d in dates):
        raise ValueError('Incomplete panel; missing returns cannot be zero-filled')
    return dates, symbols, panel


def months_before(d, months):
    n = d.year * 12 + d.month - 1 - months
    y, m = n // 12, n % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def simulate(dates, symbols, panel, cfg):
    lb = cfg['lookback_months']
    if not isinstance(lb, int) or lb < 1 or cfg['vol_com'] <= 0 or cfg['warmup_days'] < 2:
        raise ValueError('Invalid lookback or volatility settings')
    if cfg['vol_target'] <= 0 or cfg['annual_days'] <= 0 or cfg['cost_bps'] < 0 or cfg['initial_capital'] <= 0:
        raise ValueError('Invalid capital, volatility or costs')
    if cfg['gross_cap'] is not None and cfg['gross_cap'] <= 0:
        raise ValueError('Invalid exposure cap')
    decay = cfg['vol_com'] / (1 + cfg['vol_com'])
    means = dict.fromkeys(symbols, 0.0)
    seconds = dict.fromkeys(symbols, 0.0)
    weights = dict.fromkeys(symbols, 0.0)
    pending = None
    history = []
    records, logs = [], []
    equity = peak = cfg['initial_capital']
    start = date.fromisoformat(cfg['evaluation_start']) if cfg['evaluation_start'] else None
    end = date.fromisoformat(cfg['evaluation_end']) if cfg['evaluation_end'] else None
    for i, d in enumerate(dates):
        turnover = 0.0
        if pending is not None:
            turnover = sum(abs(pending[s] - weights[s]) for s in symbols)
            weights = pending
            pending = None
        active = start is None or d >= start
        active = active and (end is None or d <= end)
        gross = sum(weights[s] * panel[d][s] for s in symbols)
        cost = turnover * cfg['cost_bps'] / 10000
        if active and any(weights.values()):
            net = gross - cost
            if net <= -1:
                raise ValueError('Portfolio insolvency; leverage settings invalid for this path')
            equity *= 1 + net
            peak = max(peak, equity)
            record = {'date':d.isoformat(), 'gross_return':gross,'cost':cost,'net_return':net,
                      'equity':equity,'drawdown':equity/peak-1,'gross_exposure':sum(map(abs, weights.values()))}
            record.update({s:weights[s]*panel[d][s] for s in symbols})
            records.append(record)
        if turnover:
            logs.append({'date':d.isoformat(),'turnover':turnover,**weights})
        # Use previous month's completed data only; schedule for next close-to-close day.
        if i and d.month != dates[i-1].month:
            cutoff = months_before(dates[i-1], lb)
            window = [row for hd,row in history if hd > cutoff]
            ready = i >= cfg['warmup_days'] and dates[0] <= cutoff
            if ready:
                new = {}
                for s in symbols:
                    momentum = math.prod(1+row[s] for row in window)-1
                    mass = 1-decay**i
                    variance = max(0, seconds[s]/mass-(means[s]/mass)**2)
                    vol = math.sqrt(cfg['annual_days']*variance)
                    new[s] = (1 if momentum>0 else -1 if momentum<0 else 0)*cfg['vol_target']/vol/len(symbols) if vol>1e-10 else 0
                exposure = sum(map(abs,new.values()))
                cap = cfg['gross_cap']
                if cap and exposure > cap:
                    new = {s:w*cap/exposure for s,w in new.items()}
                pending = new
        for s in symbols:
            r = panel[d][s]
            means[s] = decay*means[s]+(1-decay)*r
            seconds[s] = decay*seconds[s]+(1-decay)*r*r
        history.append((d,panel[d]))
    if not records:
        raise ValueError('No active observations after warmup')
    return records, logs


def metrics(records, annual):
    r = [x['net_return'] for x in records]
    sd = statistics.stdev(r) if len(r)>1 else 0
    downside = math.sqrt(sum(min(0,x)**2 for x in r)/len(r))
    monthly, yearly = {}, {}
    for x in records:
        for group, key in ((monthly,x['date'][:7]),(yearly,x['date'][:4])):
            group[key] = group.get(key,1)*(1+x['net_return'])
    mr = [x-1 for x in monthly.values()]
    loss = -sum(x for x in mr if x<0)
    elapsed = (date.fromisoformat(records[-1]['date'])-date.fromisoformat(records[0]['date'])).days+1
    total = math.prod(1+x for x in r)
    return {'observations':len(r),'months':len(mr),'total_return':total-1,
            'cagr':total**(365.25/elapsed)-1,'max_drawdown':min(x['drawdown'] for x in records),
            'sharpe':statistics.mean(r)/sd*math.sqrt(annual) if sd else None,
            'sortino':statistics.mean(r)/downside*math.sqrt(annual) if downside else None,
            'monthly_win_rate':sum(x>0 for x in mr)/len(mr),
            'monthly_profit_factor':sum(x for x in mr if x>0)/loss if loss else None,
            'mean_daily_exposure':statistics.mean(x['gross_exposure'] for x in records),
            'yearly_returns':{k:v-1 for k,v in yearly.items()}}


def write_csv(path, rows):
    if not rows:
        return
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def main():
    ap=argparse.ArgumentParser()
    for name in ('data','manifest','config','out'):
        ap.add_argument('--'+name,required=True)
    args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    manifest=json.loads(Path(args.manifest).read_text())
    for key in ('kind','source','return_definition','roll_method','currency','reviewed'):
        if key not in manifest:
            raise ValueError('Manifest missing '+key)
    if manifest['kind'] not in ('synthetic','etf_proxy','futures_excess_returns'):
        raise ValueError('Unknown dataset kind')
    if manifest['kind']=='futures_excess_returns' and manifest['reviewed'] is not True:
        raise ValueError('Futures roll/return definition must be reviewed first')
    dates,symbols,panel=load(args.data)
    records,logs=simulate(dates,symbols,panel,cfg)
    summary=metrics(records,cfg['annual_days'])
    summary['market_mean_daily_gross_contributions']={s:statistics.mean(x[s] for x in records) for s in symbols}
    out=Path(args.out); out.mkdir(parents=True,exist_ok=False)
    write_csv(out/'daily.csv',records);write_csv(out/'weights.csv',logs)
    write_csv(out/'yearly.csv',[{'year':k,'return':v} for k,v in summary['yearly_returns'].items()])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    commit=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
    audit={'config':cfg,'manifest':manifest,'input_sha256':hashlib.sha256(Path(args.data).read_bytes()).hexdigest(),
           'git_commit':commit,'symbols':symbols,'data_start':str(dates[0]),'data_end':str(dates[-1]),
           'warnings':['Research weights, not contract execution','Roll costs and financing not modeled',
                       'Synthetic data: no investment evidence'] if manifest['kind']=='synthetic' else ['Not an exact original-paper replication']}
    (out/'run.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
