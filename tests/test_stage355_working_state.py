"""Bounded saved-case and source-contract checks; all execution is forbidden."""
from copy import deepcopy
from contextlib import closing
import hashlib
import gc
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from tools.platform_store import Store, plain, encode
from tools.platform_host import Host
from tools.platform_models import input_for, payload_for
from tools.diagnostic_reference_adapter import ScopedReferenceAdapter
from tools.working_state import project_working_state
from tools.acceptance_definitions import resolve_acceptance
from tools.parameter_impacts import parameter_impacts
from tools.diagnostic_handoff import engineering_fixture, consume_handoff
from tools.execution_completion import structured_feedback
from examples.stage355_inspect import inspect
from tools.state_io import read
from tools.diagnostic_workflow import ROOT


def fingerprint(store):
    with store.connect(True) as db:
        return hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()


class WorkingStateTests(TestCase):
    def setUp(self):
        self.guards=[]
        for target in ('tools.platform_host.Host.invoke','tools.platform_host.Host.resume',
                       'tools.model_transports.deepseek.request_completion',
                       'extensions.tendon_family.backends.MujocoBackend.run',
                       'extensions.tendon_family.gvs_trajectory.TrajectoryWorkspace.__init__'):
            guard=patch(target,side_effect=AssertionError('Offline checks forbid execution: '+target))
            guard.start();self.guards.append(guard)
        self.addCleanup(lambda:[guard.stop() for guard in self.guards])

    def cases(self):
        for stage in ('stage353','stage354'):
            for mode in ('single_context','dual_context'):
                store=Store(ROOT/f'runs/{stage}_milestone0_20261003'/mode)
                with store.connect(True) as db:
                    ids=[r[0] for r in db.execute('SELECT run_id FROM sessions')
                         if r[0].endswith(('shared','design','diagnostic'))]
                yield stage,mode,store,ids

    def test_inspection_provider_and_no_mutation(self):
        self.payload_sizes={}
        for stage,mode,store,ids in self.cases():
            before=fingerprint(store)
            for identity in ids:
                with self.subTest(stage=stage,mode=mode,identity=identity):
                    view=inspect(store.root,identity)
                    self.assertEqual(view,inspect(store.root,identity))
                    model_input=input_for(Host(store.root,identity))
                    self.assertEqual(model_input.context['working_state'],view)
                    payload=payload_for(Host(store.root,identity),ScopedReferenceAdapter())
                    presented=json.loads(payload['messages'][1]['content'])
                    self.assertEqual(presented['working_state'],view)
                    advertised={t['function']['name'] for t in payload['tools']}
                    state=store.session(identity)['state']
                    from tools.platform_models import phase_tools
                    active=phase_tools(state) or []
                    for action in view['actions']:
                        if action['tool'] in active and action['native_function']:
                            self.assertIn(action['native_function'],advertised)
                    self.assertLess(len(encode(payload).encode()),400000)
                    self.assertEqual(payload['model'],'deepseek-flash')
                    self.assertEqual(payload['thinking'],{'type':'enabled'})
                    self.assertEqual(payload['reasoning_effort'],'high')
                    self.assertEqual(payload['max_tokens'],model_input.context['policy']['model']['max_tokens'])
                    self.payload_sizes[identity]=len(encode(payload).encode())
            self.assertEqual(before,fingerprint(store))

    def test_completed_computation_incomplete_delivery_and_explicit_null(self):
        for stage,mode,store,ids in self.cases():
            for identity in ids:
                view=project_working_state(store,identity)
                self.assertTrue(view.workflow['computation_complete'])
                self.assertEqual(view.workflow['delivery_complete'],stage=='stage354')
                self.assertIsNotNone(view.latest_tested)
                self.assertEqual(view.latest_tested['configuration'],view.prepared['executed_configuration'])
                self.assertTrue(view.prepared['scientific_scope_matches_execution'])
                self.assertNotEqual(view.prepared['configuration'],view.latest_tested['configuration'])
                if stage=='stage353':
                    self.assertIsNone(view.products.accepted_revision)
                    self.assertFalse(view.selection['recorded'])
                elif mode=='dual_context':
                    self.assertTrue(view.selection['recorded'])
                    self.assertIsNone(view.selection['selected_candidate'])
                    self.assertEqual(view.selection['candidate_disposition'],'defer_selection')
                    self.assertTrue(view.workflow['physical_acceptance']['terminal'])
                    self.assertFalse(view.workflow['physical_acceptance']['joint'])
                else:
                    self.assertEqual(view.selection['selected_candidate'],view.baseline)
                    self.assertNotEqual(view.latest_tested,view.selection['selected_candidate'])

    def test_ledger_and_recovery_agreement(self):
        from tools.platform_diagnosis_coordinator import recovery_status
        for _,_,store,ids in self.cases():
            for identity in ids:
                view=project_working_state(store,identity);session=store.session(identity)
                self.assertEqual(view.budgets['project'],store.remaining())
                self.assertEqual(view.budgets['role'],store.remaining(identity))
                self.assertEqual(view.budgets['phase'],store.phase_remaining(identity))
                self.assertEqual(view.budgets['spendable'],store.spendable(identity))
                self.assertEqual(view.recovery,recovery_status(session['state'],session['snapshot']['input']['policy']['model']))
                self.assertNotIn('decoder',encode(view.recovery))
                for capacity in view.budgets['spendable']['constraints']:
                    for key,value in view.budgets['spendable']['remaining'].items():
                        self.assertLessEqual(value,capacity['remaining'][key])

    def test_role_isolation_and_exact_handoff(self):
        store=Store(ROOT/'runs/stage354_milestone0_20261003/dual_context')
        ids=[r[0] for r in store.connect(True).execute('SELECT run_id FROM sessions') if r[0].endswith(('design','diagnostic'))]
        views=[project_working_state(store,i) for i in ids]
        for view,identity in zip(views,ids):
            state=store.session(identity)['state']
            expected={r['selector']['reference']['artifact_id'] for r in state['fact_catalog'].values()}
            self.assertEqual({r['artifact_id'] for r in view.evidence['permitted_references']},expected)
            self.assertEqual(view.evidence['scope'],state['fact_scope'])
        self.assertNotEqual(views[0].evidence['context_id'],views[1].evidence['context_id'])
        for field in ('baseline','latest_tested','selection','acceptance','prepared'):
            self.assertEqual(getattr(views[0],field),getattr(views[1],field))
        fixture=engineering_fixture(store,views[0])
        self.assertEqual(consume_handoff(store,views[0],fixture),fixture)
        with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):
            consume_handoff(store,views[1],fixture.model_copy(update=dict(working_state=dict(run_id=ids[1],contract=views[1].contract,version=views[1].version))))
        self.assertEqual(fixture.provenance,'engineering_fixture')
        self.assertIsNone(fixture.search_plan)

    def test_acceptance_sources_and_synthetic_change(self):
        store=Store(ROOT/'runs/stage354_milestone0_20261003/dual_context')
        feedback=read(store.root/'feedback.json');ref=feedback['execution']['configuration']
        config=store.artifact(ref);original=deepcopy(config)
        definitions=resolve_acceptance(config,ref)
        self.assertEqual(definitions['terminal']['value'],.01)
        self.assertEqual(definitions['holding']['duration']['value'],.05)
        self.assertEqual(definitions['holding']['position']['value'],.01)
        self.assertEqual(definitions['holding']['speed']['value'],.02)
        synthetic=deepcopy(config);effective=synthetic['effective']
        effective['task']['evaluator']['parameters']['data']['tolerance_m']=.123
        effective['policy']['controller']['parameters']['data']['settling'].update(window_s=.1,position_limit_m=.2,speed_limit_m_s=.3)
        changed=resolve_acceptance(synthetic,ref)
        self.assertEqual(changed['terminal']['value'],.123)
        self.assertEqual(changed['holding']['coverage']['expected_sample_count'],11)
        self.assertEqual(changed['holding']['position']['value'],.2)
        self.assertEqual(changed['holding']['speed']['value'],.3)
        del effective['policy']['controller']['parameters']['data']['settling']
        missing=resolve_acceptance(synthetic,ref)
        self.assertIsNone(missing['holding']['duration']['value'])
        self.assertTrue(missing['missing'])
        self.assertEqual(config,original)
        snapshot_definition=resolve_acceptance(dict(input=config['effective']),ref)
        self.assertEqual(snapshot_definition['terminal']['source']['pointer'],'/input/task/evaluator/parameters/data/tolerance_m')

    def test_feedback_and_comparison_use_resolver(self):
        from tools.diagnostic_revision import comparison_view
        store=Store(ROOT/'runs/stage354_milestone0_20261003/dual_context')
        identity=next(r[0] for r in store.connect(True).execute('SELECT run_id FROM sessions') if r[0].endswith('design'))
        state=store.session(identity)['state'];role=state['role_context']
        actual=comparison_view(role,deepcopy(state))
        self.assertEqual(actual['thresholds'],dict(terminal_error_m=.01,holding_max_error_m=.01,holding_max_speed_m_s=.02,holding_window_s=.05))
        result=role['improvement_feedback_content']['execution'];config=store.artifact(result['configuration'])['effective']
        synthetic=deepcopy(config)
        synthetic['task']['evaluator']['parameters']['data']['tolerance_m']=.123
        synthetic['policy']['controller']['parameters']['data']['settling'].update(window_s=.1,position_limit_m=.2,speed_limit_m_s=2.)
        source=dict(configuration=synthetic,execution_id=result['execution_id'],owner='fixture',manifest=result['configuration'],files={})
        with patch('extensions.tendon_family.control_evidence.ControlEvidence.read_file',return_value=[]):
            changed=structured_feedback(store,result,source)
        self.assertEqual(changed['terminal']['limit_m'],.123)
        self.assertAlmostEqual(changed['holding']['interval_s'][0],.25)
        self.assertEqual(changed['holding']['position_limit_m'],.2)
        self.assertEqual(changed['holding']['speed_limit_m_s'],2.)
        self.assertEqual(changed['acceptance_definition']['terminal']['source'],dict(
            reference=result['configuration'],pointer='/effective/task/evaluator/parameters/data/tolerance_m'))

    def test_two_parameter_builder_mapping(self):
        from tools.platform_tools import _candidate
        from tools.platform_registry import registry
        from schemas.platform import SessionInput
        from tools.diagnostic_improvement import actual_diff
        store=Store(ROOT/'runs/stage354_milestone0_20261003/dual_context')
        feedback=read(store.root/'feedback.json');ref=feedback['baseline_facts']['configuration']
        effective=store.artifact(ref)['effective']
        mappings=parameter_impacts(effective,reference=ref)
        for row in mappings['mapped']:
            self.assertTrue(row['implementation_supported']);self.assertTrue(row['authorized_parameter'])
            self.assertEqual(row['granted_range'],[0.,1.])
            changed=_candidate(SessionInput.model_validate(effective),{row['parameter']:.05},registry())
            self.assertEqual(actual_diff(effective,plain(changed)),[dict(pointer=row['effective_pointer'].removeprefix('/effective'),before=0.,after=.05)])
            self.assertEqual(plain(changed)['task'],effective['task'])
            self.assertEqual(plain(changed)['robot'],effective['robot'])
            self.assertIn('simulation.run',row['fresh_steps'])
            self.assertIn('TrajectoryWorkspace',row['reconstruct'][1])

    def test_unsealed_operation_and_unauthorized_installed_capability(self):
        source=Store(ROOT/'runs/stage353_milestone0_20261003/single_context')
        with TemporaryDirectory(dir=ROOT/'runs') as directory:
            fixture=Store(directory)
            with closing(source.connect(True)) as original,closing(sqlite3.connect(fixture.db)) as target:
                original.backup(target)
            with closing(sqlite3.connect(fixture.db)) as db:
                identity=next(r[0] for r in db.execute('SELECT run_id FROM sessions') if r[0].endswith('shared'))
                state=json.loads(db.execute('SELECT state FROM sessions WHERE run_id=?',(identity,)).fetchone()[0])
                state['unaccepted_draft']=dict(status='unaccepted',tool='diagnosis.submit',phase='revision',arguments={})
                db.execute('UPDATE sessions SET state=? WHERE run_id=?',(encode(state),identity))
                db.execute("UPDATE calls SET receipt=NULL,status='unknown' WHERE rowid=(SELECT min(rowid) FROM calls WHERE run_id=?)",(identity,))
                db.commit()
            before=fingerprint(fixture);view=project_working_state(fixture,identity)
            self.assertTrue(view.operations['unresolved'])
            self.assertEqual(view.products.unaccepted_draft['status'],'unaccepted')
            self.assertIsNone(view.products.accepted_revision)
            simulation=next(a for a in view.actions if a.tool=='simulation.run')
            self.assertTrue(simulation.installed);self.assertFalse(simulation.permitted)
            self.assertTrue(any('no frozen tool binding' in reason for reason in simulation.reasons))
            self.assertEqual(view.budgets['spendable'],fixture.spendable(identity))
            self.assertEqual(before,fingerprint(fixture))
            # A stale completion-stage record cannot seal an operation whose
            # authoritative call row is unresolved, including another executor.
            with closing(sqlite3.connect(fixture.db)) as db:
                db.execute("UPDATE calls SET receipt=NULL,status='unknown' WHERE request_id='complete-simulation'")
                db.commit()
            unsealed=project_working_state(fixture,identity)
            self.assertFalse(unsealed.workflow['computation_complete'])
            self.assertEqual(unsealed.operations['completed_stages']['simulation']['status'],'unresolved')
            gc.collect()
