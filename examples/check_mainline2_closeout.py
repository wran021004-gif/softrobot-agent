"""Saved data plus distinct synthetic historical facts; offline engineering only."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys
import shutil
import gc
import unittest
from uuid import uuid4
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.context_assembly import (EvidenceArchive, assemble_context, create_working_state,
    assemble_working_request, persist_working_state, restore_working_state, request_facts,
    check_outgoing_request, pointer_part)
from tools.state_io import read, atomic_json, digest
from tools.platform_store import Store
from tools.platform_host import Host
from examples.check_context_assembly import saved_research_fixture, M4ROOT


def read_offloaded(directory, state, archive, fact_id, canonical_reference):
    """Use the advertised public tool, including its grant and archive checks."""
    # The synthetic Host's authorization anchor belongs to the isolated fixture.
    with patch('tools.platform_store.ROOT',directory):
        return _read_offloaded(directory,state,archive,fact_id,canonical_reference)


def _read_offloaded(directory, state, archive, fact_id, canonical_reference):
    from examples.platform_fixtures import project, reference_input
    store = Store(directory/'reader'); grant = project()
    grant['budget'].update(model_calls=0, backend_solves=0, worker_calls=0)
    store.create(grant)
    host = Host(store.root, 'closeout-reader')
    inp = reference_input(host.run_id)
    inp['policy'].update(allowed_tools=['evidence.read'], tool_bindings={}, search=None)
    inp['policy']['budget'].update(model_calls=0, backend_solves=0, worker_calls=0)
    host.create(inp); host.resume()
    # A reader Host owns its own Store. Expose the already authorized canonical
    # snapshot through a scoped manifest containing only that local source;
    # do not grant access to the original campaign's Store.
    reader_archive = EvidenceArchive(directory/'reader_context',scope=archive.scope)
    assert reader_archive.snapshot(archive.load(canonical_reference))==canonical_reference
    with store.transaction() as db:
        session = store.session(host.run_id, db)['state']
        session['role_context'] = dict(context_source_manifest=reader_archive.manifest(), context_archive_scope=archive.scope)
        store.update_state(db, host.run_id, session)
    result = host.invoke(dict(request_id='offloaded-fact', tool_id='evidence.read', tool_version='1.0.0',
        arguments=dict(reference=canonical_reference, pointer='/facts/'+pointer_part(fact_id),
            byte_limit=8192), reason='Offline synthetic historical fact retrieval.'))
    assert result['execution_status']=='completed', result
    content = store.artifact(result['output'])['content']
    assert content==state['current_facts'][fact_id]
    assert store.session(host.run_id)['state']['reads']
    used = store.remaining()['used']
    assert all(used[k]==0 for k in ('model_calls','backend_solves','worker_calls'))
    return dict(fact_id=fact_id, public_tool='evidence.read', exact_binding_preserved=True,
        read_ledger_recorded=True, retrieved_fact_count=1)


def restore_probe(directory):
    source = read(directory/'input.json')
    state, archive = restore_working_state(source['reference'], store=Store(directory/'checkpoint'),
        scope=source['scope'], stores=(Store(M4ROOT),), as_of_unix=1791377100.)
    assert digest(state['current_facts'])==source['facts_identity']
    wire, audit = assemble_working_request(source['payload'], source['config'], 'research_decision', state,
        archive=archive, context_slot='research_packet')
    assert audit['selected_fact_ids']==source['selected_fact_ids']
    context = json.loads(wire['messages'][1]['content'])['role_context']['research_packet']
    assert context['working_context']['fact_archive']['reference']==audit['canonical_fact_reference']
    assert request_facts(dict(payload=wire,context_assembly_audit=audit))==state['current_facts']
    check_outgoing_request(wire,source['config'],'research_decision')
    retrieval = read_offloaded(directory, state, archive, source['offloaded_fact_id'], audit['canonical_fact_reference'])
    atomic_json(directory/'recovered.json', dict(new_process=True, archive_fact_count=len(state['current_facts']),
        inline_fact_count=len(audit['selected_fact_ids']), selection_preserved=True,
        complete_request_bytes=audit['measurement']['utf8_bytes'], retrieval=retrieval))


def growth_probe(directory):
    directory.mkdir(parents=True, exist_ok=True)
    protected = [M4ROOT/'platform.sqlite', M4ROOT/'scheduler_state.json', ROOT/'runs/.platform_authorities.sqlite']
    hashes = lambda: {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    before = hashes()
    store, _, saved_packet, authority, payload = saved_research_fixture()
    archive = EvidenceArchive(directory/'context', scope={'role':'Mainline 2 closeout offline'}, stores=(store,))
    config = read(M4ROOT/'freeze.json')['provider_configuration']
    saved = assemble_context('research_decision', saved_packet, archive=archive, authority=authority)
    # Exact current counterexample selector exercises selection as well as recovery.
    counter_id, counter = next((key,f) for key,f in saved['canonical_facts'].items()
        if f['metric']=='holding_max_speed_m_s' and f['value']>.02)
    claim = dict(claim_id='closeout-counterexample', hypothesis_status='unresolved',
        supporting_evidence=[dict(fact_id=counter_id)], counterexamples=[dict(fact_id=counter_id)])
    records = []; template = saved_packet['history']['rows'][0]
    # Frozen current-decision evidence does not include these unrelated synthetic executions.
    for count in (0,16,64):
        packet = deepcopy(saved_packet)
        for i in range(count):
            row = deepcopy(template); eid = 'synthetic-closeout-execution-'+str(i)
            row['candidate'].update(execution_id=eid, candidate_id=eid)
            row['scientific_configuration_identity'] = digest(dict(synthetic_history=i))
            row['engineering_fixture'] = True
            source = row['metrics']['source']
            ev = deepcopy(archive.load(source['evaluation']))
            simulation = archive.snapshot(dict(engineering_fixture=True, synthetic_execution=i))
            ev.update(source_execution_id=eid, original_execution_id=eid, source=simulation)
            ev['metrics'][0]['value'] = .019+i*.00001
            evref = archive.snapshot(ev)
            profile = deepcopy(archive.load(source['profile']))
            profile['detail'].update(execution_id=eid, evaluation=evref, simulation=simulation)
            profile['detail']['sampled_settling'].update(max_error_m=.019+i*.00001,max_speed_m_s=.03+i*.00001,passed=False)
            pref = archive.snapshot(profile)
            row['metrics']['source'].update(execution_id=eid,evaluation=evref,profile=pref)
            packet['history']['rows'].append(row)
        state = create_working_state(packet, authority=authority, archive=archive, claims=[claim])
        wire, audit = assemble_working_request(payload, config, 'research_decision', state,
            archive=archive, context_slot='research_packet')
        check_outgoing_request(wire,config,'research_decision')
        assembly = assemble_context('research_decision', packet, archive=archive, authority=authority)
        assert assembly['view']['scientific_overlap']==saved['view']['scientific_overlap']
        assert assembly['view']['bound_evidence']['replications']==saved['view']['bound_evidence']['replications']
        assert set(saved['canonical_facts'])<=state['current_facts'].keys()
        assert counter_id in audit['selected_fact_ids']
        assert request_facts(dict(payload=wire,context_assembly_audit=audit))==state['current_facts']
        facts = state['current_facts']
        per_execution = sum(f['execution_id']==template['candidate']['execution_id']
            for f in saved['canonical_facts'].values())
        assert len(facts)==len(saved['canonical_facts'])+count*per_execution
        records.append(dict(synthetic_executions=count, **audit['fact_selection'],
            complete_request_bytes=audit['measurement']['utf8_bytes'],
            conservative_estimated_input_tokens=audit['measurement']['estimated_input_tokens'],
            unchanged_input_budget_tokens=audit['measurement']['input_budget_tokens'], passed=True))
        if count==64:
            offloaded = next(key for key in facts if facts[key]['execution_id'].startswith('synthetic-') and key not in audit['selected_fact_ids'])
            checkpoint = Store(directory/'checkpoint')
            atomic_json(directory/'input.json',dict(reference=persist_working_state(state,store=checkpoint,archive=archive),
                scope=archive.scope,payload=payload,config=config,facts_identity=digest(facts),
                selected_fact_ids=audit['selected_fact_ids'],offloaded_fact_id=offloaded))
    assert len({r['inline_fact_count'] for r in records})==1
    assert records[0]['archived_fact_count']<records[1]['archived_fact_count']<records[2]['archived_fact_count']
    assert max(r['complete_request_bytes'] for r in records)-min(r['complete_request_bytes'] for r in records)<1024
    process = subprocess.run([sys.executable,str(Path(__file__).resolve()),'--restore',str(directory)],
        cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    assert process.returncode==0,process.stderr
    recovered = read(directory/'recovered.json')
    # Complete-prefetch reports and oversized required sets must fail honestly.
    report = dict(bound_facts=state['current_facts'])
    report_state = create_working_state(report, authority={'roles':{}}, archive=archive)
    failures = {}
    for purpose in ('final_report','research_decision'):
        try: assemble_working_request(payload,config,purpose,report_state,archive=archive)
        except ValueError as exc:
            assert 'CONTEXT_PREPARATION_REQUIRED_MATERIAL_EXCEEDS_BUDGET' in str(exc)
            failures[purpose] = 'CONTEXT_PREPARATION_REQUIRED_MATERIAL_EXCEEDS_BUDGET'
        else: raise AssertionError('Required prefetch was silently truncated')
    assert hashes()==before
    return dict(growth=records,recovery=recovered,required_material_failures=failures,
        full_history_relationships_preserved=True, current_counterexample_retained=True,
        protected_sources_unchanged=True, new_provider_requests=0, scientific_experiments=0)


def verify(output):
    names = ['tests.test_research_tasks', 'tests.test_context_assembly',
        'tests.test_research_mainline2.Mainline2Tests.test_saved_positive_and_shared_negative_gates',
        'tests.test_research_mainline2.Mainline2Tests.test_protocol_components_outcomes_and_required_sources',
        'tests.test_research_mainline2.Mainline2Tests.test_null_shortfall_keeps_voluntary_stop_legal',
        'tests.test_research_mainline2.Mainline2Tests.test_display_selection_does_not_change_full_relationships',
        'tests.test_research_recovery.ResearchRecoveryTests.test_saved_multiround_restore_into_new_process_and_shared_facts',
        'tests.test_report_completion']
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    def ids(tests):
        return [name for test in tests for name in (ids(test) if isinstance(test, unittest.TestSuite) else [test.id()])]
    checks = ids(suite)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    atomic_json(output/'verification.json', dict(passed=result.wasSuccessful(), checks_run=result.testsRun,
        check_ids=checks, command='conda run -n softagent python examples/check_mainline2_closeout.py --verify --output evidence/research_mainline2_closeout_20261007',
        failures=[dict(check=t.id(),trace=trace) for t,trace in result.failures+result.errors],
        comparison_negative_reasons=['PROTOCOL_REQUIRED_COMPONENT_MISSING_OR_UNKNOWN',
            'ACCEPTANCE_COMPONENT_OUTCOME_INCONSISTENT','PROTOCOL_REQUIRED_SOURCE_MISSING:evaluation'],
        saved_positive=dict(joint_counts=[6,7],relation='improved',full_suite_completed=False),
        null_stop=dict(legal=True,observed=None,support='not_assessed',optimality='not_assessed'),
        new_provider_requests=0,scientific_experiments=0,
        limits=['No live-model validation.','Historical scheduler-fixture implementation seal remains in force.']))
    if not result.wasSuccessful(): raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--restore',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    if args.restore: restore_probe(args.restore)
    elif args.verify: verify(args.output)
    else:
        fixture=ROOT/'runs'/('closeout-fixture-'+uuid4().hex)
        try:
            result=growth_probe(fixture)
            atomic_json(args.output/'growth.json',result)
            print(json.dumps(result,ensure_ascii=False))
        finally:
            gc.collect(); target=fixture.resolve()
            assert target.is_relative_to((ROOT/'runs').resolve()) and target.name.startswith('closeout-fixture-')
            shutil.rmtree(target)
