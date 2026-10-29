"""Sealed numerical fragments + synthetic bindings; no Provider or science."""
import json
from copy import deepcopy
from pathlib import Path
import unittest
from tests.research import test_s129_agent_reporting as reporting
from tests.research.test_information_flow import flow_host, generation
from tools.platform_store import plain
from tools.research import reporter, agent
from tools.research.contracts import Plan
from tools.research.evidence_policy import admit_decision, citation_role, registered_references
from tools.research.evidence_views import quantitative_facts
from tools.research.experience import retrieve, read_progress
from tools.research.state import state, update

FACTS=json.loads((Path(__file__).parent/'fixtures/p62f_facts.json').read_text())


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):reporting.AgentReportingTests.setUpClass()

    def setUp(self):
        self.f=reporting.AgentReportingTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.h=self.f.h

    def math(self):
        value=self.f.f.math_result('inconclusive')
        value.update(deepcopy(FACTS['mathematics']))
        return self.f.put(value)

    def test_all_constraints_solver_and_target_distance_survive_compact_wire(self):
        ref=self.math();update(self.h,analysis_results=[ref])
        receipt=reporter.investigate(self.h,dict(question='Solver and every task violation',references=[ref]))
        saved=self.h.store.artifact(receipt['report_reference'])
        payload=json.loads(reporter._wire(self.h,receipt['report_reference'],saved)['messages'][-1]['content'])
        result=payload['report']['results'][0];metrics={m['name']:m for m in result['metrics']}
        self.assertEqual(metrics['holding_max_error_m']['value'],0.010000056805892363)
        self.assertFalse(metrics['holding_max_error_m']['passed'])
        self.assertEqual(metrics['holding_max_speed_m_s']['value'],0.02000489088519356)
        self.assertEqual(metrics['holding_max_speed_m_s']['time_s'],.33)
        self.assertEqual(metrics['holding_max_error_m']['window_s'],[.3,.35000000000000003])
        self.assertTrue(metrics['terminal_error_m']['passed'])
        q=result['quantitative_facts'];self.assertFalse(q['solver']['success'])
        self.assertEqual(q['solver']['iterations'],100)
        self.assertEqual(q['mathematical_conclusion'],'inconclusive')
        self.assertEqual(q['operating_point']['target_position_distance_m'],0.053749418601506754)
        self.assertIn('not force',q['operating_point']['residual_semantics'])
        self.assertEqual({r['constraint_id'] for r in q['sampled_constraints']['failed_samples']},
            {'holding_max_error_m','holding_max_speed_m_s'})
        self.assertLess(len(json.dumps(payload)),35000)
        for m in result['metrics']:
            self.assertEqual(reporter.read_evidence(self.h,m['source'],record_read=False),m['value'])

    def test_physical_direction_valid_failure_and_unknown_ordering(self):
        refs=[]
        for acceptance in FACTS['physics']:
            value=self.f.f.physical_result();value['acceptance']=deepcopy(acceptance)
            refs.append(self.f.put(value))
        report=reporter.assemble(self.h,refs,question='Second column is baseline')
        changes={r['metric']:r for r in report.results[0].deterministic_summary['comparisons'][0]['metrics']}
        self.assertEqual(changes['evaluator:task_bound']['direction'],'improved')
        self.assertEqual(changes['holding_position']['direction'],'improved')
        self.assertEqual(changes['holding_speed']['direction'],'worsened')
        self.assertAlmostEqual(changes['holding_speed']['delta'],.029181403855198178)
        self.assertIsNone(report.relations[0].single_factor_attribution)
        for ref in refs:
            facts=quantitative_facts(self.h.store.artifact(ref),ref)
            self.assertTrue(facts['evaluation_valid']);self.assertEqual(facts['task_acceptance'],'valid_failure')
            self.assertFalse(facts['acceptance']['accepted'])
        for ref in refs:
            value=self.h.store.artifact(ref);value['acceptance']['task_family']='fixture.unknown'
            refs[refs.index(ref)]=self.f.put(value)
        report=reporter.assemble(self.h,refs,question='Unknown evaluator')
        self.assertTrue(all(c['direction']=='unknown' for c in report.results[0].deterministic_summary['comparisons'][0]['metrics']))

    def test_report_reference_unwrap_and_interpretation_cannot_replace_facts(self):
        ref=self.math();receipt=reporter.investigate(self.h,dict(question='First',references=[ref]))
        report_ref=receipt['report_reference'];saved=self.h.store.artifact(report_ref)
        self.assertEqual(citation_role(self.h,report_ref),'reporter_report')
        saved['report']['interpretations']=[dict(kind='new_information',text='Fixture deliberate false claim: all constraints passed.',sources=[],status='reporter_interpretation')]
        saved['interpretation_status']='available'
        summary=reporter.reporter_handoff_summary(self.h,report_ref,saved)
        self.assertTrue(any(m['passed'] is False for m in summary['findings'][0]['metrics']))
        self.assertIn('Non-authoritative',summary['interpretation_scope'])
        next_report=reporter.investigate(self.h,dict(question='Second',references=[report_ref]))
        next_saved=self.h.store.artifact(next_report['report_reference'])
        self.assertEqual(next_saved['report']['results'][0]['identity']['result']['reference'],ref)
        self.assertNotIn(report_ref,registered_references(self.h))

    def test_one_rejection_identifies_report_and_allows_explicit_correction(self):
        h=flow_host();domain=state(h)['family_space_reference']
        report=reporter.investigate(h,dict(question='Fixture domain only',references=[domain]))['report_reference']
        raw=generation(h);raw['supporting_evidence']=[report]
        with self.assertRaisesRegex(ValueError,'UNREGISTERED_RESEARCH_EVIDENCE') as caught:
            admit_decision(h,Plan.model_validate(raw))
        feedback=agent.error_feedback(h,dict(name='research_plan',input=raw,toolUseId='fixture-reject'),caught.exception,state(h))
        self.assertEqual(feedback['citation_errors'][0]['role'],'reporter_report')
        self.assertEqual(feedback['citation_errors'][0]['reference'],report)
        self.assertEqual(feedback['inventory_query']['pointer'],'/citation_eligibility')
        self.assertEqual(raw['supporting_evidence'],[report])
        raw['supporting_evidence']=[]
        self.assertIsNotNone(admit_decision(h,Plan.model_validate(raw)))

    def test_empty_knowledge_filters_supply_legal_read_and_delivery_not_faked(self):
        h=flow_host()
        empty=retrieve(h,dict(operation='search',task='reach-and-hold',version='999'))
        recovery=empty['empty_search_recovery'];self.assertIn('position_tool_axis',recovery['available_task_tags'])
        read=retrieve(h,recovery['exact_reads'][0])
        self.assertEqual(read['evidence_role'],'context_only')
        self.assertFalse(read_progress(h)['reads'][0]['body_delivered'])
        self.assertNotIn(read['reference'],registered_references(h))

    def test_exact_knowledge_body_survives_feedback_handoff_and_confirmed_wire(self):
        from tests.research.test_recent_round_tools import run_fixture
        from tests.research.test_information_flow import packet
        from tools.platform_host import Host
        h=flow_host()
        wires=run_fixture(h,[('experience_retrieve',dict(operation='search',task='reach',version='999')),
            ('experience_retrieve',dict(operation='read',entry_id='research-strict-near-tolerance',revision='2')),
            ('research_recall',dict(trace='actions')),None])
        self.assertIn('empty_search_recovery',json.dumps(packet(wires[1])))
        self.assertIn('historical_facts',json.dumps(wires[2]))
        progress=read_progress(h);self.assertTrue(progress['reads'][0]['body_delivered'])
        self.assertEqual(read_progress(Host(h.store.root,h.run_id)),progress)
        self.assertEqual(packet(wires[3])['knowledge']['read_progress'],progress)
        self.assertEqual(sum(e['kind']=='session_handoff' and e['status']=='committed' for e in h.store.events(h.run_id)),3)


if __name__=='__main__':unittest.main()
