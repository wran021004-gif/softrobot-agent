"""Real generator/Store contracts; saved matrices are explicit numerical fixtures."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tools.platform_store import plain
from tools.state_io import digest
from tools.research import design, optimal_capability as opt
from tools.research.state import state, update, save
from tools.research.contracts import AnalysisRequest
from tools.research.task_constraints import describe_analysis_requirements
from tests.research import test_variable_segments as fixture
from tests.research.test_s130_mainline import saved


class FamilySensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.VariableSegmentTests.setUpClass()
        cls.addClassCleanup(fixture.VariableSegmentTests.doClassCleanups)
        cls.h=fixture.VariableSegmentTests.host
        cls.original=deepcopy(state(cls.h))
        cls.raw=saved()[0]['baseline']

    def setUp(self):
        update(self.h,**deepcopy(self.original))
        spec=deepcopy(state(self.h)['spec'])
        spec['family_sensitivity_variables']=opt.freeze_family_variables(spec['family_space'],dict(
            version='family_sensitivity_v1',variables=['segments.0.length_m','segments.1.young_pa','segments.8.length_m']))
        spec['mathematical_methods']={opt.CONIC:'offline fixture',opt.SENSITIVITY:'offline fixture'}
        spec['budgets']['mathematical_evaluations']=30
        update(self.h,spec=spec,freeze='offline-family-fixture',analysis_results=[])

    def generate(self,**values):
        result=fixture.VariableSegmentTests.generate(**dict(segment_count=2,tendon_count=3,**values))
        self.assertEqual(result['status'],'generated',result)
        return result['candidate'],design.verify_candidate(self.h,result['candidate'])

    def stencil(self):
        spec=state(self.h)['spec'];refs=[];candidates=[]
        default=spec['family_space']['segment_domains'].get('0',spec['family_space']['segment_domain'])['length_m']['default']
        for delta in (0,-.0005,.0005):
            edits={} if delta==0 else {'0':dict(length_m=default+delta)}
            ref,c=self.generate(segments=edits);candidates.append(ref)
            raw=deepcopy(self.raw);cfg=c['configuration']
            bound=dict(raw['binding'],candidate=ref,candidate_id=c['candidate_id'],
                effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']),source_identity=c['source_identity'])
            raw.update(candidate=ref,binding=bound,implementation=state(self.h)['freeze'],protocol=spec['analysis_protocol'])
            raw['requested_operation'].update(candidate=ref,operating_point='controller_start_input')
            raw['model']['protocol_identity']=digest(spec['analysis_protocol'])
            raw['model']['binding'].update(bound,analysis_protocol_identity=digest(spec['analysis_protocol']),
                model_identity='synthetic-'+str(delta))
            raw['task_analysis']=plain(describe_analysis_requirements(cfg,bound))
            refs.append(save(self.h,raw,'explicit_synthetic_model_fixture'))
        update(self.h,analysis_results=refs)
        return AnalysisRequest(candidate=candidates[0],operation='task_capability',operating_point='controller_start_input',
            protocol=spec['analysis_protocol'],capability_method=opt.CONIC,
            optimal_sensitivity=dict(variable='segments.0.length_m',steps=[.0005],model_results=refs))

    def test_sparse_defaults_and_actual_generated_geometry(self):
        ref,c=self.generate()
        params,grant=opt.family_parameters(state(self.h)['spec'],c,'segments.0.length_m')
        explicit=deepcopy(c);explicit['parameters']=params
        # Canonical request provenance must match as well as geometry.
        result=design.generate_candidate(self.h,params,dict(origin='offline_explicit_default'))
        self.assertEqual(result['candidate'],ref)
        self.assertEqual(grant['bounds_source']['path'],'segment_domains.0.length_m')
        self.assertIsInstance(params['segments']['0']['young_pa'],float)
        changed=deepcopy(c);changed['configuration']['robot']['structure']['data']['components'][0]['length_m']+=.001
        with self.assertRaisesRegex(ValueError,'GENERATED_CONFIGURATION'):opt.family_parameters(state(self.h)['spec'],changed,'segments.0.length_m')

    def test_one_and_nine_segment_index_and_modulus(self):
        for count,path in ((1,'segments.0.length_m'),(9,'segments.8.length_m'),(2,'segments.1.young_pa')):
            c=fixture.VariableSegmentTests.candidates[count]
            p,_=opt.family_parameters(state(self.h)['spec'],c,path)
            self.assertIsNotNone(design.parameter_value(p,path))
        with self.assertRaisesRegex(ValueError,'TOPOLOGY'):
            opt.family_parameters(state(self.h)['spec'],fixture.VariableSegmentTests.candidates[1],'segments.1.young_pa')
        with self.assertRaisesRegex(ValueError,'AUTHORIZED'):
            opt.family_parameters(state(self.h)['spec'],fixture.VariableSegmentTests.candidates[2],'segments.1.length_m')

    def test_stencil_and_rejections_before_worker(self):
        q=self.stencil()
        with patch('tools.research.task_constraints.check_analysis_applicability',return_value={'status':'applicable'}):
            context=opt.sensitivity_context(self.h,q)
            self.assertEqual(len(context['points']),3)
            readiness=opt.candidate_methods(self.h,plain(q.candidate))
            self.assertEqual(readiness['status'],'executable',readiness)
            bad=q.model_copy(update={'optimal_sensitivity':q.optimal_sensitivity.model_copy(update={'steps':[.0006]})})
            with self.assertRaisesRegex(ValueError,'STENCIL'):opt.sensitivity_context(self.h,bad)
            refs=state(self.h)['analysis_results'];raw=self.h.store.artifact(refs[-1])
            for field,value,reason in [('implementation','foreign','IMPLEMENTATION'),('protocol',{},'PROTOCOL')]:
                changed=deepcopy(raw);changed[field]=value
                replacement=save(self.h,changed,'synthetic_rejected_binding')
                update(self.h,analysis_results=[*refs,replacement])
                bad=q.model_copy(update={'optimal_sensitivity':q.optimal_sensitivity.model_copy(update={'model_results':[*q.optimal_sensitivity.model_results[:2],replacement]})})
                with self.assertRaisesRegex(ValueError,reason):opt.sensitivity_context(self.h,bad)
            update(self.h,analysis_results=refs[:2])
            with self.assertRaisesRegex(ValueError,'REGISTERED'):opt.sensitivity_context(self.h,q)

    def test_second_design_changes_and_foreign_candidates_rejected(self):
        q=self.stencil();spec=state(self.h)['spec']
        base=design.verify_candidate(self.h,q.candidate)
        parameters,_=opt.family_parameters(spec,base,'segments.0.length_m')
        for edits in ({'tendon_count':4},{'control_weights':{'holding_tip_speed_weight':.5}},
                      {'segments':{'0':dict(length_m=.1005,young_pa=1e6)}}):
            request=deepcopy(parameters);request.update(edits)
            result=design.generate_candidate(self.h,request,dict(origin='offline_negative'))
            if result['status']!='generated':continue  # Generator rejects unsupported edits itself.
            changed=design.verify_candidate(self.h,result['candidate'])
            effective,_=opt.family_parameters(spec,changed,'segments.0.length_m')
            expected=deepcopy(parameters)
            design.set_parameter(expected,'segments.0.length_m',design.parameter_value(effective,'segments.0.length_m'))
            self.assertNotEqual(effective,expected)
        update(self.h,candidates={})
        with self.assertRaisesRegex(ValueError,'OWNED'):opt.sensitivity_context(self.h,q)

    def test_grant_and_cost_boundaries(self):
        space=state(self.h)['spec']['family_space']
        for path in ('segments.-1.length_m','segments.9.length_m','segments.0.density_kg_m3'):
            with self.assertRaises(ValueError):opt.freeze_family_variables(space,dict(version='family_sensitivity_v1',variables=[path]))
        self.assertEqual(opt.sensitivity_cost(1,0,30,conic_authorized=True)['remaining_total_range'],[8,11])
        self.assertEqual(opt.sensitivity_cost(2,0,30,conic_authorized=True)['remaining_total_range'],[14,19])
        self.assertEqual(opt.sensitivity_cost(2,5,30)['remaining_total_range'],[9])
        self.assertIsNone(opt.sensitivity_cost(1,None,30)['missing_models'])
        self.assertFalse(opt.sensitivity_cost(1,3,4)['budget_sufficient'])


if __name__=='__main__':unittest.main()
