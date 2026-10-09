"""Fail-closed initialization and validation for an invite-only Pilot spend ledger."""
import math
from pathlib import Path

from paid_budget import BudgetError, pending_total, read, save, window_total


def _amount(value, name, *, allow_zero=False):
 try:
  amount=float(value)
 except (TypeError,ValueError):
  raise BudgetError('PILOT_BUDGET_CONFIG_INVALID:'+name) from None
 if not math.isfinite(amount) or amount < 0 or (amount == 0 and not allow_zero):
  raise BudgetError('PILOT_BUDGET_CONFIG_INVALID:'+name)
 return amount


def _int(value, name, *, minimum=0):
 if isinstance(value,bool):
  raise BudgetError('PILOT_BUDGET_CONFIG_INVALID:'+name)
 try:
  number=int(value)
 except (TypeError,ValueError):
  raise BudgetError('PILOT_BUDGET_CONFIG_INVALID:'+name) from None
 if number < minimum or str(number)!=str(value).strip():
  raise BudgetError('PILOT_BUDGET_CONFIG_INVALID:'+name)
 return number


def initialize(path, *, authorization, historical_estimated_yuan,
               historical_call_count, historical_pending_calls,
               pilot_limit_yuan, overall_limit_yuan, max_students,
               starts_at, ends_at):
 """Create once from aggregate history, or validate an existing ledger without resetting it.

 The copied baseline contains only aggregate cost/call metadata, never prior prompts,
 answers, provider payloads, or historical call records.
 """
 p=Path(path)
 baseline=_amount(historical_estimated_yuan,'historical_estimated_yuan',allow_zero=True)
 pilot_limit=_amount(pilot_limit_yuan,'pilot_limit_yuan')
 overall_limit=_amount(overall_limit_yuan,'overall_limit_yuan')
 call_count=_int(historical_call_count,'historical_call_count')
 pending_count=_int(historical_pending_calls,'historical_pending_calls')
 students=_int(max_students,'max_students',minimum=1)
 if pending_count:
  raise BudgetError('PILOT_BASELINE_HAS_PENDING_CALLS_STOP')
 if not isinstance(authorization,str) or not authorization.strip():
  raise BudgetError('PILOT_AUTHORIZATION_REQUIRED')
 if not isinstance(starts_at,str) or not starts_at.strip() or not isinstance(ends_at,str) or not ends_at.strip():
  raise BudgetError('PILOT_WINDOW_REQUIRED')
 if baseline+pilot_limit>overall_limit:
  raise BudgetError('PILOT_GLOBAL_BUDGET_EXCEEDED_STOP')

 expected={
  'authorization':authorization,
  'start_call':1,
  'limit_yuan':pilot_limit,
  'max_students':students,
  'starts_at':starts_at,
  'ends_at':ends_at,
  'historical_estimated_yuan':baseline,
  'historical_call_count':call_count,
 }
 if p.exists():
  d=read(p)
  if d.get('pilot_budget')!=expected or d.get('limit_yuan')!=overall_limit:
   raise BudgetError('PILOT_LEDGER_AUTHORIZATION_CONFLICT_STOP')
  calls=d.get('calls',[])
  if not isinstance(calls,list) or not calls:
   raise BudgetError('PILOT_LEDGER_BASELINE_MISSING_STOP')
  first=calls[0]
  if (first.get('task')!='HISTORICAL_ESTIMATED_BASELINE' or first.get('status')!='SETTLED'
      or float(first.get('estimated_yuan',-1))!=baseline
      or _int(first.get('historical_call_count',-1),'ledger_historical_call_count')!=call_count):
   raise BudgetError('PILOT_LEDGER_BASELINE_CONFLICT_STOP')
  if pending_total(calls):
   raise BudgetError('PILOT_LEDGER_PENDING_CALL_STOP')
  if window_total(calls)>overall_limit:
   raise BudgetError('PILOT_GLOBAL_BUDGET_EXCEEDED_STOP')
  if window_total(calls,expected['start_call'])>pilot_limit:
   raise BudgetError('BUDGET_PILOT_LIMIT_YUAN_STOP')
  return d

 d={
  'limit_yuan':overall_limit,
  'started_runs':0,
  'calls':[{
   'task':'HISTORICAL_ESTIMATED_BASELINE',
   'status':'SETTLED',
   'estimated_yuan':baseline,
   'historical_call_count':call_count,
  }],
  'pilot_budget':expected,
  'price_basis':'Prior-call aggregate from Owner original ledger; no raw history copied. New Pilot calls use live token usage and single-run hard caps.',
 }
 save(p,d)
 return d
