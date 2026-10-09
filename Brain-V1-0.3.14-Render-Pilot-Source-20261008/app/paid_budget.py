"""Single-process paid batch ledger. Public-price estimate, not provider invoice."""
import json,os
from pathlib import Path
LIMIT=20.0
MAX_OUTPUT=32768
class BudgetError(ValueError):pass
def call_charge(c):
 status=c.get('status')
 if status=='PENDING':
  return float(c.get('reserved_yuan',c.get('estimated_yuan',0)) or 0)
 return float(c.get('estimated_yuan',0) or 0)
def call_reserved(c):
 return float(c.get('reserved_yuan',c.get('estimated_yuan',0)) or 0) if c.get('status')=='PENDING' else 0.0
def window_total(calls,start=0,end=None):
 return sum(call_charge(c) for c in calls[start:end])
def pending_total(calls,start=0,end=None):
 return sum(call_reserved(c) for c in calls[start:end])
def settled_estimated_total(calls,start=0,end=None):
 return sum(float(c.get('estimated_yuan',0) or 0) for c in calls[start:end] if c.get('status')!='PENDING')
def save(path,d):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2));tmp.replace(p)
def read(path):
 p=Path(path)
 return json.loads(p.read_text()) if p.exists() else {'limit_yuan':LIMIT,'started_runs':0,'calls':[],'price_basis':'2026-09-28 Beijing public list price; no cache discounts; estimate only'}
def ensure_baseline(path,baseline_path):
 p=Path(baseline_path)
 if not p.exists():return
 baseline=json.loads(p.read_text())
 if not Path(path).exists():
  save(path,baseline);return
 current=read(path)
 n=len(baseline['calls'])
 if current['started_runs']<baseline['started_runs'] or current['calls'][:n]!=baseline['calls']:
  raise BudgetError('BUDGET_BASELINE_CONFLICT_STOP')
def reserve(path,task,payload):
 d=read(path)
 if any(c['status']=='PENDING' for c in d['calls']):raise BudgetError('BUDGET_UNSETTLED_CALL_STOP')
 # UTF-8 byte count plus framing margin is deliberately conservative for text.
 bound=len(json.dumps(payload,ensure_ascii=False).encode())+4096
 if bound>200000:raise BudgetError('BUDGET_INPUT_TOO_LARGE')
 amount=(bound*6+MAX_OUTPUT*24)/1e6
 if window_total(d['calls'])+amount>float(d.get('limit_yuan',LIMIT)):raise BudgetError('BUDGET_20_YUAN_STOP')
 performance=d.get('performance_budget')
 if performance and window_total(d['calls'],performance['start_call'])+amount>float(performance['limit_yuan']):raise BudgetError('BUDGET_PERFORMANCE_LIMIT_YUAN_STOP')
 pilot=d.get('pilot_budget')
 if pilot and window_total(d['calls'],pilot['start_call'])+amount>float(pilot['limit_yuan']):raise BudgetError('BUDGET_PILOT_LIMIT_YUAN_STOP')
 full=d.get('full_experience_budget')
 if full:
  if window_total(d['calls'],full['start_call'])+amount>float(full['limit_yuan']):raise BudgetError('BUDGET_FULL_LIMIT_YUAN_STOP')
 else:
  owner=d.get('owner_budget')
  if owner and window_total(d['calls'],owner['start_call'])+amount>float(owner['limit_yuan']):raise BudgetError('BUDGET_OWNER_LIMIT_YUAN_STOP')
 d['calls'].append(dict(task=task,status='PENDING',estimated_yuan=0.0,reserved_yuan=amount));save(path,d)
 return len(d['calls'])-1
def settle(path,index,usage):
 d=read(path)
 if not isinstance(usage,dict):raise BudgetError('BUDGET_USAGE_MISSING_STOP')
 a=usage.get('prompt_tokens');b=usage.get('completion_tokens')
 if type(a)!=int or type(b)!=int or min(a,b)<0:raise BudgetError('BUDGET_USAGE_INVALID_STOP')
 price_in,price_out=(2,8) if a<=256000 else (6,24)
 cost=(a*price_in+b*price_out)/1e6
 c=d['calls'][index];reserved=float(c.get('reserved_yuan',c.get('estimated_yuan',0)) or 0)
 c.update(status='SETTLED',prompt_tokens=a,completion_tokens=b,usage=usage,estimated_yuan=cost);save(path,d)
 if cost>reserved:raise BudgetError('BUDGET_RESERVATION_EXCEEDED_STOP')
