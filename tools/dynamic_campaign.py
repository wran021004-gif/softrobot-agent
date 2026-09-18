"""Versioned reach campaign for the existing deterministic workbench.

Reuses its owner lock, durable IO, source snapshots, ToolResult boundary,
single-model transport and saved-evidence principle. Never continues V1 scores.
"""
import copy
import gzip
import json
import math
import os
from pathlib import Path
import time
import zipfile
import numpy as np
from schemas.design_spec import DesignSpec
from schemas.exploration import ExplorationPhysics, ExplorationControl
from schemas.workbench import WorkbenchResult,DeepSeekConfig
from schemas.dynamic_workbench import TOOLS,native_tools
from tools.state_io import atomic_json,read,digest
from tools.spec_tools import ROOT,load_yaml,load_task_package
from tools.workbench import Workbench,owner,source_hashes,runtime
from tools.design_compiler import build_robot_ir
from tools.reach_dynamics import DynamicsBackends,MODEL_ID,SOLVER
from tools.trajectory_diagnosis import historical_audit,diagnose,metadata_from_shared
from tools.dynamic_context import (evidence_page, encoded_size, prompt_with_version,
    PAGE_VERSION, TARGET_BYTES, MAX_REQUEST_BYTES, RequestTooLarge, request_progress)
from tools.dynamic_experiment import ExperimentSupport
from tools.dynamic_recovery import ToolCountRecovery

GRANT=ROOT/'configs/experiments/round9_grant.json'
LEDGER=ROOT/'runs/round9_budget.json'


class DynamicCampaign(ExperimentSupport,ToolCountRecovery,Workbench):
    def __init__(self,root):
        super().__init__(root);self.backends=DynamicsBackends();self.tick=time.monotonic();self.state=None
        self.loaded_numerical_sources=self.numerical_sources()
    def create(self,source=ROOT/'runs/round8_ready'):
        if LEDGER.exists(): raise ValueError('Round 9 grant already bound; resume '+read(LEDGER)['active_root'])
        if self.root.exists(): raise ValueError('New campaign requires a new directory')
        grant=read(GRANT); task,env=load_task_package(); source=Path(source).resolve()
        if load_yaml(ROOT/'configs/run.yaml')['steps']*load_yaml(ROOT/'configs/simulator.yaml')['timestep_s']!=grant['objective']['time_s']:
            raise ValueError('Frozen run duration differs from authorized objective time')
        self.root.mkdir(parents=True); inputs=self.root/'inputs';inputs.mkdir()
        history=historical_audit(source,self.root/'history')
        old=read(source/'state.json'); c=old['candidates'][-1]
        old_eval=read(source/c['evaluate_candidate_ref'])['data']; row_path=source/old_eval['run']/'model_result.json'
        plan=read(row_path)['metrics']; theta=plan['theta_rad'];phi=plan['phi_rad']
        control=ExplorationControl(bend_y_rad=theta*math.cos(phi),bend_z_rad=theta*math.sin(phi)).model_dump()
        config=DeepSeekConfig.model_validate(load_yaml(ROOT/'configs/deepseek.yaml')).model_dump()
        sources=source_hashes()
        self.state=dict(version='dynamic_workbench_v2',status='PAUSED',request=dict(task=task.model_dump(mode='json'),environment=env.model_dump(mode='json'),
            grant=grant,grant_hash=digest(grant),runtime=runtime(),design_session=config,source_hashes=sources,history=history,
            permissions=sorted({v[1] for v in TOOLS.values()})),candidates=[],attempts=[],decisions=[],model_calls=[],evidence={},
            working_memory=dict(findings=[],unresolved=[],next_action='historical diagnosis and dynamic baseline'),verified_diagnoses=[],stop_reason=None)
        self.ledger=dict(version='campaign_ledger_v2',authorization_id=grant['authorization_id'],active_root=str(self.root),grant_hash=digest(grant),
            limits=grant['limits'],used={k:0 for k in grant['limits']},entries=[])
        atomic_json(inputs/'grant.json',grant);atomic_json(inputs/'task.json',self.state['request']['task']);atomic_json(inputs/'environment.json',self.state['request']['environment'])
        (inputs/'system_prompt.md').write_text((ROOT/'configs/prompts/dynamic_design_system.md').read_text(encoding='utf8'),encoding='utf8')
        atomic_json(inputs/'lineage.json',dict(source=str(source),source_state_hash=history['source_state_sha256'],source_design_hash=c['design_hash'],
            source_budget=read(ROOT/'runs/round8_budget.json'),note='Historical evidence only; new backend evaluations have new identities.'))
        with zipfile.ZipFile(self.root/'source_snapshot.zip','w',zipfile.ZIP_DEFLATED) as z:
            for name in sources:z.write(ROOT/name,name)
        self.add_candidate(c['design'],control,None,{},['history/audit.json'],'Historical c002 baseline, legacy physics retained')
        for p in self.root.rglob('*.json'): self.register(p)
        self.save();return self.state
    def load(self):
        self.state=read(self.root/'state.json');self.ledger=read(LEDGER);self.tick=time.monotonic()
        if self.ledger['active_root']!=str(self.root) or self.ledger['grant_hash']!=self.state['request']['grant_hash']: raise ValueError('Grant identity mismatch')
        if digest(read(self.root/'inputs/grant.json'))!=self.state['request']['grant_hash'] or digest(read(GRANT))!=self.state['request']['grant_hash']:raise ValueError('Frozen grant changed')
        task,env=load_task_package()
        if task.model_dump(mode='json')!=self.state['request']['task'] or env.model_dump(mode='json')!=self.state['request']['environment']:raise ValueError('Frozen task/environment changed')
        for name in ('configs/run.yaml','configs/simulator.yaml','metrics/reach.py','tasks/reach_free/contract.yaml'):
            if __import__('hashlib').sha256((ROOT/name).read_bytes()).hexdigest()!=self.state['request']['source_hashes'][name]:
                raise ValueError('Frozen execution/evaluation definition changed: '+name)
        # Cache identity is source-bound; changed numerical sources cannot silently mix results.
        for c in self.state['candidates']:
            if digest(read(self.root/c['path']))!=c['identity_hash']:raise ValueError('Candidate bytes changed')
        for row in self.ledger['entries']:
            if row['status']=='running':
                row.update(status='interrupted',reason='Process stopped; charged reservation retained')
                # Unmeasured activity is kept as a reservation, not reported as
                # actual paused wall time and not returned as free credit.
                row['unsettled_wall_s']=row.get('reserved_wall_s',0)
                if row['resource'] in ('matlab_dynamic','mujoco'):
                    self.recover_rollout(row)
        self.save();return self.state
    def recover_rollout(self,receipt):
        # A completed worker artifact may precede the campaign state commit.
        # Reconcile it without rerunning; absent/incomplete results stay charged.
        for identity_path in self.root.glob('candidates/c*/**/identity.json'):
            identity=read(identity_path)
            if digest(identity)!=receipt['key']:continue
            folder=identity_path.parent;result_path=folder/'result.json';shared_path=folder/'shared_input.json'
            if not result_path.exists() or not shared_path.exists():return
            out=read(result_path);shared=read(shared_path)
            if not out.get('complete') or out.get('shared_input_hash')!=digest(shared):return
            from tools.trajectory_diagnosis import load_rows
            rows=load_rows(folder/'trajectory.json.gz')
            if not rows or abs(rows[-1]['time_s']-shared['duration'])>1e-8:return
            if not all(np.isfinite(r['qpos_rad']).all() and np.isfinite(r['qvel_rad_s']).all() for r in rows):return
            cid=folder.parents[1].name;c=self.candidate(cid);backend=out['backend']
            if identity['design']!=c['design_hash'] or identity['control']!=c['control_hash']:return
            completed_wall=max(0,result_path.stat().st_mtime-receipt.get('started_at_epoch_s',result_path.stat().st_mtime))
            recovered_wall=min(receipt.get('reserved_wall_s',completed_wall),completed_wall)
            self.ledger['used']['active_wall_s']+=recovered_wall
            if self.experiment() and receipt.get('experiment_id')==self.experiment()['experiment_id']:
                self.experiment()['used']['active_wall_s']+=recovered_wall
            out.update(candidate_id=cid,control_hash=c['control_hash'],physics_version=c['physics_version'],
                result_ref=result_path.relative_to(self.root).as_posix(),recovered_completed_artifact=True)
            atomic_json(result_path,out)
            for p in folder.iterdir():
                if p.is_file():self.register(p)
            c['results'][backend]=out;receipt.update(status='completed',result_ref=out['result_ref'],recovered=True,unsettled_wall_s=0);return
    def register(self,path):
        path=Path(path);ref=path.relative_to(self.root).as_posix()
        self.state['evidence'][ref]=dict(sha256=__import__('hashlib').sha256(path.read_bytes()).hexdigest())
        return ref
    def save(self):
        now=time.monotonic();elapsed=now-self.tick;self.ledger['used']['active_wall_s']+=elapsed;self.tick=now
        exp=self.experiment()
        if exp:
            if exp['status']=='RUNNING':exp['used']['active_wall_s']+=elapsed
            atomic_json(self.root/f"experiments/{exp['experiment_id']}/experiment.json",exp)
        atomic_json(LEDGER,self.ledger);atomic_json(self.root/'budget.json',self.ledger)
        atomic_json(self.root/'state.json',self.state);atomic_json(self.root/'working_memory.json',self.state['working_memory'])
    def remaining(self):
        rem={k:max(0,v-self.ledger['used'][k]) for k,v in self.ledger['limits'].items()}
        rem['active_wall_s']=max(0,rem['active_wall_s']-sum(r.get('unsettled_wall_s',0) for r in self.ledger['entries']))
        return rem
    def reserve(self,resource,key,purpose='validation'):
        old=next((r for r in self.ledger['entries'] if r['resource']==resource and r['key']==key),None)
        if old:return old,False
        rem=self.check_resource(resource)
        if resource=='mujoco' and purpose=='validation' and rem[resource]<=6:raise ValueError('MuJoCo reserve is for diagnostic/baseline/sensitivity')
        self.ledger['used'][resource]+=1
        cap={'matlab_dynamic':120,'mujoco':180,'model_calls':90}.get(resource,0)
        row=dict(resource=resource,key=key,status='running',purpose=purpose,index=len(self.ledger['entries']),
            reserved_wall_s=min(cap,rem['active_wall_s']),started_at_epoch_s=time.time(),**self.action_provenance())
        if self.experiment():
            row['reserved_wall_s']=min(row['reserved_wall_s'],self.experiment_remaining()['active_wall_s'])
            if resource in self.experiment()['used']:self.experiment()['used'][resource]+=1
        self.ledger['entries'].append(row);self.save();return row,True
    def check_resource(self,resource):
        rem=self.remaining()
        if rem[resource]<1 or rem['active_wall_s']<=0:raise ValueError('BUDGET_EXHAUSTED: '+resource)
        er=self.experiment_remaining()
        if er and (er.get(resource,1)<1 or er['active_wall_s']<=0):raise ValueError('EXPERIMENT_BUDGET_EXHAUSTED: '+resource)
        return rem
    def finish(self,row,status='completed',**kw):
        row.update(status=status,unsettled_wall_s=0,**kw);self.save()
    def candidate(self,cid):
        c=next((c for c in self.state['candidates'] if c['candidate_id']==cid),None)
        if c is None:raise ValueError('Unknown candidate')
        if digest(read(self.root/c['path']))!=c['identity_hash']:raise ValueError('Candidate identity changed')
        return c
    def add_candidate(self,design,control,parent,changes,evidence,reason):
        d=DesignSpec.model_validate(design);ir=build_robot_ir(d);ctl=ExplorationControl.model_validate(control)
        design=d.model_dump(mode='json',exclude_none=True);control=ctl.model_dump();identity=dict(design=design,control=control)
        dh=digest(design);ch=digest(control);ih=digest(identity)
        old=next((c for c in self.state['candidates'] if c['identity_hash']==ih),None)
        if old:return old
        cid=f"c{len(self.state['candidates']):03d}";receipt,new=self.reserve('candidates',ih)
        c=dict(candidate_id=cid,parent_id=parent,design=design,control=control,design_hash=dh,control_hash=ch,
            physics_hash=digest(ir.mechanics.model_dump()),physics_version=ir.mechanics.profile,identity_hash=ih,changes=changes,
            evidence=evidence,reason=reason,path=f'candidates/{cid}/candidate.json',results={})
        if self.experiment():c['provenance']=self.action_provenance()
        atomic_json(self.root/c['path'],identity);atomic_json(self.root/f'candidates/{cid}/robot_ir.json',ir.model_dump(mode='json'))
        self.state['candidates'].append(c);self.register(self.root/c['path']);self.finish(receipt);return c
    def create_candidate(self,parent_id,changes,evidence,reason):
        if 'candidate_design' not in self.state['request']['permissions']:raise ValueError('PERMISSION_DENIED: candidate_design')
        parent=self.candidate(parent_id);d=copy.deepcopy(parent['design']);ctl=copy.deepcopy(parent['control'])
        # Explicit V2 physics fields trigger version transition; control-only variants preserve V1.
        physics=dict(d.get('exploration_physics') or ExplorationPhysics().model_dump())
        for k,v in changes.items():
            if k in ExplorationControl.model_fields:ctl[k]=v
            elif k in ExplorationPhysics.model_fields and k not in ('profile','validated','mass_mode'):physics[k]=v;d['exploration_physics']=physics
            elif k in ('total_length_m','body_radius_m','tendon_routing_radius_m','tendon_count'):
                d[k]=v
                if k=='body_radius_m':d['exploration_physics']=physics
            elif k=='physics_version' and v=='equivalent_rod_v2':d['exploration_physics']=physics
            else:raise ValueError('PARAMETER_NOT_AUTHORIZED: '+k)
        return self.add_candidate(d,ctl,parent_id,changes,evidence,reason)
    def numerical_sources(self):
        names=['tools/reach_dynamics.py','tools/mujoco_tools.py','tools/design_compiler.py','matlab/tdcr_planar_dynamic.m',
               'controllers/pcc_tip_feedback.py','tools/pcc_math.py','metrics/reach.py','physics_contracts/equivalent_rod_v2.md',
               'tools/task_context.py','controllers/registry.py','controllers/factories.py','tools/optimization_interfaces.py',
               'schemas/framework.py','tools/dynamic_actions.py',
               'schemas/exploration.py','schemas/design_spec.py','schemas/robot_ir.py','schemas/settings.py','tools/spec_tools.py']
        return {n:__import__('hashlib').sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    def simulate(self,cid,backend,purpose='validation',model_id=None):
        if 'simulate' not in self.state['request']['permissions']:raise ValueError('PERMISSION_DENIED: simulate')
        if backend not in ('matlab','mujoco'):raise ValueError('Unknown backend')
        sources=self.numerical_sources()
        if sources!=self.loaded_numerical_sources:raise ValueError('Numerical source changed during process; restart to load new code and cache identity')
        c=self.candidate(cid);expected=MODEL_ID if backend=='matlab' else 'mujoco_segmented_v2' if c['physics_version']=='equivalent_rod_v2' else 'mujoco_legacy_v1'
        if model_id and model_id!=expected:raise ValueError('Model/backend mismatch')
        identity=dict(design=c['design_hash'],control=c['control_hash'],physics=c['physics_hash'],task=digest(self.state['request']['task']),
            environment=digest(self.state['request']['environment']),model=expected,solver=SOLVER if backend=='matlab' else load_yaml(ROOT/'configs/simulator.yaml'),
            runtime=runtime(),sources=sources,objective=self.state['request']['grant']['objective'])
        key=digest(identity);folder=self.root/f'candidates/{cid}/{backend}/{key[:12]}';result_path=folder/'result.json'
        if result_path.exists():
            ref=result_path.relative_to(self.root).as_posix()
            if ref not in self.state['evidence'] or self.state['evidence'][ref]['sha256']!=__import__('hashlib').sha256(result_path.read_bytes()).hexdigest():raise ValueError('Cache evidence changed')
            for p in folder.iterdir():
                if p.is_file() and p.suffix in ('.json','.xml','.gz'):self.check_evidence(p.relative_to(self.root).as_posix())
            out=read(result_path);out['cache_hit']=True;return out
        resource='matlab_dynamic' if backend=='matlab' else 'mujoco'
        self.check_resource(resource)
        if backend=='matlab':
            # Environment startup is campaign activity, preceding the bounded
            # rollout reservation; one Engine is reused for all subsequent trials.
            self.backends.engine();self.save()
        receipt,new=self.reserve(resource,key,purpose)
        if not new:raise ValueError('Interrupted/failed rollout already charged; create an explicit new hypothesis or resume completed evidence')
        receipt.update(candidate_id=cid,backend=backend);self.save()
        folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'identity.json',identity)
        snapshot=self.root/f'sources/{digest(sources)}.zip'
        if not snapshot.exists():
            snapshot.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(snapshot,'w',zipfile.ZIP_DEFLATED) as archive:
                for source in sources:archive.write(ROOT/source,source)
            self.register(snapshot)
        try:
            cap=min(receipt['reserved_wall_s'],getattr(self,'optimization_deadline',float('inf'))-time.monotonic())
            if cap<=0:raise ValueError('Activity wall limit reached before backend start')
            out=self.backends.simulate(backend,build_robot_ir(DesignSpec.model_validate(c['design'])),ExplorationControl.model_validate(c['control']),folder,timeout_s=cap)
        except Exception as exc:
            out=dict(computation_status='failed',complete=False,reason=str(exc),backend=backend,model_id=expected,position_error_m=None)
        out.update(candidate_id=cid,control_hash=c['control_hash'],physics_version=c['physics_version'],result_ref=result_path.relative_to(self.root).as_posix())
        if self.experiment():out['provenance']=self.action_provenance()
        atomic_json(result_path,out)
        for p in folder.iterdir():
            if p.is_file():self.register(p)
        c['results'][backend]=out
        self.finish(receipt,'completed' if out['complete'] else 'failed',result_ref=out['result_ref'])
        if (folder/'trajectory.json.gz').exists():
            shared=read(folder/'shared_input.json');diag=diagnose(folder/'trajectory.json.gz',metadata_from_shared(shared,cid,backend,self.root.name))
            atomic_json(folder/'diagnosis.json',diag);self.register(folder/'diagnosis.json');out['diagnosis_ref']=(folder/'diagnosis.json').relative_to(self.root).as_posix()
            atomic_json(result_path,out);self.register(result_path);self.save()
        return out
    def optimize(self,args,evidence,reason):
        sid=args['search_id'];path=self.root/f'searches/{sid}.json';parent=self.candidate(args['parent_id']);variables=args['variables']
        bounds=self.state['request']['grant']['bounds']
        if any(v not in bounds for v in variables) or len(set(variables))!=len(variables):raise ValueError('Unknown/duplicate search variable')
        if parent['physics_version']!='equivalent_rod_v2':raise ValueError('Create an explicit V2 parent before continuous physical design optimization')
        flat={**parent['design'],**parent['design']['exploration_physics'],**parent['control']}
        logs={'root_ei_nm2','bending_viscosity_nm2_s','line_density_kg_m','tendon_servo_kp_n_per_m'}
        from tools.optimization_interfaces import ParameterSpace, CampaignEvaluator, MatlabCoordinateProposal
        space=ParameterSpace(variables,bounds,logs)
        def encode(c):return space.encode({**c['design'],**c['design']['exploration_physics'],**c['control']})
        decode=space.decode
        evaluator=CampaignEvaluator(self,'matlab');search=MatlabCoordinateProposal(self)
        if path.exists():
            s=read(path)
            if s['args']!=args:raise ValueError('Search ID already bound to different arguments')
        else:
            s=dict(args=args,best=encode(parent),best_id=parent['candidate_id'],best_score=None,iteration=0,step=args['initial_step'],
                trials=[],actual_evaluations=0,active_wall_s=0,cycle_improved=False,stopping_reason=None,algorithm='MATLAB bounded coordinate pattern local search')
            if self.experiment():s['provenance']=self.action_provenance()
            atomic_json(path,s)
        # Recover the true charged rollout count even if the process died after
        # a backend receipt was written but before the search checkpoint.
        s['actual_evaluations']=sum(r['resource']=='matlab_dynamic' and r['purpose']=='search:'+sid for r in self.ledger['entries'])
        start=time.monotonic()
        self.optimization_deadline=start+min(1800-s['active_wall_s'],self.remaining()['active_wall_s'])
        if self.experiment():self.optimization_deadline=min(self.optimization_deadline,start+self.experiment_remaining()['active_wall_s'])
        while s['actual_evaluations']<args['max_evaluations'] and s['iteration']<args['max_evaluations']*3:
            if s['active_wall_s']+time.monotonic()-start>=1800 or self.remaining()['active_wall_s']<=0:s['stopping_reason']='WALL_CAP';break
            if self.experiment() and (self.experiment_remaining()['matlab_dynamic']<=0 or self.experiment_remaining()['active_wall_s']<=0):
                s['stopping_reason']='EXPERIMENT_CAP';break
            if self.remaining()['model_calls']<=self.state['request']['grant']['reserved']['model_calls'] or self.remaining()['tool_calls']<=self.state['request']['grant']['reserved']['tool_calls']:
                s['stopping_reason']='CAMPAIGN_CLOSEOUT_RESERVE';break
            self.search_provenance=dict(type='matlab_coordinate_search',search_id=sid,trial_index=s['iteration'],
                                        originating_decision=s.get('provenance'))
            if self.remaining()['matlab_dynamic']<=0 or self.remaining()['candidates']<=0:s['stopping_reason']='RESOURCE_CAP';break
            if not s['trials']:x=s['best'];proposal='parent baseline'
            else:
                proposal=search.propose(s,sid)
                x=proposal['x']
            trial=dict(index=s['iteration'],parameters=decode(x),status='started',evidence=evidence)
            if self.experiment():trial['provenance']=self.action_provenance()
            s['pending_trial']=trial;atomic_json(path,s)
            # Deterministic ID/identity plus per-rollout receipts make re-entry idempotent.
            try:
                c=parent if not s['trials'] else self.create_candidate(args['parent_id'],trial['parameters'],evidence,reason)
                outcome=evaluator.evaluate(c,'search:'+sid)
                delta=outcome.actual_evaluations;s['actual_evaluations']+=delta
                trial.update(candidate_id=c['candidate_id'],result_ref=outcome.evidence_ref,actual_rollouts=delta,
                    status=outcome.status,score=outcome.score,reason=outcome.reason)
                score=outcome.score
                if outcome.status=='VALID' and (s['best_score'] is None or score<s['best_score']):
                    s.update(best=x,best_score=score,best_id=c['candidate_id'],cycle_improved=True)
            except ValueError as exc:trial.update(status='rejected',reason=str(exc),actual_rollouts=0)
            s['trials'].append(trial);s['iteration']+=1
            s.pop('pending_trial',None)
            if s['iteration']%(2*len(variables))==0:
                if not s['cycle_improved']:s['step']/=2
                s['cycle_improved']=False
                if s['step']<.0005:s['stopping_reason']='LOCAL_STEP_TOLERANCE';break
            atomic_json(path,s);self.register(path);self.save()
        s['active_wall_s']+=time.monotonic()-start;s['stopping_reason']=s['stopping_reason'] or 'EVALUATION_CAP'
        self.optimization_deadline=float('inf')
        self.search_provenance=None
        atomic_json(path,s);self.register(path)
        return dict(best_candidate_id=s['best_id'],best_error_m=s['best_score'],actual_evaluations=s['actual_evaluations'],
            stopping_reason=s['stopping_reason'],search_ref=path.relative_to(self.root).as_posix(),
            representatives=sorted([t for t in s['trials'] if t.get('score') is not None],key=lambda t:t['score'])[:4],global_optimum_claim=False)
    def compare(self,ids=(),offset=0,limit=12):
        from tools.dynamic_comparison import compare_backends
        candidates=[c for c in self.state['candidates'] if not ids or c['candidate_id'] in ids]
        sources={}
        for c in candidates[offset:offset+limit]:
            self.candidate(c['candidate_id'])
            for backend,r in c['results'].items():
                if r.get('result_ref'):
                    self.check_evidence(r['result_ref'])
                if r.get('complete'):
                    sources.update(self.saved_sources(r))
        comparisons=[compare_backends(self.root,c) for c in candidates[offset:offset+limit]]
        comparison_path=self.root/f'comparisons/{digest(dict(ids=ids,offset=offset,limit=limit))[:16]}.json'
        atomic_json(comparison_path,comparisons);self.register(comparison_path)
        metadata=comparison_path.with_suffix('.provenance.json')
        atomic_json(metadata,dict(source_hashes=sources,parameters=dict(candidate_ids=ids,offset=offset,limit=limit),
            processor='tools.dynamic_comparison.compare_backends',processor_sha256=__import__('hashlib').sha256((ROOT/'tools/dynamic_comparison.py').read_bytes()).hexdigest(),
            backend_solves=0,rescoring=False,artifact_hashes={comparison_path.relative_to(self.root).as_posix():self.state['evidence'][comparison_path.relative_to(self.root).as_posix()]['sha256']}))
        self.register(metadata)
        return dict(total=len(candidates),next_offset=offset+limit if offset+limit<len(candidates) else None,
            source_hashes=sources,backend_solves=0,rescoring=False,metadata_ref=metadata.relative_to(self.root).as_posix(),
            cross_backend=comparisons,comparison_ref=comparison_path.relative_to(self.root).as_posix(),rows=[
            {k:c[k] for k in ('candidate_id','parent_id','design','control','design_hash','control_hash','physics_version','physics_hash','changes','results')}
            for c in candidates[offset:offset+limit]])
    def dispatch(self,name,args,evidence,reason):
        from tools.dynamic_actions import BINDINGS
        if set(BINDINGS)!=set(TOOLS):raise ValueError('REGISTRY_BINDING_MISMATCH')
        if name not in BINDINGS:raise ValueError('Tool is not executable')
        return BINDINGS[name](self,args,evidence,reason)
    def saved_sources(self,result):
        """Registered input hashes, shared by comparison, diagnosis and observation."""
        ref=result['result_ref'];self.check_evidence(ref)
        folder=(self.root/ref).parent
        hashes={}
        for path in (self.root/ref,folder/'trajectory.json.gz',folder/'shared_input.json'):
            item=path.relative_to(self.root).as_posix();self.check_evidence(item)
            hashes[item]=self.state['evidence'][item]['sha256']
        if (folder/'diagnosis.json').exists():
            item=(folder/'diagnosis.json').relative_to(self.root).as_posix();self.check_evidence(item)
            hashes[item]=self.state['evidence'][item]['sha256']
        return hashes
    def check_evidence(self,ref):
        if ref not in self.state['evidence']:raise ValueError('Unregistered evidence: '+ref)
        p=(self.root/ref).resolve()
        if not p.is_relative_to(self.root) or __import__('hashlib').sha256(p.read_bytes()).hexdigest()!=self.state['evidence'][ref]['sha256']:raise ValueError('Evidence changed')
    def submit(self,name,args,reason,evidence,memory=None):
        started=time.monotonic();before=copy.deepcopy(self.ledger['used'])
        seq=len(self.state['decisions']);receipt,new=self.reserve('decisions',str(seq));self.finish(receipt)
        decision=dict(sequence=seq,tool=name,arguments=args,reason=reason,evidence=evidence,status='pending',
            origin=getattr(self,'decision_origin','codex_development'),
            provenance=self.action_provenance(),
            evidence_hashes={ref:self.state['evidence'].get(ref,{}).get('sha256') for ref in evidence})
        self.state['decisions'].append(decision);self.save()
        tool_receipt=None
        try:
            if name not in TOOLS:raise ValueError('Tool not in executable allowlist')
            schema,permission,_=TOOLS[name]
            if permission not in self.state['request']['permissions']:raise ValueError('PERMISSION_DENIED')
            if name in ('create_candidate','simulate_candidate','evaluate_candidate','optimize_matlab'):
                rem=self.remaining();res=self.state['request']['grant']['reserved']
                if rem['model_calls']<=res['model_calls'] or rem['tool_calls']<=res['tool_calls']:
                    raise ValueError('RESEARCH_BUDGET_RESERVED_FOR_COMPARISON_DIAGNOSIS_AND_CLOSEOUT')
            if not evidence:raise ValueError('Evidence is required')
            for ref in evidence:self.check_evidence(ref)
            parsed=schema.model_validate(args).model_dump();self.guard_experiment_action(name,parsed)
            receipt,new=self.reserve('tool_calls',str(seq));tool_receipt=receipt
            data=self.dispatch(name,parsed,evidence,reason);result=WorkbenchResult(tool=name,status='completed',data=data)
            self.finish(receipt);decision['status']='accepted'
        except Exception as exc:
            if tool_receipt:self.finish(tool_receipt,'failed',reason=str(exc))
            result=WorkbenchResult(tool=name,status='failed',failure_code='TOOL_ERROR',message=str(exc));decision['status']='failed'
        if name=='optimize_matlab':self.optimization_deadline=float('inf');self.search_provenance=None
        # Unknown names are untrusted; never interpolate them into a filesystem path.
        safe_name=name if name in TOOLS else 'unknown_tool'
        ref=f'attempts/{seq:03d}_{safe_name}/result.json'
        from tools.public_feedback import runner_feedback
        from schemas.public_tools import PublicResult
        result=result.model_copy(update={'public':PublicResult.model_validate(runner_feedback(self,'dynamics',name,result.model_dump(mode='json'),ref,
            before=before,elapsed_s=time.monotonic()-started))})
        atomic_json(self.root/ref,result.model_dump(mode='json'));self.register(self.root/ref)
        decision['result_ref']=ref;self.state['attempts'].append(dict(tool=name,arguments=args,result_ref=ref,
            decision_sequence=seq,provenance=decision['provenance']))
        if memory:self.state['working_memory']={k:([str(x)[:300] for x in v[:4]] if isinstance(v,list) else str(v)[:300]) for k,v in memory.items() if k in ('findings','unresolved','next_action')}
        self.save();return result.model_dump(mode='json'),ref
    def latest_preview(self,max_bytes=4000):
        if not self.state['attempts']:return None
        a=self.state['attempts'][-1];ref=a['result_ref'];result=read(self.root/ref)
        summary={k:result[k] for k in ('tool','status','failure_code') if k in result}
        summary.update(cite_as=ref,evidence_ref=ref)
        if result.get('message'):summary['message']=result['message'][:240]
        if result.get('public'):
            summary['public']={k:result['public'][k] for k in ('tool_id','execution_status','solver_status','analysis_status','task_status','error','cost','details_ref')}
        if a['tool']=='read_evidence' and result.get('status')=='completed':
            data=result.get('data',{})
            if isinstance(data,dict) and data.get('page_version')==PAGE_VERSION and encoded_size(data)<=8000:
                summary['data']=data  # Keep the exact page the model requested.
            else:
                # Upgrade legacy feedback from its original source/offset, not
                # the sliced result (which has already lost original indices).
                summary['data']=self.dispatch('read_evidence',a['arguments'],[], '')
            return summary
        summary['data']=evidence_page(result,ref,'/data' if 'data' in result else '',
                                      max_bytes=max_bytes)
        return summary
    def context(self):
        recent=self.state['candidates'][-2:];ranked=sorted([c for c in self.state['candidates'] if c['results'].get('mujoco',{}).get('complete')],
            key=lambda c:c['results']['mujoco']['position_error_m'])[:2]
        model_ranked=sorted([c for c in self.state['candidates'] if c['results'].get('matlab',{}).get('complete')],
            key=lambda c:c['results']['matlab']['position_error_m'])[:2]
        selected={c['candidate_id']:c for c in [self.state['candidates'][0],*ranked,*model_ranked,*recent]}
        if self.experiment():
            experimental=self.experiment_candidates()
            best=[]
            for backend in ('matlab','mujoco'):
                best+=sorted([c for c in experimental if c['results'].get(backend,{}).get('complete')],
                             key=lambda c:c['results'][backend]['position_error_m'])[:2]
            baseline=next(c for c in self.state['candidates'] if c['candidate_id']==self.experiment()['baseline_id'])
            selected={c['candidate_id']:c for c in [baseline,*best,*experimental[-2:]]}
        candidates=[]
        metric_keys=('complete','computation_status','model_id','position_error_m','model_task_success','canonical_task_success',
                     'tip_m','last_valid_time_s','residual_qvel_norm_rad_s','result_ref','diagnosis_ref')
        for c in selected.values():
            candidates.append(dict(candidate_id=c['candidate_id'],parent_id=c['parent_id'],changes=c['changes'],
                physics_version=c['physics_version'],evidence_ref=c['path'],evidence=c['evidence'],
                results={backend:{k:r[k] for k in metric_keys if k in r} if r else {'computation_status':'NOT_RUN'}
                         for backend in ('matlab','mujoco') for r in [c['results'].get(backend)]}))
        history=self.state['request']['history']
        return dict(task=self.state['request']['task'],environment=self.state['request']['environment'],grant=self.state['request']['grant'],
            permissions=self.state['request']['permissions'],
            history=dict(status=history.get('status'),interpretation=str(history.get('interpretation',''))[:300],evidence_ref='history/audit.json'),
            candidates=candidates,remaining=self.remaining(),memory=copy.deepcopy(self.state['working_memory']),
            recent_decisions=[{**{k:d[k] for k in ('sequence','tool','status','result_ref') if k in d},'reason':d.get('reason','')[:160]}
                              for d in self.state['decisions'][-3:]],
            latest_tool_result=self.latest_preview(),verified_diagnoses=copy.deepcopy(self.state['verified_diagnoses'][-2:]),
            progress=request_progress(self),experiment=self.experiment_summary(),tool_call_correction=self.correction_context(),
            evidence_help='history/c002_diagnosis.json; inputs/grant.json; use returned result/diagnosis refs. compare_candidates pages the full table.')
    def build_model_request(self):
        """Pure request builder shared by resume and read-only size inspection."""
        config=self.state['request']['design_session']
        prompt,version=prompt_with_version((self.root/'inputs/system_prompt.md').read_text(encoding='utf8'))
        context=self.context()
        payload=dict(model=config['model'],thinking={'type':'enabled'},max_tokens=8192,stream=False,tools=native_tools(),
                     messages=[dict(role='system',content=prompt),dict(role='user',content='')])
        def measure():
            payload['messages'][1]['content']=json.dumps(context,ensure_ascii=False)
            return encoded_size(payload)
        metrics=dict(initial_bytes=measure(),target_bytes=TARGET_BYTES,limit_bytes=MAX_REQUEST_BYTES,
                     compactions=[],prompt_version=version)
        # Fixed priorities. Never trim task, permissions, schema, memory or the
        # current evidence page. Every removed preview retains a readable ref.
        if measure()>TARGET_BYTES:
            context['history']={'evidence_ref':'history/audit.json'}
            context['recent_decisions']=[{k:v for k,v in d.items() if k!='reason'} for d in context['recent_decisions'][-1:]]
            metrics['compactions'].append('history_and_decisions')
        if measure()>TARGET_BYTES:
            for c in context['candidates']:
                c.pop('changes',None);c.pop('evidence',None)
                for r in c['results'].values():r.pop('tip_m',None);r.pop('residual_qvel_norm_rad_s',None)
            metrics['compactions'].append('candidate_details')
        if measure()>TARGET_BYTES and context['latest_tool_result'] and context['latest_tool_result'].get('tool')!='read_evidence':
            context['latest_tool_result']=self.latest_preview(max_bytes=1800)
            metrics['compactions'].append('tool_preview')
        metrics.update(total_bytes=measure(),components=dict(system=encoded_size(payload['messages'][0]),
                       user=encoded_size(payload['messages'][1]),tools=encoded_size(payload['tools'])))
        if metrics['total_bytes']>MAX_REQUEST_BYTES:
            metrics['reason']='Task, permissions, tool schemas, current read page and working memory must remain intact'
            raise RequestTooLarge(metrics)
        return payload,metrics
    def run_model(self,steps=12):
        from tools.legacy.workbench_deepseek import request_completion,redact
        config=self.state['request']['design_session'];key=os.environ.get('DEEPSEEK_API_KEY','')
        self.recover_model_responses()
        correction=self.correction_for_decision()
        if correction and correction['outcome']!='pending':
            self.state.update(status='PAUSED',stop_reason=f"Correction for request {correction['rejected_request_index']:03d} is {correction['outcome']}; its single allowance is consumed. {correction.get('error')}")
            if self.experiment() and self.experiment()['status']=='RUNNING':self.experiment()['status']='PAUSED'
            self.save();return
        if self.experiment() and self.experiment()['stop_decision_sequence'] is not None:return
        if not key:
            self.state.update(status='WAITING_FOR_KEY',stop_reason='DEEPSEEK_API_KEY missing; no model request sent'+('; tool-count correction remains pending' if correction else ''))
            if self.experiment() and self.experiment()['status']=='RUNNING':self.experiment()['status']='PAUSED'
            self.save();return
        self.state.update(status='RUNNING',stop_reason=None)
        if self.experiment():self.experiment()['status']='RUNNING'
        self.save()
        for _ in range(steps):
            if self.state['status']!='RUNNING':break
            correction=self.correction_for_decision()
            try:
                for resource in ('model_calls','decisions','tool_calls'):self.check_resource(resource)
            except ValueError as exc:
                self.state.update(status='PAUSED',stop_reason=str(exc)+('; correction remains pending' if correction else ''))
                break
            index=len(self.state['model_calls'])
            try:
                payload,metrics=self.build_model_request()
            except RequestTooLarge as exc:
                self.state.update(status='PAUSED',stop_reason=str(exc),last_input_metrics=exc.metrics)
                atomic_json(self.root/'context_pause.json',dict(error=str(exc),**exc.metrics))
                self.save();self.render();break
            self.state['last_input_metrics']=metrics
            version=metrics['prompt_version']
            version_path=self.root/f"inputs/prompt_versions/{version['effective_sha256']}.json"
            if not version_path.exists():atomic_json(version_path,version)
            folder=self.root/f'model_calls/{index:03d}';atomic_json(folder/'request.json',payload)
            row=dict(index=index,status='reserved',decision_sequence=len(self.state['decisions']),request_ref=f'model_calls/{index:03d}/request.json',
                     input_metrics=metrics,prompt_version_ref=version_path.relative_to(self.root).as_posix())
            if self.experiment():row['experiment_id']=self.experiment()['experiment_id']
            if correction:
                row['correction_for']=correction['rejected_request_index']
                correction.update(correction_request_index=index,outcome='reserved')
            self.state['model_calls'].append(row)
            self.current_model_row=row;self.decision_origin='deepseek_api'
            try:
                # reserve saves row + correction link + the charge together
                # before HTTP I/O; recovery cannot grant another correction.
                receipt,new=self.reserve('model_calls',str(index))
            except ValueError as exc:
                self.state['model_calls'].pop()
                if correction:correction.update(correction_request_index=None,outcome='pending')
                self.state.update(status='PAUSED',stop_reason=str(exc));break
            finally:
                self.current_model_row=None;self.decision_origin='codex_development'
            if not new:
                row.update(status='failed',error='Existing interrupted request reservation; no API resent')
                self.settle_correction(row);self.state.update(status='PAUSED',stop_reason=row['error']);break
            try:
                bounded_config={**config,'timeout_s':min(config['timeout_s'],receipt['reserved_wall_s'])}
                response=redact(request_completion(bounded_config,payload,key),key);atomic_json(folder/'response.json',response)
                row['status']='responded';self.save();self.apply_model_response(row,response)
                self.settle_correction(row)
                self.finish(receipt,'completed' if row['status']=='completed' else 'failed')
            except Exception as exc:
                row.update(status='failed',error=redact(str(exc),key));self.finish(receipt,'failed')
                self.state.update(status='MODEL_RETRY_REQUIRED',stop_reason=row['error']);self.settle_correction(row);break
            self.save();self.render()
        if self.state['status']=='RUNNING':self.state['status']='PAUSED'
        self.save()
        if self.experiment():
            self.experiment()['status']='STOPPED' if self.state['status']=='STOPPED' else 'PAUSED'
            self.save();self.render_experiment()
    def apply_model_response(self,row,response):
        sequence=row['decision_sequence']
        if len(self.state['decisions'])>sequence:
            d=self.state['decisions'][sequence]
            row.update(status='completed' if d.get('result_ref') else 'failed',feedback_ref=d.get('result_ref'),
                error=None if d.get('result_ref') else 'Decision interrupted; do not dispatch twice, inspect saved receipts')
            return
        choice=response['choices'][0]
        calls=choice['message'].get('tool_calls') or []
        row['usage']=response.get('usage')
        if len(calls)!=1:
            self.reject_tool_count(row,calls);return
        if choice.get('finish_reason')=='length':raise ValueError('MODEL_OUTPUT_TRUNCATED')
        f=calls[0]['function'];args=json.loads(f['arguments']);reason=args.pop('reason');evidence=args.pop('evidence');memory=args.pop('working_memory')
        self.decision_origin='deepseek_api';self.current_model_row=row
        try:
            result,ref=self.submit(f['name'],args,reason,evidence,memory)
            row.update(status='completed',feedback_ref=ref,usage=response.get('usage'),tool=f['name'])
        finally:self.decision_origin='codex_development';self.current_model_row=None
    def selected_design(self):
        decision=next((d for d in reversed(self.state['decisions']) if d['tool']=='stop_design' and d['status']=='accepted'),None)
        if not decision or 'selection' not in decision:return None
        selection=decision['selection'];cid=selection['selected_candidate_id']
        path=(self.root/self.candidate(cid)['path']).resolve() if cid is not None else None
        if path is not None and not path.is_relative_to(self.root):raise ValueError('Candidate path outside campaign')
        return dict(selected_candidate_id=cid,design_file=str(path) if path else None,
                    reason=selection['reason'],source=selection['source'])
    def print_selected_design(self):
        selection=self.selected_design()
        if selection:
            print(f"Selected candidate: {selection['selected_candidate_id'] or 'None'}")
            print(f"Design file: {selection['design_file'] or 'None'}")
            print(f"Reason: {selection['reason']}")
            print(f"Source: {selection['source']}")
            if self.experiment():print('Historical best: c066 (before llm_reach_v1; separate from the final selection).')
    def render(self):
        from tools.dynamic_view import render_workbench
        render_workbench(self)
    def close(self):self.backends.close()
