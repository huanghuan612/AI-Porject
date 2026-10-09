"""Transport boundary only. Never invent semantic judgments or change evidence status."""
import copy

def normalize_validation(out,history,new_ids):
 result=copy.deepcopy(out);archived=[]
 for key in ('evidence_validation','evidence_status'):
  rows=result[key];ids=[r['evidence_id'] for r in rows]
  if len(ids)!=len(set(ids)):raise ValueError('DUPLICATE_VALIDATION_REFERENCE')
  kept=[]
  for row in rows:
   eid=row['evidence_id']
   if eid in new_ids:kept.append(row);continue
   if eid not in history:raise ValueError('VALIDATION_UNKNOWN_HISTORY_ID:'+eid)
   old=history[eid]
   if key=='evidence_status':
    if row['status']!=old['evidence_status']:kept.append(row);continue
    if row['clarifying_evidence_ids']:kept.append(row);continue
   else:
    semantic_ok=row['valid'] and all(row[k] for k in ('supported_by_raw','context_preserved','attribution_correct','constructs_separated'))
    if old['evidence_status']=='ACTIVE' and (not semantic_ok or row['suspicious'] or row['unknown_only']):raise ValueError('HISTORICAL_VALIDATION_CONFLICT:'+eid)
    if old['evidence_status']=='INVALID' and semantic_ok:raise ValueError('HISTORICAL_VALIDATION_CONFLICT:'+eid)
    if old['evidence_status'] not in ('ACTIVE','INVALID'):raise ValueError('HISTORICAL_REVIEW_REQUIRES_EXPLICIT_TRANSITION:'+eid)
   archived.append({'field':key,'row':copy.deepcopy(row)})
  result[key]=kept
 if {r['evidence_id'] for r in result['evidence_validation']}!=set(new_ids):raise ValueError('VALIDATION_MUST_COVER_NEW_EVIDENCE')
 return result,archived

def exact_ids(item,ids):
 schema={'type':'array','items':copy.deepcopy(item),'minItems':len(ids),'maxItems':len(ids)}
 schema['items']['properties']['evidence_id']={'enum':list(ids)} if ids else False
 if ids:schema['allOf']=[{'contains':{'properties':{'evidence_id':{'const':eid}},'required':['evidence_id']},'minContains':1,'maxContains':1} for eid in ids]
 return schema

def constrain_new_validation_pairs(schema,ids):
 """Reflect existing D08/R06 status gates for current-turn evidence only."""
 failed=[{'properties':{key:{'const':False}},'required':[key]} for key in
  ('valid','supported_by_raw','context_preserved','attribution_correct','constructs_separated')]
 status=schema['properties']['evidence_status']
 for eid in ids:
  status.setdefault('allOf',[]).append({'contains':{'properties':{'evidence_id':{'const':eid}},
   'required':['evidence_id']},'minContains':1,'maxContains':1})
  def validation_has(row):
   return {'properties':{'evidence_validation':{'contains':{'allOf':[
    {'properties':{'evidence_id':{'const':eid}},'required':['evidence_id']},row]}}},
    'required':['evidence_validation']}
  def status_is(value):
   return {'properties':{'evidence_status':{'contains':{'properties':{
    'evidence_id':{'const':eid},'status':{'const':value}},
    'required':['evidence_id','status']}}},'required':['evidence_status']}
  schema.setdefault('allOf',[]).extend([
   {'if':validation_has({'properties':{'suspicious':{'const':True}},'required':['suspicious']}),
    'then':status_is('UNCERTAIN')},
   {'if':validation_has({'properties':{'unknown_only':{'const':True}},'required':['unknown_only']}),
    'then':status_is('UNKNOWN')},
   {'if':validation_has({'anyOf':failed}),'then':status_is('INVALID')},
  ])
 return schema
