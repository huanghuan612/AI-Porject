"""State, budget, durable events and independent Brain test entry. No Lovable dependency."""
import copy,hashlib,json,sqlite3,time,uuid
from pathlib import Path
from adapter import make_adapter,AdapterError
from engine import Pipeline,RuleError,require,RULE_HASH,ROOT,eligible
from contracts import FIELDS,BASE,validate,MICRO
VERSION='0.3.14-offline-repair-candidate'

def dump(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
def sha(x):return hashlib.sha256(dump(x).encode()).hexdigest()
class Brain:
 def __init__(self,path=None,clock=time.time,adapter_factory=make_adapter):
  self.path=str(path or ROOT/'data/brain-v02.sqlite3');self.clock=clock;self.adapter_factory=adapter_factory
  Path(self.path).parent.mkdir(parents=True,exist_ok=True)
  with self.db() as d:
   d.execute('CREATE TABLE IF NOT EXISTS live_sessions(id TEXT PRIMARY KEY,revision INTEGER,payload TEXT)')
   d.execute('CREATE TABLE IF NOT EXISTS live_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT,request_id TEXT,input_hash TEXT,record TEXT,UNIQUE(session_id,request_id))')
 def db(self):
  d=sqlite3.connect(self.path,timeout=20);d.row_factory=sqlite3.Row;return d
 def create(self,mode='MANUAL_REPLAY'):
  require(mode in ('MANUAL_REPLAY','LIVE_MODEL'),'MODE_REQUIRED')
  sid=uuid.uuid4().hex
  s={'session_id':sid,'revision':0,'version':VERSION,'rule_hash':RULE_HASH,'mode':mode,'processing':None,
   'started':None,'questions':[],'target_counts':{},'clarification_counts':{},'responses':[], 'response_meta':{},
   'evidence':{},'student_state':{k:[] for k in FIELDS},'hypotheses':{},'hypothesis_audits':{},'competitions':[],
   'contradictions':[],'decision':None,'gates':{},'display':{'mirror':None,'directions':[]},'direction_updates':{},
   'exploration_closed':False,'budget_exhausted':False,'effective_state':'ASK','stop_reason':None,
   'micro':{'task':None,'status':'NOT_STARTED','started':None,'submission_received':False,'feedback_count':0,'updates':[]},'last_output_contract':None}
  with self.db() as d:d.execute('INSERT INTO live_sessions VALUES(?,?,?)',(sid,0,dump(s)))
  return s
 def get(self,sid):
  with self.db() as d:r=d.execute('SELECT payload FROM live_sessions WHERE id=?',(sid,)).fetchone()
  if not r:raise ValueError('SESSION_NOT_FOUND')
  s=json.loads(r['payload']);return self.sync_budget(s)
 def sync_budget(self,s):
  if not s['exploration_closed'] and s['effective_state']!='BLOCKED' and s['started'] is not None and self.clock()-s['started']>=480:
   s['budget_exhausted']=True;s['exploration_closed']=True;s['stop_reason']='TIME_LIMIT'
   if s['micro']['status'] not in ('RUNNING','AWAITING_FEEDBACK'):s['effective_state']='UNKNOWN' if not s['display']['mirror'] and not s['display']['directions'] else 'STOP'
  return s
 def events(self,sid):
  self.get(sid)
  with self.db() as d:return [json.loads(r['record']) for r in d.execute('SELECT record FROM live_events WHERE session_id=? ORDER BY seq',(sid,))]
 def save(self,s,old_revision,req,fingerprint,record):
  with self.db() as d:
   d.execute('BEGIN IMMEDIATE')
   row=d.execute('SELECT revision FROM live_sessions WHERE id=?',(s['session_id'],)).fetchone()
   require(row and row['revision']==old_revision,'REVISION_CONFLICT')
   s['revision']=old_revision+1
   record.update(session_id=s['session_id'],revision=s['revision'],state=copy.deepcopy(s))
   d.execute('UPDATE live_sessions SET revision=?,payload=? WHERE id=?',(s['revision'],dump(s),s['session_id']))
   d.execute('INSERT INTO live_events(session_id,request_id,input_hash,record) VALUES(?,?,?,?)',(s['session_id'],req,fingerprint,dump(record)))
  return record
 def action(self,p):
  require(isinstance(p,dict),'JSON_OBJECT_REQUIRED')
  for key in ('session_id','request_id','expected_revision','action'):require(key in p,'MISSING:'+key)
  require(type(p['expected_revision']) is int,'REVISION_INTEGER_REQUIRED')
  require(isinstance(p['request_id'],str) and bool(p['request_id']),'REQUEST_ID_REQUIRED')
  sid=p['session_id'];fingerprint=sha(p)
  with self.db() as d:r=d.execute('SELECT * FROM live_events WHERE session_id=? AND request_id=?',(sid,p['request_id'])).fetchone()
  if r:
   require(r['input_hash']==fingerprint,'IDEMPOTENCY_KEY_REUSED');return json.loads(r['record'])
  s=self.get(sid);require(s['revision']==p['expected_revision'],'REVISION_CONFLICT')
  require(not s['processing'] or p['action']=='retry','SESSION_PROCESSING_OR_INTERRUPTED')
  rev=s['revision'];logs=[];record={'version':VERSION,'rule_hash':RULE_HASH,'mode':s['mode'],'action':p['action'],'model_calls':logs,'product_rule_result':'PASS','displayed_text':None,'error':None}
  operation=p['action']
  # Infrastructure-only operations never call a model.
  if operation=='question':self.question(s,p)
  elif operation=='stop':
   s['exploration_closed']=True;s['effective_state']='STOP';s['stop_reason']='STUDENT_STOPPED'
  elif operation=='micro_start':
   require(p.get('opt_in') is True,'D15_EXPLICIT_OPT_IN_REQUIRED');require(s['micro']['task'] is not None and s['micro']['status']=='OFFERED','MICRO_TASK_NOT_OFFERED')
   s['micro'].update(status='RUNNING',started=self.clock());s['exploration_closed']=True;s['effective_state']='MICRO_EXPERIENCE'
  elif operation in ('micro_decline','micro_exit'):
   require(s['micro']['task'] is not None,'NO_MICRO_TASK')
   require(s['micro']['status'] in ('OFFERED','RUNNING','AWAITING_FEEDBACK'),'MICRO_ALREADY_FINISHED')
   s['micro']['status']='DECLINED' if operation=='micro_decline' else 'EXITED'
   s['micro']['updates']=[{'target_type':'HYPOTHESIS','target_id':h,'outcome':'MAINTAIN','evidence_ids':[],'reason':'未取得新的有效行为信息；拒绝/退出本身不推断兴趣或能力','not_based_only_on_completion_score_speed_exit':True} for h in s['micro']['task']['target_hypothesis']]
   s['exploration_closed']=True;s['effective_state']='UNKNOWN';s['stop_reason']=operation.upper()
  elif operation=='micro_offer':
   require(s['micro']['task'] is None,'D15_ONLY_ONE_TASK')
   adapter=self.adapter_factory(s['mode'],p.get('replay',{}));pipe=Pipeline(adapter,logs)
   direction_id=p.get('direction_id');valid_directions={d['direction_id']:d for d in s['display']['directions']}
   require(direction_id is None or direction_id in valid_directions,'DIRECTION_GATE_NOT_PASSED')
   rg='MICRO-'+uuid.uuid4().hex[:12]
   try:
    out=pipe.call('micro_task',s,{'mode':'PERSONALIZED' if direction_id else 'NEUTRAL','direction':valid_directions.get(direction_id),'assigned_response_group_id':rg})
    task=out['task_data']['task'];validate(task,MICRO)
    require(task['response_group_id']==rg,'MICRO_RESPONSE_GROUP_MISMATCH')
    require(task['direction_id']==direction_id and task['mode']==('PERSONALIZED' if direction_id else 'NEUTRAL'),'D14_NO_FAKE_PERSONALIZATION')
    for k in ('instruction','what_is_being_tested','observable_support_signal','observable_counter_signal','ambiguous_signal'):require(bool(task[k].strip()),'MICRO_SIGNAL_REQUIRED:'+k)
    require(len({task[k] for k in ('observable_support_signal','observable_counter_signal','ambiguous_signal')})==3,'MICRO_SIGNALS_MUST_DIFFER')
    require(len(task['target_hypothesis'])==len(set(task['target_hypothesis'])),'DUPLICATE_MICRO_TARGET')
    require(all(h in s['hypotheses'] for h in task['target_hypothesis']),'MICRO_UNKNOWN_HYPOTHESIS')
    if direction_id:require(set(task['target_hypothesis'])==set(valid_directions[direction_id]['supporting_hypothesis_ids']),'MICRO_DIRECTION_HYPOTHESIS_MISMATCH')
    else:require('这是为了获得新信息，目前还不能判断它是否适合你' in task['notice'],'D14_NEUTRAL_DISCLOSURE_REQUIRED')
    checked=pipe.call('output_check',s,{'micro_task':task,'output_id':task['task_id']})
    audits={x['output_id']:x for x in checked['task_data']['checks']};a=audits.get(task['task_id'])
    require(a and all(a[k] for k in ('scope_preserved','trace_semantically_valid','not_personality_or_career_fit','uncertainty_honest')),'MICRO_TASK_AUDIT_FAILED')
    s['micro'].update(task=task,status='OFFERED');pipe.mark()
   except (ValueError,AdapterError) as e:record.update(product_rule_result='BLOCKED',error=str(e))
  elif operation in ('answer','mirror_feedback','micro_submit','micro_feedback','retry'):
   if operation=='retry':
    require(s.get('failed_input') or s['processing'],'NO_FAILED_INPUT_TO_RETRY')
    require(bool(s['responses']),'NO_SAVED_INPUT')
    response=s['responses'][-1];input_operation=response['kind']
   else:
    answer=p.get('answer');require(isinstance(answer,str) and bool(answer.strip()) and len(answer)<=12000,'ANSWER_REQUIRED_MAX_12000')
    response=self.make_response(s,p);input_operation=operation
    s['responses'].append(response);rg=response['response_group_id']
    s['response_meta'][rg]={'dependency_root':response['dependency_root'],'dependency_roots':response.get('dependency_roots',[response['dependency_root']]),'counter_check':response['counter_check']}
   micro=input_operation.startswith('micro_')
   # Commit original input before network inference. Crash leaves a visible interrupted receipt.
   s['processing']=p['request_id']
   receipt=self.save(s,rev,p['request_id']+':received',fingerprint,{'action':operation,'phase':'INPUT_SAVED','raw_response':response,'mode':s['mode']})
   rev=s['revision'];s['processing']=None
   try:
    adapter=self.adapter_factory(s['mode'],p.get('replay',{}));pipe=Pipeline(adapter,logs)
    result=pipe.process(s,response,micro=micro);s=result
    if input_operation=='answer':
     if len(s['questions'])>=6:s['budget_exhausted']=True;s['exploration_closed']=True;s['stop_reason']='QUESTION_LIMIT'
    self.sync_budget(s)
    self.effective_action(s)
    require(s['effective_state']!='BLOCKED',s['stop_reason'] or 'SELECTED_ACTION_GATE_BLOCKED')
    if micro:
     if input_operation=='micro_submit':s['micro']['status']='AWAITING_FEEDBACK'
     else:s['micro']['status']='COMPLETED'
     s['effective_state']='STOP';s['exploration_closed']=True
     for did,u in s['direction_updates'].items():
      if u['outcome']=='OVERTURN':s['display']['directions']=[d for d in s['display']['directions'] if d['direction_id']!=did]
    s['failed_input']=False
   except (ValueError,AdapterError) as e:
    record.update(product_rule_result='BLOCKED',error=str(e));s['effective_state']='BLOCKED';s['failed_input']=True;s['last_failure_code']=str(e)
    if logs:logs[-1]['product_rule_decision']='BLOCKED'
    # Raw input remains; partially processed model changes do not enter committed state.
  elif operation=='recover_interrupted':raise ValueError('USE_SEPARATE_RECOVERY_ENDPOINT')
  else:raise ValueError('UNKNOWN_ACTION')
  if record['product_rule_result']=='BLOCKED':
   s['effective_state']='BLOCKED'
   if logs:logs[-1]['product_rule_decision']='BLOCKED'
  s['processing']=None;record['displayed_text']=s['display'] if record['product_rule_result']=='PASS' else None
  return self.save(s,rev,p['request_id'],fingerprint,record)

 def question(self,s,p):
  require(not s['exploration_closed'],'EXPLORATION_CLOSED')
  require(not s['questions'] or s['questions'][-1]['answered'],'PENDING_QUESTION')
  if len(s['questions'])>=6:raise RuleError('D12_QUESTION_LIMIT')
  q=p.get('question');require(isinstance(q,dict),'QUESTION_REQUIRED')
  from contracts import QC
  validate(q['context'],QC)
  response_mode=q.get('response_mode','SHORT_TEXT')
  response_options=q.get('response_options',[])
  require(response_mode in ('SHORT_TEXT','SINGLE_CHOICE'),'QUESTION_RESPONSE_MODE_INVALID')
  require(isinstance(response_options,list),'QUESTION_RESPONSE_OPTIONS_INVALID')
  if response_mode=='SHORT_TEXT':
   require(not response_options and not q['context']['options'],'SHORT_TEXT_OPTIONS_MUST_BE_EMPTY')
   if s['mode']=='LIVE_MODEL':
    count=sum(x.get('response_mode','SHORT_TEXT')=='SHORT_TEXT' for x in s['questions'])
    require(count<2,'SHORT_TEXT_QUESTION_LIMIT')
  else:
   require(s['mode']=='LIVE_MODEL','CHOICE_QUESTION_LIVE_ONLY')
   from question_display import student_options
   expected=student_options({'response_options':response_options})
   require([x['label'] for x in expected]+['不确定']==q['context']['options'],'QUESTION_OPTIONS_CONTEXT_MISMATCH')
  for k in ('target_id','intent','channel'):require(isinstance(q.get(k),str) and bool(q[k].strip()),'QUESTION_'+k+'_REQUIRED')
  require(s['target_counts'].get(q['target_id'],0)<2,'D12_TARGET_LIMIT')
  plan=(s['decision'] or {}).get('task_data',{}).get('question_plan')
  if s['decision']:
   require(s['decision']['next_action'].startswith('ASK_') and plan is not None,'NEXT_ACTION_NOT_QUESTION')
   require(q['target_id']==plan['target_id'] and q['channel']==plan['channel'],'QUESTION_MUST_FOLLOW_APPROVED_INTENT')
   if s['mode']=='LIVE_MODEL':
    require(response_mode==plan.get('response_mode') and response_options==plan.get('response_options'),'QUESTION_RESPONSE_PLAN_MISMATCH')
  clarify=plan['clarifies_evidence_id'] if plan else None
  if clarify:
   require(s['clarification_counts'].get(clarify,0)<1,'D08_ONE_CLARIFICATION');s['clarification_counts'][clarify]=1
  parent=q.get('parent_question_id')
  if plan and s['decision']['next_action']=='ASK_PROBE' and not parent and s['questions']:parent=s['questions'][-1]['question_id']
  root=None
  if parent:
   match=next((x for x in s['questions'] if x['question_id']==parent),None);require(match is not None,'PARENT_QUESTION_UNKNOWN');root=match['dependency_root']
  qid='Q'+str(len(s['questions'])+1);rg='RG'+str(len(s['questions'])+1)
  question={'question_id':qid,'question_context':q['context'],'target_id':q['target_id'],'intent':q['intent'],'channel':q['channel'],
   'response_mode':response_mode,'response_options':response_options,
   'response_group_id':rg,'dependency_root':root or rg,'counter_check':bool(plan and plan['counter_check']),
   'clarifies_evidence_id':clarify,'answered':False,'issued_at':self.clock()}
  if s['started'] is None:s['started']=self.clock()
  s['questions'].append(question);s['target_counts'][q['target_id']]=s['target_counts'].get(q['target_id'],0)+1
  s['effective_state']={'ASK_ANCHOR':'ASK','ASK_PROBE':'PROBE','ASK_COUNTER':'COUNTER_CHECK'}.get((s['decision'] or {}).get('next_action'),'ASK')

 def make_response(self,s,p):
  op=p['action'];now=self.clock()
  if op=='answer':
   require(not s['exploration_closed'],'EXPLORATION_CLOSED')
   require(s['questions'] and not s['questions'][-1]['answered'],'NO_PENDING_QUESTION')
   q=s['questions'][-1];q['answered']=True
   selected_id=p.get('selected_option_id');selected_text=None
   if q.get('response_mode','SHORT_TEXT')=='SINGLE_CHOICE':
    options={x['option_id']:x['label'] for x in q.get('response_options',[])};options['UNSURE']='不确定'
    require(selected_id in options,'CHOICE_SELECTION_REQUIRED')
    selected_text=options[selected_id]
    require(p['answer']==selected_text,'CHOICE_RAW_ANSWER_MISMATCH')
   else:require(selected_id is None,'SHORT_TEXT_CANNOT_HAVE_CHOICE')
   return {'question_id':q['question_id'],'question_context':q['question_context'],'response_group_id':q['response_group_id'],
    'raw_answer':p['answer'],'dependency_root':q['dependency_root'],'counter_check':q['counter_check'],'channel':q['channel'],
    'clarifies_evidence_id':q['clarifies_evidence_id'],'kind':op,'received_at':now,
    'response_mode':q.get('response_mode','SHORT_TEXT'),'selected_option_id':selected_id,
    'selected_option_text':selected_text,'supplemental_text':p['answer'] if q.get('response_mode','SHORT_TEXT')=='SHORT_TEXT' else None}
  if op=='mirror_feedback':
   m=s['display']['mirror'];require(m is not None,'NO_DISPLAYED_MIRROR')
   roots={s['response_meta'][s['evidence'][e]['response_group_id']]['dependency_root'] for e in m['evidence_ids']}
   return {'question_id':'FEEDBACK-'+m['output_id'],'question_context':{'question_text':'学生主动对当前观察补充或修正','options':[],'scenario':m['text']},
    'response_group_id':'FEEDBACK-'+uuid.uuid4().hex[:10],'raw_answer':p['answer'],'dependency_root':sorted(roots)[0],
    'dependency_roots':sorted(roots),'counter_check':False,'channel':'voluntary_feedback','clarifies_evidence_id':None,'kind':op,'received_at':now,
    'response_mode':'SHORT_TEXT','selected_option_id':None,'selected_option_text':None,'supplemental_text':p['answer']}
  micro=s['micro'];require(micro['started'] is not None,'D15_OPT_IN_REQUIRED')
  elapsed=now-micro['started'];require(elapsed<=300,'D15_TOTAL_FIVE_MINUTES')
  task=micro['task']
  if op=='micro_submit':
   require(micro['status']=='RUNNING' and not micro['submission_received'],'D15_ONE_TASK_SUBMISSION')
   require(elapsed<=180,'D15_TASK_THREE_MINUTES');micro['submission_received']=True
   question={'question_text':task['instruction'],'options':[],'scenario':task['what_is_being_tested']}
  else:
   require(micro['status'] in ('RUNNING','AWAITING_FEEDBACK') and (micro['submission_received'] or elapsed>=180),'TASK_NOT_FINISHED')
   require(micro['feedback_count']==0,'D15_ONE_OPTIONAL_FEEDBACK');micro['feedback_count']=1
   question={'question_text':'可选：对刚才任务的过程和感受补充一句','options':[],'scenario':task['instruction']}
  return {'question_id':task['task_id']+('::feedback' if op=='micro_feedback' else ''),'question_context':question,
   'response_group_id':task['response_group_id'],'raw_answer':p['answer'],'dependency_root':task['response_group_id'],
   'counter_check':True,'channel':'micro_experience','clarifies_evidence_id':None,'kind':op,'received_at':now,
   'response_mode':'SHORT_TEXT','selected_option_id':None,'selected_option_text':None,'supplemental_text':p['answer']}

 def effective_action(self,s):
  if s['budget_exhausted'] or s['exploration_closed']:
   s['effective_state']='STOP' if s['display']['mirror'] or s['display']['directions'] else 'UNKNOWN'
   s['last_output_contract']['next_action']='STOP';s['last_output_contract']['stop_reason']=s['stop_reason'] or 'EXPLORATION_CLOSED';return
  d=s['decision'];a=d['next_action'];plan=d['task_data']['question_plan']
  if a=='STOP':s['exploration_closed']=True;s['stop_reason']=d['stop_reason'];s['effective_state']='STOP' if s['display']['mirror'] or s['display']['directions'] else 'UNKNOWN'
  elif a.startswith('ASK_'):
   if s['target_counts'].get(plan['target_id'],0)>=2:
    # Do not invent another target or an automatic stop rule.
    s['effective_state']='BLOCKED';s['stop_reason']='QUESTION_PLAN_EXCEEDS_TARGET_BUDGET'
   else:s['effective_state']={'ASK_ANCHOR':'ASK','ASK_PROBE':'PROBE','ASK_COUNTER':'COUNTER_CHECK'}[a]
  elif a=='MIRROR_READY':s['effective_state']='MIRROR' if s['gates']['mirror']['status']=='PASS' else 'BLOCKED'
  elif a=='RETURN_SMALL_INSIGHT':s['effective_state']='SMALL_INSIGHT' if s['gates']['small_insight']['status']=='PASS' else 'BLOCKED'
  if s['display']['directions'] and s['effective_state'] in ('MIRROR','SMALL_INSIGHT'):s['effective_state']='DIRECTION'

 def trace(self,sid,identifier):
  s=self.get(sid);mirror=s['display']['mirror'];dirs={d['direction_id']:d for d in s['display']['directions']}
  if identifier in s['hypotheses']:hids=[identifier];claim=s['hypotheses'][identifier]['claim']
  elif mirror and identifier==mirror['output_id']:hids=mirror['hypothesis_ids'];claim=mirror['text']
  elif identifier in dirs:hids=dirs[identifier]['supporting_hypothesis_ids'];claim=dirs[identifier]['theme']
  else:raise ValueError('TRACE_ID_NOT_FOUND')
  return {'claim':claim,'hypotheses':[{'hypothesis':s['hypotheses'][hid],
   'support':[s['evidence'][e] for e in s['hypotheses'][hid]['supporting_evidence_ids']],
   'counter':[s['evidence'][e] for e in s['hypotheses'][hid]['contradicting_evidence_ids']]} for hid in hids]}
