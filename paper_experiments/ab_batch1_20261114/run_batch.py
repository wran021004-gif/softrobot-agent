"""First formal A/B batch. Thin capability boundary over existing Core kernels.

No FULL solutions enter model context. No high-level research/math orchestration.
Resume uses the same Store, request IDs and completed physical evidence.
"""
import os, sys, json, time, csv, traceback, argparse
from pathlib import Path
from copy import deepcopy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORE = ROOT/'.worktrees/core-five-task-native-feedback-20261113'
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

NAMES={'T01':'T01_M1_reach_hold','T04':'T04_figure_eight_tracking','T07':'T07_C1_four_tendon'}
MODES={'A':'llm_only','B':'direct_math_tools'}
LIMITS=dict(requests=60,llm_tokens=350000,candidate_count=12,physics_evaluations=24,integration_steps=180000,mathematical_calls=24,wall_s=2400)
PROVIDER=dict(model='gpt-5.6-sol',reasoning_effort='medium',base_url='http://127.0.0.1:8789/v1',credential='~/.softrobot-agent/chatgpt-api-account3.json')

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

def inputs(task):
    if task=='PHS-2D':
        spec=read(ROOT/'runs/psd2d-core-only-20261112/fresh-store/resolved_configuration.json')
        return spec['configuration'],spec['family_space'],None
    source=ROOT/'paper_experiments/ten_task_codex_solve_20261112'/NAMES[task]
    # Resolved configuration is the original family scaffold, never a selected candidate.
    spec=read(source/'RESOLVED_STUDY_CONFIG.json')
    cfg=spec['configuration'];space=read(source/'FAMILY_SPACE.json')
    space['executable_segment_counts']=list(range(1,10))
    space['executable_tendon_count_bounds']=[1,7]
    protocol=read(ROOT/'paper_experiments/five_task_completion_20261113'/NAMES[task]/'TASK_PROTOCOL.json')
    return cfg,space,protocol

class Run:
    def __init__(self,task,method):
        self.task,self.method=task,method
        self.id=f'batch1-{task.lower()}-{MODES[method]}-20261114'
        self.folder=HERE/task/method;self.folder.mkdir(parents=True,exist_ok=True)
        os.chdir(self.folder)  # Native engine logs belong to this independent run.
        self.store=Store(self.folder/'STORE')
        self.base,self.space,self.protocol=inputs(task)
        self.limits={**LIMITS}
        if method=='A':self.limits['mathematical_calls']=0
        if task=='PHS-2D':self.limits.update(integration_steps=850000,physics_evaluations=30,wall_s=3600)
        self.base['run_id']=self.id
        self.base['policy']['allowed_tools']=[];self.base['policy']['tool_bindings']={}
        self.base['policy']['budget']=dict(model_calls=self.limits['requests'],tool_calls=100,backend_solves=self.limits['physics_evaluations'],worker_calls=0,wall_s=self.limits['wall_s'])
        if not self.store.db.exists():
            self.store.create(ProjectConfig(project_id=self.id,grant_id=self.id,authorization_source='User authorizes eight formal A/B runs, full legal family space, original physical tasks, at most 60 provider requests across batch.',budget=self.base['policy']['budget']))
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
        if not recovering:
            self.guard('candidate_count');self.s['candidate_count']+=1;self.save_state()
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
        from tools.research.config import controller_configuration
        source=ROOT/'paper_experiments/ten_task_codex_solve_20261112'/NAMES[self.task]
        original=read(source/('TASK_'+condition+'.json'));original['task']=task
        cfg['policy']['controller']=controller_configuration(read(source/('CONTROL_'+condition+'.json')),original)
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

    def physical(self,cfg,u,folder):
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
        try:raw=playback_tensions(inp,p,scene,u.tolist(),folder)
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
        out=[]
        requested=args.get('conditions',list(control) if control and 'default' not in control else cases)
        for cond in requested:
            if cond not in cases:raise ValueError('Unknown required condition')
            cfg=self.config_case(candidate,cond)
            folder=self.folder/'physics'/f"p{self.s['physics_evaluations']+1:03d}-{alias}-{cond}";folder.mkdir(parents=True,exist_ok=True)
            if self.task=='PHS-2D':
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
            else:
                ctl=control.get(cond,control.get('default'))
                if ctl is None:raise ValueError('Explicit control required for '+cond)
                if self.task=='T04':cfg=self.prepared(cfg,ctl,folder)
                u=self.commands(cfg,ctl);self.put(dict(candidate=alias,condition=cond,control=ctl,applied_inputs_n=u.tolist()),'control_inputs')
                raw=self.physical(cfg,u,folder)
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
        n=round(settle['task']['timing']['duration_s']/settle['task']['timing']['control_period_s'])
        settle['task']['initializer']['parameters']['data']=dict(qpos_rad={j:0. for j in p['dofs']},qvel_rad_s={j:0. for j in p['dofs']},unspecified='zero')
        sf=folder/'initial_settling';sf.mkdir(exist_ok=True)
        raw=self.physical(settle,np.tile(initial_u,(n,1)),sf);self.put(raw,'task_required_initial_settling')
        q=dict(zip(p['dofs'],raw['samples'][-1]['qpos_rad']));u=dict(zip([t['entity'] for t in p['tendons']],initial_u))
        prepared=qualify(cfg,q,u,folder/'qualified_initial.xml');ref=self.put(dict(contract='task.prepared_initial',data=prepared),'mandatory_initial_qualification')
        self.trace('initial_qualification',dict(qualified=prepared['qualified'],residual=prepared['static_balance_inf_nm'],reference=ref,optional_mathematical_tool=False))
        if not prepared['qualified']:raise ValueError('Physical initial settling did not meet original static qualification: '+str(prepared['static_balance_inf_nm']))
        cfg['task']['initializer']['parameters']['data']={k:prepared[k] for k in ('qpos_rad','qvel_rad_s','tensions_n')};cfg['task']['initializer']['parameters']['data'].update(qualification=ref,unspecified='zero')
        return cfg

    def math(self,args):
        if self.method!='B':raise PermissionError('llm_only forbids all optional mathematical tools')
        self.guard('mathematical_calls');self.s['mathematical_calls']+=1;self.save_state()
        if self.task=='PHS-2D' and args['operation'] in ('equilibrium','kkt','jacobian','finite_difference'):
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
            value=plain(gvs_equilibrium_tool(SimpleNamespace(input=inp),request));r=self.put(value,'direct_gvs_equilibrium');return dict(reference=r,result=value)
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
            generation_notes=dict(section_station_counts={c['id']:len(c.get('sections',[])) for c in assembly['components'] if c['kind']=='flexible_segment'},rules='sections replaces each existing section station, so supply the exact prototype count; omitting sections preserves original sections. All spans first_segment=0 under base-only rule. guide_s lists interior normalized guide stations. Candidate aliases are returned only on success.'),
            mathematical_interface=None if self.method=='A' else dict(operations=['equilibrium','kkt','jacobian','finite_difference'] if self.task=='PHS-2D' else ['jacobian','mechanics','finite_difference','equilibrium'],description='Direct existing native kernels only. Explicit candidate, condition, qpos_rad,qvel_rad_s,tensions_n. Active finite_difference options={horizon_s:0.01,difference_step_n:0.02}; horizon <=0.05. Active equilibrium uses existing GVS damped Newton: tensions_n, optional basis={strategy:structural_linear},initial_q,max_iterations,tolerance. Passive equilibrium/kkt/jacobian args material_s,force_world_n,qpos_rad; passive finite_difference additionally requires explicit locations,increment_n,direction_world,force_n. No intent projection, automatic problem constructor, differentiation router or high-level research optimization.'),
            knowledge='Generic SI mechanics, family domains and task definitions only. Historical FULL final designs and decision traces are inaccessible.')

    def step(self,command):
        if 'operation' not in command and len(command)==1:
            op,args=next(iter(command.items()))
            command=dict(operation=op,arguments=dict(generation=args) if op=='generate' else args)
        op=command['operation'];args=command.get('arguments',{k:v for k,v in command.items() if k!='operation'})
        if op=='generate' and 'generation' not in args:args=dict(generation=args)
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
            self.s['messages']=[dict(role='system',content='You are the sole research/design LLM in a formal bounded experiment. Independently design a soft robot and explicit controls. You may use every legal FamilySpace parameter and topology; do not assume any historical solution. Return exactly one research_step function call each turn. Its commands execute sequentially; inspect actual physics between revisions. Commands: generate arguments {generation:full GenerationRequestV2 without family_space_identity}; evaluate arguments {candidate:cN, controls:{condition:control}, optional conditions:[...]}; '+('math is forbidden. ' if self.method=='A' else 'math arguments {candidate,operation:jacobian|mechanics|finite_difference|equilibrium|kkt, condition,qpos_rad,qvel_rad_s,tensions_n,options}. Choose your own mathematical question/parameters. ')+ 'finish arguments {candidate:cN}. Every call must record concise decision, cited earlier evidence and expected outcome. Never infer acceptance without every original required condition. No tools for historical files, shell, automatic optimization or high-level math exist. Use budget efficiently, revise structure and control based on evidence. At most 60 requests, plus the stated finite token, structure and physics ceilings; leave a final evaluated candidate. Physical failure is a valid result. One action batch can generate and evaluate the new known alias c1,c2,... .'),dict(role='user',content=json.dumps(self.context(),ensure_ascii=False))]
            self.s['messages'][0]['content']+=' Transport uses text JSON: return the research_step arguments object {decision,evidence,commands} as JSON text, with no markdown. Exact command format: {"operation":"generate","arguments":{"generation":{...}}} or {"operation":"evaluate","arguments":{"candidate":"c1","controls":{...}}}. Only successful generation returns an alias; do not infer aliases from failed attempts. The Host enforces the same operation allowlist.'
            self.save_state()
        elif 'Transport uses text JSON' not in self.s['messages'][0]['content']:
            self.s['messages'][0]['content']+=' Transport uses text JSON: return the research_step arguments object {decision,evidence,commands} as JSON text, with no markdown. The Host enforces the same operation allowlist.'
        cred=read(Path(PROVIDER['credential']).expanduser())
        schema=dict(type='object',properties=dict(decision=dict(type='string'),evidence=dict(type='array',items=dict(type='string')),commands=dict(type='array',items=dict(type='object',properties=dict(operation=dict(type='string',enum=['generate','evaluate','finish']+(['math'] if self.method=='B' else [])),arguments=dict(type='object')),required=['operation','arguments']))),required=['decision','commands'])
        while self.s['requests']<self.limits['requests'] and self.s['status']=='running':
            self.guard('requests')
            if self.s['llm_tokens']+16000>self.limits['llm_tokens']:
                self.s['status']='budget_complete';break
            wire=self.s['messages'] if len(self.s['messages'])<=4 else self.s['messages'][:2]+self.s['messages'][-2:]
            # Exact owned working set survives bounded conversational context.
            latest={(r['candidate'],r['condition']):r for r in self.s['evaluations']}
            snapshot=dict(available_candidates={k:self.candidate(k)['topology'] for k in self.s['candidates']},latest_evaluations=[{k:r.get(k) for k in ('candidate','condition','accepted','validity','max_violation','reference')} for r in latest.values()],current_limits=self.limits,resource_use={k:self.s[k] for k in ('requests','llm_tokens','candidate_count','physics_evaluations','integration_steps','mathematical_calls')})
            wire=wire+[dict(role='user',content='Current authoritative own-run working set: '+json.dumps(snapshot))]
            idx=self.s['requests']+1;request=dict(model=PROVIDER['model'],messages=wire,stream=False)
            # Reserve the serialized input conservatively plus the existing
            # runtime's 32768-token response allowance before sending.
            reservation=len(json.dumps(request,ensure_ascii=False).encode('utf8'))+32768
            if self.s['llm_tokens']+reservation>self.limits['llm_tokens']:
                self.trace('token_budget_stop',dict(reported_tokens=self.s['llm_tokens'],remaining=self.limits['llm_tokens']-self.s['llm_tokens'],conservative_request_reservation=reservation))
                self.s['status']='budget_complete';break
            self.trace('provider_request',dict(request_number=idx,request=request))
            self.s['requests']+=1;self.save_state();start=time.time()
            try:
                with httpx.Client(timeout=600,trust_env=False) as client:
                    resp=client.post(PROVIDER['base_url']+'/chat/completions',headers={'Authorization':'Bearer '+cred['api_key']},json=request)
                    if resp.status_code!=200:raise RuntimeError('HTTP '+str(resp.status_code)+': '+resp.text[:3000])
                    response=resp.json()
                self.trace('provider_response',dict(request_number=idx,response=response,wall_s=time.time()-start))
                usage=response.get('usage',{});self.s['llm_tokens']+=usage.get('total_tokens',0);self.s.setdefault('token_usage_records',[]).append(usage)
                message=response['choices'][0]['message'];self.s['messages'].append(dict(role='assistant',content=message.get('content') or ''))
                calls=message.get('tool_calls',[])
                if not calls:
                    content=message.get('content','').strip()
                    if content.startswith('```'):content=content.split('\n',1)[1].rsplit('```',1)[0].strip()
                    calls=[dict(id='text-'+str(idx),function=dict(arguments=content))]
                for call in calls:
                    value=command_json(call['function']['arguments']);self.trace('research_decision',dict(request_number=idx,**value));feedback=[]
                    # A tool-boundary reload permits necessary interface fixes
                    # without cancelling another in-flight model request.
                    import importlib.util
                    spec=importlib.util.spec_from_file_location('batch1_live',__file__);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                    self.__class__=module.Run
                    for command in value['commands']:
                        try:result=self.step(command)
                        except Exception as exc:result=dict(error=type(exc).__name__,reason=str(exc));self.trace('operation_error',dict(command=command,**result,traceback=traceback.format_exc()))
                        feedback.append(dict(command=command,result=result))
                        self.save_state()
                    # Native full artifacts stay in Store; bounded exact numerical feedback.
                    self.s['messages'].append(dict(role='user',content=json.dumps(clean(dict(feedback=feedback,remaining={k:self.limits[k]-self.s[k] for k in ['requests','llm_tokens','candidate_count','mathematical_calls']},resource_use={k:self.s[k] for k in ['candidate_count','physics_evaluations','integration_steps']},instruction='Continue independent research or finish. All required conditions must be evaluated on one final design.')),ensure_ascii=False)))
            except Exception as exc:
                self.trace('provider_error',dict(request_number=idx,error=type(exc).__name__,reason=str(exc)))
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
        final['resources']['structure_generation_attempts']=self.s['candidate_count']
        final['resources']['candidate_count']=len(self.s['candidates'])
        self.put(final,'final_result');write(self.folder/'result.json',final)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--task',choices=[*NAMES,'PHS-2D']);ap.add_argument('--method',choices=['A','B']);ap.add_argument('--recover-last',action='store_true');ap.add_argument('--interrupted',action='store_true');ap.add_argument('--resume-interface',action='store_true');ap.add_argument('--recover-response',action='store_true');ap.add_argument('--recover-evaluation',action='store_true');ap.add_argument('--finalize-only',action='store_true');args=ap.parse_args()
    r=Run(args.task,args.method)
    if args.interrupted:r.record_interruption()
    r.finalize() if args.finalize_only else r.recover_last() if args.recover_last else r.resume_interface() if args.resume_interface else r.recover_response() if args.recover_response else r.recover_evaluation() if args.recover_evaluation else r.run()
