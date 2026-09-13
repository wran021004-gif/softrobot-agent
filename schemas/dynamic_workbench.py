"""Versioned executable boundary for the reach dynamics campaign."""
from typing import Literal
from pydantic import Field
from schemas.common import Contract

class Candidate(Contract):
    candidate_id: str=Field(pattern=r'^c\d{3}$')
class Simulate(Candidate):
    backend: Literal['matlab','mujoco']
    model_id: str | None=None
    purpose: Literal['validation','diagnostic','baseline','sensitivity']='validation'
class Create(Contract):
    parent_id: str=Field(pattern=r'^c\d{3}$')
    changes: dict=Field(min_length=1)
class Optimize(Contract):
    parent_id: str=Field(pattern=r'^c\d{3}$')
    variables: list[str]=Field(min_length=1,max_length=6)
    bounds_ref: Literal['round9_grant']='round9_grant'
    objective_ref: Literal['reach_final_error_v1']='reach_final_error_v1'
    max_evaluations: int=Field(default=24,ge=1,le=240)
    search_id: str=Field(default='search0',pattern=r'^[a-zA-Z0-9_-]{1,40}$')
    initial_step: float=Field(default=.1,gt=0,le=.5)
class Diagnose(Simulate):
    entity: str='all'
    t_start_s: float=Field(default=0,ge=0,le=2)
    t_end_s: float=Field(default=2,ge=0,le=2)
    fields: list[str]=Field(default_factory=list,max_length=8)
class Compare(Contract):
    candidate_ids: list[str]=Field(default_factory=list,max_length=320)
    offset: int=Field(default=0,ge=0)
    limit: int=Field(default=12,ge=1,le=50)
class Observe(Simulate):
    pass
class Read(Contract):
    evidence_ref: str
    pointer: str=''
    offset: int=Field(default=0,ge=0)
    limit: int=Field(default=10,ge=1,le=50)
class Claim(Contract):
    evidence_ref: str
    record_type: Literal['events','queries']='queries'
    record_index: int=Field(ge=0)
    entity_name: str
    t_start_s: float
    t_end_s: float
    field: str
    value: float
    statement: str=Field(min_length=1,max_length=600)
class Stop(Contract):
    pass

TOOLS={
 'create_candidate':(Create,'candidate_design','Branch any registered candidate, changing design, equivalent physics or control; cite recorded evidence.'),
 'simulate_candidate':(Simulate,'simulate','Run only the selected backend. MATLAB screening does not set canonical reach success. One rollout charged even on failure.'),
 'evaluate_candidate':(Candidate,'simulate','Compatibility: evaluate candidate in MuJoCo with its own controller, no bundled MATLAB calls.'),
 'optimize_matlab':(Optimize,'analysis','MATLAB bounded local coordinate search, checkpoint every trial, one dynamic budget unit per actual rollout. Resume identical search_id. Pick 4-6 evidence-based variables initially.'),
 'diagnose_trajectory':(Diagnose,'read_evidence','Query exact entity and time from saved trajectory. Force and state have distinct time phases. Returns sampled facts, events and evidence refs.'),
 'compare_candidates':(Compare,'read_evidence','Paged design/control/physics/backend comparison. Unevaluated backends remain NOT_RUN.'),
 'observe_candidate':(Observe,'derived_artifacts','Render saved MATLAB or MuJoCo coordinates, curves and event list; zero backend solves.'),
 'read_evidence':(Read,'read_evidence','Read registered JSON via pointer and pagination; never directory crawling.'),
 'record_verified_diagnosis':(Claim,'read_evidence','Record your concrete diagnostic statement with exact machine-checkable entity, time interval, numeric field and value from a diagnosis record.'),
 'stop_design':(Stop,'read_evidence','Stop with cited results and limitations; distinguish workflow, numerical completion, MATLAB prediction and canonical MuJoCo success.')}

def native_tools():
    out=[]
    for name,(schema,permission,description) in TOOLS.items():
        s=schema.model_json_schema();s['properties'].update(reason={'type':'string'},evidence={'type':'array','items':{'type':'string'},'minItems':1},
          working_memory={'type':'object','properties':{'findings':{'type':'array','items':{'type':'string'}},'unresolved':{'type':'array','items':{'type':'string'}},'next_action':{'type':'string'}},'additionalProperties':False})
        s['required']=s.get('required',[])+['reason','evidence','working_memory']
        out.append(dict(type='function',function=dict(name=name,description=description,parameters=s)))
    return out
