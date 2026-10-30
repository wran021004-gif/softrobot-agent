"""F1 actual SDK/Mock wire regressions. All numbers and replies are fixtures."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.platform_store import plain
from tools.research import core,reporter
from tools.research.research_context import read_coverage,result_index_progress
from tools.research.state import state,save,update
from tools.state_io import read,atomic_json
from tests.research.test_p63c2_scientific_intent import question_host,control_question
from tests.research.test_p63a_math_interface import generate,t1_request,synthetic_t1,offline_dispatch
from tests.research.test_p63b3_action_interface import feedback
from tests.research.test_information_flow import packet
from tests.research.test_recent_round_tools import run_fixture


def plan(candidate):
    return dict(action='diagnose',hypothesis='Offline: the initial schedule satisfies all frozen task limits.',
        expected_observation='All limits pass.',weakening_observation='A measured violation.',
        fixed_conditions='Frozen candidate and task.',stopping_condition='Fixture only; no real science.',
        interpretation='Synthetic intent, not a verified conclusion.',
        decision=dict(hypothesis_id='offline-f1',research_intent='DIAGNOSE',selected_candidate=candidate,selected_method='trajectory_feasibility',requested_budget=0))


class ResultFeedbackTests(unittest.TestCase):
    def setUp(self):
        for target in ('tools.service_execution._run_contained','extensions.tendon_family.mujoco_analysis.NativeModel','mujoco.mj_step','tools.research.provider.load_credential'):
            p=patch(target,side_effect=AssertionError('NO_REAL_PROVIDER_WORKER_OR_PHYSICS'));p.start();self.addCleanup(p.stop)

    def contained(self,command,log,timeout,**kwargs):
        request=read(Path(command[-1]));value=synthetic_t1(request)
        value['native_dynamics']['optimization']['search_dimension']=8
        atomic_json(Path(command[-1]).with_name('result.json'),value)
        return SimpleNamespace(returncode=0)

    def test_completed_result_and_reporter_available_unavailable_missing_on_actual_wire(self):
        for mode in ('available','unavailable','missing'):
            with self.subTest(mode=mode):
                h=question_host();c=generate(h);t1_request(h,c)
                def stored_report(host,value,before=None,**kwargs):
                    ref=value['reference'];report=plain(reporter.assemble(host,[ref]))
                    report['interpretations']=([dict(kind='further_investigation',text='OFFLINE source-linked unresolved mechanism.',sources=[dict(reference=ref,pointer='/nonlinear_capability')])] if mode=='available' else [])
                    return reporter._save(host,report,status='unavailable' if mode=='unavailable' else 'available',error='OFFLINE unavailable' if mode=='unavailable' else None)
                with patch('tools.service_execution._run_contained',side_effect=self.contained),patch('tools.research.reporter.scientific_feedback',side_effect=stored_report):
                    responses=[('research_plan',plan(c)),('research_analysis',control_question())]
                    if mode=='available':
                        next_plan=plan(c);next_plan['hypothesis']='OFFLINE new question after the first completed result.'
                        next_plan['decision']['hypothesis_id']='offline-f1-next'
                        responses.append(('research_plan',next_plan))
                    wires=run_fixture(h,[*responses,None])
                if mode=='available':
                    replanned=packet(wires[3])
                    self.assertNotIn('post_result_decision',replanned)
                    self.assertEqual(replanned['tool_continuation']['analysis_handoff']['status'],'diagnose_completed')
                before=packet(wires[1]);after=packet(wires[2])
                self.assertEqual(before['tool_continuation']['analysis_handoff']['status'],'diagnose_completed')
                self.assertNotIn('post_result_decision',before)
                self.assertEqual(after['tool_continuation']['analysis_handoff']['status'],'result_completed')
                self.assertIn('post_result_decision',after)
                self.assertNotIn('Submit scientific question fields',json.dumps(after['tool_continuation']))
                result=after['mathematical_research']['latest_result']
                self.assertEqual(result['quantities']['J'],.5)
                self.assertEqual(result['task_acceptance'],'unmeasured')
                self.assertEqual(result['search_cost']['first_complete_response_callbacks'],10)
                self.assertEqual(after['reporter_findings'][0]['interpretations']!=[],mode=='available')
                self.assertFalse(after['reporter_findings'][0]['scientific_citation_eligible'])
                self.assertEqual(after['current_research_state']['mathematical_read_progress'][0]['mathematical_request'],'result_recorded')
                self.assertIn('research_analysis',[t['function']['name'] for t in wires[2]['tools']])
                self.assertTrue(any(r['action']=='research_analysis' and r['status']!='blocked' for group in after['capabilities'] for r in group['actions']))

    def test_index_first_repeat_changed_and_body_reads_on_actual_wire(self):
        h=question_host();c=generate(h);q=t1_request(h,c)
        first=offline_dispatch(h,q,'offline-f1-initial')['reference']
        query=dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/all_fresh_results')
        original=core.read_tool_evidence;calls=[];new=[]
        def index_read(host,payload,**kwargs):
            if payload.get('pointer')=='/all_fresh_results':
                calls.append(payload)
                if len(calls)==3:
                    value=deepcopy(host.store.artifact(first));value['fixture_revision']='OFFLINE additional result'
                    ref=save(host,value,'offline_new_result');new.append(ref)
                    update(host,analysis_results=[*state(host)['analysis_results'],ref])
            return original(host,payload,**kwargs)
        with patch('tools.research.agent.read_tool_evidence',side_effect=index_read):
            wires=run_fixture(h,[('evidence_read',query),('evidence_read',query),('evidence_read',query),
                ('evidence_read',dict(reference=first,view='full')),None])
        self.assertEqual(packet(wires[0])['evidence_access']['stop_index']['read_progress']['status'],'unread')
        self.assertEqual(feedback(h,'offline-use-0')['this_read'],'first_delivery')
        # A successful send confirms a tool response; the next read sees it.
        self.assertEqual(feedback(h,'offline-use-1')['this_read'],'exact_repeat')
        self.assertIn('no new scientific information',feedback(h,'offline-use-1')['notice'])
        self.assertEqual(feedback(h,'offline-use-2')['this_read'],'changed_content')
        self.assertEqual(feedback(h,'offline-use-2')['results'],[first,*new])
        coverage=read_coverage(h);indexes=[r for r in coverage if r['query']['pointer']=='/all_fresh_results']
        self.assertEqual([r['classification'] for r in indexes],['new_query','exact_repeat','changed_content'])
        self.assertTrue(all(r['successfully_provided'] and not r['full_artifact'] and not r['complete_data'] for r in indexes))
        progress=result_index_progress([first,*new],coverage)
        self.assertEqual(progress['status'],'read_unchanged');self.assertEqual(progress['complete_body_reads'],[first])
        self.assertEqual(progress['unread_bodies'],new)
        self.assertEqual(core.read_evidence(h,query,record_read=False),[first,*new])
        self.assertEqual(state(h).get('evaluation_reads',[]),[])
        self.assertEqual(state(h)['mathematical_evaluations'],1)


if __name__=='__main__':unittest.main()
