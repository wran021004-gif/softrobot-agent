"""Read-only projection checks; fabricated metrics are fixtures, never research evidence."""
from copy import deepcopy
import unittest

from tools.platform_store import plain
from tools.research.core import read_evidence
from tools.research.evidence_views import result_card
from tools.research.feedback import task_gap
from tools.research.research_context import mathematical_decision_view
from tools.research import task_constraints as methods
from tests.research.test_c1_method_context import C1Archive
from tests.research.test_evidence_policy import physical
from tests.research.test_research_reporting import offline_host, ref


class EvidenceClarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c1=C1Archive()

    @classmethod
    def tearDownClass(cls):
        cls.c1.archive.close()

    def test_physical_gap_joins_active_metric_without_changing_ranking_or_acceptance(self):
        for active,value,unit in (('holding_speed',.024,'m/s'),('holding_position',.03,'m')):
            result=physical(passed=False)
            components=result['acceptance']['components']
            components['holding_speed'].update(value=.01,limit=.02,unit='m/s')
            components[active]['value']=value
            reference=ref(result);before=deepcopy(result)
            host,current=offline_host({reference['artifact_id']:result},results=[reference])
            gap=task_gap(result);metric,=gap['dominant_constraints']
            self.assertEqual((metric['constraint_id'],metric['value'],metric['limit'],metric['unit']),
                (active,value,components[active]['limit'],unit))
            self.assertEqual(metric['scope'],'physical_task')
            self.assertAlmostEqual(gap['normalized_gap'],max(0.,value/metric['limit']-1))
            self.assertEqual(read_evidence(host,dict(reference=reference,pointer=metric['source_pointer']+'/value'),
                                          record_read=False),value)
            self.assertEqual(gap['accepted'],result['acceptance']['accepted'])
            self.assertEqual(result,before);self.assertEqual(current['evaluation_reads'],[])
        # A clipped zero gap still identifies the tightest signed margin, not arbitrary zero ties.
        result['acceptance']['components']['holding_position']['value']=.002
        self.assertEqual(task_gap(result)['normalized_gap'],0.)
        self.assertEqual(task_gap(result)['dominant_constraints'][0]['constraint_id'],'holding_speed')
        episode=dict(terminal_position_error_m=.001,holding_max_position_error_m=.002,
                     holding_max_speed_m_s=.024,complete=True,holding_coverage_complete=True)
        rl=dict(independent_evaluation_executed=True,episodes=[episode],passed=False,
                acceptance=dict(terminal_position_limit_m=.01,position_limit_m=.01,holding_speed_limit_m_s=.02))
        metric,=task_gap(rl)['dominant_constraints']
        self.assertEqual((metric['value'],metric['unit'],metric['source_pointer']),(.024,'m/s','/episodes/0/holding_max_speed_m_s'))

    def test_saved_native_bottleneck_reaches_l0_as_prediction_with_original_sources(self):
        host,state=self.c1.host();reference=state['analysis_results'][0]
        before=self.c1.artifact(reference);card=result_card(host,reference)
        view=mathematical_decision_view(plain(card))
        for label in ('baseline','best'):
            metric=view['native_analysis']['comparison'][label]['worst_constraint']
            self.assertEqual((metric['constraint_id'],metric['limit'],metric['unit'],metric['scope']),
                ('holding_max_speed_m_s',.02,'m/s','model_sample'))
            self.assertEqual(read_evidence(host,metric['source'],record_read=False),metric['value'])
            self.assertEqual(read_evidence(host,metric['threshold_source'],record_read=False),metric['limit'])
            self.assertEqual(metric['normalized_signed_excess'],before['native_analysis']['comparison'][label]['signed_maximum_excess'])
        self.assertNotEqual(card.evidence_summary.claim_kind,'PHYSICAL_OBSERVATION')
        self.assertEqual(before['task_acceptance'],'unmeasured')
        self.assertEqual(self.c1.artifact(reference),before)
        host.store.transaction.assert_not_called();host.store.reserve.assert_not_called()

    def test_catalog_exposes_scope_cost_and_conditional_admission_without_new_methods(self):
        host,state=self.c1.host();before=deepcopy(state)
        view=methods.mathematical_method_view(host,state['reference_candidate'])
        catalog=methods.mathematical_catalog(view);rows=catalog['methods']
        self.assertEqual(set(rows),set(view['methods']))
        self.assertNotIn('cross_applied_schedule_decomposition',rows)
        self.assertIn('selected_method is proposal text',catalog['limitations'][1])
        self.assertIn('internal force-balance residuals do not establish',rows['native_dynamics_v1']['description'])
        self.assertIn('two integration timesteps',rows['short_input_response_v1']['description'])
        self.assertIn('does not establish finite-horizon',rows['instantaneous_braking_v1']['description'])
        cost=rows['mujoco_direct_control_v1']['cost_scope']
        for fact in ('S baselines','FD probes','candidate evaluation','prefix reconstruction','independent physical_replay','same rollouts, not extra runs'):
            self.assertIn(fact,cost)
        self.assertIn('four FD rollouts per channel',rows['short_input_response_v1']['cost_scope'])
        self.assertEqual(rows['mujoco_direct_control_v1']['execution_status'],'conditional_on_admission')
        self.assertEqual(rows['mujoco_direct_control_v1']['formal_execution_authorized'],
                         view['methods']['mujoco_direct_control_v1']['formal_execution_authorized'])
        saved=self.c1.artifact(state['analysis_results'][0])
        cost=saved['native_analysis']['cost'];callbacks=saved['native_dynamics']['optimization']['cost_feedback']
        self.assertEqual((cost['optimization_evaluations'],cost['rollouts'],callbacks['evaluation_callbacks']),(26,26,26))
        self.assertEqual(cost['physics_steps'],18200)
        self.assertEqual(state,before)
        host.store.transaction.assert_not_called();host.store.reserve.assert_not_called()


class DecisionWorksetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import gzip,io,tarfile
        from tests.research.c3_readiness_audit import C3Archive
        from tools.research.config import ROOT
        path=ROOT/'evidence/b3_r1_history_assisted_050/immutable_artifacts.tar.gz'
        cls.r1=C3Archive(path);cls.r1.archive.close()
        # Read the immutable archive in memory, avoiding repeated gzip seeks.
        cls.r1.archive=tarfile.open(fileobj=io.BytesIO(gzip.decompress(path.read_bytes())))
        cls.addClassCleanup(cls.r1.archive.close)

    def host(self):
        h,s=self.r1.host();s['count_closeout']=False;h.actor='offline-fixture'
        return h,s

    def test_plan_schema_and_runtime_share_action_intents_and_payload_ownership(self):
        from jsonschema import Draft202012Validator
        from tools.research.agent import plan_schema,error_feedback
        from tools.research.contracts import Plan,PLAN_RESEARCH_INTENTS
        from tools.research.evidence_policy import admit_decision
        from unittest.mock import patch
        h,s=self.host();candidate=list(s['candidates'].values())[-1]
        actions=Plan.model_json_schema()['properties']['action']['enum']
        self.assertEqual(set(actions),set(PLAN_RESEARCH_INTENTS))
        schema=plan_schema(actions,decision_required=True)
        intents=[r for r in schema['allOf'] if 'research_intent' in r.get('then',{}).get('properties',{}).get('decision',{}).get('properties',{})]
        validator=Draft202012Validator(dict(allOf=intents))
        for action,intent in PLAN_RESEARCH_INTENTS.items():
            validator.validate(dict(action=action,decision=dict(research_intent=intent)))
            self.assertTrue(list(validator.iter_errors(dict(action=action,decision=dict(research_intent='RL_TRAINING')))))
        expected=dict(execute='NMPC_EXECUTION',initialize_control='CONTROL_SEARCH',diagnose='DIAGNOSE',
            replay='MATHEMATICAL_ANALYSIS',select='SELECT',stop='STOP')
        payloads=dict(execute=dict(candidate=candidate),initialize_control=dict(control_seed=dict(candidate=candidate)),
            replay=dict(mechanics_source=candidate),select=dict(selected_execution=candidate))
        for action,intent in expected.items():
            value=dict(action=action,hypothesis='Offline contract fixture',expected_observation='No worker',
                weakening_observation='Contract mismatch',fixed_conditions='Frozen task',stopping_condition='End fixture',
                interpretation='Not scientific evidence',decision=dict(hypothesis_id='fixture',research_intent=intent,
                selected_method='fixture',selected_candidate=candidate),**payloads.get(action,{}))
            Draft202012Validator(schema).validate(value);Plan.model_validate(value)
            Draft202012Validator(plan_schema([action],decision_required=True)).validate(value)
            wrong=deepcopy(value);wrong['decision']['research_intent']='RL_TRAINING'
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(wrong)))
            with self.assertRaisesRegex(ValueError,'RESEARCH_INTENT_ACTION_MISMATCH') as caught:
                admit_decision(h,Plan.model_validate(wrong))
            with patch('tools.research.agent.record',return_value=candidate):
                feedback=error_feedback(h,dict(name='research_plan',input=wrong),caught.exception,s)
            self.assertIn('requires decision.research_intent='+intent,feedback['expected'])
        h.store.reserve.assert_not_called()

    def test_r1_current_sources_and_execution_boundaries_survive_compact_wire_and_handoff(self):
        import json
        from tools.research.research_context import agent_decision_brief
        from tools.research.agent import DeepSeekModel
        from tools.research.session_handoff import initial_messages
        h,s=self.host();before=deepcopy(s);brief=agent_decision_brief(h);current=brief['current_candidate']
        self.assertTrue(current['control_initialized']);self.assertTrue(current['has_completed_nmpc_execution'])
        self.assertEqual(current['candidate'],self.r1.artifact(s['selected_solution'])['candidate'])
        self.assertLessEqual(len(current['control_sources']),3)
        self.assertNotIn('tensions_n',json.dumps(current))
        origins={r['origin_status'] for r in current['control_sources']}
        self.assertIn('measured_execution',origins);self.assertIn('mathematical_prediction',origins)
        for source in current['control_sources']:
            small=read_evidence(h,source['query'],record_read=False)
            self.assertEqual(small['source'],source['source']);self.assertTrue(small['full_control_sequence'])
            self.assertEqual(small['task_acceptance'],'unmeasured')
            self.assertLess(len(json.dumps(small)),2200)
        self.assertTrue(brief['best_valid']['task_gap']['accepted'])
        self.assertFalse(brief['best_valid']['historical_only'])
        self.assertEqual(brief['budget']['public_operation_budget']['remaining_total'],68)
        self.assertEqual(brief['budget']['science_budget']['remaining_full_replays'],1)
        self.assertEqual(brief['budget']['science_budget']['native']['recorded_physics_steps'],10000)
        trace=read_evidence(h,brief['action_trace']['full_trace_query'],record_read=False)
        self.assertTrue(any(r['execution_kind']=='read_only_diagnosis' for r in trace['recent']))
        wire=self.r1.requests()[-1][2];tail=dict(role='user',content='CURRENT_RESEARCH_PACKET\n'+json.dumps(dict(research=brief)))
        for messages in (wire['messages'][:-1]+[tail],[wire['messages'][0],*DeepSeekModel.format_request_messages(initial_messages(h.run_id)),tail]):
            delivered=json.loads(json.dumps(messages))[-1]
            self.assertEqual(json.loads(delivered['content'].split('\n',1)[1])['research']['current_candidate'],current)
        self.assertEqual(s,before);h.store.transaction.assert_not_called();h.store.reserve.assert_not_called()

    def test_r1_pointer_wrapper_range_and_fields_corrections_are_readable(self):
        from tools.research.agent import error_feedback
        from tools.research.config import ROOT
        from tools.state_io import read
        from unittest.mock import patch
        h,s=self.host();errors=read(ROOT/'evidence/b3_r1_history_assisted_050/agent_error_inventory.json')['errors']
        cases=[next(e for e in errors if e['tool']=='evidence_read' and predicate(e)) for predicate in (
            lambda e:e['input_excerpt'].get('pointer','').startswith('/result/'),
            lambda e:e['input_excerpt'].get('pointer')=='/control_result_links' and e['input_excerpt'].get('view')=='full',
            lambda e:e['code']=='EVIDENCE_RANGE_REQUIRES_LIST_POINTER',
            lambda e:e['code']=='INVALID_EVIDENCE_POINTER' and e['input_excerpt'].get('fields') and not e['input_excerpt'].get('pointer'),
            lambda e:e['code']=='EVIDENCE_FIELDS_REQUIRES_OBJECT_POINTER')]
        for entry in cases:
            query=self.r1.artifact(entry['reference'])['tool_use']['input']
            with self.subTest(query=query),patch('tools.research.agent.record',return_value=entry['reference']):
                with self.assertRaises((ValueError,KeyError,IndexError)) as caught:
                    read_evidence(h,query,record_read=False)
                feedback=error_feedback(h,dict(name='evidence_read',input=query),caught.exception,s)
                nav=feedback['evidence_navigation'];self.assertEqual(nav['reference'],query['reference'])
                read_evidence(h,nav['corrected_query'],record_read=False)
                for suggested in nav.get('list_queries',[]):read_evidence(h,suggested,record_read=False)
        h.store.transaction.assert_not_called();h.store.reserve.assert_not_called()

    def test_diagnose_intent_does_not_dispatch_native_or_charge_mathematics(self):
        from unittest.mock import patch
        from tools.research import core,diagnostic
        from tools.research.research_context import tool_feedback
        h,s=self.host();before=deepcopy(s);candidate=list(s['candidates'].values())[-1]
        value=dict(action='diagnose',hypothesis='Offline intent fixture',expected_observation='Read existing evidence',
            weakening_observation='No new computation',fixed_conditions='Frozen task',stopping_condition='End fixture',
            interpretation='Not scientific evidence',decision=dict(hypothesis_id='fixture',research_intent='DIAGNOSE',
            selected_method='mujoco_direct_control_v1',selected_candidate=candidate))
        with patch.object(core,'guard'),patch.object(core,'save',return_value=candidate),patch.object(core,'update'),\
                patch.object(diagnostic,'save',return_value=candidate),patch.object(diagnostic,'update'),\
                patch('tools.research.research_context.save',return_value=candidate),\
                patch.object(h.store,'reserve',return_value=(dict(execution_id='offline-fixture'),True)),\
                patch('tools.research.analysis.dispatch') as worker:
            output=core.dispatch(h,value,'offline-diagnose-fixture')
            feedback=tool_feedback(h,output)
        result=output['result'];self.assertEqual(result['numerical_evidence'],[])
        self.assertEqual(result['new_scientific_computations'],0)
        self.assertEqual(result['execution_feedback']['new_scientific_computations'],0)
        self.assertEqual(result['execution_feedback']['status'],'read_only_diagnosis_completed')
        self.assertEqual(feedback['execution_feedback'],result['execution_feedback'])
        self.assertEqual(output['scientific_results'],[]);self.assertEqual(s,before);worker.assert_not_called()
        read_evidence(h,result['execution_feedback']['execution_entry']['methods_query'],record_read=False)


class ScientificFeedbackTests(unittest.TestCase):
    """Frozen C3 artifacts only; no worker, Provider or writable historical Store."""
    @classmethod
    def setUpClass(cls):
        from tests.research.c3_readiness_audit import FrozenDecisionBoundary
        from tools.research.config import ROOT
        cls.before=FrozenDecisionBoundary(ROOT,'A')
        cls.after=FrozenDecisionBoundary(ROOT,'C')
        cls.addClassCleanup(cls.before.archive.close)
        cls.addClassCleanup(cls.after.archive.close)

    def test_empty_fields_schema_runtime_and_exact_summary_correction(self):
        import json
        from jsonschema import Draft202012Validator
        from tools.research.contracts import EvidenceQuery
        from tools.research.agent import error_feedback
        from unittest.mock import patch
        b=self.before;h=b.host;reference=b.saved_state['results'][0]
        invalid=dict(reference=reference,view='fields',fields=[])
        validator=Draft202012Validator(EvidenceQuery.model_json_schema())
        for query in (invalid,dict(reference=reference,view='fields')):
            self.assertTrue(list(validator.iter_errors(query)))
            with self.assertRaisesRegex(ValueError,'EVIDENCE_FIELDS_REQUIRES_NONEMPTY_FIELDS') as caught:
                read_evidence(h,query,record_read=False)
            with patch('tools.research.agent.record',return_value=reference):
                feedback=error_feedback(h,dict(name='evidence_read',input=query),caught.exception,b.saved_state)
            self.assertEqual(feedback['error_code'],'EVIDENCE_FIELDS_REQUIRES_NONEMPTY_FIELDS')
            correction=json.loads(feedback['expected'].split('Use exact query: ',1)[1])
            self.assertEqual(correction,dict(reference=reference,view='summary'))
            read_evidence(h,correction,record_read=False)
        for view in ('full','summary','range','working_set','mathematical_capabilities'):
            query=dict(reference=reference,view=view)
            validator.validate(query);self.assertEqual(EvidenceQuery.model_validate(query).fields,[])
        selected=dict(reference=reference,view='fields',fields=['status'])
        validator.validate(selected);self.assertIn('status',read_evidence(h,selected,record_read=False))
        h.store.reserve.assert_not_called();h.store.transaction.assert_not_called()

    def test_finite_native_failure_scope_reaches_card_l0_and_mathematical_view(self):
        import json
        from tools.research.research_context import agent_decision_brief
        b=self.after;h=b.host;r=b.saved_state['analysis_results'][0];original=b.artifact(r)
        card=plain(result_card(h,r));view=mathematical_decision_view(card)
        self.assertNotEqual(card['evidence_summary']['claim_kind'],'MODEL_EXCLUSION')
        for limits in (card['evidence_summary']['unresolved'],view['unresolved']['evidence_limits']):
            self.assertTrue(any('neither proves structural infeasibility' in text for text in limits))
        # The last native result remains readable even when an independent replay is newer.
        brief=agent_decision_brief(h)
        self.assertIn('neither proves structural infeasibility',json.dumps(brief))
        feedback=read_evidence(h,dict(reference=r,view='working_set',pointer='/mathematical_decision_view'),record_read=False)
        self.assertEqual(feedback['unresolved'],view['unresolved'])
        self.assertEqual(view['owning_study'],original['owning_study'])
        self.assertEqual(original,b.artifact(r));self.assertEqual(h.store.session()['state'],b.saved_state)
        self.assertTrue(brief['mathematical_capabilities']['methods'])
        h.store.reserve.assert_not_called();h.store.transaction.assert_not_called()

    def test_current_history_native_and_replay_costs_remain_separate(self):
        from tools.research.budget import decision_budget
        from tools.research.research_context import history_index
        # Native cost is zero in R1 before execution, even with imported native evidence.
        b=self.before;budget=decision_budget(b.host)['science_budget']
        self.assertEqual(budget['native']['recorded_physics_steps'],0)
        self.assertEqual(budget['charged_mathematical_evaluations'],0)
        history=history_index(b.host)
        self.assertTrue(any((r['cost']['native'] or {}).get('physics_steps')==8000 for r in history))
        self.assertTrue(all(r['historical_only'] and 'no charge' in r['cost']['accounting_scope'] for r in history))
        b=self.after;h=b.host;r=b.saved_state['analysis_results'][0]
        budget=decision_budget(h)['science_budget'];raw=b.artifact(r)
        self.assertEqual((budget['native']['recorded_rollouts'],budget['native']['recorded_physics_steps']),(8,8000))
        resources={c.name:c for c in result_card(h,r).resources}
        self.assertEqual(resources['native_physics_steps'].amount,8000)
        self.assertEqual(read_evidence(h,plain(resources['native_physics_steps'].source),record_read=False),8000)
        self.assertEqual(raw['native_dynamics']['cost']['optimization_evaluations'],8)
        replay_resources={c.name:c for c in result_card(h,b.saved_state['physical_replays'][0]).resources}
        self.assertEqual(replay_resources['physics_steps'].amount,1000)
        self.assertEqual(budget['native']['recorded_physics_steps'],8000)
        # Missing-cost fixture is a projection check, never new scientific evidence.
        from tools.research.evidence_views import _resources
        missing={c.name:c.amount for c in _resources(dict(native_dynamics={}),r)}
        self.assertIsNone(missing['native_physics_steps']);self.assertIsNone(missing['native_rollouts'])
        from unittest.mock import patch
        partial=deepcopy(raw);partial['native_dynamics']['cost'].pop('physics_steps')
        original=h.store.artifact.side_effect
        with patch.object(h.store.artifact,'side_effect',lambda ref,**kw:partial if plain(ref)==r else original(ref,**kw)):
            self.assertFalse(decision_budget(h)['science_budget']['native']['cost_record_complete'])
        h.store.reserve.assert_not_called();h.store.transaction.assert_not_called()


if __name__=='__main__':unittest.main()
