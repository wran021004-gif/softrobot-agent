"""F0 fixtures only: no Provider, physical stepping, MATLAB, NMPC or training."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from schemas.research_reporting import (
    EvidenceLocation, EvidenceRelation, MathematicalQuantity, ReporterInterpretation,
    ResourceUse, ScientificReport,
)
from schemas.platform import EvidenceRef
from tools.platform_store import plain
from tools.state_io import digest
from tools.research import analysis
from tools.research.contracts import Plan
from tools.research.core import read_evidence
from tools.research.evidence_policy import admit_decision, registered_references, summarize_evidence
from tools.research.evidence_views import result_card
from tools.research.research_context import compact_evidence
from tests.research.test_evidence_policy import physical
from tests.research import test_task_analysis_contract as task_fixtures
from tests.research import test_mainline as mainline_fixtures
from tests.research.s7_study import engineering_plan


def ref(value):
    return dict(artifact_id=digest(value),media_type='application/json')


def offline_host(values, **fields):
    """In-memory controlled Store surface; persistence/execution are forbidden."""
    current=dict(spec=dict(mode='engineering_numerical'),results=[],candidates={},
        evaluation_reads=[],guidance_reads=[],rl_evidence_reads=[])
    current.update(fields)
    store=Mock()
    store.artifact.side_effect=lambda r:values[plain(r)['artifact_id']]
    store.session.side_effect=lambda run:dict(state=current)
    store.transaction.side_effect=AssertionError('NO_PERSISTENCE_OR_SCIENCE')
    store.reserve.side_effect=AssertionError('NO_EXECUTION_GRANT')
    store.connect.side_effect=ValueError('NO_SAVED_EXECUTION_FILES_IN_FIXTURE')
    return SimpleNamespace(store=store,run_id='f0-synthetic-fixture'),current


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        task_fixtures.TaskAnalysisTests.setUpClass()

    def setUp(self):
        self.fixture=task_fixtures.TaskAnalysisTests();self.fixture.setUp()
        self.candidate=plain(EvidenceRef.model_validate(self.fixture.ref))
        self.values={self.candidate['artifact_id']:dict(configuration=self.fixture.cfg,
            parameters={'fixture_only':True})}

    def put(self,value):
        reference=ref(value);self.values[reference['artifact_id']]=value
        return reference

    def physical_result(self):
        raw=dict(physics_steps=700,samples=[dict(time_s=t,position_error_m=.03,speed_m_s=.04,
            tip_m=[.3,0.,.2],tip_velocity_m_s=[.04,0.,0.],actual_tension_n=[.2]*6)
            for t in (0.,.30,.35)])
        value=physical(passed=False)
        value.update(candidate=self.candidate,raw_reference=self.put(raw),owning_study='f0-fixture',
            source_reference=self.put({'fixture_control':True}),boundary=dict(elapsed_s=1.5),physical_launches=1)
        value['acceptance']['task_identity']=digest(self.fixture.cfg['task'])
        value['acceptance']['components']['holding_speed'].update(value=.04,limit=.02,unit='m/s')
        for name in ('evaluator:task_bound','holding_position'):
            value['acceptance']['components'][name]['value']=.03
        return value

    def math_result(self, conclusion='feasible_witness'):
        f=self.fixture;q=f.q.model_copy(update=dict(operation='trajectory_feasibility'))
        # Fabricated replay/solver metadata exercises projection, not solver validity.
        constraint=plain(f.req.constraints[0])
        record=dict(constraint_id=constraint['constraint_id'],signal='tip_position',
            absolute_time_s=.35,value=[.001,0.,0.],margins=[.009],violation=0.,
            normalized_violation=0.,units='m',passed=True)
        trajectory=dict(status=conclusion,replay=dict(passed=conclusion=='feasible_witness',records=[record]),
            certificate=dict(verified=conclusion=='model_infeasibility_certificate',margin=.1))
        value=dict(status='computed',operation=q.operation,candidate=self.candidate,binding=f.binding,
            model=plain(f.fixture_model()),trajectory=trajectory,charged_analysis_evaluations=1,
            charged_numerical_s=.02)
        applicability=f.applicability(query=q,model=f.fixture_model())
        if conclusion=='not_applicable':
            value['status']='not_applicable';applicability.update(status='not_applicable',reasons=['Fixture unsupported physics'])
        return json.loads(json.dumps(analysis.scoped_result(value,f.req,applicability,q)))

    def test_physical_card_keeps_metrics_identity_extrema_costs_and_raw_pointers(self):
        value=self.physical_result();reference=self.put(value)
        host,current=offline_host(self.values,physical_replays=[reference])
        before=deepcopy((self.values,current));card=result_card(host,reference)
        self.assertEqual(card.identity.study,'f0-fixture')
        self.assertEqual(plain(card.identity.candidate),self.candidate)
        self.assertEqual(plain(card.identity.control_source),value['source_reference'])
        self.assertEqual(card.evidence_summary.claim_kind,'PHYSICAL_OBSERVATION')
        metric=next(m for m in card.metrics if m.name=='holding_speed')
        self.assertEqual((metric.value,metric.threshold,metric.unit,metric.passed),(.04,.02,'m/s',False))
        self.assertIn(card.main_violations[0],('evaluator:task_bound','holding_position'))
        for m in card.metrics:
            self.assertEqual(read_evidence(host,plain(m.source),record_read=False),m.value)
            if m.threshold_source:self.assertEqual(read_evidence(host,plain(m.threshold_source),record_read=False),m.threshold)
        for observation in card.critical_observations:
            self.assertEqual(read_evidence(host,plain(observation.source),record_read=False)['time_s'],observation.time_s)
        costs={r.name:r for r in card.resources}
        self.assertEqual(costs['physics_steps'].amount,700)
        self.assertEqual(costs['elapsed_s'].time_basis,'worker_wall')
        self.assertIsNone(costs['cpu_time'].amount);self.assertIsNone(costs['provider_cost'].amount)
        for r in card.resources:
            if r.amount is not None:self.assertEqual(read_evidence(host,plain(r.source),record_read=False),r.amount)
        self.assertEqual((self.values,current),before)
        card.deterministic_summary['constraints']['holding_speed']['value']=999.
        card.critical_observations[0].observed['tip_m'][0]=999.
        self.assertEqual((self.values,current),before)
        self.assertFalse(host.store.transaction.called)

    def test_math_card_preserves_existing_summaries_and_conclusion_strength(self):
        kinds={'feasible_witness':'MODEL_WITNESS','model_infeasibility_certificate':'MODEL_EXCLUSION',
            'inconclusive':'NUMERICAL_DIAGNOSTIC','not_applicable':'NUMERICAL_DIAGNOSTIC'}
        for conclusion,kind in kinds.items():
            with self.subTest(conclusion=conclusion):
                value=self.math_result(conclusion);reference=self.put(value)
                host,current=offline_host(self.values,analysis_results=[reference])
                original=deepcopy(value);compact=analysis.compact_result(value,reference)
                decision=analysis.decision_result(value,reference)
                card=result_card(host,reference)
                self.assertEqual(card.evidence_summary.claim_kind,kind)
                self.assertEqual(card.mathematics.claim.conclusion,conclusion)
                from tools.research.task_constraints import SCIENTIFIC_INTERPRETATION
                self.assertEqual(card.deterministic_summary,{**decision,'scientific_interpretation':SCIENTIFIC_INTERPRETATION})
                self.assertEqual(value,original);self.assertEqual(analysis.compact_result(value,reference),compact)
                metric=card.metrics[0]
                self.assertEqual((metric.value,metric.threshold,metric.unit),([.001,0.,0.],.01,'m'))
                self.assertEqual(read_evidence(host,plain(metric.source),record_read=False),metric.value)
                self.assertEqual(read_evidence(host,plain(metric.threshold_source),record_read=False),metric.threshold)
                self.assertNotIn('observed_task_pass',card.evidence_summary.supported_inferences)
                self.assertEqual(current['guidance_reads'],[])
        # A failed calculation keeps its computation status separate from conclusion.
        value=self.math_result('inconclusive');value['status']='execution_incomplete'
        value['scoped_claim']['computation_status']='execution_incomplete'
        host,_=offline_host(self.values);card=result_card(host,self.put(value))
        self.assertEqual(card.mathematics.claim.computation_status,'execution_incomplete')
        self.assertEqual(card.mathematics.claim.conclusion,'inconclusive')

    def test_search_card_keeps_baseline_proposals_predictions_and_stop_reason(self):
        observed=self.physical_result();evaluation=self.put(observed)
        def row(label,predicted=None,actual=None):
            return dict(label=label,reference=evaluation,candidate=self.candidate,
                source=self.put(dict(fixture_control=label)),prediction_base=evaluation if predicted else None,
                predicted_improvement=predicted,actual_improvement=actual,task_gap=dict(normalized_gap=1.,accepted=False),
                original_acceptance=observed['acceptance'])
        baseline=row('baseline');proposal=row('local_response_proposal',.2,.1)
        value=dict(candidate=self.candidate,source=baseline['source'],candidates=[baseline,proposal],best=proposal,
            starts=[],start_feedback=[],stop_reason='iteration_limit',cost_feedback=dict(new_physical_evaluations=1))
        reference=self.put(value);host,current=offline_host(self.values,control_search_results=[reference])
        before=deepcopy(self.values);old=compact_evidence(value,reference);card=result_card(host,reference)
        search=card.control_search
        self.assertEqual(search.baselines[0].label,'baseline')
        self.assertEqual((search.proposals[0].predicted_improvement,search.proposals[0].actual_improvement),(.2,.1))
        self.assertEqual(search.stop_reason.value,'iteration_limit')
        metric=next(m for m in search.best.metrics if m.name=='holding_speed')
        self.assertEqual((metric.value,metric.threshold,metric.unit),(.04,.02,'m/s'))
        self.assertEqual(read_evidence(host,plain(metric.source),record_read=False),metric.value)
        self.assertEqual(read_evidence(host,plain(search.best.source),record_read=False),proposal)
        self.assertEqual(compact_evidence(value,reference),old);self.assertEqual(self.values,before)
        self.assertNotEqual(card.evidence_summary.claim_kind,'PHYSICAL_OBSERVATION')
        self.assertEqual(current['evaluation_reads'],[])

    def test_read_modes_share_boundary_and_default_read_markers_are_unchanged(self):
        value=self.physical_result();value['a/b']={'~key':[1,2,3,4]};reference=self.put(value)
        host,current=offline_host(self.values,results=[reference],task_math_references=[reference])
        queries=[dict(view='summary'),dict(view='fields',fields=['candidate','acceptance']),
            dict(pointer='/a~1b/~0key',view='range',start=1,count=2),dict(pointer='/acceptance/components/holding_speed/value')]
        with patch('tools.research.core.update',side_effect=lambda h,**v:current.update(v)):
            for query in queries:
                before=deepcopy(current)
                internal=read_evidence(host,dict(reference=reference,**query),record_read=False)
                self.assertEqual(current,before)
                self.assertEqual(read_evidence(host,dict(reference=reference,**query)),internal)
            self.assertEqual(len(current['evaluation_reads']),1)
            self.assertEqual(len(current['guidance_reads']),2)
            self.assertEqual(len(current['rl_evidence_reads']),4)
            current['success_gate']=True
            foreign=self.put({'fixture':'unregistered'})
            for record_read in (True,False):
                with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE'):
                    read_evidence(host,dict(reference=foreign),record_read=record_read)
        self.assertFalse(host.store.transaction.called)

    def test_internal_reads_do_not_satisfy_evaluation_guidance_or_rl_markers(self):
        reference=self.put(self.physical_result())
        for kind in ('results','physical_replays','rl_evaluations','rl_training_summaries',
                'task_math_references','holding_diagnostic_reference'):
            with self.subTest(kind=kind):
                host,current=offline_host(self.values)
                current[kind]=reference if kind=='holding_diagnostic_reference' else [reference]
                before=deepcopy(current)
                with patch('tools.research.core.update',side_effect=lambda h,**v:current.update(v)):
                    result_card(host,reference)
                    self.assertEqual(current,before)
                    read_evidence(host,dict(reference=reference))
                marker='guidance_reads' if kind in ('task_math_references','holding_diagnostic_reference') else 'evaluation_reads'
                self.assertEqual(current[marker],[reference])

    def test_internal_card_does_not_grant_select_eligibility(self):
        from tools.research import feedback
        from tools.research.state import state
        case=mainline_fixtures.MainlineTests();case.setUp();self.addCleanup(case.tearDown)
        before=deepcopy(state(case.host));ledger=case.host.store.remaining();events=case.host.store.events(case.host.run_id)
        result_card(case.host,case.result)
        self.assertEqual(state(case.host),before)
        self.assertEqual(case.host.store.remaining(),ledger);self.assertEqual(case.host.store.events(case.host.run_id),events)
        self.assertFalse(feedback.eligibility(case.host,case.result)['eligible'])
        read_evidence(case.host,dict(reference=case.result))
        self.assertTrue(feedback.eligibility(case.host,case.result)['eligible'])

    def test_report_modes_future_math_and_comparison_scope_are_typed(self):
        reference=self.put(self.math_result());host,_=offline_host(self.values)
        card=result_card(host,reference)
        unavailable=MathematicalQuantity(name='optimal_task_violation',structural_parameters=['segments.0.length_m'],
            control_reoptimization='required')
        sensitivity=MathematicalQuantity(name='structural_sensitivity',structural_parameters=['segments.0.length_m'],
            control_reoptimization='required')
        card=card.model_copy(update=dict(mathematics=card.mathematics.model_copy(update=dict(quantities=[unavailable,sensitivity]))))
        report=ScientificReport(mode='result_summary',results=[card],interpretations=[ReporterInterpretation(
            kind='unresolved_question',text='Fixture hypothesis only',sources=[card.identity.result])])
        self.assertEqual(ScientificReport.model_validate_json(report.model_dump_json()),report)
        self.assertIsNone(report.results[0].mathematics.quantities[0].value)
        investigation=ScientificReport(mode='investigation',question='Compare available evidence',results=[card,card])
        self.assertEqual(len(investigation.results),2)
        for invalid in (dict(mode='investigation'),dict(mode='result_summary',results=[card,card])):
            with self.assertRaises(ValueError):ScientificReport.model_validate({'results':[card],**invalid})
        with self.assertRaises(ValueError):MathematicalQuantity(name='bound',status='verified',value=0.)
        with self.assertRaises(ValueError):MathematicalQuantity(name='bound',value=0.)
        with self.assertRaises(ValueError):ResourceUse(name='cost',unit='USD',amount=0.)
        with self.assertRaises(ValueError):ResourceUse(name='elapsed',unit='s')
        for pointer in ('relative','/~2bad'):
            with self.assertRaises(ValueError):EvidenceLocation(reference=reference,pointer=pointer)
        relation=dict(kind='structures',left=card.identity,right=card.identity,sources=[card.identity.result])
        with self.assertRaises(ValueError):EvidenceRelation(**relation)
        with self.assertRaises(ValueError):EvidenceRelation(**relation,comparable=True,
            changed_factors=['structure','control'],single_factor_attribution='structure')
        self.assertIsNone(EvidenceRelation(**relation,reasons=['Different controls and structures']).single_factor_attribution)

    def test_report_interpretation_is_never_registered_or_promoted_to_evidence(self):
        reference=self.put(self.math_result('inconclusive'));host,current=offline_host(self.values,analysis_results=[reference])
        current['spec']['research_decisions']=True
        card=result_card(host,reference);before=registered_references(host)
        report=ScientificReport(mode='result_summary',results=[card],interpretations=[
            ReporterInterpretation(kind='hypothesis',text='Fixture text claiming an optimal structure')])
        report_ref=self.put(plain(report))
        self.assertFalse(report.authoritative_scientific_evidence)
        self.assertEqual(summarize_evidence(plain(report),report_ref)['claim_kind'],'UNVERIFIED_HYPOTHESIS')
        self.assertEqual(registered_references(host),before)
        plan=Plan.model_validate(engineering_plan('stop','STOP',supporting_evidence=[report_ref]))
        with self.assertRaisesRegex(ValueError,'UNREGISTERED_RESEARCH_EVIDENCE'):admit_decision(host,plan)
        with self.assertRaises(ValueError):ScientificReport(mode='result_summary',results=[card],authoritative_scientific_evidence=True)
        self.assertFalse(host.store.transaction.called or host.store.reserve.called)


if __name__=='__main__':unittest.main()
