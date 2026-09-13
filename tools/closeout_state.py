"""Candidate-boundary recovery using existing RunArtifacts and TraceWriter."""
import hashlib
import math
from pathlib import Path
from time import perf_counter
from tools.artifact_tools import RunArtifacts, file_hash
from tools.trace_tools import TraceWriter, read_trace, validate_trace
from schemas.run_record import RunRecord


from tools.state_io import read, digest, atomic_json  # Backward-compatible campaign imports.


def verify_run(path, expected=None):
    path=Path(path)
    if expected and file_hash(path/'run.json')!=expected:
        raise ValueError('Manifest hash mismatch: '+str(path))
    manifest=read(path/'run.json')
    if manifest['final_status']=='RUNNING':
        raise ValueError('Unsealed evidence')
    for name,h in manifest['artifact_hashes'].items():
        target=(path/name).resolve()
        if not target.is_relative_to(path.resolve()) or file_hash(target)!=h:
            raise ValueError('Artifact hash mismatch: '+name)
    import zipfile
    with zipfile.ZipFile(path/'source_snapshot.zip') as z:
        for name,h in manifest['source_hashes'].items():
            if hashlib.sha256(z.read(name)).hexdigest()!=h:
                raise ValueError('Source hash mismatch: '+name)
    validate_trace(read_trace(path/'trace.jsonl'),path)
    return manifest


def resume_artifacts(path):
    path=Path(path).resolve(); record=RunRecord.model_validate(read(path/'run.json'))
    if record.final_status!='RUNNING':
        raise ValueError('Sealed parent cannot be resumed')
    run=RunArtifacts.__new__(RunArtifacts); run.path=path; run.record=record
    run.trace=read(path/'trace.json')
    events=read_trace(path/'trace.jsonl',validate=False); validate_trace(events,path,complete=False)
    # Parent records boundaries only; it never leaves an open candidate span.
    writer=TraceWriter.__new__(TraceWriter); writer.path=path/'trace.jsonl'; writer.run_id=path.name
    writer.events=events; writer.stack=[events[0].event_id]; writer.closed=False; writer.started=perf_counter()
    run.events=writer
    return run


class CampaignState:
    def __init__(self,run,plan,resume=False):
        self.run=run; self.plan=plan
        self.data=read(run.path/'campaign_state.json') if resume else dict(
            plan_hash=digest(plan),attempts=[],reuse=[],decisions=[],incumbents={},completed_stages=[],workflow_status='RUNNING')
        if self.data['plan_hash']!=digest(plan):
            raise ValueError('Frozen plan mismatch')
        if resume:
            for a in self.data['attempts']:
                if a['status'] in ('pending','running'):
                    a['status']='interrupted'
        self.save()

    def save(self):
        self.run.save('campaign_state.json',self.data)

    def used(self,stage,fidelity):
        return sum(a['stage']==stage and a['fidelity']==fidelity for a in self.data['attempts'])

    def remaining(self):
        return {s:{f:cap-self.used(s,f) for f,cap in values.items()} for s,values in self.plan['stage_budgets'].items()}

    def key(self,design,fidelity,controller):
        return digest(dict(execution=self.plan['execution_fingerprint'],design=design,fidelity=fidelity,
            controller=controller,feedback=self.plan['feedback_parameters'] if controller=='C2' else None,
            initial_command='deterministic frozen MATLAB PCC plan',initial_state=self.plan['initial_state'],
            timing='feedback begins at step 0, before mj_step; every 20 steps'))

    def cached(self,key):
        for a in self.data['attempts']:
            if a['key']==key and a['status']=='completed':
                verify_run(self.run.path.parent/a['run_id'],a['run_manifest_hash'])
                self.data['reuse'].append({'attempt_id':a['attempt_id'],'key':key,'reason':'verified exact execution fingerprint'})
                self.save(); return a
        return None

    def reserve(self,stage,design,fidelity,controller,retry_of=None):
        if self.used(stage,fidelity)>=self.plan['stage_budgets'][stage][fidelity] or len(self.data['attempts'])>=48:
            raise ValueError('Stage budget exhausted; later stages are reserved')
        a=dict(attempt_id=f'attempt_{len(self.data["attempts"]):03d}',stage=stage,design=design,
            fidelity=fidelity,controller=controller,key=self.key(design,fidelity,controller),status='running',retry_of=retry_of)
        self.data['attempts'].append(a); self.save()  # before any backend call
        self.run.save(a['attempt_id']+'_input.json',a.copy())
        return a

    def complete(self,attempt,result):
        attempt.update(result)
        value=attempt.get('canonical_error_m')
        if attempt['status']=='completed' and isinstance(value,(int,float)) and math.isfinite(value):
            for route in ('global',attempt['controller']):
                prior=self.data['incumbents'].get(route)
                if prior is None or (value,attempt['attempt_id'])<(prior['canonical_error_m'],prior['attempt_id']):
                    self.data['incumbents'][route]=dict(attempt)
        self.run.save(attempt['attempt_id']+'_result.json',attempt.copy()); self.save()

    def decide(self,rule,evidence,action):
        # Open the actual saved evidence now, before choosing/executing the action.
        observations={name:read(self.run.path/name) for name in evidence}
        decision=dict(rule_id=rule,evidence={name:file_hash(self.run.path/name) for name in evidence},
            observations=observations,action=action,remaining_budget=self.remaining())
        name=f'decision_{len(self.data["decisions"]):03d}.json'
        self.run.save(name,decision); self.data['decisions'].append(name); self.save()
        self.run.events.emit('DECISION_RECORDED','closeout_decision',decision=dict(actor='harness',
            decision=rule,rationale='Frozen rule applied to persisted observations; see decision artifact',
            requested_tools=(),evidence_refs=self.run.events.refs(name),next_action=rule),evidence_refs=self.run.events.refs(name))
        return observations
