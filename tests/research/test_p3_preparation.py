"""Configuration and contract preflight only; never prepare a Study or Worker."""
import hashlib,json
from pathlib import Path
from types import SimpleNamespace
import unittest
from extensions.reference.contracts import PassiveStageV2,PassiveStiffnessV2,PassiveMechanismV2
from extensions.reference.passive_program import force_at
from extensions.tendon_family.family_space import parse_space
from tools.state_io import digest

ROOT=Path(__file__).resolve().parents[2]
DOC=ROOT/'docs/research/feedback-repair-p3-preparation-20261109'


class P3PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=ROOT/'configs/research/passive_progressive_stiffness_dev_v1.json'
        cls.protocol=json.loads(cls.path.read_bytes())
        cls.manifest=json.loads((DOC/'p3-source-manifest.json').read_text(encoding='utf-8'))
        cls.draft=json.loads((DOC/'p3-preparation-draft.json').read_text(encoding='utf-8'))

    def test_authoritative_file_hash_task_identity_and_readonly_source(self):
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),'3f88a70e4461a384969d2173ae7c5da68379556344fd89df3fed7a7e993b064d')
        self.assertEqual(digest(self.protocol),self.manifest['canonical_protocol_identity'])
        self.assertEqual(self.manifest['source_commit'],'83d9b8f35b4015a924e0f8c32d073607247f92b9')
        self.assertTrue(self.manifest['final_freeze']['protocol_matches'])
        self.assertEqual(self.manifest['source_store']['snapshot']['development_freeze']['protocol'],self.protocol)

    def test_five_stages_vectors_timing_and_interval_end_smoothstep_contract(self):
        p=self.protocol;programs={}
        for case,direction in p['directions'].items():
            stages=[];start=0.;previous=0.
            for stage in p['stages']:
                end=start+stage['duration_s']
                stages.append(PassiveStageV2(name=stage['name'],start_s=start,end_s=end,
                    force_start_world_n=[previous*v for v in direction],force_end_world_n=[stage['force_n']*v for v in direction],
                    interpolation='smoothstep',ramp_until_s=start+p['ramp_s'],
                    observation_window_s=[start,end],scoring_window_s=[end-p['tail_s'],end]))
                start=end;previous=stage['force_n']
            self.assertEqual(start,20.);programs[case]=stages
            self.assertEqual(p['force_point']['s'],.7)
        goal=SimpleNamespace(programs=programs)
        self.assertEqual(force_at(goal,'plus_x',12.5)[0],[.2,0.,0.])
        self.assertEqual(force_at(goal,'minus_x',12.5)[0],[-.2,0.,0.])
        dt=p['timestep_s'];self.assertEqual(dt,.000125);self.assertEqual(p['scoring_interval_s'],.01)
        alpha=(dt/.5)**2*(3-2*dt/.5)
        self.assertAlmostEqual(force_at(goal,'plus_x',4+dt)[0][0],.05*alpha,places=15)

    def test_same_tendon_mechanism_and_complete_validation_scope(self):
        p=self.protocol;a=p['acceptance']
        spec=PassiveStiffnessV2(load_condition='plus_x',stages=['low','middle','high'],reference_stage='unloaded',
            material_s=.7,direction_world=[1,0,0],**{k:a[k] for k in ('denominator_min_m','denominator_uncertainty_multiplier',
                'stiffness_ratio_min','low_tension_max_n','high_tension_min_n','low_slack_min_m','high_constraint_residual_max_m')})
        self.assertEqual(spec.low_tension_max_n,.005);self.assertEqual(spec.high_tension_min_n,.05)
        self.assertEqual(spec.low_slack_min_m,1e-7);self.assertEqual(spec.high_constraint_residual_max_m,5e-5)
        mechanism=PassiveMechanismV2.model_validate(p['mechanism']);self.assertEqual(mechanism.high_displacement_increase_min,1.25)
        cases=self.manifest['final_freeze']['case_scope'];self.assertEqual(len(cases),8)
        scope=self.draft['required_validation_scope'];self.assertEqual(scope['half_timestep_s'],.0000625)
        self.assertEqual(scope['perturbation']['amplitude_rad'],.001);self.assertEqual(scope['max_displacement_difference_m'],.001)
        self.assertTrue(scope['per_physics_step_checks']);self.assertTrue(scope['independent_saved_state_replay'])

    def test_original_domain_and_launch_blockers_are_explicit(self):
        family=json.loads((ROOT/'configs/research/family_space_p3_original_v1.json').read_bytes())
        parsed=parse_space(family)
        self.assertEqual(list(parsed.segment_count_bounds),[2,6]);self.assertEqual(list(parsed.tendon_count_bounds),[2,4])
        spec=self.draft['study_spec_draft'];self.assertEqual(spec['family_search']['segment_counts'],[2,3,4,5,6])
        self.assertEqual(spec['family_search']['tendon_counts'],[2,3,4]);self.assertFalse(spec['knowledge']['allow_benchmark_answers'])
        self.assertTrue(self.draft['preparation_only']);self.assertGreater(len(self.draft['blockers']),0)
        self.assertFalse((ROOT/spec['evidence_destination']).exists())
        self.assertIsNone(self.draft['budget_policy']['mathematical_cumulative_limit'])


if __name__=='__main__':unittest.main()
