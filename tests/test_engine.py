import copy,json,math,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
from backtest import simulate,load,metrics
class Tests(unittest.TestCase):
 def setUp(self):
  self.cfg=json.loads(Path('configs/baseline.json').read_text());self.dates=[];self.panel={};d=date(2018,1,1)
  for i in range(1400):
   if d.weekday()<5:self.dates.append(d);self.panel[d]={'A':0.001+0.005*math.sin(i),'B':-0.001+0.005*math.cos(i)}
   d+=timedelta(days=1)
 def run_engine(self,panel=None,cfg=None):return simulate(self.dates,['A','B'],panel or self.panel,cfg or self.cfg)
 def test_no_future_leakage(self):
  a,_=self.run_engine();p=copy.deepcopy(self.panel);cutoff=self.dates[650]
  for d in self.dates[651:]:p[d]={'A':0.2,'B':-0.1}
  b,_=self.run_engine(panel=p)
  self.assertEqual([x for x in a if x['date']<=str(cutoff)],[x for x in b if x['date']<=str(cutoff)])
 def test_direction_and_delay(self):
  _,logs=self.run_engine();first=date.fromisoformat(logs[0]['date']);i=self.dates.index(first)
  self.assertEqual(self.dates[i-1].month,first.month);self.assertNotEqual(self.dates[i-2].month,first.month)
  self.assertGreater(logs[0]['A'],0);self.assertLess(logs[0]['B'],0)
 def test_costs(self):
  a,_=self.run_engine();b,_=self.run_engine(cfg={**self.cfg,'cost_bps':0});self.assertGreater(b[-1]['equity'],a[-1]['equity'])
 def test_cap(self):
  rows,_=self.run_engine(cfg={**self.cfg,'gross_cap':0.5});self.assertTrue(all(x['gross_exposure']<=0.500000001 for x in rows))
 def test_missing_data(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'x.csv';p.write_text('date,symbol,return\n2020-01-01,A,0.01\n2020-01-01,B,0.02\n2020-01-02,A,0.03\n')
   with self.assertRaises(ValueError):load(p)
 def test_holdout(self):
  rows,_=self.run_engine(cfg={**self.cfg,'evaluation_start':'2020-01-01'})
  self.assertTrue(all(x['date']>='2020-01-01' for x in rows));self.assertAlmostEqual(rows[0]['equity'],10000*(1+rows[0]['net_return']))
 def test_financing_and_borrow_reduce_returns(self):
  zero,_=self.run_engine(cfg={**self.cfg,'financing_rate':0,'borrow_rate':0})
  charged,_=self.run_engine(cfg={**self.cfg,'financing_rate':0.04,'borrow_rate':0.02})
  self.assertLess(charged[-1]['equity'],zero[-1]['equity'])
  self.assertTrue(any(x['financing_cost']>0 for x in charged))
  self.assertTrue(any(x['borrow_cost']>0 for x in charged))
 def test_unleveraged_cap_has_no_financing(self):
  records,_=self.run_engine(cfg={**self.cfg,'gross_cap':1,'financing_rate':0.08})
  self.assertTrue(all(x['financing_cost']<1e-15 for x in records))
 def test_passive_uses_same_absolute_exposures(self):
  _,active=self.run_engine()
  _,passive=self.run_engine(cfg={**self.cfg,'mode':'passive_vol'})
  for x,y in zip(active,passive):
   self.assertAlmostEqual(abs(x['A']),y['A']);self.assertAlmostEqual(abs(x['B']),y['B'])
 def test_invalid_financing_rejected(self):
  with self.assertRaises(ValueError):self.run_engine(cfg={**self.cfg,'financing_rate':-1})
if __name__=='__main__':unittest.main()
