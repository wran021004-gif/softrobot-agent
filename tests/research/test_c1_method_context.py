"""Read-only C1 archive checks; no Provider, Store writes or scientific workers."""
from copy import deepcopy
import json
from pathlib import Path
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools.platform_store import plain
from tools.research import task_constraints as methods
from tools.research.research_context import compact_scientific_delivery, mathematics_authorization

ROOT=Path(__file__).resolve().parents[2]
ARCHIVE=ROOT/'evidence/mujoco_c1_autonomous/immutable_artifacts.tar.gz'


def encoded(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf8')


class C1Archive:
    """Test fixture over the existing export, with persistence forbidden."""
    def __init__(self):
        self.archive=tarfile.open(ARCHIVE)
        self.snapshot=json.load(self.archive.extractfile(next(m for m in self.archive.getmembers() if m.name.startswith('snapshot/'))))

    def artifact(self,ref,raw=False):
        ref=plain(ref);suffix='.json' if ref.get('media_type','application/json')=='application/json' else '.bin'
        body=self.archive.extractfile('artifacts/'+ref['artifact_id']+suffix).read()
        return body if raw else json.loads(body)

    def host(self,events=None):
        events=self.snapshot['events'] if events is None else events
        s=deepcopy(self.snapshot['session']['state'])
        published={r['artifact_id'] for e in events for r in e['outputs']}
        for key in ('results','analysis_results','physical_replays','plans'):
            s[key]=[r for r in s[key] if r['artifact_id'] in published]
        s.update(research_status='ready',success_gate=None,selected=None,pending=None,
            mathematical_evaluations=len(s['analysis_results']))
        store=Mock();store.artifact.side_effect=self.artifact
        store.session.return_value=dict(state=s)
        store.events.return_value=events;store.remaining.return_value=deepcopy(self.snapshot['ledger'])
        store.transaction.side_effect=AssertionError('READ_ONLY_ARCHIVE_NO_WRITES')
        store.reserve.side_effect=AssertionError('NO_SCIENTIFIC_OR_PROVIDER_ADMISSION')
        store.connect.side_effect=ValueError('ARCHIVED_FIXTURE_HAS_NO_LIVE_SQLITE')
        return SimpleNamespace(store=store,run_id=self.snapshot['session']['run_id']),s

    def requests(self):
        rows=[]
        for i,e in enumerate(self.snapshot['events']):
            if e['kind']!='r3_request':continue
            meta=self.artifact(e['outputs'][0])
            if meta['purpose']!='conversation':continue
            wire=self.artifact(meta['request']);tail=wire['messages'][-1]
            assert tail['content'].startswith('CURRENT_RESEARCH_PACKET\n')
            packet=json.loads(tail['content'].split('\n',1)[1])
            rows.append((e,meta,wire,packet,self.snapshot['events'][:i]))
        return rows

    def project(self,packet,events):
        after=deepcopy(packet);host,s=self.host(events)
        s['count_closeout']=packet['research']['budget']['closeout']['active']
        candidate=packet['research']['mathematical_capabilities']['candidate']
        after['research']['mathematical_capabilities']=methods.mathematical_catalog(methods.mathematical_method_view(host,candidate))
        after['research']['mathematics_authorization']=mathematics_authorization(host,s)
        latest=after['research'].get('latest_scientific_feedback') or {}
        ref=latest.get('reference')
        if ref and self.artifact(ref).get('control_schedule_reference'):
            from tools.research.analysis import compact_result
            latest['control_handoff']=compact_result(self.artifact(ref),ref)['control_handoff']
        after['research']=compact_scientific_delivery(after['research'])
        return after


def context_measurement(fixture):
    """Actual wire baseline; change only its L0 tail, never SDK history/reasoning."""
    rows=fixture.requests()
    nmpc=next(r for r in rows if r[3]['research']['latest_reports'])
    native=next(r for r in rows if any('mathematics' in f for report in r[3]['research']['latest_reports'] for f in report['findings']))
    selected=[('initial',rows[0]),('after_nmpc',nmpc),('after_native',native),('before_select',rows[-1])]
    result=[]
    for label,(event,meta,wire,packet,events) in selected:
        assert len(encoded(wire))==meta['input_bytes']
        after=fixture.project(packet,events);new_wire=deepcopy(wire)
        new_wire['messages'][-1]['content']='CURRENT_RESEARCH_PACKET\n'+json.dumps(after,separators=(',',':'))
        parts=dict(fixed_instructions=0,history_assistant=0,history_reasoning=0,history_tool_feedback=0,history_other=0,
            dynamic_tail=len(encoded(wire['messages'][-1])),tool_schema=len(encoded(wire['tools'])))
        for message in wire['messages'][:-1]:
            clean=deepcopy(message);clean.pop('reasoning_content',None)
            if message['role']=='system':parts['fixed_instructions']+=len(encoded(message))
            elif message['role']=='assistant':
                parts['history_assistant']+=len(encoded(clean));parts['history_reasoning']+=len(encoded(message))-len(encoded(clean))
            else:parts['history_tool_feedback' if message['role']=='tool' else 'history_other']+=len(encoded(message))
        parts['envelope_and_separators']=meta['input_bytes']-sum(parts.values())
        from tools.research.provider_context import capacity_estimate
        provider=fixture.snapshot['session']['state']['spec']['runtime']['provider']
        estimates=[capacity_estimate(encoded(w),provider) for w in (wire,new_wire)]
        sections=lambda p:{k:len(encoded(v)) for k,v in p['research'].items()}
        result.append(dict(boundary=label,request_id=event['request_id'],original_wire_bytes=meta['input_bytes'],
            equivalent_wire_bytes=len(encoded(new_wire)),original_L0_bytes=len(encoded(packet)),new_L0_bytes=len(encoded(after)),
            original_L0_report_format_bytes=len(json.dumps(packet,ensure_ascii=False).encode()),parts=parts,
            offline_input_estimates=[e['input_estimate'] for e in estimates],offline_estimate_method=estimates[0]['method'],
            original_research_sections=sections(packet),new_research_sections=sections(after),
            history_and_schema_unchanged=(new_wire['messages'][:-1]==wire['messages'][:-1] and new_wire['tools']==wire['tools'])))
    return dict(scope='Four actual C1 wires. Counterfactual changes only the current dynamic L0; history, reasoning, tool Schema and fixed instructions unchanged. No new Provider token usage measured.',boundaries=result)


class MethodContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c1=C1Archive()

    @classmethod
    def tearDownClass(cls):cls.c1.archive.close()

    def test_method_planning_and_execution_applicability_remain_distinct(self):
        from schemas.platform import SessionInput
        from tools.research.contracts import AnalysisRequest
        from tools.research.native_analysis import assessment,applicability
        host,s=self.c1.host();ref=s['reference_candidate'];cfg=host.store.artifact(ref)['configuration']
        row=methods.mathematical_method_view(host,ref)['methods']['mujoco_direct_control_v1']
        self.assertEqual(row['planning_status'],'requires_parameters');self.assertTrue(row['kernel_supported'])
        self.assertIn('control_optimization.source',row['missing'])
        raw=host.store.artifact(s['analysis_results'][0]);q=AnalysisRequest.model_validate(raw['requested_operation'])
        req=methods.describe_analysis_requirements(cfg,{})
        fit=lambda query:applicability(req,query,assessment(SessionInput.model_validate(cfg),req),raw['native_dynamics']['initial_state'])
        self.assertEqual(fit(q)['status'],'applicable')
        bad_request=deepcopy(raw['requested_operation'])
        bad_request['control_optimization']['settings'].update(correction_window_s=[.3,.35],knots_s=[.3,.34])
        bad=AnalysisRequest.model_validate(bad_request)
        self.assertEqual(fit(bad)['status'],'not_applicable')
        missing=q.model_copy(update=dict(control_optimization=None))
        self.assertEqual(fit(missing)['status'],'not_applicable')
        missing_request=deepcopy(raw['requested_operation']);missing_request['control_optimization']=None
        with self.assertRaises(ValueError):AnalysisRequest.model_validate(missing_request)
        tracking=deepcopy(cfg);tracking['task']=json.loads((ROOT/'tasks/tracking_linear_development.json').read_text(encoding='utf8'))['task']
        def plan(configuration,protocol=s['spec']['analysis_protocol']):
            requirements=methods.describe_analysis_requirements(configuration,{})
            return next(r for r in methods.analysis_capabilities(configuration,requirements,protocol,remaining_evaluations=10) if r['operation']=='mujoco_direct_control_v1')
        self.assertEqual(plan(tracking)['planning_status'],'unsupported')
        loaded=deepcopy(cfg);loaded['task']['environment']['data']['external_forces']=[dict(entity='payload',force_n=[.1,0.,0.],start_s=0.,end_s=.35)]
        self.assertEqual(plan(loaded)['planning_status'],'unsupported')
        protocol=deepcopy(s['spec']['analysis_protocol']);protocol['period_s']=.02
        self.assertEqual(plan(cfg,protocol)['planning_status'],'unsupported')

    def test_authorization_budget_and_known_c1_approval_projection(self):
        host,s=self.c1.host();ref=s['reference_candidate'];before=deepcopy(s)
        self.assertTrue(mathematics_authorization(host,s)['registered_study_scope_authorized'])
        s['success_gate']=dict(synthetic_existing_pass=True)
        self.assertEqual(methods.mathematical_method_view(host,ref)['methods']['mujoco_direct_control_v1']['planning_status'],'blocked')
        s['success_gate']=None
        s['mathematical_evaluations']=s['spec']['budgets']['mathematical_evaluations']
        self.assertEqual(methods.mathematical_method_view(host,ref)['methods']['mujoco_direct_control_v1']['planning_status'],'insufficient_budget')
        s['spec']['capabilities'].remove('analysis')
        self.assertEqual(methods.mathematical_method_view(host,ref)['methods']['mujoco_direct_control_v1']['planning_status'],'unauthorized')
        s.update(before);host.store.events.return_value=[]
        self.assertEqual(methods.mathematical_method_view(host,ref)['methods']['mujoco_direct_control_v1']['planning_status'],'unauthorized')
        host.store.transaction.assert_not_called();host.store.reserve.assert_not_called()

    def test_four_frozen_contexts_preserve_science_and_reduce_only_dynamic_input(self):
        data=context_measurement(self.c1)
        self.assertEqual(len(data['boundaries']),4)
        for row in data['boundaries']:
            self.assertTrue(row['history_and_schema_unchanged']);self.assertLess(row['equivalent_wire_bytes'],row['original_wire_bytes'])
        for _,_,_,packet,events in self.c1.requests():
            before=deepcopy(packet);after=self.c1.project(packet,events)
            for k in ('task','task_identity','budget','stop_result_index','available_research_actions','best_valid','research_intent'):
                self.assertEqual(after['research'][k],packet['research'][k],k)
            for old,new in zip(packet['research']['latest_reports'],after['research']['latest_reports']):
                self.assertEqual(old['interpretation_sources'],[source for interpretation in old['interpretations'] for source in interpretation['sources']])
                for key in ('interpretations','scope','limitations','unresolved','comparisons'):
                    self.assertEqual(old[key],new[key])
                for x,y in zip(old['findings'],new['findings']):
                    self.assertEqual(x['metrics'],y['metrics']);self.assertEqual(x.get('mathematics'),y.get('mathematics'))
                    diag=(y.get('recorded_summary') or {}).get('recorded_control_diagnostics')
                    if diag and diag.get('relevant_updates'):
                        self.assertTrue(diag['full_observations_query'])
                        self.assertTrue(all(r['optimization_raw_status']=='Maximum_Iterations_Exceeded' and r['plan_accepted'] for r in diag['relevant_updates']))
            self.assertEqual(packet,before)

    def test_observed_navigation_and_native_handoff_errors(self):
        from tools.research.core import read_evidence
        from tools.research.analysis import compact_result
        from tools.research.agent import error_feedback
        host,s=self.c1.host();ref=s['reference_candidate']
        queries=[dict(reference=ref,view='fields',fields=['candidate_index']),dict(reference=s['physical_replays'][0],view='fields',fields=['task_passed'])]
        for query,key in zip(queries,['derived_view_query','acceptance_query']):
            with self.assertRaises(KeyError) as caught:read_evidence(host,query,record_read=False)
            self.assertIn(key,caught.exception.evidence_navigation)
        raw=host.store.artifact(s['analysis_results'][0]);handoff=compact_result(raw,s['analysis_results'][0])['control_handoff']
        self.assertEqual(handoff['request_fields']['physical_replay']['source'],raw['control_schedule_reference'])
        self.assertEqual(handoff['task_acceptance'],'unmeasured');self.assertNotIn('missing',handoff)
        for marker in ['NATIVE_ANALYSIS_REQUIRES_EXACT_STATE_OR_FROZEN_INITIALIZATION','DISPOSITION_REQUIRES_EXACT_ACTUAL_READ','explicit evidence_read of this completed evaluation required','ACTION_REQUIRES_ONLY_physical_replay']:
            use=dict(name='research_plan',input=dict(action='physical_replay'))
            with patch('tools.research.agent.record',return_value=ref):feedback=error_feedback(host,use,ValueError(marker),s)
            self.assertTrue(feedback['field']);self.assertFalse(feedback['scientific_execution_started'])
            self.assertGreater(len(feedback['expected']),len(marker))
