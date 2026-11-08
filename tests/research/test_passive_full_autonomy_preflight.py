"""Configuration/admission checks only; no numerical or Provider workers."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from tools.platform_store import plain
from tools.research import core, search
from tools.research.config import ROOT, resolve
from tools.research.state import state
from tools.research.design import generate_candidate, verify_candidate
from tools.research.contracts import FamilyMixedSearch, FamilyMixedSearchV2, MechanismStudy
from tools.research.structure_research import parameters, prepare_context
from tools.research.scientific_intent import parameter_catalog, question_schema
from tools.research.optimal_capability import freeze_family_variables
from tools.state_io import read, digest

PROFILE=ROOT/'configs/research/study_passive_base_only_full_autonomous_20261108.json'


class FullAutonomyPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(dir=ROOT/'runs',prefix='full-autonomy-offline-')
        fixture=resolve(PROFILE)
        fixture['study_id']='offline-full-autonomy-preflight-'+uuid4().hex
        fixture['configuration']['run_id']=fixture['study_id']
        fixture.pop('resolved_identity');fixture['resolved_identity']=digest(fixture)
        with patch('tools.research.config.resolve',return_value=fixture):
            cls.h=core.prepare(PROFILE,directory=Path(cls.temp.name)/'fresh-offline-fixture')
        from tools.research.agent import decision_packet
        # Exercise the actual empty-Study startup packet, including legacy
        # Knowledge metadata, before any candidate exists. No Provider send.
        cls.startup_packet=decision_packet(cls.h,research_only=True)
        cls.spec=state(cls.h)['spec']
        generated=generate_candidate(cls.h,dict(version='serial_family_generation_v2',
            family_space_identity=cls.spec['family_space_identity'],segment_count=2,tendon_count=4),
            dict(origin='offline_configuration_fixture_no_scientific_execution'))
        assert generated['status']=='generated',generated
        cls.ref=generated['candidate']
        cls.c=verify_candidate(cls.h,cls.ref)

    @classmethod
    def tearDownClass(cls):
        import gc
        gc.collect()  # Release SQLite context-manager connections before Windows removal.
        assert Path(cls.temp.name).resolve().is_relative_to((ROOT/'runs').resolve())
        cls.temp.cleanup()

    def study(self,**changes):
        return MechanismStudy(**dict(operation='interact',
            target=dict(quantity='tangent_compliance',reduction='norm'),
            parameter_paths=['segments.0.length_m','segments.0.young_pa'],
            parameter_bounds={'segments.0.length_m':(.08,.24),'segments.0.young_pa':(1e6,1e7)},
            point_semantics='re_equilibrated',load_condition='s3_positive',
            effect_semantics='mechanism_effect',max_evaluations=4,**changes))

    def test_complete_registry_discovery_and_open_domain(self):
        rows=parameters(self.spec,self.c)
        actual=[r for r in rows if '*' not in r['parameter_id']]
        self.assertTrue(all(r['study_authorized'] for r in actual))
        catalog=parameter_catalog(self.spec,self.c)
        self.assertEqual({r['parameter_id'] for r in catalog},{r['parameter_id'] for r in rows})
        length=next(r for r in catalog if r['parameter_id']=='segments.0.length_m')
        self.assertTrue(length['selectable'] and length['local_domain_required'])
        self.assertIsNone(length['domain']['maximum'])
        self.assertFalse(next(r for r in catalog if r['parameter_id'].startswith('control_weights.'))['effective'])
        self.assertEqual(freeze_family_variables(self.spec['family_space'],dict(version='family_sensitivity_v2',variables=['*']))['variables'],['*'])

    def test_local_intervals_and_both_passive_block_modes(self):
        before=deepcopy(self.spec['family_space'])
        context=prepare_context(self.spec,self.c,self.study(),[])
        self.assertEqual(context['minimum_evaluations'],4)
        self.assertEqual(context['selected_parameters'][0]['physical_domain']['maximum'],None)
        for mode,effect,point,target in (
            ('passive_equilibrium','mechanism_effect','re_equilibrated',dict(quantity='tangent_compliance',reduction='norm')),
            ('passive_task_response','finite_time_task_response','frozen_task_initial_state',dict(quantity='finite_time_task_violation',goal='decrease'))):
            q=FamilyMixedSearchV2.model_validate(dict(version='family_mixed_search_v2',method='bounded_coupled_block_v1',
                family_space_identity=self.spec['family_space_identity'],previous_candidate_ref=self.ref,
                analysis=dict(operation='interact',effect_semantics=effect,operating_point=point,
                    physical_problem='passive_unilateral_equilibrium',control_treatment='no_active_control',
                    target=target,parameter_paths=self.study().paths,parameter_bounds=self.study().parameter_bounds,
                    **(dict(load_condition='s3_positive') if mode=='passive_equilibrium' else {}))))
            result=search.coupled_problem(self.h,q,4)
            self.assertIsNotNone(result)
        self.assertEqual(before,self.spec['family_space'])
        for bounds in ({'segments.0.length_m':(0,.24)}, {'segments.0.length_m':(.17,.24)},
                {'segments.0.length_m':(.24,.08)}, {'unregistered':(0,1)}):
            study=self.study().model_copy(update=dict(parameter_bounds=bounds))
            with self.assertRaises(ValueError):prepare_context(self.spec,self.c,study,[])
        with self.assertRaises(ValueError):prepare_context(self.spec,self.c,self.study().model_copy(update=dict(parameter_bounds={})),[])

    def test_dynamic_block_all_conditions_alias_preserves_frozen_scope(self):
        query=dict(version='family_mixed_search_v2',method='bounded_coupled_block_v1',
            family_space_identity=self.spec['family_space_identity'],previous_candidate_ref=self.ref,
            analysis=dict(operation='interact',effect_semantics='finite_time_task_response',
                operating_point='frozen_task_initial_state',physical_problem='passive_unilateral_equilibrium',
                control_treatment='no_active_control',target='finite_time_task_violation',
                parameter_paths=self.study().paths,parameter_bounds=self.study().parameter_bounds))
        before=self.h.store.remaining()
        implicit=search.coupled_problem(self.h,FamilyMixedSearchV2.model_validate(query),4)
        query['analysis']['load_condition']='all_frozen_conditions'
        explicit_query=FamilyMixedSearchV2.model_validate(query)
        explicit=search.coupled_problem(self.h,explicit_query,4)
        self.assertEqual(explicit_query.analysis.load_condition,'all_frozen_conditions')
        self.assertEqual(explicit['analysis_request'],implicit['analysis_request'])
        for key in ('points','profile','task_identity','protocol','max_evaluations'):
            self.assertEqual(explicit.get(key),implicit.get(key))
        query['analysis']['load_condition']='s3_positive'
        with self.assertRaisesRegex(ValueError,'DYNAMIC_TASK_ALWAYS_REQUIRES_ALL_FROZEN_LOADS'):
            search.coupled_problem(self.h,FamilyMixedSearchV2.model_validate(query),4)
        self.assertEqual(self.h.store.remaining(),before)

    def test_v4_precheck_honors_local_intervals_without_dispatching_science(self):
        from tools.research.scientific_intent import compile_question
        payload=dict(version='scientific_question_v4',domain='structure',structure=dict(
            operation='interact',effect_semantics='finite_time_task_response',target='finite_time_task_violation',
            parameter_paths=self.study().paths,parameter_bounds={k:list(v) for k,v in self.study().parameter_bounds.items()},
            operating_point='frozen_task_initial_state',control_treatment='no_active_control',
            physical_problem='passive_unilateral_equilibrium',load_condition='all_frozen_conditions',requested_budget=4))
        intent=dict(candidate=self.ref,agent_hypothesis=dict(next_research_action='mechanism_research'))
        before=self.h.store.remaining()
        with patch('tools.research.scientific_intent.completed_question_plan',return_value=intent), \
                patch('tools.research.scientific_intent.selected_question_schema',return_value=question_schema(self.spec,self.c)), \
                patch('tools.research.scientific_intent.compile_mechanism',return_value=dict(status='metadata_admitted')) as dispatch:
            result=compile_question(self.h,payload,tool_use_id='offline-local-domain')
            self.assertEqual(result['status'],'metadata_admitted',result)
            self.assertEqual(dispatch.call_count,1)
            missing=deepcopy(payload);missing['structure']['parameter_bounds']={}
            denied=compile_question(self.h,missing,tool_use_id='offline-missing-domain')
            self.assertEqual(denied['status'],'unsupported')
            self.assertIn('Open physical domain',denied['reason'])
            outside=deepcopy(payload);outside['structure']['parameter_bounds']['segments.0.length_m']=[0.,.24]
            denied=compile_question(self.h,outside,tool_use_id='offline-invalid-domain')
            self.assertIn('LOCAL_INTERVAL_MUST_CONTAIN_CURRENT_VALUE_WITHIN_PHYSICAL_DOMAIN',denied['reason'])
            self.assertEqual(dispatch.call_count,1)
        self.assertEqual(self.h.store.remaining(),before)

    def test_clearance_failure_retains_original_constructor_measurements(self):
        from extensions.tendon_family import generated_serial as family
        from tools.research.design import construction_diagnostic
        request=dict(version='serial_family_generation_v2',family_space_identity=self.spec['family_space_identity'],
            segment_count=2,tendon_count=4,spans=[dict(first_segment=0,last_segment=1,count=4,radius_m=.001)])
        try:family.generate_family(dict(space=self.spec['family_space'],request=request))
        except ValueError as exc:
            self.assertEqual(str(exc),'SECTION_ROUTE_CLEARANCE')
            diagnostic=construction_diagnostic(exc)
        else:self.fail('Fixture must fail the original route-clearance check')
        self.assertEqual(diagnostic['status'],'failed_geometry_check')
        self.assertEqual(diagnostic['segment'],'segment_0')
        self.assertEqual(diagnostic['tendon'],'tendon_0')
        self.assertEqual(diagnostic['span_index'],0)
        self.assertAlmostEqual(diagnostic['actual_distance_m'],.001)
        self.assertLess(diagnostic['actual_distance_m'],diagnostic['required_distance_m'])
        self.assertEqual(construction_diagnostic(ValueError('SECTION_ROUTE_CLEARANCE'))['status'],'unavailable')

    def test_coordinate_grant_and_scientific_schema(self):
        from extensions.tendon_family.family_space import search_domains
        for mode in ('passive_equilibrium','passive_task_response'):
            q=FamilyMixedSearch.model_validate(dict(version='family_mixed_search_v1',
                family_space_identity=self.spec['family_space_identity'],variable_groups=['lengths'],
                segment_counts=[2],tendon_counts=[4],screening_fidelity='diagnostic',
                objective='equilibrium_qualification' if mode=='passive_equilibrium' else 'task_violation',
                operating_point='standardized_initial_pretension',max_proposals=4,max_evaluations=4,
                evaluation_mode=mode,bounds={'length_m':(.08,.24)}))
            search_domains(self.spec['family_space'],q,self.spec['family_search'])
        schema=question_schema(self.spec,self.c)
        self.assertIn('parameter_bounds',schema['$defs']['ScientificStructureV4']['properties'])
        self.assertFalse(self.spec['family_search']['require_explicit_start'])
        self.assertEqual(self.spec['initial_structure_strategy'],'agent_choice')

    def test_task_knowledge_budgets_and_fresh_store(self):
        from tools.research.budget import mathematical_remaining,replay_remaining
        from tools.research.task_constraints import registered_analysis_method_names
        from tools.research.math_capability_catalog import capability_inventory
        original=read(ROOT/'tasks/phs2d_original_ten_v1_2.json')
        self.assertEqual(self.startup_packet['study_id'],self.h.run_id)
        canonical=deepcopy(original['task'])
        canonical['initializer']['parameters']['data']=dict(rule='all_candidate_dofs_zero_v1')
        self.assertEqual(self.spec['canonical_task_identity'],digest(canonical))
        self.assertEqual(self.spec['canonical_task'],canonical)
        self.assertEqual(len(original['task']['goal']['data']['load_conditions']),10)
        self.assertEqual(set(registered_analysis_method_names()),{k for k,v in capability_inventory().items() if v['interface_status']=='registered'})
        rows=self.spec['knowledge_manifest']['entries'];keys={(r['entry_id'],r['revision']) for r in rows}
        for key in [('skill-parameter-model','3'),('skill-matched-comparison','3'),('skill-local-to-experiment','3'),
                ('general-routing','2'),('general-material-inertia','2'),('mechanism-research-process','1'),('phs2d-research-process','2')]:
            self.assertIn(key,keys)
        self.assertFalse(any(r.get('benchmark_sensitive') for r in rows))
        self.assertIsNone(mathematical_remaining(self.spec,10**9))
        self.assertIsNone(replay_remaining(self.spec,10**9))
        self.assertIsNone(self.spec['analysis_cap_s'])
        self.assertEqual(self.spec['family_space']['segment_count_bounds'],[1,None])
        self.assertEqual(self.spec['family_space']['tendon_count_bounds'],[1,None])
        current=state(self.h)
        self.assertFalse(current['plans'] or current['analysis_results'] or current['results'] or current['pending'])
        self.assertEqual(current['mathematical_evaluations'],0)
        self.assertEqual(self.h.store.remaining()['occupied'],{})
        self.assertFalse(any(e['kind']=='r3_request' for e in self.h.store.events(self.h.run_id)))
        self.assertNotEqual(self.h.store.root,ROOT/'runs/research/passive-base-only-autonomous-study-20261107')


if __name__=='__main__':unittest.main()
