"""Saved records and explicitly synthetic growth; engineering validation only."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch,MagicMock
from uuid import uuid4
import gc
import json
import shutil

from tools.context_assembly import (ROOT,EvidenceArchive,assemble_context,assemble_working_context,
    create_working_state,update_working_state,assemble_working_request,request_facts,
    check_outgoing_request,selection_roles,assert_experiment_eligible,persist_working_state,restore_working_state)
from tools.research_tasks import aggregate_acceptance,compare_acceptance,stop_interpretation
from tools.state_io import read,digest
from tools.platform_models import DeepSeekAdapter
from tools.platform_store import Store

SAVED=ROOT/'evidence/research_native_development_v3_20261007/structural_continuation_20261007'


class Mainline2Tests(TestCase):
    def setUp(self):
        self.root=ROOT/'runs'/('mainline2-offline-'+uuid4().hex);self.root.mkdir()
        self.archive=EvidenceArchive(self.root/'context',scope={'role':'Mainline 2 offline engineering'})
        self.addCleanup(self.cleanup)
        self.verification=read(SAVED/'verification.json')
        self.schedule=self.verification['plan']['schedule']
        self.groups=deepcopy(self.verification['groups'])
        self.config=read(ROOT/'runs/milestone4_autonomous_20261006/freeze.json')['provider_configuration']

    def cleanup(self):
        gc.collect();target=self.root.resolve()
        assert target.is_relative_to((ROOT/'runs').resolve()) and target.name.startswith('mainline2-offline-')
        shutil.rmtree(target)

    def compare(self,groups=None,**kwargs):
        groups=groups or self.groups
        aggregates=[aggregate_acceptance(g['records'],10,schedule=self.schedule,**kwargs) for g in groups]
        return aggregates,compare_acceptance(aggregates[1],aggregates[0])

    def test_saved_positive_and_shared_negative_gates(self):
        groups_before=digest(self.groups)
        aggregates,comparison=self.compare()
        self.assertEqual([g['accepted'] for g in aggregates],[6,7])
        self.assertEqual(comparison['relation'],'improved')
        self.assertFalse(any(a['all_scheduled_accepted'] for a in aggregates))
        for mutate in (
            lambda g:g[0]['records'].pop(),
            lambda g:g[0]['records'][0]['receipt'].update(cache_hit=True,charged={'backend_solves':0}),
            lambda g:g[0]['records'][0]['receipt'].update(execution_id='foreign'),
            lambda g:g[0]['records'][0]['acceptance'].update(status='incomplete',accepted=None),
            lambda g:g[0]['records'][0]['acceptance'].update(task_identity='different-task'),
        ):
            copied=deepcopy(self.groups);mutate(copied)
            preserved,comparison=self.compare(copied)
            self.assertEqual(comparison['relation'],'unavailable')
            self.assertTrue(comparison['unresolved'])
            self.assertIsNotNone(preserved[1]['entries'][0]['acceptance'])
        a,b=aggregates[1],deepcopy(aggregates[0]);b['comparison_scope']={'task':'unmatched'}
        self.assertEqual(compare_acceptance(a,b)['relation'],'unavailable')
        self.assertEqual(digest(self.groups),groups_before)

    def test_protocol_permitted_reuse_never_fills_fresh_slot(self):
        policy={'require_fresh_repetitions':False,'allow_historical_reuse':True}
        rows=[deepcopy(g['records'][0]) for g in self.groups]
        for row in rows:
            row['historical_reuse']=True
            row['receipt'].update(cache_hit=True,charged={'backend_solves':0})
        def aggregates(required):
            schedule=[dict(self.schedule[0],fresh_required=required)]
            return [aggregate_acceptance([r],1,schedule=schedule,evidence_policy=policy) for r in rows]
        a,b=aggregates(False)
        self.assertEqual([a['accepted'],b['accepted']],[1,1])
        self.assertTrue(a['entries'][0]['historical_reuse']);self.assertFalse(a['entries'][0]['fresh_execution'])
        self.assertNotEqual(compare_acceptance(b,a)['relation'],'unavailable')
        a,b=aggregates(True)
        self.assertEqual([a['accepted'],b['accepted']],[0,0])
        self.assertEqual(compare_acceptance(b,a)['relation'],'unavailable')
        # Passing an old producer receipt without a cache wrapper still remains
        # reuse when explicitly declared; it cannot satisfy a fresh slot.
        for row in rows:row['receipt'].update(cache_hit=False,charged={'backend_solves':1})
        a,b=aggregates(True)
        self.assertFalse(a['entries'][0]['fresh_execution'])
        self.assertEqual(compare_acceptance(b,a)['relation'],'unavailable')

    def test_legal_stop_keeps_unsupported_explanation_separate(self):
        aggregate=self.compare()[0][1]
        view=dict(executable_capacity={'wall_s':4000},plan_shortfall={'wall_s':590},actual_shortfall={'wall_s':0})
        stop=stop_interpretation(aggregate,'voluntary_stop',operational=view,
            assertions=[dict(field='executable_capacity',resource='wall_s',value=0)])
        self.assertTrue(stop['legal']);self.assertEqual(stop['explanation_support'],'unsupported')
        self.assertFalse(stop['success_claim_supported']);self.assertEqual(stop['optimality'],'not_assessed')
        self.assertEqual(stop_interpretation(aggregate,'limited_value')['explanation_support'],'not_assessed')
        prior=read(SAVED/'final_report_blocker_review.json')
        continuation=read(SAVED.parent/'report_completion_20261007/continuation_authorization.json')['authorization']
        self.assertEqual((prior['repairs_used'],prior['repair_ceiling']),(7,7))
        self.assertEqual((continuation['previous_repairs'],continuation['cumulative_material_repairs']),(7,8))
        from tools.report_completion import phase_boundaries
        boundaries=phase_boundaries(continuation)
        self.assertEqual(boundaries[0]['repairs_used'],7)
        self.assertEqual(boundaries[1]['authorized_cumulative_repair_ceiling'],8)
        self.assertNotIn('repairs_used',boundaries[1])
        self.assertNotEqual(boundaries[0]['cutoff'],boundaries[1]['cutoff'])

    def test_roles_preserve_original_stop_and_post_verification_selection(self):
        frozen=read(SAVED/'final_frozen_selection.json');before=deepcopy(frozen)
        roles=selection_roles(frozen)
        self.assertEqual(roles['incumbent_at_decision']['candidate_id'],'batch-ebbeadbdaca10732-0')
        self.assertEqual(roles['promoted_deliverable']['candidate_id'],'batch-396bdbbae02626d3-0')
        self.assertEqual(frozen,before)

    def test_display_selection_does_not_change_full_relationships(self):
        from examples.check_context_assembly import saved_research_fixture
        store,state,packet,authority,payload=saved_research_fixture()
        archive=EvidenceArchive(self.root/'history',scope=self.archive.scope,stores=(store,))
        full=assemble_context('research_decision',packet,archive=archive,authority=authority)
        narrower=deepcopy(authority)
        narrower['comparison_execution_ids']=[authority['roles']['selected_incumbent']['execution_id']]
        narrow=assemble_context('research_decision',packet,archive=archive,authority=narrower)
        self.assertEqual(full['canonical_facts'],narrow['canonical_facts'])
        self.assertEqual(full['view']['scientific_overlap'],narrow['view']['scientific_overlap'])
        self.assertEqual(full['view']['bound_evidence']['replications'],narrow['view']['bound_evidence']['replications'])

    def test_growth_claim_retrieval_and_real_read_tool(self):
        from tools.platform_tools import read_evidence
        from schemas.platform_operations import ReadEvidence
        ref=self.archive.snapshot({'engineering_fixture':True,'counterexample':False,'rows':[{'index':i,'unit':'1'} for i in range(40)]})
        authority={'roles':{},'legal_actions':{},'remaining_budget':{},'stop':{'status':'stopped'}}
        state=create_working_state({'bound_facts':{}},authority=authority,archive=self.archive,
            claims=[dict(claim_id='cause',statement='Unknown',supporting_evidence=[],counterexamples=[])])
        state=update_working_state(state,archive=self.archive,claim_revisions=[dict(claim_id='cause',statement='Counterexample retains uncertainty',
            supporting_evidence=[],counterexamples=[dict(reference=ref,pointer='/counterexample',value=False)])],
            experiment_updates=[dict(experiment_id='synthetic-'+str(i),status='pending',engineering_fixture=True) for i in range(40)])
        store=Store(self.root/'checkpoint');checkpoint=persist_working_state(state,store=store,archive=self.archive)
        restored,archive=restore_working_state(checkpoint,store=store,scope=self.archive.scope,as_of_unix=1791370000)
        self.assertEqual(restored['claims'],state['claims']);self.assertEqual(restored['experiments'],state['experiments'])
        view=assemble_working_context('research_decision',restored,archive=archive)['view']
        history=view['working_context']['recovery']['claim_history']['cause']['original_history']
        self.assertEqual(len(archive.retrieve(history['reference'],pointer=history['pointer'])['page']['content']),2)
        page=archive.retrieve(ref,pointer='/rows',limit=10);self.assertEqual(page['continuation']['offset'],10)
        # The actual evidence.read implementation resolves an offloaded source
        # from the advertised role allowlist and retains its bounded read record.
        fake=MagicMock();fake.session.return_value={'state':{'role_context':{'context_source_manifest':archive.manifest(),'context_archive_scope':archive.scope}}}
        fake.root=self.root
        ctx=SimpleNamespace(artifact=lambda r:(_ for _ in ()).throw(ValueError('ARTIFACT_NOT_FOUND')),store=fake,run_id='offline')
        with patch('tools.context_assembly.EvidenceArchive.from_manifest',return_value=archive):
            result=read_evidence(ctx,ReadEvidence(reference=ref,pointer='/rows',limit=10))
        self.assertEqual(result.next_offset,10);self.assertEqual(result.content,page['page']['content'])
        self.assertIn('reads',fake.update_state.call_args.args[2])
        with self.assertRaisesRegex(ValueError,'SEALED'):assert_experiment_eligible(restored,{'experiment_id':'retry'})

    def test_exact_final_request_boundary_before_credentials(self):
        payload={'model':self.config['model'],'max_tokens':self.config['max_tokens'],'messages':[
            {'role':'system','content':'Offline boundary recording.'},{'role':'user','content':'Saved evidence.'}],
            'tools':[{'type':'function','function':{'name':'report','parameters':{'type':'object'}}}]}
        adapter=DeepSeekAdapter();adapter.request_config=self.config;adapter.request_purpose='final_report'
        recorded=[]
        def transport(config,wire):recorded.append(deepcopy(wire));return {'offline_recorded':True}
        with patch.object(adapter,'_transport',side_effect=transport),patch('tools.platform_models.os.environ.get',side_effect=AssertionError('NO_CREDENTIAL_READ')):
            self.assertEqual(adapter.respond(payload,0),{'offline_recorded':True})
            self.assertEqual(recorded,[payload])
            for addition in ('retained history','diagnostic return','schema'):
                overflow=deepcopy(payload)
                if addition=='schema':overflow['tools'][0]['function']['parameters']['description']='x'*100000
                else:overflow['messages'].append({'role':'tool','content':addition+'x'*100000})
                with self.assertRaisesRegex(ValueError,'SEND_BOUNDARY_OVERFLOW'):adapter.respond(overflow,0)
            self.assertEqual(len(recorded),1)

    def test_host_archive_read_keeps_grant_scope_and_integrity_checks(self):
        from examples.platform_fixtures import project,reference_input
        from tools.platform_host import Host
        store=Store(self.root/'reader');grant=project()
        grant['budget'].update(model_calls=0,backend_solves=0,worker_calls=0)
        store.create(grant)
        host=Host(store.root,'offline-reader');inp=reference_input(host.run_id)
        inp['policy'].update(allowed_tools=['evidence.read'],tool_bindings={},search=None)
        inp['policy']['budget'].update(model_calls=0,backend_solves=0,worker_calls=0)
        host.create(inp);host.resume()
        ref=self.archive.snapshot({'engineering_fixture':True,'rows':list(range(30))})
        with store.transaction() as db:
            state=store.session(host.run_id,db)['state']
            state['role_context']={'context_source_manifest':self.archive.manifest(),'context_archive_scope':self.archive.scope}
            store.update_state(db,host.run_id,state)
        def call(reference):
            return host.invoke(dict(request_id=uuid4().hex,tool_id='evidence.read',tool_version='1.0.0',
                arguments=dict(reference=reference,pointer='/rows',limit=10),reason='Offline archived source read.'))
        result=call(ref)
        self.assertEqual(result['execution_status'],'completed',result)
        page=store.artifact(result['output']);self.assertEqual(page['content'],list(range(10)))
        self.assertEqual(page['next_offset'],10)
        self.assertTrue(store.session(host.run_id)['state']['reads'])
        denied=call(dict(ref,artifact_id='0'*64))
        self.assertIn('CONTEXT_READ_OUT_OF_SCOPE',denied['error'])
        source=ROOT/self.archive.sources[ref['artifact_id']]['path'];original=source.read_bytes()
        source.write_bytes(b'{"tampered":true}')
        try:self.assertIn('CONTEXT_ARCHIVE_CHANGED',call(ref)['error'])
        finally:source.write_bytes(original)
        with store.transaction() as db:
            state=store.session(host.run_id,db)['state'];state['role_grant']={'permitted_tools':[]}
            store.update_state(db,host.run_id,state)
        self.assertIn('TOOL_NOT_IN_DIAGNOSTIC_REQUEST_SCOPE',call(ref)['error'])
        with store.transaction() as db:
            state=store.session(host.run_id,db)['state']
            state['role_context']['campaign_permissions']={'elapsed_deadline_unix':10}
            store.update_state(db,host.run_id,state)
        with self.assertRaisesRegex(ValueError,'SEND_DEADLINE_EXPIRED'):
            check_outgoing_request({'model':self.config['model'],'messages':[],'max_tokens':self.config['max_tokens']},self.config,
                'research_decision',host=host,as_of_unix=11)
        used=store.remaining()['used']
        self.assertEqual((used['model_calls'],used['backend_solves'],used['worker_calls']),(0,0,0))
