"""Concrete v5 regression risks using the actual Stage 3.53 saved products."""
from copy import deepcopy
import gc
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from tools.state_io import read
from tools.platform_store import plain
from tools.diagnostic_revision import ensure_aliases,resolve_aliases,alias_errors,correct,materialize
from tools.diagnostic_reference_adapter import ScopedReferenceAdapter
from tools.platform_models import payload_for,ToolProtocolError
from schemas.diagnostic_revision import CompactRevision
from schemas.platform_handoff import InventoryDiagnosisSubmission,InventoryGap
from tools.diagnostic_inventory import validate_gaps
from examples.stage354_milestone0 import ROOT,MilestoneWorkflow,import_suffix,SUFFIX_LIMITS


class ReferenceTests(TestCase):
    def state(self,scope='one'):
        return dict(fact_scope={'project':scope},fact_catalog={
            h:dict(handle=h,field='terminal_error_m',units='m',selector=dict(reference={'artifact_id':h,'media_type':'application/json'},pointer='/value',value=v),value=v)
            for h,v in [('full-one',.1),('full-two',.2)]})

    def test_stable_exact_aliases_and_scope(self):
        state=self.state();original=deepcopy(ensure_aliases(state))
        state['fact_catalog']=dict(reversed(list(state['fact_catalog'].items())))
        self.assertEqual(ensure_aliases(state),original)
        restored=json.loads(json.dumps(state));self.assertEqual(resolve_aliases(restored,{'x':['F1']}),{'x':[state['fact_catalog']['full-one']['selector']]})
        restored['fact_catalog']['third']=dict(state['fact_catalog']['full-two'],handle='third')
        self.assertEqual(ensure_aliases(restored)['aliases']['F1'],'full-one')
        legacy=self.state();legacy['reference_interface']=dict(version='1.0.0',scope=legacy['fact_scope'],aliases={'F001':'full-one'})
        self.assertEqual(ensure_aliases(legacy)['aliases'],{'F001':'full-one','F002':'full-two'})
        self.assertTrue(alias_errors(legacy,{'x':['F1']}))
        self.assertEqual(len(alias_errors(restored,{'x':['F000','F999'],'y':['full-one']})),3)
        other=self.state('other');other['fact_catalog']={};self.assertTrue(alias_errors(other,{'x':['F001']}))
        restored['fact_scope']={'project':'other'}
        with self.assertRaisesRegex(ValueError,'SCOPE_CHANGED'):ensure_aliases(restored)

    def test_one_field_correction_preserves_rest(self):
        draft={'report':{'facts':[{'references':['bad'],'statement':'unchanged'}]},'recommendation':'unchanged'}
        fixed=correct(draft,{'corrections':[{'path':'/report/facts/0/references/0','value':'F001'}]})
        expected=deepcopy(draft);expected['report']['facts'][0]['references']=['F001'];self.assertEqual(fixed,expected)
        self.assertEqual(draft['report']['facts'][0]['references'],['bad'])
        explicit=correct(draft,{'corrections':[{'path':'/arguments/report/facts/0/references/0','value':'F001'}]})
        self.assertEqual(explicit,fixed)
        with self.assertRaisesRegex(ValueError,'MISSING'):correct(draft,{'corrections':[{'path':'/invented','value':1}]})

    def test_capability_authorization_and_missing_data(self):
        for status in ('capability_unavailable','execution_unauthorized'):
            validate_gaps([InventoryGap(status=status,needed='Additional full trajectory solve',basis='Not in this phase grant')],{'entries':[]})
        with self.assertRaisesRegex(ValueError,'SOURCE_REQUIRED'):
            validate_gaps([InventoryGap(status='not_retained',needed='Data',basis='Absent')],{'entries':[]})


class SavedSuffixTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(dir=ROOT/'runs');cls.config=read(ROOT/'examples/stage354_experiment.json')
        cls.config['evidence_directory']=str(Path(cls.temp.name)/'export')
        cls.w=MilestoneWorkflow(Path(cls.temp.name)/'single_context','single_context',experiment=cls.config)
        cls.w.limits=SUFFIX_LIMITS;cls.w.numerical_limits=dict(local_solves=0,prediction_evaluations=0)
        cls.w.prepare({'offline_fixture':True})
        cls.feedback=import_suffix(cls.w,Path(cls.config['historical_workflows'])/'single_context')
        cls.retained=[dict(reference=cls.w.chain['feedback'],result=cls.feedback['result'],receipt=cls.feedback['receipt'],result_content=cls.w.store.artifact(cls.feedback['result']))]
        from tools.diagnostic_facts import handover
        handover(cls.w.host('diagnostic'),cls.w.chain['feedback'],cls.feedback,origin={'fixture':True},kind='campaign_comparison')
        with patch('tools.diagnostic_workflow.run_loop',side_effect=RuntimeError('capture')):
            try:cls.w.phase('revision','diagnosis_report','revised_report',previous_report=cls.w.chain['initial_report'],
                previous_report_content=cls.w.store.artifact(cls.w.chain['initial_report']),check_feedback=cls.retained,improvement_feedback_content=cls.feedback)
            except RuntimeError as exc:
                if str(exc)!='capture':raise

    @classmethod
    def tearDownClass(cls):gc.collect();cls.temp.cleanup()

    def adapter(self):
        a=ScopedReferenceAdapter();payload=payload_for(self.w.host('diagnostic'),a);return a,payload

    def revision(self,a):
        initial=self.w.store.artifact(self.w.chain['initial_report']);state=a.fact_state
        alias=next(alias for alias,h in ensure_aliases(state)['aliases'].items() if state['fact_catalog'][h]['selector']['reference']==self.feedback['result']
            and state['fact_catalog'][h]['selector']['pointer']=='/detail/terminal_error_m')
        return dict(changes=[dict(kind='hypothesis',identifier=initial['report']['attribution'][0]['cause'],disposition='weakened',
            supporting_fact_ids=['candidate_terminal'],reason='Actual candidate evidence limits the initial interpretation.')],
            new_facts=[dict(fact_id='candidate_terminal',statement='Candidate terminal error as recorded.',references=[alias])],
            new_limitations=['One bounded experiment cannot identify a dominant cause.'],recommendation='Defer adoption.',rationale='Consider actual candidate evidence.')

    def test_saved_materialization_and_exact_profile(self):
        a,payload=self.adapter();revision=self.revision(a);initial=self.w.store.artifact(self.w.chain['initial_report'])
        output=a.resolve_business('diagnosis.submit',revision)
        validated=InventoryDiagnosisSubmission.model_validate(output)
        self.assertEqual(output['report']['facts'][:-1],initial['report']['facts'])
        for k,v in initial['fact_selectors'].items():self.assertEqual(output['fact_selectors'][k],v)
        from tools.platform_handoff import submit
        from types import SimpleNamespace
        host=self.w.host('diagnostic')
        ctx=SimpleNamespace(store=host.store,run_id=host.run_id,host=host,artifact=host.store.artifact)
        with patch('tools.platform_handoff.transition',return_value='accepted'):
            self.assertEqual(submit(ctx,validated),'accepted')
        context=json.loads(payload['messages'][1]['content'])['role_context']
        self.assertIn('comparison_view',context)
        # The working-state observation retains canonical registry IDs; native
        # invocation instructions and advertised function names still agree.
        self.assertNotIn('diagnosis.submit',context['instructions'])
        self.assertIn('diagnosis_submit',{t['function']['name'] for t in payload['tools']})
        self.assertNotIn('query the needed evidence',payload['messages'][1]['content'])
        self.assertLess(len(json.dumps(payload).encode()),400000)

    def test_collect_invalid_fields_and_references_then_patch(self):
        a,_=self.adapter();draft=self.revision(a);draft['new_facts'][0]['references']=['F000','F99999'];draft['unexpected']='field';draft['recommendation']=''
        with self.assertRaises(ToolProtocolError) as caught:a.resolve_business('diagnosis.submit',draft)
        self.assertGreaterEqual(len(caught.exception.issues),4)
        stored=self.w.store.session(a.context_id)['state']['unaccepted_draft'];self.assertEqual(stored['arguments'],draft)
        a,payload=self.adapter();good=self.revision(a)
        fixed=a.resolve_business('diagnosis.submit',{'corrections':[
            {'operation':'remove','path':'/unexpected'}, {'path':'/recommendation','value':'Defer adoption.'},
            {'path':'/new_facts/0/references','value':good['new_facts'][0]['references']}]})
        self.assertEqual(fixed['report']['facts'][-1]['statement'],draft['new_facts'][0]['statement'])
        self.assertEqual(self.w.store.remaining()['used']['model_calls'],0)

    def test_real_stage353_typo_still_rejected(self):
        review=read(ROOT/'evidence/stage353_milestone0_20261003/single_context_protocol_review.json')
        a,_=self.adapter()
        self.assertTrue(alias_errors(a.fact_state,{'x':[review['submitted_handle']]}))
        self.assertTrue(alias_errors(a.fact_state,{'x':[review['available_handle']]}))
        # Historical long handles remain readable through the historical interface.
        from tools.diagnostic_facts import resolve_handles
        state=read(ROOT/'evidence/stage353_milestone0_20261003/single_context/evidence_contexts.json')['shared']
        self.assertEqual(len(resolve_handles(state,{'x':[review['available_handle']]} )['x']),1)

    def test_final_selection_binding(self):
        a,_=self.adapter();a.wire={'design.respond_diagnosis':__import__('schemas.diagnostic_revision',fromlist=['WireFinalDecision']).WireFinalDecision}
        fields=dict(disposition='defer',reasoning='Candidate feedback does not justify replacement.',next_action='finish',candidate_disposition='retain_baseline',selected_candidate='baseline')
        result=a.resolve_business('design.respond_diagnosis',fields)
        self.assertEqual(result['selected_candidate'],self.feedback['baseline_facts']['candidate'])
        fields['selected_candidate']='candidate'
        with self.assertRaisesRegex(ValueError,'MISMATCH'):a.resolve_business('design.respond_diagnosis',fields)

    def test_native_decode_and_unknown_name(self):
        from schemas.platform import ModelResponse
        a,payload=self.adapter();args=self.revision(a)
        response=ModelResponse(raw={'choices':[{'message':{'tool_calls':[{'type':'function','function':{'name':'diagnosis_submit','arguments':json.dumps(args)}}]}}]})
        bindings=self.w.store.session(a.context_id)['snapshot']['input']['policy']['tool_bindings']
        result=a.decode(response,0,bindings,payload['tools']);self.assertEqual(result['tool_id'],'diagnosis.submit')
        response.raw['choices'][0]['message']['tool_calls'][0]['function']['name']='diagnosis.submit'
        with self.assertRaises(ToolProtocolError):a.decode(response,0,bindings,payload['tools'])

    def test_missing_profile_reference_is_one_actionable_preflight_error(self):
        a,_=self.adapter();draft=self.revision(a)
        alias=next(k for k,h in ensure_aliases(a.fact_state)['aliases'].items()
            if a.fact_state['fact_catalog'][h]['selector']['pointer']=='/campaign_comparison/candidate/terminal_error_m')
        draft['new_facts'][0]['references']=[alias]
        with self.assertRaises(ToolProtocolError) as caught:a.resolve_business('diagnosis.submit',draft)
        problem=next(e for e in caught.exception.issues if e['path']=='new_facts.references')
        self.assertTrue(problem['available_aliases'])
        for ref in problem['available_aliases']:
            self.assertEqual(resolve_aliases(a.fact_state,{'x':[ref]})['x'][0]['reference'],self.feedback['result'])

    def test_preserved_dual_draft_root_patch_offline_only(self):
        # Regression of the actual paid failure, never mutate or resume its store.
        from tools.platform_store import Store
        from types import SimpleNamespace
        directory=ROOT/'runs/stage354_milestone0_20261003/suffix_dual_context'
        if not (directory/'outcome.json').exists():self.skipTest('Paid failure fixture not yet available')
        store=Store(directory);freeze=read(directory/'freeze.json');identity=freeze['hosts']['diagnostic']
        state=store.session(identity)['state'];before=deepcopy(state)
        a=ScopedReferenceAdapter();a.fact_state=deepcopy(state);a.role=a.fact_state['role_context'];a.phase='revision'
        a.wire={'diagnosis.submit':CompactRevision};a.fixed=a.role['native_fixed'];a.store=store
        event=next(e for e in store.events(identity) if e['kind']=='model_raw_response' and e['request_id']=='model-3')
        raw=store.artifact(event['outputs'][0])['raw'];args=json.loads(raw['choices'][0]['message']['tool_calls'][0]['function']['arguments'])
        self.assertTrue(all(c['path'].startswith('/arguments/') for c in args['corrections']))
        with patch.object(a,'retain'):
            result=a.resolve_business('diagnosis.submit',args)
        validated=InventoryDiagnosisSubmission.model_validate(result)
        from tools.platform_handoff import submit
        ctx=SimpleNamespace(store=store,run_id=identity,artifact=store.artifact)
        with patch('tools.platform_handoff.transition',return_value='offline-valid'):
            self.assertEqual(submit(ctx,validated),'offline-valid')
        self.assertEqual(store.session(identity)['state'],before)

    def test_z_pending_tool_can_complete_without_replenishing_model_limit(self):
        from tools.platform_models import run_loop
        from tools.platform_store import zero
        a,payload=self.adapter();host=self.w.host('diagnostic');draft=self.revision(a)
        arguments={**a.resolve_business('diagnosis.submit',draft),**a.fixed['diagnosis.submit']}
        cost={**zero(),'model_calls':4,'wall_s':1.}
        row,_=host.store.reserve(host.run_id,'offline-four-provider-attempts','fixture','fixture',cost)
        host.store.complete(row,dict(request_id='offline-four-provider-attempts',execution_id=row['execution_id'],caller='fixture',
            tool_id='fixture.provider',tool_version='1.0.0',execution_status='completed',charged=zero()),elapsed=1.)
        before=host.store.remaining()['used'];phase=host.store.phase_remaining(host.run_id)
        self.assertEqual(phase['remaining']['model_calls'],0)
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];state.update(turn=4,protocol_corrections_used=2,protocol_corrections_consecutive=2)
            state['pending']=dict(decision=dict(request_id='model-3-tool',tool_id='diagnosis.submit',tool_version='2.0.0',
                arguments=arguments,reason='Offline saved-response normalization fixture',evidence=[]),parent=row['parent_id'],input=self.w.chain['initial_report'])
            host.store.update_state(db,host.run_id,state,'paused')
        a.respond=lambda *args: self.fail('No fifth revision provider call is permitted')
        run_loop(host,a)
        after=host.store.remaining()['used'];self.assertEqual(after['model_calls'],before['model_calls'])
        self.assertEqual(after['tool_calls'],before['tool_calls']+1)
        state=host.store.session(host.run_id)['state'];self.assertIn('diagnosis_report',state['handoffs'])
        self.assertEqual(state['protocol_corrections_used'],2);self.assertEqual(state['protocol_corrections_consecutive'],0)
        self.assertEqual(host.store.phase_remaining(host.run_id)['limit'],phase['limit'])
