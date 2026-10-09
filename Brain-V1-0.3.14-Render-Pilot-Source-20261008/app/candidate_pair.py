"""One transport request for two candidate generators, followed by separate output audit."""
import copy,json,hashlib
from pathlib import Path
from adapter import AdapterError
from compact_transport import compact_schema
from contracts import task_schema,validate

def parse(raw):
 def pairs(items):
  out={}
  for k,v in items:
   if k in out:raise ValueError('DUPLICATE_JSON_KEY')
   out[k]=v
  return out
 if len(raw)>2_000_000:raise ValueError('OUTPUT_TOO_LARGE')
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))

def fingerprint(layers):
 data={k:v for k,v in layers.items() if k!='current_task'};data['context']=layers['current_task']['context']
 return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

class CandidatePairAdapter:
 compact_transport=True
 def __init__(self,inner):self.inner=inner;self.pending=None;self.last_batch_trace=None
 def metadata(self):return {**self.inner.metadata(),'candidate_transport':'paired_generation_separate_audit'}
 def call(self,task,layers,schema):
  control=getattr(self.inner,'control',None)
  if control:control.check()
  self.last_batch_trace=None
  if task=='direction' and self.pending:
   saved=self.pending;self.pending=None
   if saved['fingerprint']!=fingerprint(layers):raise AdapterError('CANDIDATE_SNAPSHOT_MISMATCH')
   validate(saved['output'],schema)
   self.last_batch_trace={'paired_with':'mirror','network_request':False,'snapshot_hash':saved['fingerprint']}
   return json.dumps(saved['output'],ensure_ascii=False)
  self.pending=None
  if task!='mirror':return self.inner.call(task,layers,schema)
  direction_schema,_=compact_schema(task_schema('direction'))
  bundle={'type':'object','properties':{'mirror':schema,'direction':direction_schema},'required':['mirror','direction'],'additionalProperties':False}
  request=copy.deepcopy(layers)
  instructions=json.loads((Path(__file__).parent/'prompts/tasks.json').read_text())
  request['current_task']={'name':'candidate_pair','instruction':'Generate two independent candidates from the same validated state. Return separate mirror and direction objects. Do not audit or approve either candidate. A later independent output_check request performs the audit. Each subtask retains its own schema and responsibility.','subtasks':{'mirror':layers['current_task']['instruction'],'direction':instructions['direction']},'context':layers['current_task']['context'],'schema':bundle}
  raw=self.inner.call('candidate_pair',request,bundle)
  self.last_batch_trace={'network_request':True,'snapshot_hash':fingerprint(layers),'raw_bundle':raw}
  out=parse(raw);validate(out,bundle)
  self.pending={'fingerprint':fingerprint(layers),'output':copy.deepcopy(out['direction'])}
  return json.dumps(out['mirror'],ensure_ascii=False)
