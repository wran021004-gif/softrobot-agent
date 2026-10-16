"""One genuine bounded Strands pilot with imported P1-P5 evidence."""
import asyncio
import hashlib
import json
from pathlib import Path
import tarfile

from tools.research import core,rl
from tools.research.agent import converse,pending as provider_pending
from tools.research.budget import engineering_closeout
from tools.research.design import numerical_binding,verify_candidate
from tools.research.state import state,save,update
from tools.state_io import atomic_json,read

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'configs/research/study_sorosim_s5_agent_feedback.json'


def sealed(archive,reference):
    body=archive.extractfile('artifacts/'+reference['artifact_id']+'.json').read()
    if hashlib.sha256(body).hexdigest()!=reference['artifact_id']:
        raise ValueError('SEALED_SOURCE_ARTIFACT_HASH_MISMATCH')
    return json.loads(body)


def plan(action,**data):
    return dict(action=action,
        hypothesis='The Agent can choose a testable next action after reading actual P1-P5 failures.',
        expected_observation='A genuine model-generated action grounded in exact imported evidence.',
        weakening_observation='No evidence read, only a scripted action, provider failure or ungrounded explanation.',
        fixed_conditions='Frozen original task, Design B materialization and bounded stage grants.',
        stopping_condition='One live pilot within 12 provider requests and the declared scientific counts.',
        interpretation='A single feedback decision does not establish Agent superiority.',**data)


def import_context(host,stage,path,brief):
    raw=Path(path).read_bytes()
    body=json.loads(raw)
    reference=save(host,dict(stage=stage,source_path=str(Path(path).relative_to(ROOT)),
        source_sha256=hashlib.sha256(raw).hexdigest(),original=body,
        ownership='read-only prior-stage evidence; not a current-study execution'),
        'imported_scoped_stage_evidence')
    return dict(stage=stage,reference=reference,summary=brief,
        source_sha256=hashlib.sha256(raw).hexdigest())


def run(directory):
    host=core.prepare(STUDY,directory)
    if 'freeze' not in state(host):core.bind(host)
    old=read(ROOT/'evidence/sorosim_s4b/recovered_pilot/summary.json')['rows'][1]
    with tarfile.open(ROOT/'evidence/sorosim_s4b/recovered_pilot/immutable_artifacts.tar.gz') as archive:
        params=sealed(archive,old['candidate'])['parameters']
    generated=core.dispatch(host,plan('generate',generation=params),'s5agent-materialize-B',origin='engineering')['result']
    candidate=generated['candidate']
    current=verify_candidate(host,candidate)
    if numerical_binding(current['configuration'],state(host)['spec'])['physical_design_identity']!=old['physical_design_identity']:
        raise ValueError('S5_AGENT_DESIGN_B_MISMATCH')
    s5a=read(ROOT/'evidence/sorosim_s5a/summary.json')
    s5a_archive=ROOT/'evidence/sorosim_s5a/study/immutable_artifacts.tar.gz'
    with tarfile.open(s5a_archive) as archive:
        source=sealed(archive,s5a['source'])
    if hashlib.sha256(s5a_archive.read_bytes()).hexdigest()!=read(ROOT/'evidence/sorosim_s5a/comparison_detail.json')['source_archive_sha256']:
        raise ValueError('S5A_ARCHIVE_CHANGED')
    source_ref=save(host,source,'imported_exact_mathematical_source')
    relation=rl.import_mathematical_reference(host,candidate,source_ref)
    references=rl.compatible_references(host)
    if not any(v.get('available') and v['candidate']==candidate and v['source']==source_ref for v in references):
        raise ValueError('S5_AGENT_RESIDUAL_REFERENCE_NOT_ADMITTED')
    s45=read(ROOT/'evidence/sorosim_s45/interior_summary.json')
    s5b=read(ROOT/'evidence/sorosim_s5b/summary.json')
    s5rl=read(ROOT/'evidence/sorosim_s5rl/summary.json')
    s5t=read(ROOT/'evidence/sorosim_s5t/summary.json')
    context=[
        import_context(host,'S4.5',ROOT/'evidence/sorosim_s45/interior_summary.json',dict(
            mathematical_classification=read(ROOT/'evidence/sorosim_s45/posthoc_verification.json')['mathematical_classification'],
            optimizer_converged=False,source=s45['solve']['reference'],cross_A_with_U_B='engineering_error_unavailable',
            cross_B_with_U_A='complete_original_task_failure')),
        import_context(host,'S5-A',ROOT/'evidence/sorosim_s5a/summary.json',dict(
            accepted=False,terminal_error_m=s5a['acceptance']['metrics']['terminal_error_m'],
            holding_max_speed_m_s=s5a['acceptance']['metrics']['holding_max_speed_m_s'],
            maximum_position_discrepancy_m=s5a['comparison']['max_position_difference_m'])),
        import_context(host,'S5-B',ROOT/'evidence/sorosim_s5b/summary.json',dict(
            accepted=False,terminal_error_m=s5b['acceptance']['metrics']['terminal_error_m'],
            holding_max_speed_m_s=s5b['acceptance']['metrics']['holding_max_speed_m_s'],
            updates=s5b['controller_facts']['updates'],solver_errors=s5b['controller_facts']['solver_error_count'])),
        import_context(host,'S5-RL',ROOT/'evidence/sorosim_s5rl/summary.json',dict(
            training_actions=s5rl['stage_usage']['stages']['actual_actions'],
            independently_evaluated_modes=[dict(mode=r['mode'],passed=r['evaluation_facts']['passed'],
                terminal_error_m=r['evaluation_facts']['episodes'][0]['terminal_position_error_m'],
                holding_max_speed_m_s=r['evaluation_facts']['episodes'][0]['holding_max_speed_m_s']) for r in s5rl['routes']])),
        import_context(host,'S5-T',ROOT/'evidence/sorosim_s5t/summary.json',dict(
            reliability=s5t['kkt']['reliability'],envelope_gradient=s5t['kkt']['envelope_gradient'],
            full_reoptimizations=0))]
    update(host,stage_context=context,preseeded_candidate=candidate,
        preseeded_mathematical_reference=relation)
    blocker=None
    try:
        asyncio.run(converse(host))
    except Exception as exc:
        blocker=dict(error_type=type(exc).__name__,reason=str(exc),
            provider_requests=state(host)['pilot']['live_model_requests'],
            pending_science=state(host).get('pending'),pending_provider_requests=len(provider_pending(host)))
        save(host,blocker,'live_agent_blocker')
        if not state(host).get('pending') and not provider_pending(host):
            engineering_closeout(host,'Live provider or Agent runtime blocked; no fabricated model decision')
    events=host.store.events(host.run_id)
    actions=[]
    for event in events:
        if event['kind']=='model_original_tool_request':
            use=host.store.artifact(event['outputs'][0])['tool_use']
            actions.append(dict(name=use['name'],input=use['input'],tool_use_id=use['toolUseId']))
    outcome=dict(stage='S5-Agent',candidate=candidate,mathematical_source=source_ref,
        context=context,model_generated_tools=actions,model_request_count=state(host)['pilot']['live_model_requests'],
        research_status=state(host)['research_status'],blocker=blocker,
        backend_launches=host.store.remaining()['used']['backend_solves'],
        public_operations=host.store.remaining()['used']['tool_calls'])
    outcome_ref=save(host,outcome,'s5_agent_pilot_summary')
    exported=core.export(host,ROOT/'evidence/sorosim_s5_agent/study')
    atomic_json(ROOT/'evidence/sorosim_s5_agent/summary.json',dict(outcome,stage_summary_reference=outcome_ref))
    return exported


if __name__=='__main__':
    import sys
    print(run(Path(sys.argv[1])))
