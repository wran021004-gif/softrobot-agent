"""Isolated engineering fixtures; no Provider, physics Worker or scientific progress."""
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from tools.platform_store import plain
from tools.research import config
from tools.research.contracts import ScientificControlEffort,ControlSeedRequest,AnalysisRequest,REGISTERED_MATHEMATICS_SCOPE
from tools.research.scientific_intent import control_settings,compile_question,selected_question_schema
from tools.research.structure_intent import compile_search
from tools.research.physical_replay import seed_control,binding
from tools.research.local_control_search import search
from tools.research.evidence_views import native_control_domain
from tools.research.structure_research import parameters
from tools.research.state import state,update
from tools.research.experience import retrieve,retrieval_hint
from tools.research.research_context import agent_decision_brief,research_decision_brief_v3,information_flow_brief
from tests.research import test_m1_native_search_scope as fixtures
from tests.research.test_p63a_math_interface import generate,diagnose
from tests.research.test_research_authorization_preflight import approve

SPEC=config.ROOT/'configs/research/study_m1_low_tendon_speed004_v1.json'
EFFORT=dict(method='pattern',evaluation_requests=24,iterations=8,knot_count=2,coefficient_limit_n=8.,initial_radius_n=4.)


class ControlMechanismScopeTests(unittest.TestCase):
    def test_legacy_defaults_and_invalid_scales(self):
        spec=config.resolve(SPEC);old=dict(method='pattern',evaluation_requests=4)
        self.assertNotIn('coefficient_limit_n',plain(ScientificControlEffort.model_validate(old)))
        q=control_settings(spec,old)
        self.assertEqual((q.coefficient_limit_n,q.initial_radius_n,q.minimum_radius_n,q.difference_step_n),(2.,.1,.0001,.01))
        for changes in (dict(coefficient_limit_n=0),dict(initial_radius_n=float('inf')),dict(initial_radius_n=9)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):control_settings(spec,{**EFFORT,**changes})

    def test_v4_and_joint_search_share_explicit_domain(self):
        with patch.object(fixtures,'SPEC',SPEC),fixtures.scoped_fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            c=generate(h);source=seed_control(h,ControlSeedRequest(candidate=c,tensions_n=[[3.]*4]))['source'];diagnose(h,c,'scientific_question')
            self.assertEqual(h.store.artifact(source)['trajectory']['tensions_n'][0],[3.]*4)
            with self.assertRaises(ValueError):seed_control(h,ControlSeedRequest(candidate=c,tensions_n=[[9.]*4]))
            q=dict(version='scientific_question_v4',domain='control',control=dict(
                effect_semantics='reoptimized_task_capability',numerical_method='mujoco_direct_control_v1',
                control_scope=dict(mode='full_task'),control_search_effort=EFFORT,source_selection=dict(control_source=source)))
            compiled=compile_question(h,q,tool_use_id='wide-v4')
            self.assertEqual(compiled['status'],'ready',compiled)
            settings=compiled['request']['control_optimization']['settings']
            self.assertEqual((settings['coefficient_limit_n'],settings['initial_radius_n']),(8.,4.))
            schema=selected_question_schema(h)
            self.assertIn('coefficient_limit_n',str(schema));self.assertIn('initial_radius_n',str(schema))
            batch=compile_search(h,fixtures.proposal(control_search_effort=EFFORT),'wide-batch')
            self.assertEqual(batch['search']['control_settings'],settings)
            self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_original_optimizer_exceeds_old_domain_but_keeps_physical_inputs(self):
        with patch.object(fixtures,'SPEC',SPEC),fixtures.scoped_fixture() as h:
            c=generate(h);cfg=h.store.artifact(c)['configuration'];entry=seed_control(h,ControlSeedRequest(candidate=c))
            src=h.store.artifact(entry['source']);n=len(src['trajectory']['tendon_order']);seen=[];sources={}
            start=dict(id='fixture',schedule=src,limits=[8.]*n,task_options={})
            settings=control_settings(state(h)['spec'],EFFORT)
            def evaluate(start,source,metadata):
                binding(cfg,source['trajectory']);u=np.asarray(source['trajectory']['tensions_n']);seen.append(u)
                ref=str(len(seen));sources[ref]=source
                return dict(reference=ref,cost_s=0.,outputs={},task_gap=dict(valid_complete=True,accepted=False,
                    normalized_gap=float(np.mean((u-7.)**2)+1)))
            out=search([start],evaluate,plain(settings),rank_key=lambda r:r['task_gap']['normalized_gap'])
            self.assertGreater(max(u.max() for u in seen),2.2)
            self.assertTrue(all(u.min()>=0 and u.max()<=8 for u in seen))
            raw=dict(requested_operation=dict(control_optimization=dict(settings=plain(settings))),
                binding=dict(tension_bounds_n=[[0.,8.]]*n),native_dynamics=dict(original_schedule=src,
                    optimized_schedule=sources[out['best']['reference']],optimization=out))
            domain=native_control_domain(raw)
            self.assertGreater(max(row[1] for row in domain['recorded_schedule_range_n']),2.2)
            self.assertEqual(domain['settings']['coefficient_limit_n'],8.)
            self.assertIn('not joint control-space coverage',domain['scope'])

    def test_v4_current_scope_admits_effective_length_material_section_and_routing(self):
        with patch.object(fixtures,'SPEC',SPEC),fixtures.scoped_fixture() as h:
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            c=generate(h);diagnose(h,c,'scientific_question');rows=parameters(state(h)['spec'],h.store.artifact(c))
            paths=['segments.0.length_m','segments.0.young_pa','spans.0.radius_m','spans.0.phase_rad']
            paths.append(next(r['parameter_id'] for r in rows if '.sections.' in r['parameter_id'] and r['mechanism_differentiation']['supported']))
            for i,path in enumerate(paths):
                q=dict(version='scientific_question_v4',domain='structure',structure=dict(operation='differentiate',
                    effect_semantics='mechanism_effect',parameter_paths=[path],
                    target=dict(quantity='tip_acceleration_input_map',reduction='norm',goal='increase'),
                    operating_point='frozen_task_initial_state',control_treatment='fixed_absolute_tensions',requested_budget=5))
                out=compile_question(h,q,tool_use_id='mechanism-path-'+str(i))
                self.assertEqual(out['status'],'ready',(path,out))
                self.assertEqual(AnalysisRequest.model_validate(out['request']).mechanism_study.parameter_paths,[path])
            brief=agent_decision_brief(h);compact=information_flow_brief(brief,research_decision_brief_v3(brief))
            mechanism=compact['mechanism_research']
            self.assertIn('instantaneous_braking',mechanism['mechanism_categories'])
            self.assertTrue(mechanism['parameter_domains'])
            self.assertIn('full task improvement unmeasured',mechanism['task_scope'])
            self.assertEqual(state(h)['mathematical_evaluations'],0)

    def test_existing_experience_and_new_skill_retrieve_and_read_without_science_credit(self):
        with patch.object(fixtures,'SPEC',SPEC),fixtures.scoped_fixture() as h:
            before=h.store.remaining()
            for entry in ('experience-structure-readaptation','skill-control-or-structure'):
                found=retrieve(h,dict(operation='search',entry_id=entry))
                self.assertEqual(len(found['results']),1)
                read=retrieve(h,found['results'][0]['read_query'])
                self.assertTrue(read['results'][0]['content']);self.assertFalse(read['scientific_evidence'])
                self.assertEqual(read['results'][0]['revision'],'1')
            self.assertEqual(h.store.remaining(),before)

    def test_relevant_hint_is_bounded_optional_and_frozen_manifest_controls_access(self):
        with patch.object(fixtures,'SPEC',SPEC),fixtures.scoped_fixture() as h:
            phase=dict(phase='finite_search_structural_review',notice_id='synthetic-review')
            with patch('tools.research.experience.decision_phase',return_value=phase),patch('tools.research.experience.hint_progress',return_value=[]):
                hint=retrieval_hint(h)
            self.assertIn('skill-control-or-structure',hint['skill']['key'])
            self.assertEqual(hint['experience']['read_query'],dict(operation='read',entry_id='experience-structure-readaptation',revision='1'))
            self.assertNotIn('content',hint['experience'])
            delivered=[dict(summary_keys=[hint['skill']['key']],notice_id=phase['notice_id'])]
            with patch('tools.research.experience.decision_phase',return_value=phase),patch('tools.research.experience.hint_progress',return_value=delivered):
                self.assertIsNone(retrieval_hint(h))
            spec=deepcopy(state(h)['spec'])
            spec['knowledge_manifest']['entries']=[r for r in spec['knowledge_manifest']['entries'] if r['entry_id']!='skill-control-or-structure']
            update(h,spec=spec)
            self.assertEqual(retrieve(h,dict(operation='search',entry_id='skill-control-or-structure'))['results'],[])


if __name__=='__main__':unittest.main()
