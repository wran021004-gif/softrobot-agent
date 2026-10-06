"""Focused parameter connection checks; no controller solve or backend execution."""
from copy import deepcopy
from pathlib import Path
from io import BytesIO
from unittest import TestCase
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import numpy as np

from schemas.platform import SessionInput
from tools.platform_store import Store, plain
from tools.platform_registry import registry
from tools.platform_tools import _candidate
from tools.parameter_catalog import study_input, effective_catalog, STUDY_GRANTS
from tools.candidate_parameters import parameter_value, fixed_configuration
from tools.state_io import read, digest
from extensions.tendon_family.compiler import resolve
from extensions.tendon_family.design_decisions import expand_segment
from extensions.tendon_family.contracts import Space, MujocoParameters
from extensions.tendon_family.mjcf import compile_xml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '285236abf99bf36894fa08410ac82fefa177a80179c4ceba15d95f8d1bc8d978'


class ParameterCatalogTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archived = Store(ROOT/'runs/milestone4_autonomous_20261006').artifact({'artifact_id': SOURCE})['effective']
        cls.source = study_input(cls.archived)
        cls.reg = registry()

    def build(self, changes, source=None):
        return plain(_candidate(SessionInput.model_validate(source or self.source), changes, self.reg))

    def test_catalog_preserves_science_and_separates_three_dimensions(self):
        from extensions.tendon_family.gvs_profile import execution_scope
        self.assertEqual(execution_scope(self.archived),execution_scope(self.source))
        self.assertEqual(self.archived['robot'],self.source['robot'])
        catalog=effective_catalog(self.source)
        self.assertEqual(set(catalog['usable_pool']),set(STUDY_GRANTS))
        row=next(r for r in catalog['parameters'] if r['id']=='design/near_section_scale')
        self.assertEqual(row['current_value'],.95)
        restricted=effective_catalog(self.source,{'design/near_section_scale':dict(bounds=[.95,1.])})
        self.assertEqual(restricted['usable_pool'],['design/near_section_scale'])
        excluded=next(r for r in restricted['parameters'] if r['id']=='design/far_section_scale')
        self.assertTrue(excluded['technical_support']['supported'])
        self.assertFalse(excluded['study_permission']['permitted'])
        from tools.candidate_parameters import comparison_scope
        narrow=study_input(self.archived,{'design/near_section_scale':dict(bounds=[.95,1.05])})
        changed=self.build({'design/near_section_scale':.96},narrow)
        self.assertEqual(comparison_scope(narrow),comparison_scope(changed))
        changed['robot']['structure']['data']['components'][3]['physics']['young_pa']*=1.1
        self.assertNotEqual(comparison_scope(narrow),comparison_scope(changed))
        unsupported=deepcopy(self.source);unsupported['policy']['controller']['version']='8.0.0'
        self.assertFalse(effective_catalog(unsupported)['usable_pool'])
        self.assertTrue(all(r['reason'] for r in catalog['integration_backlog']))

    def test_combined_edits_survive_and_reach_resolved_backend_quantities(self):
        changes={'components/near/length_m':.165,'components/far/length_m':.125,
            'design/near_section_scale':1.,'design/far_section_scale':1.02,
            'design/near_material_scenario':'baseline','design/far_material_scenario':'stiff',
            'control/recipe/terminal_tip_speed_weight':.075,'control/recipe/holding_tip_speed_weight':.09}
        result=self.build(changes)
        for path,value in changes.items():self.assertEqual(parameter_value(result,path),value)
        a={c['id']:c for c in result['robot']['structure']['data']['components']}
        original=self.source['policy']['candidate_builder']['parameters']['data']['semantic_source']
        b={c['id']:c for c in original['components']}
        self.assertEqual(a['near']['physics']['young_pa'],8e6)
        self.assertAlmostEqual(a['far']['physics']['young_pa'],6.6e6)
        for segment in ('near','far'):
            self.assertEqual(a[segment]['physics']['density_kg_m3'],b[segment]['physics']['density_kg_m3'])
            self.assertEqual(a[segment]['physics']['bending_viscosity_nm2_s'],b[segment]['physics']['bending_viscosity_nm2_s'])
        before=resolve(self.source['robot']['structure']['data'],self.source['policy']['discretization']['data'])
        p=resolve(result['robot']['structure']['data'],result['policy']['discretization']['data'])
        self.assertEqual(p['dofs'],before['dofs'])
        self.assertEqual([t['entity'] for t in p['tendons']],[t['entity'] for t in before['tendons']])
        for part in p['parts']:
            if part['component'] not in ('near','far'):continue
            old=next(q for q in before['parts'] if q['entity']==part['entity'])
            self.assertNotEqual(part['mass_kg'],old['mass_kg'])
            self.assertFalse(np.allclose(part['stiffness_nm_rad'],old['stiffness_nm_rad']))
        scene=dict(timestep_s=.0005,gravity=[0,0,-9.81],floor_id='floor',floor_z_m=-.02,
            mount_position=[0,0,.15],mount_rotation=np.eye(3),target_world_m=[.29,.035,.19],
            control=dict(tension_execution_mode='ideal_tension'))
        stream=BytesIO();compile_xml(p,scene,MujocoParameters(),stream);stream.seek(0)
        xml=ET.parse(stream)
        for part in p['parts']:
            body=xml.find('.//body[@name="'+part['entity']+'"]')
            self.assertEqual(float(body.find('inertial').attrib['mass']),part['mass_kg'])
            for i,joint in enumerate(body.findall('joint')):
                self.assertEqual(float(joint.attrib['stiffness']),part['stiffness_nm_rad'][i])
                self.assertEqual(float(joint.attrib['damping']),part['damping_nm_s_rad'][i])
        # A second source-relative edit must never compound the first scale.
        again=self.build({'design/near_section_scale':.96},result)
        self.assertAlmostEqual(again['robot']['structure']['data']['components'][0]['sections'][0]['section']['parameters']['semi_y_m'],.0096)
        self.assertEqual(parameter_value(again,'design/far_section_scale'),1.02)

    def test_independent_subset_and_no_source_overwrite(self):
        result=self.build({'design/near_section_scale':.96})
        self.assertEqual(fixed_configuration(self.source,['design/near_section_scale']),
            fixed_configuration(result,['design/near_section_scale']))
        space=Space.model_validate(self.source['policy']['candidate_builder']['parameters']['data'])
        data=deepcopy(self.source['robot']['structure']['data'])
        data['components'][0]['physics']['density_kg_m3']=1111.
        data['components'][0]['sections'][0]['section']['angle_rad']=.123
        expand_segment(data,space,{'design/near_material_scenario':'stiff','design/near_section_scale':1.})
        self.assertEqual(data['components'][0]['physics']['density_kg_m3'],1111.)
        self.assertEqual(data['components'][0]['sections'][0]['section']['angle_rad'],.123)
        bad=space.model_copy(deep=True)
        bad.semantic_decisions['design/section_scale']=bad.semantic_decisions['design/near_section_scale']
        bad.parameters['design/section_scale']=bad.parameters['design/near_section_scale']
        with self.assertRaisesRegex(ValueError,'OVERLAPPING_SEMANTIC_DECISION'):
            expand_segment(deepcopy(data),bad,{})
        with self.assertRaisesRegex(ValueError,'CAPABILITY_UNAVAILABLE'):
            self.build({'design/section_scale':1.})

    def test_registered_pool_flows_through_shared_plan_and_batch(self):
        """Engineering in-memory fixture: real plan validation/preparation, zero spend."""
        from tools.candidate_parameters import planning_configuration,comparison_scope
        from tools.parameter_impacts import parameter_impacts
        from tools.platform_search import validate_batch_plan,prepare_offline_batch
        source_ref=dict(artifact_id=SOURCE,media_type='application/json')
        candidate=dict(candidate_id='archived-engineering-fixture',configuration=source_ref,
            owner_run_id='archived-engineering-fixture',execution_id='91c3ba1b01d6499fb26df8f95409401b')
        # Only the host acceptance/alias ledger is substituted. Plan parsing,
        # domains, candidate construction, frozen scope and ask/tell remain real.
        artifacts={SOURCE:dict(effective=deepcopy(self.archived))}
        feedback_ref=dict(artifact_id='e'*64,media_type='application/json')
        result_ref=dict(artifact_id='f'*64,media_type='application/json')
        artifacts[feedback_ref['artifact_id']]=dict(result=result_ref)
        state=dict(role_context=dict(autonomous_scheduling=True,result_feedback=feedback_ref,
            source_report=result_ref,research_records=[dict(facts=dict(candidate=candidate,valid_complete_execution=True))]))
        snapshot=dict(input=deepcopy(self.source))
        store=MagicMock()
        store.session.side_effect=lambda *args,**kwargs:dict(state=state,snapshot=snapshot)
        store.artifact.side_effect=lambda ref,**kwargs:deepcopy(artifacts[ref['artifact_id']])
        def put(db,value):
            identity=digest(value);artifacts[identity]=deepcopy(value)
            return dict(artifact_id=identity,media_type='application/json')
        store.put.side_effect=put
        budget=dict(model_calls=0,tool_calls=20,backend_solves=0,worker_calls=0,wall_s=4000.)
        store.remaining.return_value=dict(remaining=budget,used={k:0 for k in budget})
        store.spendable.return_value=dict(remaining=budget)
        store.config.return_value=dict(budget=budget,authorization_source='zero-cost engineering fixture')
        projected=planning_configuration(store,candidate,self.source['policy'])
        self.assertEqual(projected['robot'],self.archived['robot'])
        self.assertEqual(comparison_scope(projected),comparison_scope(self.source))
        # Legacy common selection from another archived source must survive
        # projection without source-relative reconstruction reverting its values.
        altered=plain(_candidate(SessionInput.model_validate(self.archived),{'design/section_scale':.97},self.reg))
        artifacts[SOURCE]=dict(effective=altered)
        projected_other=planning_configuration(store,candidate,self.source['policy'])
        self.assertEqual(parameter_value(projected_other,'design/near_section_scale'),.97)
        self.assertEqual(projected_other['robot'],altered['robot'])
        self.assertEqual(projected_other['policy']['candidate_builder']['parameters']['data']['semantic_decisions']['design/near_section_scale']['baseline_value'],.97)
        self.assertEqual(self.build({},projected_other)['robot']['structure']['data']['components'][0]['sections'][0]['section']['parameters'],
            altered['robot']['structure']['data']['components'][0]['sections'][0]['section']['parameters'])
        artifacts[SOURCE]=dict(effective=deepcopy(self.archived))
        mappings=parameter_impacts(projected)['mapped']
        self.assertEqual({r['parameter'] for r in mappings},set(STUDY_GRANTS))
        view=SimpleNamespace(run_id='offline-catalog-plan',latest_tested=candidate,baseline=candidate,
            task=dict(execution_model=self.source['policy']['dynamics_model']),acceptance={})
        proposal=deepcopy(read(ROOT/'evidence/stage356_milestone2_20261004/dual_context/search_plan.json')['plan'])
        variables={'design/near_section_scale':dict(kind='continuous',bounds=[.95,1.05]),
            'design/far_material_scenario':dict(kind='discrete',choices=['baseline','compliant','stiff'])}
        proposal.update(source_candidate=candidate,variables=variables,method='search.family_explicit@1.0.0',
            step=None,max_candidates=1,max_backend_attempts=1,target_changed_configurations=1,
            candidates=[{'design/near_section_scale':.96,'design/far_material_scenario':'stiff'}],
            planned_budget=dict(model_calls=8,tool_calls=20,backend_solves=1,worker_calls=0,wall_s=2500.))
        with patch('tools.diagnostic_revision.resolve_aliases',return_value={'plan':[dict(reference=result_ref)]}),\
                patch('extensions.tendon_family.backends.MujocoBackend.run',side_effect=AssertionError('OFFLINE')),\
                patch('tools.model_transports.deepseek.request_completion',side_effect=AssertionError('OFFLINE')):
            record=validate_batch_plan(store,view,proposal)
            self.assertEqual({r['path'] for r in record['actual_differences'][0]['actual_changes']},set(variables))
            plan_ref=put(None,record)
            host=SimpleNamespace(store=store,run_id=view.run_id)
            with patch('tools.diagnostic_handoff.accepted_product',return_value=record):
                batch=prepare_offline_batch(host,plan_ref,mode='offline_injected')
            self.assertEqual(set(batch['parameters']['initial']),set(variables))
            self.assertEqual(batch['max_backend_attempts'],1)
            self.assertIsNone(batch['pending'])
            self.assertEqual(store.remaining()['used']['backend_solves'],0)
