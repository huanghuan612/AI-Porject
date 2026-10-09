"""Provider-neutral interface plus HTTP Chat Completions-compatible implementation."""
import copy,json,os,urllib.request,urllib.error
from urllib.parse import urlparse

class AdapterError(Exception):pass
class ModelAdapter:
 def call(self,task,layers,schema):raise NotImplementedError
 def metadata(self):return {'mode':'UNSPECIFIED'}
class ManualReplayAdapter(ModelAdapter):
 def __init__(self,outputs):self.outputs=outputs
 def call(self,task,layers,schema):
  if task not in self.outputs:raise AdapterError('MANUAL_REPLAY_MISSING_TASK:'+task)
  x=copy.deepcopy(self.outputs[task])
  # Explicit fixture identity binding only; never rewrite raw answers or semantic content.
  if isinstance(x,dict):
   ctx=layers['current_task']['context']
   if task=='micro_task' and x.get('task_data',{}).get('task',{}).get('response_group_id')=='$ASSIGNED_RESPONSE_GROUP_ID':
    x['task_data']['task']['response_group_id']=ctx['assigned_response_group_id']
   for e in x.get('new_evidence',[]):
    if e['response_group_id']=='$MICRO_RESPONSE_GROUP_ID':e['response_group_id']=ctx['input']['response_group_id']
  return x if isinstance(x,str) else json.dumps(x,ensure_ascii=False)
 def metadata(self):return {'mode':'MANUAL_REPLAY','provider':None,'model':None}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
class CompatibleHTTPAdapter(ModelAdapter):
 def __init__(self,config=None):
  c=config or os.environ
  self.provider=c.get('PROVIDER','');self.model=c.get('MODEL','');self.base=c.get('API_BASE','');self.key=c.get('API_KEY','')
  missing=[k for k,v in [('PROVIDER',self.provider),('MODEL',self.model),('API_BASE',self.base),('API_KEY',self.key)] if not v]
  if missing:raise AdapterError('MODEL_CONFIG_MISSING:'+','.join(missing))
  if self.provider not in ('openai-compatible','openai'):raise AdapterError('PROVIDER_NOT_IMPLEMENTED:'+self.provider)
  u=urlparse(self.base)
  if u.username or u.password or u.query or u.fragment:raise AdapterError('API_BASE_MUST_NOT_CONTAIN_CREDENTIALS_OR_QUERY')
  if u.scheme!='https' and not (u.scheme=='http' and u.hostname in ('localhost','127.0.0.1','::1')):raise AdapterError('HTTPS_REQUIRED')
  self.url=self.base.rstrip('/')+'/chat/completions';self.timeout=45
 def metadata(self):return {'mode':'LIVE_MODEL','provider':self.provider,'model':self.model}
 def call(self,task,layers,schema):
  payload={'model':self.model,'messages':[{'role':'system','content':layers['frozen_system_rules']},
   {'role':'user','content':json.dumps({k:v for k,v in layers.items() if k!='frozen_system_rules'},ensure_ascii=False)}],
   'response_format':{'type':'json_object'},'stream':False}
  req=urllib.request.Request(self.url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
  try:
   with urllib.request.build_opener(NoRedirect()).open(req,timeout=self.timeout) as response:
    raw=response.read(2_000_001)
   if len(raw)>2_000_000:raise AdapterError('MODEL_RESPONSE_TOO_LARGE')
   data=json.loads(raw);choice=data['choices'][0]
   if choice.get('finish_reason') not in ('stop',None):raise AdapterError('MODEL_RESPONSE_NOT_COMPLETE')
   content=choice['message']['content']
   if not isinstance(content,str):raise AdapterError('MODEL_CONTENT_NOT_TEXT')
   return content.replace(self.key,'[REDACTED_API_KEY]')
  except urllib.error.HTTPError as e:raise AdapterError('MODEL_HTTP_'+str(e.code)) from None
  except (urllib.error.URLError,TimeoutError):raise AdapterError('MODEL_NETWORK_OR_TIMEOUT') from None
  except (KeyError,IndexError,ValueError,TypeError):raise AdapterError('MODEL_PROTOCOL_ERROR') from None

def safe_http_error(error,key,task):
 import re
 detail={'status':error.code,'task':task}
 try:
  payload=json.loads(error.read(32768))
  body=payload.get('error',{}) if isinstance(payload,dict) else {}
  if isinstance(body,dict):
   for field in ('type','code','param','message'):
    value=body.get(field)
    if isinstance(value,(str,int)):
     text=str(value).replace(key,'[REDACTED_API_KEY]') if key else str(value)
     text=re.sub(r'sk-[A-Za-z0-9_-]+','[REDACTED_API_KEY]',text)
     text=re.sub(r'Bearer\s+[^\s"\\]+','Bearer [REDACTED]',text,flags=re.I)
     detail[field]=text[:2000]
 except Exception:detail['message']='HTTP error details unavailable or non-JSON; body not logged.'
 request_id=error.headers.get('x-request-id') if error.headers else None
 if request_id and re.fullmatch(r'[A-Za-z0-9_-]{1,160}',request_id):detail['request_id']=request_id
 return 'MODEL_HTTP_'+str(error.code)+':'+json.dumps(detail,ensure_ascii=False)

class OpenAIResponsesAdapter(ModelAdapter):
 """Responses transport; existing Pipeline remains the JSON Schema authority."""
 def __init__(self,config=None):
  c=os.environ if config is None else config
  self.provider='openai';self.model=c.get('MODEL') or 'gpt-5.6-sol'
  self.reasoning=c.get('REASONING') or 'high'
  self.key=c.get('OPENAI_API_KEY') or c.get('API_KEY') or ''
  if not self.key:raise AdapterError('MODEL_CONFIG_MISSING:OPENAI_API_KEY')
  base=c.get('API_BASE') or 'https://api.openai.com/v1'
  u=urlparse(base)
  if u.username or u.password or u.query or u.fragment:raise AdapterError('API_BASE_MUST_NOT_CONTAIN_CREDENTIALS_OR_QUERY')
  if u.scheme!='https' or u.hostname!='api.openai.com' or u.port not in (None,443):raise AdapterError('OPENAI_OFFICIAL_HTTPS_REQUIRED')
  self.url=base.rstrip('/')+'/responses'
 def metadata(self):
  return {'mode':'LIVE_MODEL','provider':'openai','model':self.model,'reasoning':self.reasoning,'api':'responses'}
 def call(self,task,layers,schema):
  payload={'model':self.model,'reasoning':{'effort':self.reasoning},'store':False,'stream':False,
   'instructions':layers['frozen_system_rules'],
   'input':[{'role':'user','content':'Return only a JSON object matching the supplied schema.\n'+json.dumps({k:v for k,v in layers.items() if k!='frozen_system_rules'},ensure_ascii=False)}],
   'text':{'format':{'type':'json_object'}}}
  # Original schema is supplied by Pipeline in current_task and validated there.
  # JSON mode avoids silently rewriting the frozen schemas into a provider subset.
  req=urllib.request.Request(self.url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
  try:
   with urllib.request.build_opener(NoRedirect()).open(req,timeout=180) as response:raw=response.read(2_000_001)
   if len(raw)>2_000_000:raise AdapterError('MODEL_RESPONSE_TOO_LARGE')
   data=json.loads(raw)
   if data.get('status')!='completed':raise AdapterError('MODEL_RESPONSE_NOT_COMPLETE')
   chunks=[]
   for item in data['output']:
    if item.get('type')!='message':continue
    if item.get('status')!='completed' or item.get('role')!='assistant':raise AdapterError('MODEL_MESSAGE_NOT_COMPLETE')
    for part in item.get('content',[]):
     if part.get('type')=='refusal':raise AdapterError('MODEL_REFUSAL')
     if part.get('type')=='output_text':chunks.append(part['text'])
   if not chunks or not all(isinstance(x,str) for x in chunks):raise AdapterError('MODEL_CONTENT_NOT_TEXT')
   return ''.join(chunks).replace(self.key,'[REDACTED_API_KEY]')
  except urllib.error.HTTPError as e:raise AdapterError(safe_http_error(e,self.key,task)) from None
  except (urllib.error.URLError,TimeoutError):raise AdapterError('MODEL_NETWORK_OR_TIMEOUT') from None
  except (KeyError,IndexError,ValueError,TypeError):raise AdapterError('MODEL_PROTOCOL_ERROR') from None

class ZhipuAdapter(ModelAdapter):
 """Fixed official endpoint and free model; no paid fallback or automatic retries."""
 def __init__(self,config=None):
  c=os.environ if config is None else config
  self.key=c.get('ZHIPU_API_KEY','').strip()
  if not self.key:raise AdapterError('MODEL_CONFIG_MISSING:ZHIPU_API_KEY')
  self.model='glm-4.7-flash'
  self.url='https://open.bigmodel.cn/api/paas/v4/chat/completions'
 def metadata(self):
  return {'mode':'LIVE_MODEL','provider':'zhipu','model':self.model,'thinking':'enabled','api':'chat/completions'}
 def call(self,task,layers,schema):
  if os.environ.get('BRAIN_RUNTIME_LOCK')=='GLM-0.2.8':
   from pathlib import Path
   if Path(__file__).resolve().parent!=Path(os.environ['BRAIN_RUNTIME_ROOT']).resolve():raise AdapterError('RUNTIME_ADAPTER_PATH_MISMATCH')
  print('智谱模型调用：'+task+'（等待返回中）',flush=True)
  payload={'model':self.model,'messages':[
   {'role':'system','content':layers['frozen_system_rules']},
   {'role':'user','content':'Return only a JSON object matching the supplied schema.\n'+json.dumps({k:v for k,v in layers.items() if k!='frozen_system_rules'},ensure_ascii=False)}],
   'thinking':{'type':'enabled'},'response_format':{'type':'json_object'},'stream':False,'max_tokens':65536}
  from pathlib import Path
  trace=Path(os.environ['BRAIN_DIAG_DIR'])/'Runtime-Requests.jsonl' if os.environ.get('BRAIN_DIAG_DIR') else None
  def record(status,**extra):
   if trace:
    with trace.open('a',encoding='utf-8') as f:f.write(json.dumps(dict(task=task,provider='GLM',model=payload['model'],thinking=payload['thinking'],endpoint=self.url,adapter_file=str(Path(__file__).resolve()),status=status,**extra),ensure_ascii=False)+'\n')
  record('REQUEST_PREPARED')
  req=urllib.request.Request(self.url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
  try:
   with urllib.request.build_opener(NoRedirect()).open(req,timeout=180) as response:raw=response.read(2_000_001)
   if len(raw)>2_000_000:raise AdapterError('MODEL_RESPONSE_TOO_LARGE')
   data=json.loads(raw);record('RESPONSE_RECEIVED',response_model=data.get('model'));choice=data['choices'][0]
   if data.get('model') and data['model']!=self.model:raise AdapterError('RUNTIME_RESPONSE_MODEL_MISMATCH')
   if choice.get('finish_reason')!='stop':raise AdapterError('MODEL_RESPONSE_NOT_COMPLETE')
   message=choice['message']
   if message.get('refusal'):raise AdapterError('MODEL_REFUSAL')
   content=message.get('content')
   if not isinstance(content,str) or not content.strip():raise AdapterError('MODEL_CONTENT_NOT_TEXT')
   return content.replace(self.key,'[REDACTED_API_KEY]')
  except urllib.error.HTTPError as e:raise AdapterError(safe_http_error(e,self.key,task)) from None
  except (urllib.error.URLError,TimeoutError):raise AdapterError('MODEL_NETWORK_OR_TIMEOUT') from None
  except (KeyError,IndexError,ValueError,TypeError):raise AdapterError('MODEL_PROTOCOL_ERROR') from None

class BailianQwenAdapter(ModelAdapter):
 compact_transport=True
 """Aliyun Model Studio Beijing Qwen adapter; local Pipeline remains Schema authority."""
 def __init__(self,config=None):
  c=os.environ if config is None else config
  self.key=(c.get('DASHSCOPE_API_KEY') or '').strip()
  self.provider='aliyun-bailian'
  self.model='qwen3.7-plus'
  self.thinking=c.get('BAILIAN_THINKING','enabled')!='disabled'
  if not self.key:raise AdapterError('MODEL_CONFIG_MISSING:DASHSCOPE_API_KEY')
  # The Beijing legacy-compatible endpoint remains supported and avoids asking the
  # Product Owner to locate or enter a Workspace ID for this one Smoke run.
  base=c.get('API_BASE') or 'https://dashscope.aliyuncs.com/compatible-mode/v1'
  u=urlparse(base)
  if u.username or u.password or u.query or u.fragment:raise AdapterError('API_BASE_MUST_NOT_CONTAIN_CREDENTIALS_OR_QUERY')
  if u.scheme!='https' or u.hostname not in ('dashscope.aliyuncs.com',) or u.port not in (None,443):
   raise AdapterError('BAILIAN_BEIJING_HTTPS_ENDPOINT_REQUIRED')
  self.url=base.rstrip('/')+'/chat/completions'
 def metadata(self):
  return {'mode':'LIVE_MODEL','provider':self.provider,'provider_id':'aliyun-bailian','model':self.model,'thinking':'enabled' if self.thinking else 'disabled','api':'chat/completions','endpoint':self.url}
 @staticmethod
 def _strict_schema(schema):
  """Translate next_action to the documented strict-output subset.

  The complete Draft 2020-12 contract remains enforced by Pipeline locally.
  """
  def visit(node):
   if not isinstance(node,dict):return node
   if 'const' in node:
    value=node['const']
    kind=('null' if value is None else 'boolean' if isinstance(value,bool) else
     'integer' if isinstance(value,int) else 'number' if isinstance(value,float) else
     'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object')
    return {'type':kind,'enum':[value]}
   if 'anyOf' in node:
    options=node['anyOf'];nonnull=[x for x in options if x.get('type')!='null']
    if len(nonnull)==1 and len(options)==2 and any(x.get('type')=='null' for x in options):
     value=visit(nonnull[0]);types=value.get('type')
     value['type']=[types,'null'] if isinstance(types,str) else list(dict.fromkeys(types+['null']))
     return value
    return {'anyOf':[visit(x) for x in options]}
   out={}
   for key in ('type','enum','description','properties','required','additionalProperties','items','anyOf'):
    if key not in node:continue
    if key=='properties':out[key]={name:visit(value) for name,value in node[key].items()}
    elif key=='items':out[key]=visit(node[key])
    elif key=='anyOf':out[key]=[visit(value) for value in node[key]]
    else:out[key]=node[key]
   if 'enum' in out and 'type' not in out and out['enum']:
    kinds=[]
    for value in out['enum']:
     kind=('null' if value is None else 'boolean' if isinstance(value,bool) else
      'integer' if isinstance(value,int) else 'number' if isinstance(value,float) else
      'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object')
     if kind not in kinds:kinds.append(kind)
    out['type']=kinds[0] if len(kinds)==1 else kinds
   if out.get('type')=='object':
    out['required']=list(out.get('properties',{}))
    out['additionalProperties']=False
   return out
  return visit(schema)
 def call(self,task,layers,schema):
  from pathlib import Path
  response_format={'type':'json_object'}
  if task=='next_action' and not self.thinking:
   response_format={'type':'json_schema','json_schema':{'name':'brain_next_action','strict':True,
    'schema':self._strict_schema(schema)}}
  payload={'model':self.model,'messages':[
   {'role':'system','content':layers['frozen_system_rules']},
   {'role':'user','content':'Return only a JSON object matching the supplied schema.\n'+json.dumps({k:v for k,v in layers.items() if k!='frozen_system_rules'},ensure_ascii=False)}],
   'enable_thinking':self.thinking,'response_format':response_format,'stream':False}
  ledger=os.environ.get('BRAIN_BUDGET_LEDGER')
  if ledger:
   from paid_budget import reserve,settle,MAX_OUTPUT
   payload['max_completion_tokens']=MAX_OUTPUT
   budget_index=reserve(ledger,task,payload)
  print('百炼模型调用：'+task+('（思考模式，等待返回中）' if self.thinking else '（非思考模式，等待返回中）'),flush=True)
  trace=Path(os.environ['BRAIN_DIAG_DIR'])/'Runtime-Requests.jsonl' if os.environ.get('BRAIN_DIAG_DIR') else None
  def record(status,**extra):
   if trace:
    with trace.open('a',encoding='utf-8') as f:f.write(json.dumps(dict(task=task,provider='aliyun-bailian',model=self.model,thinking='enabled' if self.thinking else 'disabled',endpoint=self.url,adapter_file=str(Path(__file__).resolve()),status=status,**extra),ensure_ascii=False)+'\n')
  record('REQUEST_PREPARED')
  req=urllib.request.Request(self.url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
  try:
   with urllib.request.build_opener(NoRedirect()).open(req,timeout=240) as response:raw=response.read(2_000_001)
   if len(raw)>2_000_000:raise AdapterError('MODEL_RESPONSE_TOO_LARGE')
   data=json.loads(raw)
   if ledger:settle(ledger,budget_index,data.get('usage'))
   record('USAGE',usage=data.get('usage'))
   choice=data['choices'][0]
   returned_model=data.get('model')
   record('RESPONSE_RECEIVED',response_model=returned_model,finish_reason=choice.get('finish_reason'))
   if returned_model and returned_model!=self.model:raise AdapterError('RUNTIME_RESPONSE_MODEL_MISMATCH')
   if choice.get('finish_reason')!='stop':raise AdapterError('MODEL_RESPONSE_NOT_COMPLETE')
   message=choice['message']
   if message.get('refusal'):raise AdapterError('MODEL_REFUSAL')
   reasoning=message.get('reasoning_content')
   if self.thinking and (not isinstance(reasoning,str) or not reasoning.strip()):raise AdapterError('MODEL_THINKING_NOT_CONFIRMED')
   content=message.get('content')
   if not isinstance(content,str) or not content.strip():raise AdapterError('MODEL_CONTENT_NOT_TEXT')
   record('THINKING_CONFIRMED' if self.thinking else 'NON_THINKING_RESPONSE',reasoning_content_present=bool(reasoning))
   return content.replace(self.key,'[REDACTED_API_KEY]')
  except urllib.error.HTTPError as e:raise AdapterError(safe_http_error(e,self.key,task)) from None
  except (urllib.error.URLError,TimeoutError):raise AdapterError('MODEL_NETWORK_OR_TIMEOUT') from None
  except (KeyError,IndexError,ValueError,TypeError):raise AdapterError('MODEL_PROTOCOL_ERROR') from None

def make_adapter(mode,outputs=None):
 if mode=='LIVE_MODEL' and os.environ.get('BRAIN_RUNTIME_LOCK')=='GLM-0.2.8':
  if os.environ.get('PROVIDER')!='zhipu' or os.environ.get('MODEL')!='glm-4.7-flash':raise AdapterError('RUNTIME_PROVIDER_MODEL_MISMATCH')
  return ZhipuAdapter()
 if mode=='MANUAL_REPLAY':return ManualReplayAdapter(outputs or {})
 if mode=='LIVE_MODEL':
  provider=os.environ.get('PROVIDER','openai').lower()
  if provider=='openai':return OpenAIResponsesAdapter()
  if provider=='zhipu':return ZhipuAdapter()
  if provider in ('aliyun-bailian','bailian'):return BailianQwenAdapter()
  return CompatibleHTTPAdapter()
 raise AdapterError('INVALID_MODE')
