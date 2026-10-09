"""Invite-only WSGI gateway; no public admin endpoint or client-selected Brain mode."""
import hashlib,hmac,json,os,secrets,sqlite3,time,threading
from datetime import datetime
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlparse
from brain import Brain
from question_display import student_question,student_options
ROOT=Path(__file__).parent

class Pilot:
 def __init__(self,path,brain=None,origin='http://127.0.0.1:8766',enabled=False,
              max_invites=None,starts_at=None,ends_at=None):
  self.path=str(path);self.brain=brain or Brain(str(Path(path).with_suffix('.brain.sqlite3')))
  self.origin=origin.rstrip('/');self.enabled=enabled;self.lock=threading.Lock()
  self.max_invites=max_invites;self.starts_at=self._timestamp(starts_at) if starts_at else None
  self.ends_at=self._timestamp(ends_at) if ends_at else None
  if self.starts_at is not None and self.ends_at is not None and self.ends_at<=self.starts_at:
   raise ValueError('PILOT_WINDOW_INVALID')
  Path(path).parent.mkdir(parents=True,exist_ok=True)
  with self.db() as d:
   d.execute('CREATE TABLE IF NOT EXISTS invites(digest TEXT PRIMARY KEY,session TEXT,expires REAL,revoked INTEGER DEFAULT 0)')
   d.execute('CREATE TABLE IF NOT EXISTS tickets(digest TEXT PRIMARY KEY,invite TEXT,expires REAL)')
 def db(self):return sqlite3.connect(self.path,timeout=20)
 @staticmethod
 def digest(value):return hashlib.sha256(value.encode()).hexdigest()
 def invite(self,hours=24):
  code=secrets.token_urlsafe(24)
  with self.db() as d:
   if self.max_invites is not None and d.execute('SELECT COUNT(*) FROM invites').fetchone()[0]>=self.max_invites:
    raise ValueError('PILOT_INVITE_LIMIT_REACHED')
   d.execute('INSERT INTO invites(digest,expires) VALUES(?,?)',(self.digest(code),time.time()+hours*3600))
  return code
 @staticmethod
 def _timestamp(value):
  if not isinstance(value,str) or not value.strip():raise ValueError('PILOT_WINDOW_REQUIRED')
  try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
  except ValueError:raise ValueError('PILOT_WINDOW_INVALID') from None
  if parsed.tzinfo is None:raise ValueError('PILOT_WINDOW_TIMEZONE_REQUIRED')
  return parsed.timestamp()
 def _pilot_open(self):
  now=time.time()
  return (self.starts_at is None or now>=self.starts_at) and (self.ends_at is None or now<self.ends_at)
 def owner(self,token):
  with self.db() as d:
   row=d.execute('SELECT i.digest,i.session FROM tickets t JOIN invites i ON i.digest=t.invite WHERE t.digest=? AND t.expires>? AND i.expires>? AND i.revoked=0',(self.digest(token),time.time(),time.time())).fetchone()
  if not row:raise PermissionError('INVITE_REQUIRED')
  return row
 def login(self,code):
  with self.db() as d:
   row=d.execute('SELECT digest,expires FROM invites WHERE digest=? AND expires>? AND revoked=0',(self.digest(code),time.time())).fetchone()
   if not row:raise PermissionError('INVITE_INVALID_OR_EXPIRED')
   token=secrets.token_urlsafe(32);d.execute('INSERT INTO tickets VALUES(?,?,?)',(self.digest(token),row[0],min(row[1],time.time()+86400)))
  return token
 def operate(self,owner,data):
  identity,sid=owner;op=data.get('action')
  if op=='entry':return {'live_enabled':self.enabled}
  if op=='preview':
   if self.enabled:raise ValueError('PREVIEW_ONLY_WHEN_LIVE_DISABLED')
   return {'preview':True,'live_enabled':False,'question':'最近有没有一件事情，你愿意自己琢磨并继续做？说说具体过程和原因。','message':'这是首题界面预览。尚未调用AI，当前不能提交回答或生成发现。'}
  if op=='start':
   if sid:return self.view(self.brain.get(sid))
   if not self.enabled:raise ValueError('PILOT_NOT_RELEASED')
   if not self._pilot_open():raise ValueError('PILOT_WINDOW_CLOSED')
   if data.get('consent') is not True:raise ValueError('CONSENT_REQUIRED')
   state=self.brain.create('LIVE_MODEL');sid=state['session_id']
   with self.db() as d:d.execute('UPDATE invites SET session=? WHERE digest=?',(sid,identity))
   q={'context':{'question_text':'最近有没有一件事情，你愿意自己琢磨并继续做？说说具体过程和原因。','options':[],'scenario':'高中生日常课外活动'},'response_mode':'SHORT_TEXT','response_options':[],'target_id':'F01-process','intent':'了解具体活动过程中的内在动力','channel':'real_event'}
   state=self.brain.action({'session_id':sid,'action':'question','question':q,'expected_revision':state['revision'],'request_id':secrets.token_hex(16)})['state']
   return self.view(state)
  if not sid:raise ValueError('START_REQUIRED')
  s=self.brain.get(sid)
  if op=='view':return self.view(s)
  if op=='export':return {'session':self.view(s),'answers':[{'question':r['question_context']['question_text'],'answer':r['raw_answer'],
   'response_mode':r.get('response_mode','SHORT_TEXT'),'selected_option_id':r.get('selected_option_id'),
   'selected_option_text':r.get('selected_option_text'),'supplemental_text':r.get('supplemental_text')} for r in s['responses']]}
  if op not in ('answer','stop','micro_offer','micro_start','micro_decline','micro_submit','micro_feedback','micro_exit'):raise ValueError('ACTION_NOT_ALLOWED')
  # Keep the agreed Pilot window as a hard boundary for new work. Viewing,
  # exporting, and stopping remain available after the cutoff.
  if self.enabled and not self._pilot_open() and op not in ('stop','micro_exit'):
   raise ValueError('PILOT_WINDOW_CLOSED')
  if op in ('answer','micro_offer','micro_submit','micro_feedback') and not self.enabled:raise ValueError('PILOT_NOT_RELEASED')
  if s.get('failed_input') or s['effective_state']=='BLOCKED':raise ValueError('SESSION_BLOCKED_CONTACT_OWNER')
  p={'session_id':sid,'action':op,'expected_revision':data.get('revision'),'request_id':data.get('request_id')}
  if op in ('answer','micro_submit','micro_feedback'):p['answer']=data.get('answer')
  if op=='answer':p['selected_option_id']=data.get('selected_option_id')
  if op=='micro_offer':
   p['direction_id']=data.get('direction_id')
  if op=='micro_start':p['opt_in']=data.get('opt_in') is True
  result=self.brain.action(p);s=result['state']
  # No automatic network retries or unsolicited micro-experience launch.
  if not result.get('error') and op=='answer' and s['effective_state'] in ('ASK','PROBE','COUNTER_CHECK'):
   plan=s['decision']['task_data']['question_plan']
   response_mode=plan['response_mode'];labels=student_options(plan) if response_mode=='SINGLE_CHOICE' else []
   q={'context':{'question_text':student_question(plan),'options':[x['label'] for x in labels]+(['不确定'] if labels else []),'scenario':plan['distinguishes']},
    'response_mode':response_mode,'response_options':plan['response_options'],'target_id':plan['target_id'],'intent':s['decision']['next_question_intent'],'channel':plan['channel']}
   s=self.brain.action({'session_id':sid,'action':'question','question':q,'expected_revision':s['revision'],'request_id':p['request_id']+':next'})['state']
  return self.view(s)
 def view(self,s):
  pending=next((q for q in reversed(s['questions']) if not q['answered']),None)
  processing=bool(s.get('processing'))
  blocked=bool(s.get('failed_input') or s['effective_state']=='BLOCKED')
  now=self.brain.clock();m=s['micro'];elapsed=0 if m['started'] is None else max(0,now-m['started'])
  can_submit=m['status']=='RUNNING' and not m['submission_received'] and elapsed<180
  can_feedback=m['status'] in ('RUNNING','AWAITING_FEEDBACK') and m['feedback_count']==0 and elapsed<300 and (m['submission_received'] or elapsed>=180)
  message=''
  if blocked:message='本次处理未完成，已停止。请联系邀请你的人；这不代表对你的判断。'
  elif processing:message='正在处理已保存的回答，请等待；不会重复提交。'
  elif s['exploration_closed'] and s['effective_state'] in ('STOP','UNKNOWN') and any(mark in str(s.get('stop_reason') or '') for mark in ('Unknown','未知')):
   message='本轮探索已结束。当前信息不足以形成更进一步的结论；已保存的观察仍可查看。'
  elif s['exploration_closed'] and not s['display']['mirror'] and not s['display']['directions']:message='目前的信息还不足以形成结论。'
  mode=pending.get('response_mode','SHORT_TEXT') if pending else None
  options=([{'option_id':x['option_id'],'label':x['label']} for x in pending.get('response_options',[])]+[{'option_id':'UNSURE','label':'不确定'}]
   if pending and mode=='SINGLE_CHOICE' else [])
  return {'revision':s['revision'],'question':pending['question_context']['question_text'] if pending and not s['exploration_closed'] and not blocked and not processing else None,
   'response_mode':mode,'response_options':options,
   'question_count':len(s['questions']),'seconds_left':480 if s['started'] is None else max(0,int(480-now+s['started'])),
   'display':s['display'],'closed':s['exploration_closed'],'blocked':blocked,'processing':processing,'message':message,
   'micro':{'status':m['status'],'instruction':m['task']['instruction'] if m['task'] else None,'notice':m['task']['notice'] if m['task'] else None,
    'seconds_left':max(0,int(180-elapsed)),'feedback_seconds_left':max(0,int(300-elapsed)),
    'can_submit':can_submit and not blocked and not processing,'can_feedback':can_feedback and not blocked and not processing,
    'can_exit':m['status'] in ('OFFERED','RUNNING','AWAITING_FEEDBACK') and not blocked and not processing},'live_enabled':self.enabled}
 def __call__(self,environ,start_response):
  status='200 OK';headers=[('Content-Type','application/json; charset=utf-8'),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'"),('Referrer-Policy','no-referrer')]
  try:
   path=environ.get('PATH_INFO','/');method=environ.get('REQUEST_METHOD','GET')
   if method=='GET' and path in ('/','/pilot.js','/pilot.css'):
    name={'/':'pilot.html','/pilot.js':'pilot.js','/pilot.css':'pilot.css'}[path];body=(ROOT/name).read_bytes();headers[0]=('Content-Type',{'/':'text/html; charset=utf-8','/pilot.js':'text/javascript; charset=utf-8','/pilot.css':'text/css; charset=utf-8'}[path])
   else:
    if method!='POST' or path not in ('/pilot/login','/pilot/action'):raise ValueError('NOT_FOUND')
    if environ.get('HTTP_ORIGIN')!=self.origin:raise PermissionError('ORIGIN_REJECTED')
    if environ.get('CONTENT_TYPE','').split(';')[0]!='application/json':raise ValueError('JSON_REQUIRED')
    length=int(environ.get('CONTENT_LENGTH') or 0)
    if not 0<length<=32000:raise ValueError('REQUEST_SIZE')
    data=json.loads(environ['wsgi.input'].read(length))
    if not isinstance(data,dict):raise ValueError('JSON_OBJECT_REQUIRED')
    if not self.lock.acquire(False):
     status='429 Too Many Requests';body=json.dumps({'error':'当前正在处理一份回答，请稍后再试。'},ensure_ascii=False).encode()
    else:
     try:
      if path=='/pilot/login':
       code=data.get('code');
       if not isinstance(code,str) or len(code)>128:raise PermissionError('INVITE_INVALID')
       token=self.login(code);headers.append(('Set-Cookie','brain_pilot='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'+('; Secure' if self.origin.startswith('https://') else '')));out={'ok':True}
      else:
       cookie=SimpleCookie();cookie.load(environ.get('HTTP_COOKIE',''));token=cookie['brain_pilot'].value if 'brain_pilot' in cookie else '';out=self.operate(self.owner(token),data)
      body=json.dumps(out,ensure_ascii=False).encode()
     finally:self.lock.release()
  except PermissionError as e:status='403 Forbidden';body=json.dumps({'error':str(e)}).encode()
  except (ValueError,KeyError,TypeError) as e:status='400 Bad Request';body=json.dumps({'error':str(e)}).encode()
  except Exception:status='500 Internal Server Error';body=b'{"error":"SERVICE_ERROR"}'
  headers.append(('Content-Length',str(len(body))));start_response(status,headers);return [body]

def application_factory(config=None):
 # Live Pilot stays closed by default. Opening it requires explicit owner, time,
 # provider, persistent storage, and fail-stop spend-ledger configuration.
 c=os.environ if config is None else config
 origin=c.get('PILOT_ORIGIN','http://127.0.0.1:8766')
 hostname=c.get('RENDER_EXTERNAL_HOSTNAME')
 if not c.get('PILOT_ORIGIN') and hostname:origin='https://'+hostname
 enabled=c.get('PILOT_LIVE_ENABLED')=='1'
 path=c.get('PILOT_DB',str(ROOT/'data/pilot.sqlite3'))
 if not enabled:return Pilot(path,origin=origin,enabled=False)

 required=('PILOT_DATA_DIR','BRAIN_BUDGET_LEDGER','PILOT_AUTHORIZATION_ID',
  'PILOT_BUDGET_LIMIT_YUAN','PILOT_OVERALL_BUDGET_LIMIT_YUAN','PILOT_HISTORICAL_ESTIMATED_YUAN',
  'PILOT_HISTORICAL_CALL_COUNT','PILOT_HISTORICAL_PENDING_CALLS','PILOT_MAX_STUDENTS',
  'PILOT_START_AT','PILOT_END_AT','DASHSCOPE_API_KEY')
 missing=[name for name in required if not str(c.get(name,'')).strip()]
 if missing:raise RuntimeError('PILOT_RELEASE_CONFIG_INCOMPLETE:'+','.join(missing))
 parsed=urlparse(origin)
 if parsed.scheme!='https' or not parsed.hostname or parsed.path not in ('','/') or parsed.query or parsed.fragment:
  raise RuntimeError('PILOT_HTTPS_ORIGIN_REQUIRED')
 if c.get('PROVIDER','').lower() not in ('aliyun-bailian','bailian'):
  raise RuntimeError('PILOT_PROVIDER_MUST_BE_BAILIAN')
 if c.get('BAILIAN_THINKING')!='disabled':
  raise RuntimeError('PILOT_BAILIAN_THINKING_MUST_BE_DISABLED')
 data_dir=Path(c['PILOT_DATA_DIR']).resolve()
 db_path=Path(path).resolve();ledger_path=Path(c['BRAIN_BUDGET_LEDGER']).resolve()
 if db_path.parent!=data_dir or ledger_path.parent!=data_dir:
  raise RuntimeError('PILOT_STATE_MUST_USE_PERSISTENT_DATA_DIR')
 try:
  from adapter import AdapterError,BailianQwenAdapter
  adapter=BailianQwenAdapter(c)
 except (AdapterError,ValueError,RuntimeError) as e:
  raise RuntimeError('PILOT_BAILIAN_CONFIG_INVALID:'+str(e)) from None
 if adapter.metadata().get('model')!='qwen3.7-plus' or adapter.metadata().get('thinking')!='disabled':
  raise RuntimeError('PILOT_BAILIAN_MODEL_CONFIG_INVALID')
 from pilot_budget import initialize
 try:
  initialize(ledger_path,authorization=c['PILOT_AUTHORIZATION_ID'],
   historical_estimated_yuan=c['PILOT_HISTORICAL_ESTIMATED_YUAN'],
   historical_call_count=c['PILOT_HISTORICAL_CALL_COUNT'],
   historical_pending_calls=c['PILOT_HISTORICAL_PENDING_CALLS'],
   pilot_limit_yuan=c['PILOT_BUDGET_LIMIT_YUAN'],overall_limit_yuan=c['PILOT_OVERALL_BUDGET_LIMIT_YUAN'],
   max_students=c['PILOT_MAX_STUDENTS'],starts_at=c['PILOT_START_AT'],ends_at=c['PILOT_END_AT'])
 except ValueError as e:
  raise RuntimeError('PILOT_BUDGET_PREFLIGHT_FAILED:'+str(e)) from None
 return Pilot(path,origin=origin,enabled=True,max_invites=int(c['PILOT_MAX_STUDENTS']),
  starts_at=c['PILOT_START_AT'],ends_at=c['PILOT_END_AT'])
application=application_factory()
if __name__=='__main__':
 from wsgiref.simple_server import make_server
 with make_server('127.0.0.1',8766,application) as server:server.serve_forever()
