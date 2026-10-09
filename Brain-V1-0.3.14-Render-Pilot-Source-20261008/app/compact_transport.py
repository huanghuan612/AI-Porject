"""Omit only schema-constant top-level transport fields; never infer semantic values."""
import copy

def compact_schema(schema):
 wire=copy.deepcopy(schema)
 constants={k:copy.deepcopy(v['const']) for k,v in schema['properties'].items() if set(v)=={'const'}}
 for k in constants:wire['properties'].pop(k)
 wire['required']=[k for k in wire.get('required',[]) if k not in constants]
 return wire,constants

def restore_constants(output,constants):
 if not isinstance(output,dict):return output,[]
 out=copy.deepcopy(output);restored=[]
 for key,value in constants.items():
  if key not in out:out[key]=copy.deepcopy(value);restored.append(key)
 return out,restored
