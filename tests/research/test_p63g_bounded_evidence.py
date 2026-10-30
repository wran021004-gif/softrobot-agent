"""G0 read/SELECT regressions; Mock replies and perfect motion are fabricated."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.platform_host import Host
from tools.platform_store import plain
from tools.research import core,reporter,agent
from tools.research.config import ROOT,evidence_feedback_limit
from tools.research.contracts import PhysicalReplayRequest
from tools.research.evidence_views import acceptance_certificate
from tools.research.feedback import eligibility
from tools.research.physical_replay import dispatch,seed_control
from tools.research.contracts import ControlSeedRequest
from tools.research.research_context import read_coverage
from tools.research.state import state,update,save
from tools.state_io import read
from tests.research.test_p63c2_scientific_intent import question_host
from tests.research.test_p63a_math_interface import generate,t1_request,offline_dispatch
from tests.research.test_cross_task_integration import perfect_tracking_worker
from tests.research.test_information_flow import packet
from tests.research.test_recent_round_tools import run_fixture

POLICY=dict(version='bounded_scientific_evidence_v1')


def bounded_host():
    h=question_host();s=state(h);spec=deepcopy(s['spec'])
    spec['research_decisions']['evidence_read_policy']=POLICY
    spec['capabilities']=list(dict.fromkeys([*spec['capabilities'],'physical_replay','control_correction']))
    spec['allowed_plan_actions']=list(dict.fromkeys([*spec['allowed_plan_actions'],'physical_replay','select']))
    spec['budgets']['physical_launches']=20;spec['physical_replay_limit']=None
    spec['fidelity_policy']=read(ROOT/'configs/research/study_p63f2_m3_result_feedback_sol.json')['fidelity_policy']
    spec['final_evaluation_identity']='OFFLINE frozen fidelity fixture'
    update(h,spec=spec)
    return h


class BoundedEvidenceTests(unittest.TestCase):
    def setUp(self):
        for target in ('tools.service_execution._run_contained','extensions.tendon_family.mujoco_analysis.NativeModel','mujoco.mj_step','tools.research.provider.load_credential'):
            p=patch(target,side_effect=AssertionError('NO_REAL_PROVIDER_WORKER_OR_PHYSICS'));p.start();self.addCleanup(p.stop)

    def physical(self,h):
        candidate=generate(h)
        source=seed_control(h,ControlSeedRequest(candidate=candidate,method='baseline'))['source']
        with patch('tools.research.physical_replay.guard'),patch('tools.service_execution._run_contained',side_effect=perfect_tracking_worker):
            result=dispatch(h,PhysicalReplayRequest(candidate=candidate,source=source),'offline-g0-replay')
        return candidate,result['reference']

    def test_real_f2_large_result_bounded_on_actual_mock_wire_and_old_contract_unchanged(self):
        audit=read(ROOT/'docs/research/p63f2_live_audit.json')
        original=Host(audit['store'],audit['study_id']);connect=original.store.connect
        original.store.connect=lambda readonly=False:connect(True)
        before=original.store.db.stat().st_mtime_ns
        rawref=audit['results'][0]['reference'];raw=original.store.artifact(rawref)
        h=bounded_host()
        # Preserve original bytes/identity in an isolated OFFLINE fixture. This is
        # never the G1 Store or a claimed current-Study scientific computation.
        for ref in (raw['candidate'],raw['native_dynamics']['optimized_schedule']['provenance']['source'],raw['control_schedule_reference']):
            self.assertEqual(save(h,original.store.artifact(ref),'offline_g0_original_source'),ref)
        self.assertEqual(save(h,raw,'offline_g0_F2_read_fixture'),rawref)
        report=plain(reporter.assemble(h,[rawref]));report['interpretations']=[dict(kind='unresolved_question',text='OFFLINE source-linked interpretation remains visible.',sources=[dict(reference=rawref,pointer='/nonlinear_capability')])]
        reporter._save(h,report,status='available')
        wires=run_fixture(h,[('evidence_read',dict(reference=rawref,view='full')),None])
        event=next(e for e in h.store.events(h.run_id) if e['kind']=='model_original_tool_feedback')
        output=json.loads(h.store.artifact(event['outputs'][0])['result']['content'][0]['text'])
        self.assertEqual(output['status'],'raw_result_not_delivered')
        self.assertLess(len(json.dumps(output).encode()),evidence_feedback_limit(state(h)['spec']))
        self.assertNotIn('native_dynamics',output)
        self.assertTrue(output.get('fixed_facts') or output.get('fixed_facts_at'))
        self.assertLess(len(json.dumps(wires[1],separators=(',',':')).encode()),1048576)
        self.assertEqual(packet(wires[1])['reporter_findings'][0]['interpretations'][0]['text'],report['interpretations'][0]['text'])
        self.assertFalse(read_coverage(h)[0]['full_artifact'])
        self.assertNotIn(rawref,state(h).get('evaluation_reads',[]))
        self.assertEqual(core.read_tool_evidence(original,dict(reference=rawref,view='full'),record_read=False),raw)
        self.assertEqual(original.store.db.stat().st_mtime_ns,before)

    def test_acceptance_certificate_actual_delivery_then_formal_select(self):
        h=bounded_host();candidate,ref=self.physical(h)
        original=deepcopy(h.store.artifact(ref));certificate=acceptance_certificate(h,ref)
        self.assertTrue(certificate['complete_acceptance_view'],certificate)
        self.assertEqual(certificate['acceptance'],original['acceptance'])
        self.assertLess(len(json.dumps(certificate).encode()),evidence_feedback_limit(state(h)['spec']))
        self.assertFalse(eligibility(h,ref,selection=True)['eligible'])
        # Generating/locally returning a certificate alone does not prove delivery.
        core.read_tool_evidence(h,dict(reference=ref,view='acceptance_certificate'))
        self.assertFalse(eligibility(h,ref,selection=True)['eligible'])
        select=dict(action='select',selected_execution=ref,hypothesis='OFFLINE exact passing result can be selected.',
            expected_observation='All original conditions pass.',weakening_observation='Any original admission fails.',
            fixed_conditions='Exact independently evaluated fixture.',stopping_condition='Select this exact passing result.',
            interpretation='Fabricated perfect motion only; not research evidence.',supporting_evidence=[ref],
            decision=dict(hypothesis_id='offline-g0-select',research_intent='SELECT',selected_method='physical_replay',
                selected_candidate=candidate,claimed_inference='observed_task_pass',requested_budget=0))
        wires=run_fixture(h,[('evidence_read',dict(reference=ref,view='acceptance_certificate')),
            ('research_route',dict(tool='research_plan',action='select')),('research_plan',select)])
        rows=read_coverage(h);self.assertTrue(rows[0]['formal_acceptance_view']);self.assertFalse(rows[0]['full_artifact'])
        self.assertEqual(state(h)['selected'],ref)
        self.assertEqual(state(h)['research_status'],'stopped')
        self.assertEqual(h.store.artifact(ref),original)
        self.assertIn('acceptance_certificate',json.dumps(wires[0]['tools']))
        self.assertTrue(all(len(json.dumps(w).encode())<1048576 for w in wires))

    def test_invalid_failed_historical_wrong_fidelity_cannot_select(self):
        h=bounded_host();_,ref=self.physical(h);raw=h.store.artifact(ref)
        variants=[]
        for label in ('failed','invalid','historical','wrong_fidelity'):
            value=deepcopy(raw)
            if label=='failed':
                value['acceptance']['accepted']=False;value['acceptance']['status']='valid_failure'
                value['acceptance']['components']['holding_speed'].update(value=1.,passed=False)
            elif label=='invalid':value['acceptance']['components'].pop('holding_coverage')
            elif label=='historical':value['owning_study']='other-study';value['imported_historical_evidence']=True
            else:value['profile_identity']='wrong-profile'
            other=save(h,value,'offline_g0_'+label);update(h,physical_replays=[*state(h)['physical_replays'],other])
            view=acceptance_certificate(h,other)
            self.assertEqual(view['acceptance'],value['acceptance'])
            # Explicit marker is still insufficient; every original gate remains.
            update(h,evaluation_reads=[other])
            self.assertFalse(eligibility(h,other,selection=True)['eligible'])
            variants.append((label,other))
        run_fixture(h,[*[('evidence_read',dict(reference=ref,view='acceptance_certificate')) for _,ref in variants],None],limit=len(variants)+1)
        for label,ref in variants:
            choice=eligibility(h,ref,selection=True)
            self.assertFalse(choice['eligible'],(label,choice))
            if label=='historical':self.assertTrue(any('historical' in r for r in choice['reasons']))
            if label in ('failed','wrong_fidelity'):self.assertTrue(any('did not pass' in r for r in choice['reasons']))
        schema=agent.evidence_query_schema({})
        self.assertNotIn('acceptance_certificate',schema['properties']['view']['enum'])

    def test_stop_uses_all_result_references_without_reading_raw_arrays(self):
        h=bounded_host();c=generate(h);ref=offline_dispatch(h,t1_request(h,c),'offline-g0-math')['reference']
        query=dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/all_fresh_results')
        stop=dict(action='stop',hypothesis='OFFLINE bounded fixture closure.',expected_observation='Result remains a finite model diagnostic.',
            weakening_observation='No independent passing result.',fixed_conditions='Frozen fixture.',stopping_condition='End this offline fixture.',
            interpretation='The synthetic mathematical observation establishes no physical acceptance or global infeasibility.',supporting_evidence=[ref],
            decision=dict(hypothesis_id='offline-g0-stop',research_intent='STOP',selected_method='evidence_based_closure',
                selected_candidate=c,claimed_inference='empirical_search',requested_budget=0))
        run_fixture(h,[('evidence_read',query),('research_route',dict(tool='research_plan',action='stop')),('research_plan',stop)])
        self.assertEqual(state(h)['research_status'],'stopped')
        self.assertTrue(all(not r['full_artifact'] for r in read_coverage(h)))

    def test_all_original_conditions_still_required_after_certificate_delivery(self):
        from tests.research.test_cross_task_integration import fixture_directory,fixture_host,plan
        from tools.research.conditions import joint_assessment
        with fixture_directory() as folder:
            template=state(bounded_host())['spec']['research_decisions']
            from tools.research.config import resolve,role_provider
            def mock_config(path):
                spec=resolve(path);spec['research_decisions']=deepcopy(template)
                spec['budgets']['provider_requests']=12
                spec['configuration']['policy']['budget']['model_calls']=12
                spec['runtime']['provider']=role_provider(spec,spec['runtime']['provider'],'conversation')
                spec['configuration']['policy']['model']=deepcopy(spec['runtime']['provider'])
                return spec
            with patch('tests.research.test_cross_task_integration.resolve',side_effect=mock_config):
                h=fixture_host(folder,'study_multicondition_public.json')
            spec=deepcopy(state(h)['spec']);spec['mode']='formal_research'
            update(h,spec=spec,pilot={**state(h)['pilot'],'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
            results=[]
            with patch('tools.research.core.guard'),patch('tools.research.state.guard'),patch('tools.research.physical_replay.guard'):
                c=core.dispatch(h,plan('generate',generation=dict(version='serial_family_generation_v2',
                    family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=6)),'offline-g0-joint-generate')['result']['candidate']
                for i,condition in enumerate(spec['task_conditions']):
                    seed=core.dispatch(h,plan('initialize_control',c,control_seed=dict(candidate=c,condition_id=condition['condition_id'],tensions_n=[[.2]*6])),'offline-g0-joint-seed-'+str(i))['result']
                    with patch('tools.service_execution._run_contained',side_effect=perfect_tracking_worker):
                        result=core.dispatch(h,plan('physical_replay',seed['candidate'],physical_replay=dict(candidate=seed['candidate'],source=seed['source'])),'offline-g0-joint-replay-'+str(i))['result']
                    results.append(result['reference'])
            run_fixture(h,[*[('evidence_read',dict(reference=ref,view='acceptance_certificate')) for ref in results],None],limit=len(results)+1)
            self.assertFalse(eligibility(h,results[:1],selection=True)['eligible'])
            choice=eligibility(h,results,selection=True)
            self.assertTrue(choice['eligible'],choice)
            self.assertEqual(joint_assessment(h,results)['condition_results'],results)


if __name__=='__main__':unittest.main()
