"""Transport schemas implement the authoritative package; audits are engineering metadata."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
S={'type':'string'}; B={'type':'boolean'}; N={'type':'integer','minimum':0}
def enum(*v):return {'enum':list(v)}
def array(x):return {'type':'array','items':x}
def obj(**p):return {'type':'object','properties':p,'required':list(p),'additionalProperties':False}
def nullable(x):return {'anyOf':[{'type':'null'},x]}
SS=array(S)
FIELDS=['F01','F02','F03','F04','F05','F06','F07','F08']
QC=obj(question_text=S,options=SS,scenario=S)
EVSTATUS=enum('ACTIVE','UNKNOWN','UNCERTAIN','INVALID','RETRACTED','SUPERSEDED')
CONF=enum('LOW','MEDIUM','HIGH')
EVIDENCE=obj(evidence_id=S,source_question_id=S,question_context=QC,response_group_id=S,raw_answer=S,
 source_type=enum('A','B','C','D'),content_owner=enum('STUDENT','PARENT','TEACHER','PEER','EXTERNAL','UNKNOWN'),target_construct=S,
 minimal_interpretation=S,evidence_directness=enum('WEAK','MEDIUM','STRONG'),evidence_status=EVSTATUS,
 context_scope=S,contradiction_refs=SS,local_guardrails=SS)
HYPOTHESIS=obj(hypothesis_id=S,claim=S,supporting_evidence_ids=SS,contradicting_evidence_ids=SS,alternative_hypothesis_ids=SS,
 confidence=CONF,missing_evidence=SS,disconfirming_evidence_criteria=SS,best_next_question_intent=S,
 status=enum('ACTIVE','WEAKENED','REJECTED','CONFIRMED_ENOUGH'))
VALIDATION=obj(evidence_id=S,valid=B,supported_by_raw=B,context_preserved=B,attribution_correct=B,constructs_separated=B,
 suspicious=B,unknown_only=B,reason=S)
STATUS=obj(evidence_id=S,status=EVSTATUS,reason=S,clarifying_evidence_ids=SS)
STATE=obj(field_id=enum(*FIELDS),context_scope=S,observation=nullable(S),unknown=B,supporting_evidence_ids=SS,
 contradicting_evidence_ids=SS,hypothesis_ids=SS)
HAUDIT=obj(hypothesis_id=S,scope_preserved=B,evidence_alignment=B,cross_support=B,alternatives_differentiated=B,
 alternatives_weakened=B,direction_consistent=B,independent_groups=array(SS),contexts=array(obj(context=S,evidence_ids=SS)),
 counter_test_evidence_ids=SS,unresolved_strong_evidence_ids=SS,new_information_ids=SS,
 transition=enum('NEW','MAINTAIN','NEW_SUPPORT','STRONG_CONTRADICTION','SUPPORT_INVALIDATED','SCOPE_NARROWED','ALTERNATIVE_ADVANTAGE','CONFLICT_RESOLVED','CORE_RETRACTED','MULTIPLE_STRONG_CONTRADICTIONS','FORBIDDEN_INFERENCE_REQUIRED'),
 reason=S)
CONTRADICTION=obj(hypothesis_id=S,evidence_id=S,context_related=B,direct_negation=B,strong=B,resolved=B,reason=S)
COMPETITION=obj(hypothesis_ids=SS,relation=enum('COMPATIBLE','COMPETING','UNRESOLVED'),evidence_ids=SS,reason=S)
UPDATE_BRANCH=obj(possible_answer=S,update_intent=S)
UPDATE_BRANCH['properties']['branch_id']=enum('B1','B2','B3','B4')
CHOICE_OPTION=obj(option_id=enum('A','B','C','D'),label={'type':'string','minLength':1,'maxLength':60},branch_id=enum('B1','B2','B3','B4'))
PLAN=obj(target_id=S,channel=S,hypothesis_ids=SS,largest_unknown=S,distinguishes=S,answer_updates=array(UPDATE_BRANCH),
 already_sufficient=B,changes_channel_after_unknown=B,clarifies_evidence_id=nullable(S),counter_check=B)
# Optional for archived contracts; the live display boundary requires it.
PLAN['properties']['question_text']={'type':'string','minLength':1,'maxLength':220}
PLAN['properties']['response_mode']=enum('SINGLE_CHOICE','SHORT_TEXT')
PLAN['properties']['response_options']=array(CHOICE_OPTION)
STOPCHECK=obj(usable_hypothesis=B,remaining_unknown_minor=B,no_information_gain=B,repeated_invalid_information=B,repeated_confirmation=B,reason=S)
MIRROR=obj(output_id=S,kind=enum('SMALL_INSIGHT','WEAK_HYPOTHESIS','MIRROR'),text=S,claim=S,context_scope=S,
 hypothesis_ids=SS,evidence_ids=SS,uncertainty_explicit=B)
DIRECTION=obj(direction_id=S,theme=S,supporting_hypothesis_ids=SS,supporting_evidence_ids=SS,current_unknown=S,
 observable_validation_target=S,status=enum('EXPLORATORY'))
MICRO=obj(task_id=S,mode=enum('NEUTRAL','PERSONALIZED'),direction_id=nullable(S),instruction=S,
 target_construct=enum(*FIELDS),target_hypothesis=SS,what_is_being_tested=S,observable_support_signal=S,
 observable_counter_signal=S,ambiguous_signal=S,response_group_id=S,notice=S)
UPDATE=obj(target_type=enum('HYPOTHESIS','DIRECTION'),target_id=S,outcome=enum('ENHANCE','MAINTAIN','DOWNGRADE','OVERTURN'),
 evidence_ids=SS,reason=S,not_based_only_on_completion_score_speed_exit=B)
OUTPUTCHECK=obj(output_id=S,scope_preserved=B,trace_semantically_valid=B,not_personality_or_career_fit=B,
 low_risk_behavior_observation=B,uncertainty_honest=B,reason=S)
BASE=dict(new_evidence=[],evidence_validation=[],evidence_status=[],student_state_updates=[],active_hypotheses=[],
 supporting_evidence_ids=[],contradicting_evidence_ids=[],confidence_updates=[],missing_information=[],next_action='',
 next_question_intent='',small_insight_ready=False,mirror_ready=False,mirror_candidate=None,direction_ready=False,
 direction_candidates=[],micro_experience_update=None,stop_reason=None)
BASE_SCHEMAS=dict(new_evidence=array(EVIDENCE),evidence_validation=array(VALIDATION),evidence_status=array(STATUS),
 student_state_updates=array(STATE),active_hypotheses=array(HYPOTHESIS),supporting_evidence_ids=SS,contradicting_evidence_ids=SS,
 confidence_updates=array(obj(hypothesis_id=S,before=nullable(CONF),after=CONF,reason=S)),missing_information=SS,
 next_action=enum('','ASK_ANCHOR','ASK_PROBE','ASK_COUNTER','RETURN_SMALL_INSIGHT','MIRROR_READY','STOP'),
 next_question_intent=S,small_insight_ready=B,mirror_ready=B,mirror_candidate=nullable(MIRROR),direction_ready=B,
 direction_candidates=array(DIRECTION),micro_experience_update=nullable(array(UPDATE)),stop_reason=nullable(S))
TASKS={
 'extract':(['new_evidence'],obj()),
 'validate':(['evidence_validation','evidence_status'],obj()),
 'student_state':(['student_state_updates'],obj()),
 'hypothesis':(['active_hypotheses','supporting_evidence_ids','contradicting_evidence_ids','confidence_updates','missing_information'],obj(audits=array(HAUDIT))),
 'competition':([],obj(competitions=array(COMPETITION),contradictions=array(CONTRADICTION))),
 'next_action':(['next_action','next_question_intent','missing_information','stop_reason'],obj(question_plan=nullable(PLAN),stop_checks=STOPCHECK)),
 'mirror':(['small_insight_ready','mirror_ready','mirror_candidate'],obj()),
 'direction':(['direction_ready','direction_candidates'],obj()),
 'output_check':([],obj(checks=array(OUTPUTCHECK))),
 'micro_task':([],obj(task=MICRO)),
 'micro_update':(['micro_experience_update'],obj())}

def task_schema(task):
 owned,meta=TASKS[task]
 return obj(**{k:(BASE_SCHEMAS[k] if k in owned else {'const':v}) for k,v in BASE.items()},task_data=meta)
def envelope(task,**updates):
 import copy
 x=copy.deepcopy(BASE);x['task_data']={};x.update(updates);return x

def validate(x,schema):
 errors=sorted(Draft202012Validator(schema).iter_errors(x),key=lambda e:str(list(e.path)))
 if errors:raise ValueError('JSON_SCHEMA:'+str(list(errors[0].path))+':'+errors[0].validator)
def export():
 root=Path(__file__).parent/'schemas';root.mkdir(exist_ok=True)
 for p in root.glob('*.json'):p.unlink()
 schemas={'Evidence':EVIDENCE,'Hypothesis':HYPOTHESIS,'StudentState':array(STATE),'Mirror':MIRROR,'Direction':DIRECTION,'MicroExperience':MICRO,'MicroUpdate':array(UPDATE),'AICallContract':obj(**BASE_SCHEMAS,task_data={'type':'object'})}
 schemas.update({f'Task-{k}':task_schema(k) for k in TASKS})
 for k,v in schemas.items():
  Draft202012Validator.check_schema(v)
  (root/(k+'.schema.json')).write_text(json.dumps({'$schema':'https://json-schema.org/draft/2020-12/schema',**v},ensure_ascii=False,indent=2))
if __name__=='__main__':export()
