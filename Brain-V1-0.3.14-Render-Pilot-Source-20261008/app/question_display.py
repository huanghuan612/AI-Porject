"""Student-facing wording is separate from the internal question rationale."""
import re

def student_question(plan):
 text=plan.get('question_text')
 if not isinstance(text,str) or not text.strip():raise ValueError('STUDENT_QUESTION_TEXT_REQUIRED')
 text=text.strip()
 if len(text)>220 or re.search(r'(?<![A-Za-z0-9])H\d+(?![A-Za-z0-9])|hypothesis|confidence|支持.{0,12}假设|削弱.{0,12}假设|增强.{0,12}假设|过程导向|结果导向|外部驱动|内在动力|largest_unknown|update_intent',text,re.I):
  raise ValueError('STUDENT_QUESTION_INTERNAL_REASONING_BLOCKED')
 return text

def student_options(plan):
 options=plan.get('response_options')
 if not isinstance(options,list) or not 2<=len(options)<=4:raise ValueError('STUDENT_CHOICE_OPTIONS_COUNT')
 ids=[];branches=[];labels=[]
 for item in options:
  if not isinstance(item,dict):raise ValueError('STUDENT_CHOICE_OPTION_INVALID')
  option_id=item.get('option_id');branch=item.get('branch_id');label=item.get('label')
  if option_id not in ('A','B','C','D') or branch not in ('B1','B2','B3','B4'):
   raise ValueError('STUDENT_CHOICE_OPTION_MAPPING_INVALID')
  if not isinstance(label,str) or not label.strip() or len(label.strip())>60:
   raise ValueError('STUDENT_CHOICE_LABEL_INVALID')
  label=label.strip()
  if re.search(r'(?<![A-Za-z0-9])H\d+(?![A-Za-z0-9])|hypothesis|confidence|支持.{0,12}假设|削弱.{0,12}假设|增强.{0,12}假设|largest_unknown|update_intent|置信度|分支更新|更好答案',label,re.I):
   raise ValueError('STUDENT_CHOICE_INTERNAL_REASONING_BLOCKED')
  ids.append(option_id);branches.append(branch);labels.append(label)
 if len(ids)!=len(set(ids)) or len(branches)!=len(set(branches)) or len(labels)!=len(set(labels)):
  raise ValueError('STUDENT_CHOICE_DUPLICATE')
 return [{'option_id':item['option_id'],'label':item['label'].strip()} for item in options]
