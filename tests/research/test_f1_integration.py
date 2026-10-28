"""F1 regressions matching saved Main-Off error shapes; synthetic evidence only."""
from copy import deepcopy
import json
from uuid import uuid4
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from pydantic import ValidationError
from tools.research import agent, core
from tools.research.contracts import EvidenceQuery, Plan
from tools.research.config import ROOT, resolve
from tools.research.design import generate_candidate
from tools.research.evidence_policy import admit_decision
from tools.research.state import state, update
from tests.research.test_recent_round_tools import provision


class F1IntegrationTests(unittest.TestCase):
    def test_fresh_opt_in_resolves_without_changing_legacy_configuration(self):
        original=ROOT/'configs/research/study_bf5_public.json'
        legacy=resolve(original)
        self.assertNotIn('architecture',legacy['research_decisions'])
        self.assertNotIn('output_context_reserve_tokens',legacy['configuration']['policy']['model'])
        value=json.loads(original.read_text(encoding='utf8'))
        value['study_id']='offline-f1-config-'+uuid4().hex[:8]
        value['family_space']='family_space_base_only_tracking_v1.json'
        value['research_decisions'].update(architecture='english_decision_v1',
            role_policy=dict(version='research_roles_v2',main=dict(thinking='disabled',reasoning_effort='none'),
                reporter=dict(thinking='enabled',reasoning_effort='low')),
            analysis_interface='bound_scientific_variables_v2',
            conversation_policy=dict(version='recent_round_trace_v1',trace_limit=8),
            tool_schema_policy=dict(version='on_demand_tools_v1'))
        path=ROOT/'configs/research'/('._'+value['study_id']+'.json')
        try:
            path.write_text(json.dumps(value),encoding='utf8');fresh=resolve(path)
        finally:path.unlink()
        self.assertEqual(fresh['configuration']['policy']['model']['reasoning_effort'],'none')
        self.assertEqual(fresh['configuration']['policy']['model']['output_context_reserve_tokens'],32768)
        self.assertEqual(fresh['configuration']['task'],legacy['configuration']['task'])
        self.assertEqual(fresh['budgets'],legacy['budgets'])
        self.assertEqual(fresh['family_space']['conditional_rules'],'base_only_consecutive_spans_v1')
        self.assertEqual(resolve(original),legacy)

    def test_saved_error_shapes_repair_without_scientific_execution(self):
        h=provision();spec=deepcopy(state(h)['spec'])
        spec['research_decisions']['analysis_interface']='bound_scientific_variables_v2'
        update(h,spec=spec)
        candidate=generate_candidate(h,dict(version='serial_family_generation_v2',
            family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=4),
            dict(origin='synthetic offline F1 regression'))['candidate']
        before=h.store.remaining()
        raw=dict(action='diagnose',hypothesis='Offline saved-error shape.',
            expected_observation='Local diagnostic.',weakening_observation='Contrary evidence.',
            fixed_conditions='Frozen fixture.',stopping_condition='No computation.',interpretation='Unmeasured.',
            decision=dict(hypothesis_id='fixture',research_intent='DIAGNOSE',selected_method='endpoint'))
        schema=agent.plan_schema(['diagnose'],decision_required=True,diagnose_candidate_required=True,focused=True)
        error=next(e for e in Draft202012Validator(schema).iter_errors(raw) if list(e.absolute_path)==['decision'])
        feedback=agent.error_feedback(h,dict(name='research_plan',input=raw,toolUseId='missing-candidate'),error,state(h))
        self.assertEqual(feedback['field'],'decision.selected_candidate')
        with self.assertRaisesRegex(ValueError,'SELECTED_ANALYSIS_CANDIDATE_REQUIRED'):
            admit_decision(h,Plan.model_validate(raw))
        raw['decision']['selected_candidate']=candidate
        Draft202012Validator(schema).validate(raw)
        with patch('tools.research.core.guard'):
            core.dispatch(h,raw,'offline-f1-diagnose')
        self.assertFalse(state(h)['analysis_results'])  # diagnose records intent only.

        empty=dict(reference=candidate,view='fields',pointer='/eligible_methods')
        with self.assertRaisesRegex(ValidationError,'EVIDENCE_FIELDS_REQUIRES_NONEMPTY_FIELDS'):
            EvidenceQuery.model_validate(empty)
        self.assertFalse(Draft202012Validator(EvidenceQuery.model_json_schema()).is_valid(empty))
        query=dict(reference=candidate,view='full',pointer='/methods')
        original=deepcopy(query)
        with self.assertRaises(KeyError) as failure:
            core.read_evidence(h,query)
        repair=failure.exception.evidence_navigation['corrected_query']
        self.assertEqual(query,original)
        self.assertEqual(repair,dict(reference=candidate,view='mathematical_capabilities',pointer='/methods'))
        detail=core.read_evidence(h,repair)['endpoint']
        self.assertEqual(detail['request_template']['candidate'],candidate)
        self.assertEqual(detail['request_template']['protocol'],spec['analysis_protocol'])
        self.assertEqual(h.store.remaining()['used']['model_calls'],before['used']['model_calls'])
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertFalse(state(h)['physical_replays'])
