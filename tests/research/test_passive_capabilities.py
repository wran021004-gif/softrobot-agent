"""Integration fixtures are offline; no autonomous or physical success is claimed."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from uuid import uuid4
from tools.research import experience
from tools.research.config import ROOT, resolve, role_provider
from tools.research.state import state, update
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.evidence_policy import registered_references
from tests.research.test_phs2d_knowledge_start import fixture
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_research_authorization_preflight import approve

SPEC=ROOT/'configs/research/study_passive_research_capabilities_v1.json'


@contextmanager
def passive_host():
    from tools.research import core
    from tests.research.test_cross_task_integration import fixture_directory
    spec=resolve(SPEC);spec['study_id']='passive-capability-fixture-'+uuid4().hex[:8]
    spec['configuration']['run_id']=spec['study_id']
    with fixture_directory() as folder,patch('tools.research.config.resolve',return_value=spec):
        h=core.prepare(directory=folder)
        update(h,freeze='offline-fixture',pilot={**state(h)['pilot'],
            'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
        approve(h,[REGISTERED_MATHEMATICS_SCOPE])
        yield h


def mixed_query(spec, **changes):
    from tools.research.contracts import FamilyMixedSearch
    value=dict(version='family_mixed_search_v1',family_space_identity=spec['family_space_identity'],
        variable_groups=['materials','routing','payout'],segment_counts=[1],tendon_counts=[2],
        screening_fidelity='diagnostic',objective='equilibrium_qualification',
        operating_point='standardized_initial_pretension',max_proposals=1,max_evaluations=1,
        evaluation_mode='passive_equilibrium',diagnostic_load_conditions=['unloaded'])
    return FamilyMixedSearch.model_validate({**value,**changes})


class PassiveKnowledgeTests(unittest.TestCase):
    def test_sdk_catalogue_exact_read_and_progress_without_answers(self):
        new=resolve(SPEC)
        with fixture() as h:
            spec=deepcopy(state(h)['spec'])
            for key in ('knowledge','knowledge_manifest'):
                spec[key]=new[key]
            spec['research_decisions']['role_policy']=new['research_decisions']['role_policy']
            update(h,spec=spec)
            approve(h,[REGISTERED_MATHEMATICS_SCOPE])
            query=dict(operation='read',entry_id='passive-structure-mechanics',revision='1')
            with patch('tools.research.agent.credential',return_value='offline-fixture'):
                wires=run_fixture(h,[('experience_retrieve',query),None],limit=2)
            packets=[next(json.loads(m['content'].split('\n',1)[1])['research']
                for m in wire['messages'] if isinstance(m.get('content'),str)
                and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')) for wire in wires]
            catalogue=packets[0]['knowledge']['catalogue']
            self.assertEqual(sum(r['entry_id'].startswith('skill-') for r in catalogue),6)
            self.assertIn(('passive-force-response-research','2'),[(r['entry_id'],r['revision']) for r in catalogue])
            self.assertIn('expert_process',packets[0]['knowledge']['access'])
            self.assertNotIn('expert_process',packets[1]['knowledge']['access'] or {})
            self.assertNotIn('Chord',json.dumps(packets[0]['knowledge']))
            self.assertTrue(experience.read_progress(h)['reads'][0]['body_delivered'])
            self.assertEqual(packets[0]['knowledge']['reporter_role']['reasoning'],'medium')
            body=experience.retrieve(h,query)['results'][0]['content']
            self.assertGreaterEqual(len(body['topics']),10)
            self.assertTrue(all(r['evidence_grade'] and r['source'] for r in body['topics']))
            for entry in ('phs2d-passive-research','p3-passive-progressive-stiffness'):
                self.assertFalse(experience.retrieve(h,dict(entry_id=entry))['results'])
            self.assertEqual(registered_references(h),[])
            self.assertEqual(state(h)['mathematical_evaluations'],0)
        old=resolve(ROOT/'configs/research/study_phs2d_topology_successor_20261106.json')
        self.assertEqual(role_provider(old,old['runtime']['provider'],'reporter')['reasoning'],'none')
        self.assertEqual(role_provider(new,new['runtime']['provider'],'main')['reasoning'],'medium')


class PassiveSearchTests(unittest.TestCase):
    def test_formal_plan_multiload_and_read_only_reporter(self):
        import asyncio
        import httpx
        from tools.research import core,reporter
        from tests.research.test_s129_agent_reporting import reporter_response
        with passive_host() as h:
            loads=[r['name'] for r in state(h)['spec']['configuration']['task']['physical_problem']['loads']][:2]
            plan=dict(action='search',hypothesis='Offline fixture: compare passive qualification over two loads.',
                expected_observation='Recorded KKT eligibility in both loads.',weakening_observation='Unqualified equilibrium.',
                fixed_conditions='Same frozen task and structure across loads.',stopping_condition='One diagnostic proposal.',
                interpretation='No dynamic acceptance or scientific discovery claimed.',
                decision=dict(hypothesis_id='offline-passive-plan'),
                search=dict(version='scientific_structure_search_v1',research_goal='passive_structure_research',
                    design_variable_groups=['routing','payout'],evaluation_model='passive_equilibrium',
                    control_treatment='no_active_control',proxy_objective='equilibrium_qualification',
                    segment_counts=[1],tendon_counts=[2],diagnostic_load_conditions=loads,
                    structure_search_effort=dict(max_proposals=1,max_evaluations=2)))
            with patch.object(core,'guard'):
                out=core.dispatch(h,plan,'offline-formal-passive-search')
            ref=out['result']['reference'];raw=h.store.artifact(ref)
            self.assertEqual(raw['result']['resource_use']['actual_mathematical_evaluations'],2)
            feedback=reporter.scientific_feedback(h,out)
            self.assertEqual(feedback['interpretation_status'],'deferred',feedback)
            wires=[]
            def respond(request):
                wires.append(json.loads(request.content));return reporter_response(request)
            with patch('tools.research.provider.credential',return_value='offline-fixture'):
                asyncio.run(reporter.complete_reports(h,httpx.MockTransport(respond)))
            self.assertEqual(reporter.entries(h)[-1][1]['interpretation_status'],'available',
                [(v['interpretation_status'],v.get('error'),[c['deterministic_summary'] for c in v['report']['results']]) for _,v in reporter.entries(h)])
            self.assertEqual(wires[0]['reasoning_effort'],'medium')
            self.assertEqual(h.store.artifact(ref),raw)
            self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_physical_linkage_polygon_mesh_and_base_only(self):
        import numpy as np
        from tools.platform_store import plain
        from tools.research.mixed_moves import initial,generation
        from extensions.tendon_family.generated_serial import generate_family
        from extensions.tendon_family.compiler import resolve as compile_design
        from extensions.tendon_family.family_space import parameter_capabilities
        spec=resolve(SPEC);space=spec['family_space'];q=mixed_query(spec)
        request=generation(space,q,initial(space,q))
        def build(r):
            design,mesh,_=generate_family(dict(space=space,request=r))
            return compile_design(design,mesh)
        base=build(request)
        changed=deepcopy(request)
        changed['segments']['0']['physical_parameters'].update(density_kg_m3=2000,curvature_y_rad_m=2)
        other=build(changed)
        a=[p for p in base['parts'] if p['dofs']];b=[p for p in other['parts'] if p['dofs']]
        self.assertTrue(all(np.isclose(y['mass_kg'],2*x['mass_kg']) for x,y in zip(a,b)))
        self.assertTrue(all(np.allclose(y['inertia_com_local_kg_m2'],2*np.asarray(x['inertia_com_local_kg_m2'])) for x,y in zip(a,b)))
        self.assertTrue(any(np.linalg.norm(y['natural_rad'])>0 for y in b))
        polygon=deepcopy(request);polygon['segments']['0']['sections']=[dict(kind='polygon',
            outer_yz_m=[[-.003,-.004],[.003,-.004],[.003,.004],[-.003,.004]])]*len(space['assembly']['components'][0]['sections'])
        polygon['segments']['0']['cells']=4
        poly=build(polygon)
        self.assertEqual(len(poly['dofs']),8)
        self.assertTrue(any(r['parameter_id'].endswith('outer_yz_m.0.0') for r in parameter_capabilities(space,polygon)))
        bad=deepcopy(polygon);bad['segments']['0']['sections'][0]['outer_yz_m'][0][0]=.03
        with self.assertRaisesRegex(ValueError,'OUTSIDE_FAMILY_DOMAIN'):build(bad)
        bad=deepcopy(request);bad['segment_count']=2;bad['spans'][0]['first_segment']=1;bad['spans'][0]['last_segment']=1
        with self.assertRaisesRegex(ValueError,'BASE_ONLY'):build(bad)
        self.assertLess(space['passive_payout_domain_m']['minimum'],.3)
        self.assertGreater(space['passive_payout_domain_m']['maximum'],.5)

    def test_shared_search_real_worker_store_and_reuse(self):
        from tools.research.search import run_search
        from tools.platform_store import plain
        with passive_host() as h:
            query=mixed_query(state(h)['spec'])
            def guard(*args):pass  # Offline numerical integration, no Provider.
            output=run_search(h,plain(query),'offline-passive-search',guard=guard,execute=None,capacity=None)
            result=output['result']
            self.assertEqual(result['resource_use']['legally_constructed'],1)
            self.assertEqual(result['resource_use']['actual_mathematical_evaluations'],1)
            self.assertEqual(result['task_acceptance'],'unmeasured')
            self.assertTrue(result['physical_problem']['diagnostic_only'])
            row=result['evaluated'][0]
            ref=row['evidence']['conditions']['unloaded']['analysis']
            raw=h.store.artifact(ref)
            self.assertIn('parameterized_problem',raw['structure_research'])
            self.assertIn('sensitivity_evidence',raw['structure_research'])
            self.assertEqual(raw['structure_research']['cost']['physics_steps'],0)
            before=state(h)['mathematical_evaluations']
            repeated=run_search(h,plain(query),'offline-passive-search',guard=guard,execute=None,capacity=None)
            self.assertTrue(repeated['reused']);self.assertEqual(state(h)['mathematical_evaluations'],before)

    def test_scientific_group_compiler_owns_paths_and_scope(self):
        from tools.research.structure_research import select_group_parameters
        from tools.research.design import generate_candidate
        from tools.research.search import search_problem
        with passive_host() as h:
            spec=state(h)['spec'];q=mixed_query(spec)
            from tools.research.mixed_moves import initial,generation
            request=generation(spec['family_space'],q,initial(spec['family_space'],q))
            result=generate_candidate(h,request,dict(origin='offline-group-fixture'))
            candidate=h.store.artifact(result['candidate'])
            paths=select_group_parameters(spec,candidate,'tendon_routing')
            self.assertEqual(len(paths),2)
            self.assertTrue(all(p.startswith('spans.') for p in paths))
            with self.assertRaisesRegex(ValueError,'STATIC_TASK_OBJECTIVE_UNAVAILABLE'):
                search_problem(h,mixed_query(spec,objective='task_violation'),1)


if __name__=='__main__':unittest.main()
