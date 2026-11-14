"""First formal A/B batch. Thin capability boundary over existing Core kernels.

No FULL solutions enter model context. No high-level research/math orchestration.
Resume uses the same Store, request IDs and completed physical evidence.
"""
import os, sys, json, time, csv, traceback, argparse
import math as scalar_math
from pathlib import Path
from copy import deepcopy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORE = ROOT/'.worktrees/core-five-task-native-feedback-20261113'
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(CORE))
os.environ.update(SOFTROBOT_AGENT_HOME=str(HERE/'runtime'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
import numpy as np
import httpx
from tools.platform_store import Store, plain, zero
from tools.state_io import digest
from schemas.platform import SessionInput, ProjectConfig
from extensions.tendon_family.family_space import GenerationRequestV2, parse_space
from tools.research.design import family_configuration
from extensions.tendon_family.backends import physics_for, playback_tensions
from extensions.tendon_family.scene import assemble
from tools.research.physical_replay import evaluate_playback

from task_registry import NAMES, BATCH2, inputs, controller as task_controller
MODES={'A':'llm_only','B':'direct_math_tools'}
LIMITS=dict(requests=60,llm_tokens=350000,candidate_count=12,physics_evaluations=24,integration_steps=180000,mathematical_calls=24,wall_s=2400)
PROVIDER=dict(model='gpt-5.6-sol',reasoning_effort='medium',base_url='http://127.0.0.1:8789/v1',credential='~/.softrobot-agent/chatgpt-api-account3.json')

class CommandError(ValueError):pass
class InitialConditionFailed(ValueError):pass

def command_schema(method):
    return dict(type='object',required=['decision','commands'],additionalProperties=False,properties=dict(
        decision=dict(type='string'),evidence=dict(type='array',items=dict(type='string')),
        expected_outcome=dict(type='string'),commands=dict(type='array',minItems=1,items=dict(
            type='object',required=['operation','arguments'],additionalProperties=False,properties=dict(
                operation=dict(enum=['generate','evaluate','finish']+(['math'] if method=='B' else [])),arguments=dict(type='object'))))))

def validate_command(command,method):
    if not isinstance(command,dict) or set(command)!= {'operation','arguments'}:raise CommandError('Each command requires exactly operation and arguments')
    op=command['operation'];args=command['arguments']
    allowed=['generate','evaluate','finish']+(['math'] if method=='B' else [])
    if op not in allowed or not isinstance(args,dict):raise CommandError('Operation is not allowed or arguments is not an object')
    required={'generate':['generation'],'evaluate':['candidate'],'math':['candidate','operation'],'finish':['candidate']}[op]
    if any(k not in args for k in required):raise CommandError('Missing arguments: '+str(required))
    if op=='generate' and not isinstance(args['generation'],dict):raise CommandError('generation must be an object')
    if op!='generate' and not isinstance(args['candidate'],str):raise CommandError('candidate must be a returned alias')
    if op=='evaluate' and (not isinstance(args.get('controls',{}),dict) or not isinstance(args.get('conditions',[]),list)):raise CommandError('controls must be an object and conditions an array')
    if op=='math' and args['operation'] not in ['jacobian','mechanics','finite_difference','equilibrium','kkt']:raise CommandError('Only registered low-level primitives are allowed')

def validate_step(value,method):
    if not isinstance(value,dict) or set(value)-{'decision','evidence','expected_outcome','commands'}:raise CommandError('Unknown research_step fields')
    if not isinstance(value.get('decision'),str) or not isinstance(value.get('commands'),list) or not value['commands']:raise CommandError('decision string and nonempty commands array required')
    if not isinstance(value.get('evidence',[]),list) or any(not isinstance(x,str) for x in value.get('evidence',[])):raise CommandError('evidence must be an array of strings')
    if 'expected_outcome' in value and not isinstance(value['expected_outcome'],str):raise CommandError('expected_outcome must be a string')
    for command in value['commands']:validate_command(command,method)
    return value

def compact_evaluation(row):
    detail=row.get('diagnostics',{});checks=detail.get('constraints',{})
    failed={k:v for k,v in checks.items() if isinstance(v,dict) and (v.get('passed') is False or v.get('satisfied') is False or
        isinstance(v.get('normalized_violation'),(int,float)) and v['normalized_violation']>0 or isinstance(v.get('margin'),(int,float)) and v['margin']<0)}
    out={k:row.get(k) for k in ('candidate','condition','accepted','validity','max_violation','reference','raw','cumulative')}
    out['failed_checks']=dict(list(failed.items())[:12]);out['metrics']=(row.get('metrics') or [])[:6]
    samples=row.get('physical_observations',[])
    if samples:out['final_state']={k:samples[-1][k] for k in ('time_s','tip_m','tip_velocity_m_s','qpos_rad','qvel_rad_s') if k in samples[-1]}
    if row.get('required_case_results'):
        out['required_cases']={k:{key:v.get(key) for key in ('accepted','validity','failed_checks','reference')} for k,v in row['required_case_results'].items()}
    return out

def compact_feedback(value):
    if isinstance(value,list):return [compact_feedback(v) for v in value]
    if isinstance(value,dict) and 'condition' in value and 'validity' in value:return compact_evaluation(value)
    return value

def token_reservation(request):
    serialized=json.dumps(request,ensure_ascii=False)
    try:
        import tiktoken
        count=len(tiktoken.get_encoding('o200k_base').encode(serialized))+128
        source='tiktoken:o200k_base; serialized chat plus 128 framing tokens'
    except ImportError:
        ascii_count=sum(ord(c)<128 for c in serialized)
        other_bytes=len(serialized.encode('utf8'))-ascii_count
        count=scalar_math.ceil(ascii_count/2)+other_bytes+128
        source='fallback: ceil(ASCII characters/2) + non-ASCII UTF8 bytes + 128 framing; provider usage is authoritative'
    return dict(estimated_input_tokens=count,output_allowance_tokens=32768,total=count+32768,estimator=source)

class FixedStateFeedback:
    """LLM-supplied coefficients on the existing native execution boundary.

    No equilibrium search, differentiation, Riccati solve or gain construction.
    """
    def __init__(self,physics,control,feedforward):
        f=control['feedback'];n=len(physics['dofs']);m=len(physics['tendons'])
        self.K=np.asarray(f['gain'],float);self.qref=np.asarray(f.get('qref_rad',[0.]*n),float)
        self.vref=np.asarray(f.get('vref_rad_s',[0.]*n),float);self.feedforward=feedforward
        if self.K.shape!=(m,2*n) or self.qref.shape!=(n,) or self.vref.shape!=(n,) or not all(np.isfinite(v).all() for v in (self.K,self.qref,self.vref)):
            raise CommandError('feedback gain must be [tendons,2*named_hinges]; references must cover all named hinges')
        self.physics=physics;self.observations=[];self.control_snapshots=[];self.stop_requested=False

    def command(self,t,geometry,q,v):
        from extensions.tendon_family.control import execute_ideal_tension
        k=min(round(t/self.period_s),len(self.feedforward)-1)
        requested=self.feedforward[k]-self.K@np.r_[q-self.qref,v-self.vref]
        command,bridge=execute_ideal_tension(self.physics,requested)
        self.last=dict(**bridge,fresh_solve=False,feedback_enabled=True,feedback_update=True,
            plan_source='llm_supplied_fixed_state_feedback',solver_outcome='explicit_matrix_control',solver_failed=False,
            update_wall_s=0.,deadline_missed=False,measured_qpos_rad=q.tolist(),measured_qvel_rad_s=v.tolist(),
            reference_qpos_rad=self.qref.tolist(),reference_qvel_rad_s=self.vref.tolist())
        self.observations.append(dict(time_s=float(t),phase='interval_start_pre_step',**self.last))
        return command

def passive_cases(task,raw,evaluation,reference):
    observed=evaluation.get('diagnostics',{}).get('observations',{});cases={}
    for case in task['goal']['data']['load_conditions']:
        episode=next((e for e in raw.get('episodes',[]) if e['load_condition']==case),{})
        checks={k:v for k,v in observed.items() if k.startswith('evaluator:'+case+'_')}
        qualifications=episode.get('qualifications',{})
        stage_fail=any(v.get('passed') is False for v in qualifications.values())
        complete=episode.get('complete',False);qualified=bool(qualifications) and all(v.get('passed') is True for v in qualifications.values())
        known=bool(checks) and all(v.get('passed') is not None for v in checks.values())
        valid=complete and qualified and known and evaluation.get('validity')=='valid'
        cases[case]=dict(accepted=all(v['passed'] for v in checks.values()) and episode.get('maximum_contacts',0)==0 if valid else False if stage_fail else None,
            validity='qualification_failed' if stage_fail else 'valid' if valid else 'incomplete',complete=complete,
            checks=checks,qualifications=qualifications,failed_checks=[k for k,v in checks.items() if v.get('passed') is False]+
                [k for k,v in qualifications.items() if v.get('passed') is False],reference=reference)
    return cases

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def clean(v):
    if isinstance(v,np.ndarray):return clean(v.tolist())
    if isinstance(v,np.generic):return clean(v.item())
    if isinstance(v,float) and not np.isfinite(v):return None
    if isinstance(v,dict):return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [clean(x) for x in v]
    return v

def command_json(content):
    """Repair only omitted closing delimiters in the text-only transport."""
    try:return json.loads(content)
    except json.JSONDecodeError:pass
    stack=[];parts=[];quoted=False;escaped=False;pairs={'}':'{',']':'['};closing={'{':'}','[':']'}
    for char in content:
        if quoted:
            parts.append(char)
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
            continue
        if char=='"':quoted=True
        elif char in '{[':stack.append(char)
        elif char in '}]':
            while stack and stack[-1]!=pairs[char]:parts.append(closing[stack.pop()])
            if not stack:raise ValueError('Unrepairable command delimiters')
            stack.pop()
        parts.append(char)
    if quoted:raise ValueError('Incomplete quoted command')
    parts.extend(closing[x] for x in reversed(stack))
    return json.loads(''.join(parts))

class Run:
    def __init__(self,task,method,output_root=None,label=None):
        self.task,self.method=task,method
        label=label or ('batch2' if task in BATCH2 else 'batch1')
        destination=Path(output_root) if output_root else HERE.parent/'ab_batch2_20261114' if task in BATCH2 else HERE
        self.id=f'{label}-{task.lower()}-{MODES[method]}-20261114'
        self.folder=destination/task/method;self.folder.mkdir(parents=True,exist_ok=True)
        os.chdir(self.folder)  # Native engine logs belong to this independent run.
        self.store=Store(self.folder/'STORE')
        self.base,self.space,self.protocol=inputs(task)
        self.limits={**LIMITS}
        if method=='A':self.limits['mathematical_calls']=0
        if task=='PHS-2D':self.limits.update(integration_steps=850000,physics_evaluations=30,wall_s=3600)
        if task=='T08':self.limits.update(integration_steps=2100000,physics_evaluations=30,wall_s=3600)
        self.base['run_id']=self.id
        self.base['policy']['allowed_tools']=[];self.base['policy']['tool_bindings']={}
        self.base['policy']['budget']=dict(model_calls=self.limits['requests'],tool_calls=100,backend_solves=self.limits['physics_evaluations'],worker_calls=0,wall_s=self.limits['wall_s'])
        if not self.store.db.exists():
            self.store.create(ProjectConfig(project_id=self.id,grant_id=self.id,authorization_source='User authorizes Issue #1 formal A/B runs, full legal family space and frozen physical tasks; at most 60 provider requests per independent run.',budget=self.base['policy']['budget']))
            self.store.create_session(dict(input=self.base,dependencies={},project_commit='56cc418',adapter='batch1_direct_kernel_v1'))
            self.s=dict(started=time.time(),requests=0,llm_tokens=0,candidate_count=0,physics_evaluations=0,integration_steps=0,mathematical_calls=0,candidates={},evaluations=[],messages=[],status='running',wall_time=0.)
            self.save_state()
            self.put(dict(task_id=task,method=method,mode=MODES[method],initial_state='original task initializer; no historical candidate',family_space=self.space,task_protocol=self.protocol,base_configuration=self.base,limits=self.limits,provider=PROVIDER,knowledge='Generic physical model and complete legal FamilySpace; task-specific FULL solutions/traces excluded.',core=str(CORE),core_commit='56cc418',hardware_validation_index='Real-world Demonstrations / Physical Robot Validation: reserved, existing hardware results unchanged.'),'run_configuration')
            write(self.folder/'config.json',dict(task_id=task,method=method,mode=MODES[method],run_id=self.id,limits=self.limits,provider=PROVIDER,core=str(CORE),core_commit='56cc418',design_space=self.space,protocol=self.protocol))
        else:
            self.s=self.store.session(self.id)['state']
            meta=read(self.folder/'config.json')
            if meta['limits']!=self.limits:
                self.trace('paired_budget_addendum',dict(previous=meta['limits'],current=self.limits,reason='User clarified at most 60 requests per independent run, not entire batch. Same task A/B ceilings remain equal; continue existing Store.'))
                meta['limits']=self.limits;write(self.folder/'config.json',meta)
        meta=read(self.folder/'config.json')
        if 'original_task' not in meta:
            meta['original_task']=self.base['task'];meta['initialization']='Fresh family-space choice; zero named joints for active cases, physically qualified equilibrium for task-required prepared/passive initial conditions.'
            write(self.folder/'config.json',meta)

    def save_state(self):
        with self.store.transaction() as db:self.store.update_state(db,self.id,self.s)
    def put(self,value,kind):
        value=clean(value)
        with self.store.transaction() as db:
            r=self.store.put(db,value);self.store.event(db,self.id,kind,'saved',outputs=[r],caller='batch1')
        return plain(r)
    def trace(self,kind,value):
        r=self.put(value,kind)
        with (self.folder/'TRACE.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(timestamp=time.time(),kind=kind,artifact_reference=r,**clean(value)),ensure_ascii=False)+'\n')
        return r
    def guard(self,key,n=1):
        if self.s[key]+n>self.limits[key]:raise ValueError('BUDGET_EXHAUSTED: '+key)
        if time.time()-self.s['started']>self.limits['wall_s']:raise ValueError('BUDGET_EXHAUSTED: wall_s')

    def generate(self,args):
        recovering=getattr(self,'recover_alias',None)
        if not recovering:self.guard('candidate_count')
        g=deepcopy(args['generation']);g['family_space_identity']=digest(plain(parse_space(self.space)))
        # Repeated identical interior guide stations designate the same station.
        # Canonicalizing this redundant spelling preserves the authored route.
        for span in g.get('spans',[]):
            if span.get('guide_s'):span['guide_s']=sorted(set(span['guide_s']))
        request=GenerationRequestV2.model_validate(g)
        try:cfg,build,p=family_configuration(self.base,self.space,request,self.id)
        except ValueError as exc:
            stations={c['id']:len(c.get('sections',[])) for c in self.space['assembly']['components'] if c['kind']=='flexible_segment'}
            raise ValueError(str(exc)+'; prototype section station counts='+json.dumps(stations)+'; every span first_segment must be 0 under base_only_consecutive_spans_v1; guide_s gives interior stations, not one entry per segment.') from exc
        if not recovering:self.s['candidate_count']+=1;self.save_state()
        # A never runs NMPC or an automatic mathematical controller.
        # This controller descriptor only compiles the original physical scene;
        # playback_tensions applies the LLM-authored inputs directly.
        r=self.put(dict(configuration=cfg,generation=plain(build.request),topology=dict(segments=request.segment_count,tendons=request.tendon_count),initial_state=cfg['task']['initializer']),'candidate_generated')
        alias=recovering or 'c'+str(self.s['candidate_count']);self.s['candidates'][alias]=r;self.save_state()
        return dict(candidate=alias,topology=dict(segments=request.segment_count,tendons=request.tendon_count),initial_tip_geometry='Along base +x; world mount from frozen task.',generation=plain(build.request))

    def candidate(self,name):return self.store.artifact(self.s['candidates'][name])
    def config_case(self,candidate,condition):
        cfg=deepcopy(candidate['configuration'])
        if not self.protocol:return cfg
        case=next(c for c in self.protocol['cases'] if c['condition_id']==condition)
        task=deepcopy(case['task']);task['acceptance']=case['acceptance']
        if case.get('environment_extension'):task['environment']['data']['physical_environment']=case['environment_extension']
        cfg['task']=task
        # A task's required cases can have different controller descriptors
        # (T07 M5 has tool-axis constraints and no reach/hold settling). Reuse
        # each original case's configuration constructor; no controller runs.
        if task.get('physical_problem'):return cfg
        cfg['policy']['controller']=task_controller(self.task,condition,task)
        if task['family']=='task.tracking':
            # These dormant NMPC costs are rejected for timed Tracking. Direct
            # tension playback never evaluates them; retain the task's zero-cost
            # descriptor rather than family defaults for Reach/Hold.
            recipe=cfg['policy']['controller']['parameters']['data']['recipe']
            recipe.update(holding_tip_speed_weight=0.,terminal_tip_speed_weight=0.)
        # Original named zero initial state, remapped to actual generated joints.
        init=task['initializer']['parameters']['data']
        if self.task!='T04':
            p=physics_for(SessionInput.model_validate(cfg))
            if any(init.get('qpos_rad',{}).values()) or any(init.get('qvel_rad_s',{}).values()):raise ValueError('NONZERO_ORIGINAL_INITIALIZER_REQUIRES_EXPLICIT_MAPPING')
            cfg['task']['initializer']['parameters']['data']={k:{j:0. for j in p['dofs']} for k in ('qpos_rad','qvel_rad_s')}
            cfg['task']['initializer']['parameters']['data']['unspecified']='zero'
        count=len(cfg['robot']['structure']['data']['tendons'])
        if count!=case['independent_channels']:raise ValueError('Original task requires '+str(case['independent_channels'])+' independent channels')
        return cfg

    def commands(self,cfg,control):
        t=cfg['task']['timing'];n=round(t['duration_s']/t['control_period_s']);times=np.arange(n)*t['control_period_s'];m=len(cfg['robot']['structure']['data']['tendons'])
        knots=control.get('knots')
        if knots:
            kt=np.asarray([v['time_s'] for v in knots]);ku=np.asarray([v['tensions_n'] for v in knots],float)
            if ku.shape!=(len(kt),m) or len(kt)<1 or np.any(np.diff(kt)<=0):raise ValueError('Ordered control knots and all tendon channels required')
            u=np.stack([np.interp(times,kt,ku[:,i]) for i in range(m)],axis=1)
        else:u=np.tile(np.asarray(control['bias_n'],float),(n,1))
        if 'period_s' in control:
            w=2*np.pi*times/float(control['period_s'])
            for h in control.get('harmonics',[]):u+=np.sin(h['order']*w)[:,None]*np.asarray(h.get('sin_n',[0]*m))+np.cos(h['order']*w)[:,None]*np.asarray(h.get('cos_n',[0]*m))
        limits=np.asarray([v['force_limit_n'] for v in cfg['robot']['structure']['data']['tendons']])
        if u.shape!=(n,m) or not np.isfinite(u).all() or np.any(u<0) or np.any(u>limits):raise ValueError('Control must stay within original nonnegative tendon force limits; no clipping')
        return u

    def physical(self,cfg,u,folder,control=None):
        steps=round(cfg['task']['timing']['duration_s']/cfg['task']['timing']['timestep_s'])
        self.guard('physics_evaluations');self.guard('integration_steps',steps)
        self.s['physics_evaluations']+=1;self.save_state()
        inp=SessionInput.model_validate(cfg);p=physics_for(inp);scene=assemble(inp,p)
        # Keep full in-memory/native evidence, but checkpoint the growing sample
        # list every 100 controls instead of rewriting it after every control.
        # This changes persistence frequency only, never integration/observations.
        import extensions.tendon_family.backends as backend_module
        original_save=backend_module.atomic_json
        def checkpoint(path,value):
            if Path(path).name=='samples.json' and isinstance(value,list) and len(value)%100!=1 and len(value)!=len(u)+1:return
            return original_save(path,value)
        backend_module.atomic_json=checkpoint
        try:
            if control and 'feedback' in control:
                from extensions.tendon_family.backends import MujocoBackend
                from tools.platform_registry import registry
                backend=MujocoBackend();backend.compile(inp,registry());backend.folder=folder
                backend.controller=FixedStateFeedback(p,control,u);backend.controller.period_s=cfg['task']['timing']['control_period_s']
                rows,observations,complete,reason,count=backend.solve(max(1.,self.limits['wall_s']-(time.time()-self.s['started'])))
                evidence=backend.task_evidence;arrays=evidence['arrays']
                initial=dict(time_s=arrays['time_s'][0],tip_m=arrays['tip_m'][0],tip_velocity_m_s=arrays['tip_velocity_m_s'][0])
                raw=dict(status='completed' if complete else 'incomplete',failure=reason,samples=[initial]+rows,
                    physics_steps=count,task_evidence=evidence,controller_observations=observations,
                    supplied_control=control,controller_construction='none; only LLM-supplied fixed coefficients')
                write(folder/'samples.json',raw['samples']);write(folder/'fixed_feedback_execution.json',raw)
            else:raw=playback_tensions(inp,p,scene,u.tolist(),folder)
        except Exception as e:
            d=getattr(e,'mujoco_diagnostic',{})
            actual=d.get('confirmed_completed_steps',0)
            self.s['integration_steps']+=actual;self.save_state()
            if not d:raise
            return dict(status='incomplete',failure=dict(reason=str(e),native_diagnostic=d),samples=read(folder/'samples.json') if (folder/'samples.json').exists() else [],physics_steps=actual,cost=dict(physics_steps=actual,physics_step_attempts=d.get('attempted_steps'),forward_evaluations=d.get('forward_evaluations')))
        finally:backend_module.atomic_json=original_save
        self.s['integration_steps']+=raw['physics_steps'];self.save_state()
        return raw

    def evaluate(self,args):
        alias=args['candidate'];candidate=self.candidate(alias);control=args.get('controls',{})
        cases=[c['condition_id'] for c in self.protocol['cases'] if c['role']=='required'] if self.protocol else ['all_load_cases']
        allowed=[c['condition_id'] for c in self.protocol['cases']] if self.protocol else cases
        out=[]
        requested=args.get('conditions',list(control) if control and 'default' not in control else cases)
        # Validate every authored input before launching any physics in this command.
        for cond in requested:
            if cond not in allowed:raise CommandError('Unknown condition')
            cfg=self.config_case(candidate,cond)
            if cfg['task'].get('physical_problem'):
                if control:raise CommandError('Passive tasks have no active control input')
            else:
                ctl=control.get(cond,control.get('default'))
                if ctl is None:raise CommandError('Explicit control required for '+cond)
                u=self.commands(cfg,ctl)
                if ctl.get('initial_equilibrium_reference') and self.method!='B':raise CommandError('Only B can hand off a mathematical equilibrium artifact')
                if 'feedback' in ctl:
                    if self.task!='T10':raise CommandError('Fixed state feedback is exposed for T10 only')
                    FixedStateFeedback(physics_for(SessionInput.model_validate(cfg)),ctl,u)
        for cond in requested:
            cfg=self.config_case(candidate,cond)
            folder=self.folder/'physics'/f"p{self.s['physics_evaluations']+1:03d}-{alias}-{cond}";folder.mkdir(parents=True,exist_ok=True)
            if cfg['task'].get('physical_problem'):
                from extensions.tendon_family.passive_execution import execute
                timing=cfg['task']['timing'];goal=cfg['task']['goal']['data'];loads=goal['load_conditions']
                first=goal['programs'][loads[0]]
                unloaded_end=next(v['end_s'] for v in first if v['name']==goal['unloaded_stage'])
                steps=round((timing['duration_s']+(len(loads)-1)*(timing['duration_s']-unloaded_end))/timing['timestep_s'])
                self.guard('integration_steps',steps)
                self.guard('physics_evaluations');self.s['physics_evaluations']+=1;self.save_state()
                raw=execute(SessionInput.model_validate(cfg),folder).data.data
                self.s['integration_steps']+=raw.get('cost',{}).get('physics_steps',raw.get('physics_steps',0))
                self.s['physics_evaluations']+=max(0,len(raw.get('episodes',[]))-1);self.save_state()
                if self.task=='T08' and args.get('confirm',True) and raw.get('episodes') and all(
                        e.get('complete') and e.get('qualifications') and all(q.get('passed') is True for q in e['qualifications'].values()) for e in raw['episodes']):
                    # Mandatory physical mechanism/confirmation evidence, shared
                    # by A/B. These are existing frozen task executions, not
                    # optional mathematics or automatic design optimization.
                    from extensions.tendon_family.passive_execution import execute_pair,execute_confirmation
                    self.guard('integration_steps',6*steps);self.guard('physics_evaluations',10)
                    inp=SessionInput.model_validate(cfg);baseline_ref=self.put(raw,'passive_primary_execution')
                    reused=dict(raw=raw,source=dict(reference=baseline_ref,pointer='/'),
                        execution_directory=str(folder),actual_new_cost={k:0 for k in raw['cost']})
                    pair=execute_pair(inp,folder/'mechanism',[t['id'] for t in cfg['robot']['structure']['data']['tendons']],baseline=reused).data.data
                    self.s['integration_steps']+=pair['cost']['physics_steps'];self.s['physics_evaluations']+=len(pair.get('paired_ablation',{}).get('ablation',{}).get('episodes',[]));self.save_state()
                    pair_ref=self.put(pair,'passive_required_mechanism')
                    raw=execute_confirmation(inp,folder/'confirmation',pair,pair_ref,self.id+'-'+folder.name).data.data
                    self.s['integration_steps']+=raw['cost']['physics_steps']
                    self.s['physics_evaluations']+=len(raw.get('episodes',[]))+len(raw.get('paired_ablation',{}).get('ablation',{}).get('episodes',[]))+sum(len(v['raw'].get('episodes',[])) for v in raw.get('numerical_confirmation',{}).get('executions',{}).values());self.save_state()
            else:
                ctl=control.get(cond,control.get('default'))
                if ctl is None:raise ValueError('Explicit control required for '+cond)
                if self.task=='T04':
                    try:cfg=self.prepared(cfg,ctl,folder)
                    except InitialConditionFailed:
                        row=dict(candidate=alias,condition=cond,accepted=False,validity='initial_condition_failed',
                            trajectory_executed=False,reference=self.last_qualification['reference'],
                            static_balance_residual_nm=self.last_qualification['residual'])
                        self.s['evaluations'].append(row);self.save_state();self.trace('initial_condition_failed',row);out.append(row);continue
                u=self.commands(cfg,ctl);self.put(dict(candidate=alias,condition=cond,control=ctl,applied_inputs_n=u.tolist()),'control_inputs')
                raw=self.physical(cfg,u,folder,ctl)
            rr=self.put(raw,'physical_execution');ev,profile=evaluate_playback(cfg,raw,rr,digest(cfg))
            er=self.put(dict(evaluation=plain(ev),profile=profile,configuration=cfg,raw=rr),'independent_evaluation')
            detail=plain(ev).get('diagnostics',{});constraints=detail.get('constraints',{})
            violations=[]
            for c in constraints.values():
                if isinstance(c,dict) and isinstance(c.get('normalized_violation'),(int,float)):violations.append(c['normalized_violation'])
                elif isinstance(c,dict) and isinstance(c.get('margin'),(int,float)):
                    limit=c.get('limit',0);violations.append(max(0.,-c['margin'])/(abs(limit) if isinstance(limit,(int,float)) and limit else 1.))
            samples=raw.get('samples',[])
            row=dict(candidate=alias,condition=cond,accepted=ev.task_success,validity=ev.validity,diagnostics=detail,metrics=clean(plain(ev).get('metrics')),max_violation=max(violations) if violations else None,reference=er,raw=rr,physical_observations=[samples[i] for i in sorted(set([0,len(samples)//4,len(samples)//2,len(samples)-1]))] if samples else [],cumulative={k:self.s[k] for k in ['physics_evaluations','integration_steps','mathematical_calls','llm_tokens']})
            if cfg['task'].get('physical_problem'):row['required_case_results']=passive_cases(cfg['task'],raw,plain(ev),er)
            self.s['evaluations'].append(row);self.save_state();self.trace('evaluation',row);out.append(row)
        return out

    def prepared(self,cfg,ctl,folder):
        from tools.research.prepared_initial import qualify
        # Task-required prepared initial condition constructed solely by physical
        # settling, equally for A/B; no optional equilibrium optimizer/Jacobian.
        settle=deepcopy(cfg);settle['task']['acceptance']=None
        # Keep the frozen timed reference horizon during preparation too. Shorter
        # auxiliary horizons are rejected by the existing task adapter.
        settle['task']['sampling']['window_s']=[settle['task']['timing']['sample_period_s'],settle['task']['timing']['duration_s']]
        p=physics_for(SessionInput.model_validate(settle));m=len(p['tendons'])
        initial_u=ctl.get('initial_tensions_n',ctl.get('bias_n',[.2]*m))
        equilibrium=ctl.get('initial_equilibrium_reference')
        if equilibrium:
            if self.method!='B':raise PermissionError('A cannot use a mathematical equilibrium artifact')
            from extensions.tendon_family.gvs_projection import discretize
            value=self.store.artifact(equilibrium);binding=value.get('source_binding',{})
            if binding.get('tensions_n')!=initial_u or not value.get('q_equilibrium'):raise CommandError('Own equilibrium result and exact applied tensions must match')
            self.guard('mathematical_calls');self.s['mathematical_calls']+=1;self.save_state()
            qg=value['q_equilibrium'];qnative,_=discretize(p,cfg['robot']['structure']['data'],qg,[0.]*len(qg),basis=binding.get('basis',{'strategy':'structural_linear'}))
            q=dict(zip(p['dofs'],qnative.tolist()))
            self.trace('equilibrium_state_handoff',dict(source=equilibrium,qpos_rad=q,mathematical_converged=value.get('converged'),coordinate_mapping='Existing gvs_projection.discretize; no native equilibrium claim before qualification.'))
        else:
            n=round(settle['task']['timing']['duration_s']/settle['task']['timing']['control_period_s'])
            settle['task']['initializer']['parameters']['data']=dict(qpos_rad={j:0. for j in p['dofs']},qvel_rad_s={j:0. for j in p['dofs']},unspecified='zero')
            sf=folder/'initial_settling';sf.mkdir(exist_ok=True)
            raw=self.physical(settle,np.tile(initial_u,(n,1)),sf);self.put(raw,'task_required_initial_settling')
            q=dict(zip(p['dofs'],raw['samples'][-1]['qpos_rad']))
        u=dict(zip([t['entity'] for t in p['tendons']],initial_u))
        prepared=qualify(cfg,q,u,folder/'qualified_initial.xml');ref=self.put(dict(contract='task.prepared_initial',data=prepared),'mandatory_initial_qualification')
        self.last_qualification=dict(qualified=prepared['qualified'],residual=prepared['static_balance_inf_nm'],limit=prepared['static_balance_limit_nm'],reference=ref,optional_mathematical_tool=False)
        self.trace('initial_qualification',self.last_qualification)
        if not prepared['qualified']:raise InitialConditionFailed('Original static qualification failed: '+str(prepared['static_balance_inf_nm']))
        cfg['task']['initializer']['parameters']['data']={k:prepared[k] for k in ('qpos_rad','qvel_rad_s','tensions_n')};cfg['task']['initializer']['parameters']['data'].update(qualification=ref,unspecified='zero')
        return cfg

    def math(self,args):
        if self.method!='B':raise PermissionError('llm_only forbids all optional mathematical tools')
        self.guard('mathematical_calls');self.s['mathematical_calls']+=1;self.save_state()
        if self.base['task'].get('physical_problem') and args['operation'] in ('equilibrium','kkt','jacobian','finite_difference'):
            from extensions.tendon_family.passive import PassiveModel
            from extensions.tendon_family.passive_equilibrium import solve, StaticProblem, tangent
            from extensions.tendon_family.passive_execution import task_definition
            from tools.platform_registry import registry
            cfg=self.candidate(args['candidate'])['configuration'];inp=SessionInput.model_validate(cfg)
            goal,bounds,problem=task_definition(inp.task,registry());native=PassiveModel(physics_for(inp),plain(problem))
            s=args.get('material_s',.5);force=args.get('force_world_n',[0.,0.,0.]);q=args.get('qpos_rad',[0.]*native.model.nv)
            if args['operation']=='jacobian':
                problem=StaticProblem(native,s,force)
                value=dict(tendon_length_jacobian=problem.jacobian(np.asarray(q)).tolist(),cost=problem.cost,coordinate_count=native.model.nv)
            else:
                value=solve(native,s=s,force=force,initial=q,multistart=False)
                if args['operation']=='finite_difference':value=tangent(native,value,s,args.get('force_n',.1),args['locations'],increment=args['increment_n'],direction_world=args['direction_world'])
            r=self.put(value,'direct_passive_equilibrium_kkt');return dict(reference=r,result=clean(value))
        from extensions.tendon_family.mujoco_analysis import NativeModel, input_response
        import mujoco
        candidate=self.candidate(args['candidate']);cond=args.get('condition',self.protocol['cases'][0]['condition_id'] if self.protocol else None)
        cfg=self.config_case(candidate,cond)
        if args['operation']=='equilibrium':
            from types import SimpleNamespace
            from extensions.tendon_family.gvs_casadi import gvs_equilibrium_tool
            from extensions.tendon_family.contracts import GVSEquilibriumRequest
            from extensions.tendon_family.gvs_basis import resolve_basis
            inp=SessionInput.model_validate(cfg);basis=args.get('basis',{'strategy':'structural_linear'})
            n=len(resolve_basis(inp.robot.structure.data,basis).coordinate_order)
            names=[t['id'] for t in cfg['robot']['structure']['data']['tendons']]
            request=GVSEquilibriumRequest.model_validate(dict(tendon_tensions_n=dict(zip(names,args['tensions_n'])),initial_q=args.get('initial_q',[0.]*n),basis=basis,tolerance=args.get('tolerance',1e-10),max_iterations=args.get('max_iterations',50)))
            value=plain(gvs_equilibrium_tool(SimpleNamespace(input=inp),request))
            value['source_binding']=dict(candidate=args['candidate'],tensions_n=args['tensions_n'],basis=basis)
            r=self.put(value,'direct_gvs_equilibrium');return dict(reference=r,result=value)
        native=NativeModel(cfg);d=mujoco.MjData(native.model)
        for key in ('qpos_rad','qvel_rad_s'):
            if key in args and len(args[key])!=len(native.order):raise ValueError('Native '+key+' requires '+str(len(native.order))+' entries in this exact order: '+json.dumps(native.order)+'. Omit it to use the original all-zero state. GVS reduced coordinates cannot be supplied here.')
        d.qpos[native.qi]=args.get('qpos_rad',[0.]*len(native.order));d.qvel[native.vi]=args.get('qvel_rad_s',[0.]*len(native.order))
        u=np.asarray(args.get('tensions_n',[.2]*len(native.tendons)));native.apply(d,u)
        if args['operation']=='jacobian':
            motion,jac=native.motion(d);value=dict(motion=motion,jacobian_m_rad=jac.tolist(),coordinate_order=native.order,tendon_order=native.tendons,cost=native.cost)
        elif args['operation']=='mechanics':value=native.mechanics(d,u)
        elif args['operation']=='finite_difference':
            from tools.research.contracts import NativeAnalysisOptions
            options=NativeAnalysisOptions.model_validate(args['options'])
            value=input_response(native,d,u,options)
        else:raise PermissionError('Only directly exposed low-level operations are allowed')
        r=self.put(value,'direct_mathematical_result');self.s['integration_steps']+=native.cost['physics_steps'];self.save_state()
        return dict(reference=r,**clean(value))

    def context(self):
        space=deepcopy(self.space);assembly=space.pop('assembly')
        schema=GenerationRequestV2.model_json_schema();schema['properties'].pop('family_space_identity',None);schema['required'].remove('family_space_identity')
        cases=self.protocol['cases'] if self.protocol else [dict(condition_id='all_load_cases',task=self.base['task'])]
        return dict(task_id=self.task,method=MODES[self.method],legal_design_space=space,assembly_prototypes=assembly,generation_schema=schema,
            tasks=[dict(condition_id=c['condition_id'],role=c.get('role','required'),task={k:v for k,v in c['task'].items() if k in ('family','goal','timing','physical_problem','environment')},initial_condition='Original all-zero named joint position and velocity; T04 requires physically prepared qualified equilibrium.',acceptance=c.get('acceptance'),independent_channels=c.get('independent_channels')) for c in cases],
            limits=self.limits,physics='Existing native MuJoCo serial bending model, original frozen evaluator. Full legal structure generation; all candidates start from task initial conditions.',
            control_interface=dict(description='PHS-2D is passive: no active control or control_weights/recipe edits. LLM chooses structure, routing and fixed payout lengths. evaluate needs candidate only and executes the original ten-load-case native protocol, including its required fresh unloaded physical equilibrium solver.' if self.task=='PHS-2D' else 'Explicit absolute nonnegative tension in N. Each condition uses knots=[{time_s,tensions_n:[all channels]}], linearly interpolated on original grid. Or bias_n plus optional period_s and harmonics=[{order,sin_n,cos_n}]. No optimizer or NMPC runs. T04: initial_tensions_n constructs the required initial equilibrium by constant-input physical settling over the frozen 22 s reference horizon; shorter settle_s cannot shorten that required preparation horizon. The independent task then runs its own full 22 s from the qualified prepared state.'),
            task_specific_interface=(dict(passive=True,conditions='One both_directions execution retains plus_x/minus_x separately. No active control. Frozen development_not_registered_SELECT classification; original qualification, mechanism and numerical confirmation are required.') if self.task=='T08' else
                dict(feedback='T10 accepts control.feedback={gain:[[nu,2*n]],qref_rad:[n],vref_rad_s:[n]}; explicitly author every coefficient. n=segment_count*24 native named hinges. Control is feedforward(time) - gain @ [measured_q-qref,measured_v-vref], clipped by existing ideal tension bounds. No gain construction or optimization is called. Same candidate/control law for required and separate frozen-input control cases.') if self.task=='T10' else
                dict(equilibrium_handoff='B may supply initial_equilibrium_reference from its own converged equilibrium tool, plus identical initial_tensions_n. Existing GVS-to-native mapping then original static qualification; residual threshold remains 1e-7 N.m, trajectory remains 22 s.') if self.task=='T04' else None),
            generation_notes=dict(section_station_counts={c['id']:len(c.get('sections',[])) for c in assembly['components'] if c['kind']=='flexible_segment'},rules='sections replaces each existing section station, so supply the exact prototype count; omitting sections preserves original sections. All spans first_segment=0 under base-only rule. guide_s lists interior normalized guide stations. Candidate aliases are returned only on success.'),
            mathematical_interface=None if self.method=='A' else dict(operations=['equilibrium','kkt','jacobian','finite_difference'] if self.task=='PHS-2D' else ['jacobian','mechanics','finite_difference','equilibrium'],description='Direct existing native kernels only. Explicit candidate, condition, qpos_rad,qvel_rad_s,tensions_n. Active finite_difference options={horizon_s:0.01,difference_step_n:0.02}; horizon <=0.05. Active equilibrium uses existing GVS damped Newton: tensions_n, optional basis={strategy:structural_linear},initial_q,max_iterations,tolerance. Passive equilibrium/kkt/jacobian args material_s,force_world_n,qpos_rad; passive finite_difference additionally requires explicit locations,increment_n,direction_world,force_n. No intent projection, automatic problem constructor, differentiation router or high-level research optimization.'),
            knowledge='Generic SI mechanics, family domains and task definitions only. Historical FULL final designs and decision traces are inaccessible.')

    def step(self,command):
        validate_command(command,self.method)
        op=command['operation'];args=command['arguments']
        if op=='generate':return self.generate(args)
        if op=='evaluate':return self.evaluate(args)
        if op=='math':return self.math(args)
        if op=='finish':
            alias=args.get('candidate')
            if alias not in self.s['candidates']:raise ValueError('Finish must name an existing generated candidate: '+str(list(self.s['candidates'])))
            required=[c['condition_id'] for c in self.protocol['cases'] if c['role']=='required'] if self.protocol else ['all_load_cases']
            measured={r['condition'] for r in self.s['evaluations'] if r['candidate']==alias}
            missing=sorted(set(required)-measured)
            if missing and self.task!='T04' and self.limits['physics_evaluations']-self.s['physics_evaluations']>=len(missing) and self.s['requests']<self.limits['requests']:
                raise ValueError('Required conditions still need original physical evaluation on '+alias+': '+json.dumps(missing)+'. Provide explicit controls; failure results are acceptable. No success is required.')
            self.s['selected']=args.get('candidate');self.s['status']='completed';return dict(status='completed')
        raise PermissionError('Unregistered operation: '+op)

    def run(self):
        if self.s['status']=='completed':return
        if self.s['status']=='environment_blocked':self.s['status']='running'
        if not self.s['messages']:
            self.s['messages']=[dict(role='system',content='You are the sole research/design LLM in a formal bounded experiment. Independently design a soft robot and explicit controls. You may use every legal FamilySpace parameter and topology; do not assume any historical solution. Return one research_step JSON object each turn. Its commands execute sequentially; inspect actual physics between revisions. Commands: generate arguments {generation:full GenerationRequestV2 without family_space_identity}; evaluate arguments {candidate:cN, controls:{condition:control}, optional conditions:[...]}; '+('math is forbidden. ' if self.method=='A' else 'math arguments {candidate,operation:jacobian|mechanics|finite_difference|equilibrium|kkt, condition,qpos_rad,qvel_rad_s,tensions_n,options}. Choose your own mathematical question/parameters. ')+ 'finish arguments {candidate:cN}. Every call must record concise decision, cited earlier evidence and expected outcome. Never infer acceptance without every original required condition. No tools for historical files, shell, automatic optimization or high-level math exist. Use budget efficiently, revise structure and control based on evidence. At most 60 requests, plus the stated finite token, structure and physics ceilings; leave a final evaluated candidate. Physical failure is a valid result. One action batch can generate and evaluate the new known alias c1,c2,... .'),dict(role='user',content=json.dumps(self.context(),ensure_ascii=False))]
            self.s['messages'][0]['content']+=' Transport uses text JSON, no function-calling API. Return exactly the object defined by this JSON Schema, no markdown: '+json.dumps(command_schema(self.method))+'. generation arguments are {generation:GenerationRequestV2}; evaluate requires {candidate,controls:{condition:control},conditions?:[condition]}; math requires {candidate,operation,...explicit parameters}; finish requires {candidate}. Only successful generation returns an alias. Every required case must use the same final candidate; T10 control-role cases are evaluated and reported separately.'
            self.save_state()
        elif 'Transport uses text JSON' not in self.s['messages'][0]['content']:
            self.s['messages'][0]['content']+=' Transport uses text JSON: return the research_step arguments object {decision,evidence,commands} as JSON text, with no markdown. The Host enforces the same operation allowlist.'
        cred=read(Path(PROVIDER['credential']).expanduser())
        while self.s['requests']<self.limits['requests'] and self.s['status']=='running':
            try:self.guard('requests')
            except ValueError as exc:
                self.s['status']='budget_complete';self.s['stop_reason']=str(exc);break
            wire=self.s['messages'] if len(self.s['messages'])<=4 else self.s['messages'][:2]+self.s['messages'][-2:]
            # Exact owned working set survives bounded conversational context.
            latest={(r['candidate'],r['condition']):r for r in self.s['evaluations']}
            snapshot=dict(available_candidates={k:self.candidate(k)['topology'] for k in self.s['candidates']},latest_evaluations=[{k:r.get(k) for k in ('candidate','condition','accepted','validity','max_violation','reference')} for r in latest.values()],current_limits=self.limits,resource_use={k:self.s[k] for k in ('requests','llm_tokens','candidate_count','physics_evaluations','integration_steps','mathematical_calls')})
            wire=wire+[dict(role='user',content='Current authoritative own-run working set: '+json.dumps(snapshot))]
            idx=self.s['requests']+1;request=dict(model=PROVIDER['model'],messages=wire,stream=False)
            # Reserve the serialized input conservatively plus the existing
            # runtime's 32768-token response allowance before sending.
            reservation=token_reservation(request)
            unknown_reserved=sum(self.s.get('token_reservations',{}).get(str(n),{}).get('total',0) for n in self.s.get('unreported_token_requests',[]))
            if self.s['llm_tokens']+unknown_reserved+reservation['total']>self.limits['llm_tokens']:
                self.trace('token_budget_stop',dict(reported_tokens=self.s['llm_tokens'],unreported_reserved=unknown_reserved,remaining=self.limits['llm_tokens']-self.s['llm_tokens']-unknown_reserved,reservation=reservation))
                self.s['status']='budget_complete';break
            self.s.setdefault('token_reservations',{})[str(idx)]=reservation
            self.trace('provider_request',dict(request_number=idx,request=request,token_reservation=reservation))
            self.s['requests']+=1;self.save_state();start=time.time()
            try:
                with httpx.Client(timeout=600,trust_env=False) as client:
                    resp=client.post(PROVIDER['base_url']+'/chat/completions',headers={'Authorization':'Bearer '+cred['api_key']},json=request)
                    if resp.status_code!=200:raise RuntimeError('HTTP '+str(resp.status_code)+': '+resp.text[:3000])
                    response=resp.json()
                self.trace('provider_response',dict(request_number=idx,response=response,wall_s=time.time()-start))
                usage=response.get('usage') or {}
                if usage.get('total_tokens') is None:self.s.setdefault('unreported_token_requests',[]).append(idx)
                else:self.s['llm_tokens']+=usage['total_tokens']
                self.s.setdefault('token_usage_records',[]).append(usage)
                message=response['choices'][0]['message'];self.s['messages'].append(dict(role='assistant',content=message.get('content') or ''))
                calls=message.get('tool_calls',[])
                if not calls:
                    content=message.get('content','').strip()
                    if content.startswith('```'):content=content.split('\n',1)[1].rsplit('```',1)[0].strip()
                    calls=[dict(id='text-'+str(idx),function=dict(arguments=content))]
                for call in calls:
                    try:value=validate_step(command_json(call['function']['arguments']),self.method)
                    except (ValueError,TypeError) as exc:raise CommandError(str(exc)) from exc
                    self.trace('research_decision',dict(request_number=idx,**value));feedback=[]
                    for command in value['commands']:
                        try:result=self.step(command)
                        except Exception as exc:
                            result=dict(error=type(exc).__name__,reason=str(exc),error_class='tool_interface')
                            self.trace('operation_error',dict(command=command,**result,traceback=traceback.format_exc()))
                            if str(exc).startswith('BUDGET_EXHAUSTED:'):self.s['status']='budget_complete';self.s['stop_reason']=str(exc)
                        feedback.append(dict(command=command,result=compact_feedback(result)))
                        self.save_state()
                        if self.s['status']=='budget_complete':break
                    # Native full artifacts stay in Store; bounded exact numerical feedback.
                    self.s['messages'].append(dict(role='user',content=json.dumps(clean(dict(feedback=feedback,remaining={k:self.limits[k]-self.s[k] for k in ['requests','llm_tokens','candidate_count','mathematical_calls']},resource_use={k:self.s[k] for k in ['candidate_count','physics_evaluations','integration_steps']},instruction='Continue independent research or finish. All required conditions must be evaluated on one final design.')),ensure_ascii=False)))
            except CommandError as exc:
                self.trace('command_contract_error',dict(request_number=idx,error=str(exc),physics_started=False))
                self.s['messages'].append(dict(role='user',content=json.dumps(dict(command_error=str(exc),schema=command_schema(self.method),instruction='No commands from this malformed step executed. Correct the command contract.'))))
            except Exception as exc:
                self.trace('provider_error',dict(request_number=idx,error=type(exc).__name__,reason=str(exc)))
                if not any(u for u in self.s.get('token_usage_records',[])[-1:] if u.get('total_tokens') is not None) or len(self.s.get('token_usage_records',[]))<idx:
                    if idx not in self.s.setdefault('unreported_token_requests',[]):self.s['unreported_token_requests'].append(idx)
                self.s['status']='environment_blocked';self.s['block_reason']=str(exc)
            self.save_state()
            print(json.dumps(dict(task=self.task,method=self.method,request=idx,status=self.s['status'],candidates=self.s['candidate_count'],evaluations=self.s['physics_evaluations'],tokens=self.s['llm_tokens'])),flush=True)
        if self.s['status']=='running':self.s['status']='budget_complete'
        self.s['wall_time']=time.time()-self.s['started'];self.save_state();self.finalize()

    def recover_last(self):
        """Replay only pre-physics interface failures from the last authored plan."""
        decisions=[json.loads(l) for l in (self.folder/'TRACE.jsonl').read_text(encoding='utf8').splitlines() if json.loads(l)['kind']=='research_decision']
        plan=decisions[-1];self.recover_alias='c'+str(self.s['candidate_count'])
        if self.recover_alias in self.s['candidates']:raise ValueError('Last candidate already generated; do not duplicate formal work')
        self.s['status']='running';feedback=[]
        self.trace('interface_recovery',dict(reason='Normalize duplicate interior guide stations and accepted command spellings; resume the same last failed generation and LLM-authored evaluations, no new experiment.',original_request=plan['request_number']))
        for command in plan['commands']:
            op=command.get('operation',next(iter(command)))
            if op=='finish':continue
            try:result=self.step(command)
            except Exception as exc:result=dict(error=type(exc).__name__,reason=str(exc));self.trace('operation_error',dict(command=command,**result))
            feedback.append(dict(command=command,result=result))
        del self.recover_alias
        self.s.pop('selected',None)
        self.s['messages'].append(dict(role='user',content=json.dumps(clean(dict(interface_recovery_feedback=feedback,remaining_requests=self.limits['requests']-self.s['requests'],instruction='The same formal run continued after an adapter repair. Interpret actual evidence and use remaining paired budget. Finish only with an existing candidate.')),ensure_ascii=False)))
        self.save_state();self.run()

    def record_interruption(self):
        entries=[json.loads(l) for l in (self.folder/'TRACE.jsonl').read_text(encoding='utf8').splitlines()]
        sent={x['request_number'] for x in entries if x['kind']=='provider_request'}
        returned={x['request_number'] for x in entries if x['kind'] in ('provider_response','provider_error')}
        missing=sorted(sent-returned)
        self.s.setdefault('unreported_token_requests',[])
        for n in missing:
            if n not in self.s['unreported_token_requests']:self.s['unreported_token_requests'].append(n)
        self.trace('host_repair_interruption',dict(reason='Stop the two owned T04 clients to repair FamilySpace numeric canonicalization. No physics had started. Requests retain their count; interrupted response token usage is unknown.',requests_with_unknown_tokens=missing))
        self.save_state()

    def resume_interface(self):
        self.s['status']='running'
        latest={(r['candidate'],r['condition']):r for r in self.s['evaluations']}
        self.s['messages'][1]=dict(role='user',content=json.dumps(self.context(),ensure_ascii=False))
        self.s['messages'].append(dict(role='user',content=json.dumps(dict(host_interface_repair='FamilySpace identity is now canonicalized using the existing parser. T04 physical settling now uses its own preparation sampling window, while the final task retains its original 22 s duration and acceptance. Native math vectors require all named MuJoCo hinge coordinates, or omit vectors for zero. Continue this same run with existing candidates; no physics evaluations need repetition merely because an interface failed before execution.',available_candidates={k:self.candidate(k)['topology'] for k in self.s['candidates']},existing_evaluations=list(latest.values()),remaining={k:self.limits[k]-self.s[k] for k in self.limits if k in self.s and isinstance(self.s[k],(int,float))}),ensure_ascii=False)))
        self.trace('resume_existing_run',dict(reason='Necessary interface repair, same Store and cumulative budgets.'))
        self.save_state();self.run()

    def recover_response(self):
        entries=[json.loads(l) for l in (self.folder/'TRACE.jsonl').read_text(encoding='utf8').splitlines()]
        response=next(x for x in reversed(entries) if x['kind']=='provider_response')
        idx=response['request_number']
        if any(x['kind']=='research_decision' and x['request_number']==idx for x in entries):raise ValueError('Response already dispatched; no duplicate execution')
        value=command_json(response['response']['choices'][0]['message']['content'])
        self.trace('research_decision',dict(request_number=idx,transport_delimiter_recovery=True,**value));feedback=[];self.s['status']='running'
        for command in value['commands']:
            try:result=self.step(command)
            except Exception as exc:result=dict(error=type(exc).__name__,reason=str(exc));self.trace('operation_error',dict(command=command,**result))
            feedback.append(dict(command=command,result=result))
        self.s['messages'].append(dict(role='user',content=json.dumps(clean(dict(feedback=feedback,interface_repair='Only omitted closing JSON delimiters were restored; research fields and numbers unchanged.')),ensure_ascii=False)))
        self.save_state();self.run()

    def recover_evaluation(self):
        entries=[json.loads(l) for l in (self.folder/'TRACE.jsonl').read_text(encoding='utf8').splitlines()]
        errors=[x for x in entries if x['kind']=='operation_error' and x.get('command',{}).get('operation')=='evaluate']
        if not errors:raise ValueError('No authored evaluation to recover')
        command=errors[-1]['command'];alias=command['arguments']['candidate']
        if any(r['candidate']==alias for r in self.s['evaluations']):raise ValueError('Candidate already has actual evaluation; no duplicate recovery')
        self.trace('recover_authored_evaluation',dict(command=command,reason='Resume the last original LLM-authored control after repairing a pre-physics adapter error. No task/design/control numbers changed.'))
        self.s['status']='running'
        try:result=self.step(command)
        except Exception as exc:result=dict(error=type(exc).__name__,reason=str(exc));self.trace('operation_error',dict(command=command,**result))
        self.s['messages'].append(dict(role='user',content=json.dumps(clean(dict(recovered_evaluation=result)),ensure_ascii=False)))
        self.save_state();self.run()

    def finalize(self):
        if self.task=='T01' and self.method=='A':
            # The initial adapter's exception path charged a full planned
            # episode. Replace that with the already-saved native step counts.
            cumulative=0;checkpoints={}
            for folder in sorted((self.folder/'physics').glob('p*')):
                if not folder.is_dir():continue
                failure=folder/'numerical_failure.json';samples=folder/'samples.json'
                if failure.exists():count=read(failure)['confirmed_completed_steps']
                elif samples.exists():count=round(read(samples)[-1]['engine_time_s']/self.base['task']['timing']['timestep_s'])
                else:count=0
                cumulative+=count
                key=folder.name.split('-',1)[1];checkpoints.setdefault(key,[]).append(cumulative)
            if cumulative!=self.s['integration_steps']:
                before=self.s['integration_steps'];self.s['integration_steps']=cumulative
                for row in self.s['evaluations']:
                    points=checkpoints.get(row['candidate']+'-'+row['condition'],[])
                    if points:row['cumulative']['integration_steps']=points.pop(0)
                self.trace('confirmed_integration_cost_correction',dict(previous=before,confirmed=cumulative,basis='Existing native failure snapshots and completed engine sample times; no physics rerun.',corrected_evaluations=self.s['evaluations']))
                self.save_state()
        selected=self.s.get('selected')
        if selected is None and self.s['evaluations']:selected=self.s['evaluations'][-1]['candidate']
        if selected not in self.s['candidates'] and self.s['candidates']:selected=next(reversed(self.s['candidates']))
        final=dict(task_id=self.task,method=self.method,run_id=self.id,status=self.s['status'],selected=selected,candidate=self.candidate(selected) if selected in self.s['candidates'] else None,evaluations=[r for r in self.s['evaluations'] if r['candidate']==selected],resources={k:self.s.get(k) for k in ['requests','llm_tokens','candidate_count','physics_evaluations','integration_steps','mathematical_calls','wall_time','unreported_token_requests']},block_reason=self.s.get('block_reason'))
        final['selection_origin']='llm_final_choice' if self.s.get('selected') in self.s['candidates'] else 'last_evaluated_at_budget_stop' if final['evaluations'] else 'last_generated_no_complete_task_evaluation'
        if self.s['status']!='environment_blocked':final['block_reason']=None
        if self.task=='T04' and not final['evaluations']:
            entries=[json.loads(l) for l in (self.folder/'TRACE.jsonl').read_text(encoding='utf8').splitlines()]
            initial=[x for x in entries if x['kind']=='initial_qualification']
            if initial and not initial[-1]['qualified']:
                final['required_stage_outcomes']=dict(default=dict(accepted=False,validity='initial_condition_failed',trajectory_executed=False,qualification=initial[-1]['reference'],static_balance_residual_nm=initial[-1]['residual']))
        if self.task=='PHS-2D' and final['evaluations']:
            last=final['evaluations'][-1];record=self.store.artifact(last['reference']);raw=self.store.artifact(record['raw'])
            observed=record['evaluation'].get('diagnostics',{}).get('observations',{})
            task=record['configuration']['task'];bounds=task['evaluator']['parameters']['data']['bounds'];cases={}
            for case in task['goal']['data']['load_conditions']:
                episode=next((e for e in raw.get('episodes',[]) if e['load_condition']==case),None)
                names={b['name'] for b in bounds if b['load_condition']==case}
                checks={k:v for k,v in observed.items() if any(k.startswith('evaluator:'+n+'_') for n in names)}
                qualifications=(episode or {}).get('qualifications',{})
                complete=bool(episode and episode.get('complete'))
                known=bool(checks) and all(v.get('passed') is not None for v in checks.values())
                qualified=bool(qualifications) and all(v.get('passed') is True for v in qualifications.values())
                stage_fail=any(v.get('passed') is False for v in qualifications.values())
                accepted=(all(v['passed'] for v in checks.values()) and qualified and episode.get('maximum_contacts',0)==0) if complete and known else False if stage_fail else None
                cases[case]=dict(accepted=accepted,validity='valid' if complete and known and qualified else 'qualification_failed' if stage_fail else 'incomplete',complete=complete,checks=checks,qualifications=qualifications,reference=last['reference'],raw=record['raw'])
            final['required_case_results']=cases
        if final['evaluations'] and final['evaluations'][-1].get('required_case_results'):
            final['required_case_results']=final['evaluations'][-1]['required_case_results']
        initial={r['condition']:r for r in final['evaluations'] if r.get('validity')=='initial_condition_failed'}
        if initial:final['required_stage_outcomes']=initial
        final['raw_run_status']=self.s['status']
        required=[c['condition_id'] for c in self.protocol['cases'] if c['role']=='required'] if self.protocol else ['all_load_cases']
        latest={r['condition']:r for r in final['evaluations']}
        if final.get('required_case_results'):latest=final['required_case_results'];required=list(latest)
        stages=final.get('required_stage_outcomes',{})
        final['scientific_result']=('INITIAL_CONDITION_FAILED' if stages else 'QUALIFICATION_FAILED' if any(r.get('validity')=='qualification_failed' for r in latest.values()) else
            'PASS' if all(c in latest and latest[c].get('accepted') is True for c in required) else
            'VALID_FAILURE' if all(c in latest and latest[c].get('validity')=='valid' and latest[c].get('accepted') is not None for c in required) else
            'INTERFACE_ERROR' if self.s['status']=='environment_blocked' else 'INCOMPLETE')
        final['control_case_results']={c['condition_id']:latest.get(c['condition_id']) for c in (self.protocol or {}).get('cases',[]) if c['role']=='control'}
        final['source_classification']=(self.protocol or {}).get('source_status')
        final['resources']['llm_tokens_reported']=self.s['llm_tokens']
        if self.s.get('unreported_token_requests'):final['resources']['llm_tokens']=None
        final['stop_reason']=self.s.get('stop_reason')
        final['resources']['structure_generation_attempts']=self.s['candidate_count']
        final['resources']['candidate_count']=len(self.s['candidates'])
        self.put(final,'final_result');write(self.folder/'result.json',final)

def check_task(task):
    r=Run.__new__(Run);r.task=task;r.base,r.space,r.protocol=inputs(task)
    parse_space(r.space)
    checks=[]
    for case in (r.protocol or {}).get('cases',[]):
        cfg=r.config_case(dict(configuration=r.base),case['condition_id'])
        SessionInput.model_validate(cfg)
        checks.append(dict(condition=case['condition_id'],role=case['role'],family=cfg['task']['family'],timing=cfg['task']['timing'],channels=case.get('independent_channels')))
    return dict(task=task,core_commit='56cc418',source_classification=(r.protocol or {}).get('source_status'),cases=checks,
        domain=dict(segments=r.space['executable_segment_counts'],tendons=r.space['executable_tendon_count_bounds']),provider_requests=0,physics_executions=0)

def supplement_t04():
    """Read original B evidence; write only a new, bounded supplement Store."""
    destination=HERE/'SUPPLEMENTS/issue1_20261114'
    result_path=destination/'T04/B/result.json'
    if result_path.exists():return read(result_path)
    old=HERE/'T04/B';meta=read(old/'config.json');source=Store(old/'STORE');state=source.session(meta['run_id'])['state']
    entries=[json.loads(l) for l in (old/'TRACE.jsonl').read_text(encoding='utf8').splitlines()]
    authored=[c for x in entries if x['kind']=='research_decision' for c in x['commands'] if c.get('operation')=='evaluate' and c.get('arguments',{}).get('candidate')=='c7']
    control=deepcopy(authored[-1]['arguments']['controls']['default']);initial=control.get('initial_tensions_n',control.get('bias_n'))
    matches=[]
    for message in state['messages']:
        if message['role']!='user':continue
        try:body=json.loads(message['content'])
        except (ValueError,TypeError):continue
        for item in body.get('feedback',[]):
            command=item['command'];args=command.get('arguments',{});result=item['result']
            if command.get('operation')=='math' and args.get('candidate')=='c7' and args.get('operation')=='equilibrium' and args.get('tensions_n')==initial and result.get('reference'):
                matches.append((args,result['reference']))
    r=Run('T04','B',output_root=destination,label='batch1-supplement')
    for key in ('requests','llm_tokens','candidate_count','physics_evaluations','integration_steps','mathematical_calls','unreported_token_requests'):
        r.s[key]=deepcopy(state.get(key,[] if key=='unreported_token_requests' else 0))
    r.s['started']=time.time()-state['wall_time'];r.s['selected']='c7'
    r.s['candidates']={'c7':r.put(source.artifact(state['candidates']['c7']),'inherited_B_candidate_c7')}
    r.trace('supplement_provenance',dict(source_store=str(old/'STORE/platform.sqlite'),source_run_id=meta['run_id'],source_candidate=state['candidates']['c7'],provider_requests_allowed=0,original_resources=read(old/'result.json')['resources'],limits=r.limits))
    if matches:
        args,reference=matches[-1];value=source.artifact(reference)
        value['source_binding']=dict(candidate='c7',tensions_n=initial,basis=args.get('basis',{'strategy':'structural_linear'}),historical_B_reference=reference)
        control['initial_equilibrium_reference']=r.put(value,'inherited_B_mathematical_result')
        control['initial_tensions_n']=initial
        r.step(dict(operation='evaluate',arguments=dict(candidate='c7',controls=dict(default=control),conditions=['default'])))
        r.s['status']='completed'
    else:
        previous=read(old/'result.json')['required_stage_outcomes']['default']
        r.s['evaluations']=[dict(previous,candidate='c7',condition='default',reason='No saved equilibrium result matching the original control; original qualification failure retained.')]
        r.s['status']='completed'
    r.s['wall_time']=time.time()-r.s['started'];r.save_state();r.finalize()
    final=read(result_path);final['supplement']=dict(source_run_id=meta['run_id'],new_provider_requests=0,
        resource_delta={k:r.s[k]-state[k] for k in ('requests','llm_tokens','physics_evaluations','integration_steps','mathematical_calls')},original_result_unchanged=str(old/'result.json'))
    r.put(final,'supplement_result');write(result_path,final)
    return final

if __name__=='__main__':
    if '--check-task' in sys.argv:
        print(json.dumps(check_task(sys.argv[sys.argv.index('--check-task')+1])));sys.exit(0)
    if '--supplement-t04' in sys.argv:
        result=supplement_t04();print(json.dumps(dict(scientific_result=result['scientific_result'],resources=result['resources'],supplement=result['supplement'])));sys.exit(0)
    ap=argparse.ArgumentParser();ap.add_argument('--task',choices=[*NAMES,'PHS-2D']);ap.add_argument('--method',choices=['A','B']);ap.add_argument('--recover-last',action='store_true');ap.add_argument('--interrupted',action='store_true');ap.add_argument('--resume-interface',action='store_true');ap.add_argument('--recover-response',action='store_true');ap.add_argument('--recover-evaluation',action='store_true');ap.add_argument('--finalize-only',action='store_true');args=ap.parse_args()
    r=Run(args.task,args.method)
    if args.interrupted:r.record_interruption()
    r.finalize() if args.finalize_only else r.recover_last() if args.recover_last else r.resume_interface() if args.resume_interface else r.recover_response() if args.recover_response else r.recover_evaluation() if args.recover_evaluation else r.run()
