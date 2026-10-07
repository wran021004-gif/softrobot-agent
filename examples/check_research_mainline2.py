"""Coherent saved-record lifecycle; offline engineering, never new research."""
from copy import deepcopy
import argparse
import gc
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from tools.platform_store import Store
from tools.context_assembly import EvidenceArchive,update_working_state,persist_working_state
from tools.current_research_authority import verify_accounting_snapshot,restored_execution
from tools.research_tasks import aggregate_acceptance,compare_acceptance
from examples.check_research_recovery import prepare_sequence,child_restore,M4

SAVED=ROOT/'evidence/research_native_development_v3_20261007'
LIVE=ROOT/'runs/research_native_development_v3_20261007'
CLOCK=1791377100.0  # Explicit offline time after the saved v3 deadline.
DIAGNOSTIC=ROOT/'runs/milestone5_diagnostic_20261005/single_context'


def diagnostic_visibility():
    """Observe saved reads, explicit return, and actual principal input separately."""
    from tools.diagnostic_facts import context_view
    store=Store(DIAGNOSTIC);prefix='gvs-milestone5-diagnostic-d0e4130f5370-'
    views={}
    for suffix in ('executor','feedback-bound-final'):
        state=store.session(prefix+suffix)['state'];view=context_view(state)
        rows=[]
        for row in view['read_ledger']:
            content=store.artifact(row['result']) if row.get('result') else None
            rows.append(dict(method=row['method'],source=row.get('source'),pointer=row.get('pointer'),
                result=row.get('result'),status=row['status'],provenance=row['provenance'],
                content_identity=digest(content),content_fields=list(content) if isinstance(content,dict) else None,
                presentation=row['presentation'],displayed_handle_count=len(row['displayed_handles']),
                scope='Saved role read/explicit transfer; derived catalog visibility is not proof of principal inspection'))
        views[suffix]=dict(context_id=prefix+suffix,reads=rows)
    principal=views['feedback-bound-final']
    deliveries=[e for e in store.events(principal['context_id']) if e['kind']=='context_delivery' and e['status']=='adapter_submitted']
    request_ref=deliveries[-1]['inputs'][0];wire=store.artifact(request_ref)
    role=json.loads(wire['messages'][1]['content'])['role_context']
    principal['actual_saved_presentation']=dict(request=request_ref,message_index=1,
        context_pointer='/role_context/decision_packet',packet_reference=role['decision_packet_reference'],
        packet_fields=list(role['decision_packet']),packet_identity=digest(role['decision_packet']),
        historical_only=True,new_provider_request=False)
    assert views['executor']['reads'][0]['method']=='diagnosis.inspect_evidence'
    assert principal['reads'][0]['method']=='explicit_handoff'
    return dict(source_store=DIAGNOSTIC.relative_to(ROOT).as_posix(),role_views=views,
        local_reads_and_transferred_returns_distinct=True,principal_inspected_all_originals=False,
        limitation='Only saved context delivery establishes presentation; neither citations nor a diagnostic return establish personal inspection or causal truth.')


def observe(output):
    protected=[M4/'platform.sqlite',M4/'scheduler_state.json',LIVE/'platform.sqlite',LIVE/'live_clock.json',
        ROOT/'runs/.platform_authorities.sqlite',ROOT/'runs/milestone5_control_20261006/platform.sqlite',DIAGNOSTIC/'platform.sqlite']
    hashes=lambda:{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before=hashes();directory=ROOT/'runs'/('mainline2-lifecycle-'+uuid4().hex);directory.mkdir()
    try:
        prepare_sequence(directory)
        checkpoint_store=Store(directory/'store');input_=read(directory/'input.json')
        checkpoint=checkpoint_store.artifact(input_['reference']);state=deepcopy(checkpoint['state'])
        archive=EvidenceArchive.from_manifest(ROOT/checkpoint['source_manifest'],scope=input_['scope'],stores=(Store(M4),))
        # A modest growth extension exercises the actual working state. These
        # records are explicitly synthetic pending engineering work, not robot
        # executions. The saved scientific table and STOP do not change.
        claim=deepcopy(state['claims']['holding_response'][-1]['claim'])
        claim['statement']='Engineering growth fixture: the saved counterexamples still leave the dominant cause unresolved.'
        claim['engineering_fixture']=True
        state=update_working_state(state,archive=archive,claim_revisions=[claim],experiment_updates=[
            dict(experiment_id='engineering-growth-'+str(i),status='pending',engineering_fixture=True) for i in range(40)])
        input_.update(reference=persist_working_state(state,store=checkpoint_store,archive=archive),expected_state_identity=digest(state))
        atomic_json(directory/'input.json',input_)
        process=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--restore',str(directory),'--clock',str(CLOCK)],
            cwd=ROOT,capture_output=True,text=True,encoding='utf8')
        if process.returncode:raise RuntimeError(process.stderr)
        recovered=read(directory/'restored.json')
        requests={purpose:read(directory/(purpose+'_next_request.json')) for purpose in ('research_decision','final_report')}
        from tools.context_assembly import restore_working_state,request_facts
        restored,_=restore_working_state(input_['reference'],store=checkpoint_store,scope=input_['scope'],stores=(Store(M4),),as_of_unix=CLOCK)
        for field in ('current_facts','claims','experiments','budget','budget_accounting','candidate_artifacts'):
            assert restored[field]==state[field],field
        assert restored['authority']==state['authority'] and restored['current_execution']['sealed']
        assert all(request_facts(r)==state['current_facts'] for r in requests.values())
        v=read(SAVED/'structural_continuation_20261007/verification.json')
        aggregates=[aggregate_acceptance(g['records'],10,schedule=v['plan']['schedule']) for g in v['groups']]
        comparison=compare_acceptance(aggregates[1],aggregates[0]);assert comparison['relation']=='improved'
        saved_state=read(LIVE/'working_state.json')['state'];store=Store(LIVE)
        binding=saved_state['authority']['accounting_binding'];snapshot=store.artifact(binding['reference'])
        cutoff=verify_accounting_snapshot(store,snapshot)
        execution=restored_execution(saved_state,(store,),as_of_unix=CLOCK)
        assert execution['expired'] and set(execution['legal_actions'])=={'stop'}
        visibility=diagnostic_visibility()
        after=hashes();assert before==after
        result=dict(kind='Mainline 2 offline engineering validation',passed=True,controlled_clock_unix=CLOCK,
            lifecycle=dict(new_process=True,canonical_fact_count=len(state['current_facts']),fact_identity=digest(state['current_facts']),
                historical_state_identity=input_['expected_state_identity'],original_stop_preserved=True,
                role_identity=digest(state['authority']['roles']),hypothesis_revisions=len(state['claims']['holding_response']),
                pending_synthetic_growth=40,completed_or_uncertain_work_replayed=False,
                counterexamples_identity=digest([r['claim'].get('counterexamples') for r in state['claims']['holding_response']]),
                next_requests={p:dict(measurement=r['context_assembly_audit']['measurement'],offline=True,sent=False) for p,r in requests.items()}),
            historical_accounting_cutoff=cutoff,current_executable_authority=execution,
            saved_comparison=dict(joint_counts=[a['accepted'] for a in aggregates],comparison=comparison,full_suite_pass=False,
                source='evidence/research_native_development_v3_20261007/structural_continuation_20261007/verification.json'),
            protected_sources=dict(unchanged=True,sha256=after),
            diagnostic_visibility=visibility,
            new_activity=dict(provider_requests=0,backend_executions=0,controller_solves=0,scientific_experiments=0),
            limitations=['Offline byte/token estimates, no new provider usage measurement.','No live model behavior validation.'])
        atomic_json(output/'lifecycle.json',result)
        print(json.dumps({'passed':True,'facts':len(state['current_facts']),'joint_counts':[6,7],'new_process':True,'sources_unchanged':True}))
    finally:
        gc.collect();target=directory.resolve()
        if not target.is_relative_to((ROOT/'runs').resolve()) or not target.name.startswith('mainline2-lifecycle-'):
            raise ValueError('ENGINEERING_CLEANUP_OUTSIDE_WORKSPACE')
        shutil.rmtree(target)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--restore',type=Path)
    parser.add_argument('--clock',type=float,default=CLOCK)
    parser.add_argument('--output',type=Path,default=ROOT/'evidence/research_mainline2_20261007')
    args=parser.parse_args()
    child_restore(args.restore,as_of_unix=args.clock) if args.restore else observe(args.output)
