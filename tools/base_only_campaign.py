"""Owner-only orchestration of existing Research Study APIs; no scientific kernel.

All exact designs, schedules, requests and traces stay in ignored runs/. A durable
reservation precedes each science operation; unknown outcomes retain their upper
bound and block relaunch. Only original evaluator acceptance can close a task.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import time
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'

from tools.research import core, analysis
from tools.research.state import state, save
from tools.research.contracts import PLAN_RESEARCH_INTENTS
from tools.research.task_constraints import mathematical_method_view
from tools.research.feedback import eligibility
from tools.state_io import atomic_json, read, digest

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT/'runs/base-only-owner-20261028'
CONFIG = ROOT/'configs/research'
CAPS = {'M4':2000000,'M2':8000000,'M1':8000000,'M3':4000000,'M5':3000000,'M6':5000000}
# Formal Study ceilings alone fit each task grant, even if every callback fails.
LIMITS = {'M4':(6,500,20),'M2':(28,800,100),'M1':(16,800,100),
          'M3':(9,800,20),'M5':(6,800,20),'M6':(10,800,20)}

def plan(action, candidate=None, reason='Frozen Base-only feasibility discovery', **payload):
    return dict(action=action,hypothesis=reason,expected_observation='Original registered evidence',
        weakening_observation='Incomplete execution or unchanged original constraint violations',
        fixed_conditions='Frozen task, gravity, payload, initial state, mesh, bounds and evaluator',
        stopping_condition='First full independent acceptance, finite budget, or justified stagnation',
        interpretation='Codex-organized development discovery; finite search is no infeasibility proof',
        decision=dict(hypothesis_id='base-only-discovery',research_intent=PLAN_RESEARCH_INTENTS[action],
            selected_method=action,**(dict(selected_candidate=candidate) if candidate else {})),**payload)

def bootstrap():
    OWNER.mkdir(parents=True,exist_ok=True)
    for original, new in [('family_space_bf4_s3_tracking.json','family_space_base_only_tracking_v1.json'),
                          ('family_space_bf6_sensor_tool.json','family_space_base_only_sensor_v1.json')]:
        value=read(CONFIG/original)
        value.update(conditional_rules='base_only_consecutive_spans_v1',family_id='base_only_'+value['family_id'])
        atomic_json(CONFIG/new,value)
    for key in CAPS:
        template = ('study_tracking_public.json' if key=='M4' else 'study_bf5_public.json' if key=='M5'
                    else 'study_bf6_public.json' if key=='M6' else 'study_multicondition_public.json')
        value=read(CONFIG/template)
        value.update(study_id='base-only-'+key.lower()+'-20261028',base_commit='e0200b4b2415139088e8fea7780d4156a16cbbc1',
            mode='formal_research',authorization='User pasted request 2026-10-28 explicitly authorizes Codex-organized Base-only feasibility discovery; '+str(CAPS[key])+' physics step attempts maximum for '+key+'. No Provider, Research Agent, PPO or NMPC. Campaign supervisor and frozen count ceilings both apply.',
            family_space=('family_space_base_only_sensor_v1.json' if key=='M6' else
                'family_space_base_only_tracking_v1.json' if key in ('M4','M5') else 'family_space_stage0_base_only_v1.json'),
            evidence_destination='runs/base-only-owner-20261028/'+key+'/private-store')
        if key in ('M1','M2'):
            names=['positive_high','negative_low','central_high'] if key=='M1' else ['zero','positive','negative']
            prefix='bf7_shared_reach_v1_' if key=='M1' else 'bf2_multidirectional_hold_frozen_v1_'
            value['task_conditions']=[dict(condition_id=n,task='../../tasks/'+prefix+n+'.json') for n in names]
            value.pop('task',None)
        elif key=='M3':
            value.pop('task_conditions',None)
            value['task']='../../tasks/reach_hold_b3_050.json'
        duration=.35 if key=='M2' else .5 if key=='M3' else .6
        value['scoring_window_s']=duration
        value['analysis_protocol']=dict(windows_s=[.05,.1,duration],samples_s=[0.,.1,.2,round(duration-.02,8)])
        math, callbacks, replays=LIMITS[key]
        value['budgets']=dict(provider_requests=0,protected_provider_requests=0,public_operations=500,
            protected_public_operations=8,physical_launches=replays,mathematical_evaluations=math)
        value['native_control_limits']=dict(evaluation_requests=callbacks,iterations=100,knots_s=4)
        value['capabilities']=['analysis','control_correction','physical_replay']
        value['allowed_plan_actions']=['generate','initialize_control','physical_replay','diagnose','select','stop']
        atomic_json(CONFIG/('study_base_only_'+key.lower()+'_v1.json'),value)
    atomic_json(CONFIG/'base_only_campaign_budget_v1.json',dict(version='base-only-discovery-owner-v1',
        task_step_caps=CAPS,total_step_attempt_cap=sum(CAPS.values()),study_count_limits=LIMITS,
        reservation='Before launch reserve evaluation_requests * ceil(duration/timestep), replay ceil(duration/timestep)+1. Unknown calls retain upper bound; no relaunch.',
        m3_status='Development draft, locally frozen for this discovery only; original inherited Reach/Hold evaluation at 0.50 s. Not an approved benchmark.',
        private_evidence='runs/base-only-owner-20261028; excluded from future Agent checkout and context'))

def host_for(key):
    host=core.prepare(CONFIG/('study_base_only_'+key.lower()+'_v1.json'),directory=OWNER/key/'private-store')
    if 'freeze' not in state(host):core.bind(host)
    return host

def load_index(key):
    path=OWNER/key/'index.json'
    return read(path) if path.exists() else dict(candidates={},seeds={},analyses=[],replays=[],operations=[])

def put_index(key,index):atomic_json(OWNER/key/'index.json',index)

def generate(key,label,request=None):
    h=host_for(key);s=state(h);index=load_index(key)
    if label in index['candidates']:return index['candidates'][label]
    q=dict(version='serial_family_generation_v2',family_space_identity=s['spec']['family_space_identity'],
        segment_count=2,tendon_count=6,segments={'0':dict(cells=12),'1':dict(cells=12)})
    if request:q.update(request)
    out=core.dispatch(h,plan('generate',generation=q),'generate-'+label)
    ref=out['result']['candidate'];body=core.read_evidence(h,dict(reference=ref,view='full'))
    tendons=body['configuration']['robot']['structure']['data']['tendons']
    assert all(t['route'][0]['part']=='fixed_base' and t['route'][0]['role']=='start' for t in tendons)
    index['candidates'][label]=ref;put_index(key,index)
    return ref

def seed(key,label,condition=None,tension=.2):
    h=host_for(key);index=load_index(key);name=label+'/'+str(condition)+'/'+str(tension)
    if name in index['seeds']:return index['seeds'][name]
    ref=index['candidates'][label]
    q=dict(candidate=ref,tensions_n=[[tension]*6])
    if condition:q['condition_id']=condition
    out=core.dispatch(h,plan('initialize_control',ref,control_seed=q),'seed-'+name)['result']
    index['seeds'][name]=out;put_index(key,index);return out

def costs(body):
    for field in ('native_dynamics','native_diagnostic','native_progress'):
        if body.get(field,{}).get('cost'):return body[field]['cost']
    if body.get('cost'):return body['cost']
    failure=body.get('numerical_failure',{})
    if 'attempted_steps' in failure:return dict(physics_step_attempts=failure['attempted_steps'],physics_steps=failure['confirmed_completed_steps'])
    return {}

def reserve(key,kind,upper,details):
    index=load_index(key)
    if any(op['status']=='pending' for op in index['operations']):raise ValueError('UNKNOWN_OUTCOME_NO_RELAUNCH')
    spent=sum(op.get('charged_upper',op['reserved_upper']) for op in index['operations'])
    assert spent+upper<=CAPS[key],(spent,upper,CAPS[key])
    identifier=str(len(index['operations']))+'-'+kind
    index['operations'].append(dict(id=identifier,kind=kind,status='pending',reserved_upper=upper,details=details,started=time.time()))
    put_index(key,index);return identifier

def settle(key,identifier,body,reference):
    index=load_index(key);op=next(op for op in index['operations'] if op['id']==identifier)
    cost=costs(body);actual=cost.get('physics_step_attempts')
    op.update(status='settled',reference=reference,cost=cost,finished=time.time(),
        confirmed_lower=actual if actual is not None else 0,
        charged_upper=actual if actual is not None else op['reserved_upper'])
    assert op['charged_upper']<=op['reserved_upper'],op
    put_index(key,index)

def native(key,label,condition=None,tension=.2,callbacks=200,source_analysis=None,settings=None):
    h=host_for(key);index=load_index(key)
    if source_analysis is None:start=seed(key,label,condition,tension)
    else:
        row=index['analyses'][source_analysis]
        start=dict(candidate=row['candidate'],source=row['source'])
    cfg=h.store.artifact(start['candidate'])['configuration'];timing=cfg['task']['timing']
    duration=timing['duration_s'];period=timing['control_period_s']
    method=mathematical_method_view(h,start['candidate'])['methods']['mujoco_direct_control_v1']
    query=deepcopy(method['request_template'])
    opts=dict(version='local_control_search_v2',method='response',correction_window_s=[0.,duration],
        knots_s=[0.,round(duration/3/period)*period,round(2*duration/3/period)*period,round(duration-period,8)],
        evaluation_requests=callbacks,iterations=100,coefficient_limit_n=4.,initial_radius_n=.2,difference_step_n=.02)
    if settings:opts.update(settings)
    query['control_optimization']=dict(source=start['source'],settings=opts)
    upper=callbacks*round(duration/timing['timestep_s'])
    identifier=reserve(key,'native',upper,dict(candidate=start['candidate'],query=query,reason='Local registered response search; new source remains bound to identical candidate and full time grid'))
    out=analysis.dispatch(h,query,identifier,guard=core.guard)
    if not out.get('reference'):raise ValueError(out)
    body=core.read_evidence(h,dict(reference=out['reference'],view='full'))
    settle(key,identifier,body,out['reference'])
    index=load_index(key)
    row=dict(reference=out['reference'],candidate=start['candidate'],source=body.get('control_schedule_reference',start['source']),
        label=label,condition=condition,status=body['status'],reason=body.get('reason'),cost=costs(body),
        summary=body.get('native_analysis'),requested_callbacks=callbacks)
    index['analyses'].append(row);put_index(key,index)
    return dict(analysis=len(index['analyses'])-1,**{k:v for k,v in row.items() if k not in ('reference','candidate','source')})

def replay(key,number):
    h=host_for(key);index=load_index(key);row=index['analyses'][number]
    cfg=h.store.artifact(row['candidate'])['configuration'];timing=cfg['task']['timing']
    identifier=reserve(key,'replay',round(timing['duration_s']/timing['timestep_s'])+1,dict(analysis=number))
    result=core.dispatch(h,plan('physical_replay',row['candidate'],physical_replay=dict(candidate=row['candidate'],source=row['source'])),identifier)['result']
    body=core.read_evidence(h,dict(reference=result['reference'],view='full'))
    raw=core.read_evidence(h,dict(reference=result['raw_reference'],view='full'))
    settle(key,identifier,raw,result['reference'])
    index=load_index(key);index['replays'].append(dict(analysis=number,reference=result['reference'],candidate=row['candidate'],
        label=row['label'],condition=row['condition'],acceptance=result['acceptance'],cost=costs(raw)))
    put_index(key,index)
    candidates=[r for r in index['replays'] if r['label']==row['label'] and r['acceptance']['status']=='accepted']
    conditions=state(h)['spec'].get('task_conditions',[])
    refs=[next((r['reference'] for r in reversed(candidates) if r['condition']==c['condition_id']),None) for c in conditions] if conditions else result['reference']
    if not isinstance(refs,list) or all(refs):
        eligible=eligibility(h,refs,selection=True)
        if eligible['eligible']:
            core.dispatch(h,plan('select',selected_execution=refs),'select')
            stop(key,'First complete independent accepted witness; feasibility search ends')
    return dict(acceptance=result['acceptance'],cost=costs(raw),selected=bool(state(h).get('selected')))

def stop(key,reason):
    h=host_for(key);s=state(h)
    if s['research_status']!='stopped':
        core.dispatch(h,plan('stop',reason=reason,next_step='stop',supporting_evidence=[*s['analysis_results'],*s['physical_replays']]),'campaign-stop')
    return dict(status=state(h)['research_status'],resource_use=core.resource_use(h))

def preflight(key):
    h=host_for(key);ref=generate(key,'full-span');s=state(h)
    body=h.store.artifact(ref);cfg=body['configuration'];method=mathematical_method_view(h,ref)
    math,callbacks,replays=LIMITS[key];timing=cfg['task']['timing']
    upper=(math*callbacks+replays)*round(timing['duration_s']/timing['timestep_s'])+replays
    assert upper<=CAPS[key]
    result=dict(benchmark=key,study=s['spec']['resolved_identity'],family=s['spec']['family_space_identity'],
        rule=s['spec']['family_space']['conditional_rules'],task=cfg['task'],profile=s['profile'],
        native=method['methods']['mujoco_direct_control_v1'],study_worst_case_attempts=upper,
        cap=CAPS[key],conditions=s['spec'].get('task_conditions'),physics_executed=False)
    atomic_json(OWNER/key/'preflight.json',result)
    return {k:result[k] for k in ('benchmark','study','family','rule','study_worst_case_attempts','cap','physics_executed')}

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['bootstrap','preflight','generate','native','replay','stop','status'])
    p.add_argument('--task');p.add_argument('--label',default='full-span');p.add_argument('--condition');p.add_argument('--tension',type=float,default=.2)
    p.add_argument('--callbacks',type=int,default=200);p.add_argument('--number',type=int);p.add_argument('--settings');p.add_argument('--request');p.add_argument('--reason',default='Evidence-based campaign stop')
    args=p.parse_args()
    if args.action=='bootstrap':bootstrap();out={'configs_created':True,'physics_steps':0}
    elif args.action=='preflight':out=[preflight(k) for k in ([args.task] if args.task else CAPS)]
    elif args.action=='generate':out=generate(args.task,args.label,read(Path(args.request)) if args.request else None)
    elif args.action=='native':out=native(args.task,args.label,args.condition,args.tension,args.callbacks,args.number,json.loads(args.settings) if args.settings else None)
    elif args.action=='replay':out=replay(args.task,args.number)
    elif args.action=='stop':out=stop(args.task,args.reason)
    else:
        out={k:dict(steps_lower=sum(op.get('confirmed_lower',0) for op in load_index(k)['operations']),
            steps_upper=sum(op.get('charged_upper',op['reserved_upper']) for op in load_index(k)['operations']),
            analyses=len(load_index(k)['analyses']),replays=len(load_index(k)['replays']),
            pending=[op['id'] for op in load_index(k)['operations'] if op['status']=='pending']) for k in CAPS}
    print(json.dumps(out,ensure_ascii=False,default=str))

if __name__=='__main__':main()
