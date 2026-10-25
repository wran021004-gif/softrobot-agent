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
            version='family_sensitivity_v1',variables=['segments.0.length_m','segments.1.young_pa','segments.8.length_m','spans.0.radius_m','spans.1.radius_m']))
        spec['mathematical_methods']={opt.CONIC:'offline fixture',opt.SENSITIVITY:'offline fixture'}
        spec['budgets']['mathematical_evaluations']=30
        update(self.h,spec=spec,freeze='offline-family-fixture',analysis_results=[])

    def generate(self,**values):
        result=fixture.VariableSegmentTests.generate(**(dict(segment_count=2,tendon_count=3)|values))
        self.assertEqual(result['status'],'generated',result)
        return result['candidate'],design.verify_candidate(self.h,result['candidate'])

    def stencil(self,variable='segments.0.length_m',steps=(.0005,),count=2):
        spec=state(self.h)['spec'];refs=[];candidates=[]
        _,index,key=variable.split('.')
        default=spec['family_space']['segment_domains'].get(index,spec['family_space']['segment_domain'])[key]['default']
        for delta in [0,*[v for step in steps for v in (-step,step)]]:
            edits={} if delta==0 else {index:{key:default+delta}}
            ref,c=self.generate(segment_count=count,segments=edits);candidates.append(ref)
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
            optimal_sensitivity=dict(variable=variable,steps=list(steps),model_results=refs))

    def test_full_one_nine_segment_and_two_step_modulus_groups(self):
        with patch('tools.research.task_constraints.check_analysis_applicability',return_value={'status':'applicable'}):
            for variable,steps,count in [('segments.0.length_m',(.0005,),1),
                    ('segments.8.length_m',(.0005,),9),('segments.1.young_pa',(10000.,5000.),2)]:
                q=self.stencil(variable,steps,count)
                self.assertEqual(len(opt.sensitivity_context(self.h,q)['points']),1+2*len(steps))

    def test_second_changes_reach_real_stencil_gate(self):
        q=self.stencil();refs=list(state(self.h)['analysis_results'])
        base=design.verify_candidate(self.h,q.candidate)
        params,_=opt.family_parameters(state(self.h)['spec'],base,'segments.0.length_m')
        cases=[dict(tendon_count=4),dict(segment_count=3),dict(control_weights={'holding_tip_speed_weight':.5}),
            dict(segments={'0':dict(length_m=.1005,young_pa=8e6)}),
            dict(spans=[dict(first_segment=0,last_segment=1,count=3,phase_rad=.8)]),
            dict(segments={'0':dict(length_m=.1005,sections=[dict(kind='circle',parameters=dict(radius_m=.008))])})]
        for changes in cases:
            request=deepcopy(params);request.update(changes)
            result=design.generate_candidate(self.h,request,dict(origin='offline_stencil_negative'))
            self.assertEqual(result['status'],'generated',result)
            raw=deepcopy(self.raw);raw['candidate']=result['candidate']
            raw.update(implementation=state(self.h)['freeze'],protocol=state(self.h)['spec']['analysis_protocol'])
            raw['requested_operation']['operating_point']='controller_start_input'
            ref=save(self.h,raw,'explicit_invalid_stencil_fixture');update(self.h,analysis_results=[*refs,ref])
            bad=q.model_copy(update={'optimal_sensitivity':q.optimal_sensitivity.model_copy(update={
                'model_results':[*q.optimal_sensitivity.model_results[:2],ref]})})
            with patch('tools.research.task_constraints.check_analysis_applicability',return_value={'status':'applicable'}):
                with self.assertRaisesRegex(ValueError,'SINGLE_PARAMETER'):opt.sensitivity_context(self.h,bad)

    def test_model_task_operating_point_time_and_baseline_rejections(self):
        q=self.stencil();refs=list(state(self.h)['analysis_results'])
        mutations=[lambda r:r['binding'].update(task_identity='foreign'),
            lambda r:r['requested_operation'].update(operating_point='target_equilibrium'),
            lambda r:r['model'].update(protocol_identity='different-horizon')]
        with patch('tools.research.task_constraints.check_analysis_applicability',return_value={'status':'applicable'}):
            for mutation in mutations:
                raw=self.h.store.artifact(refs[-1]);mutation(raw)
                ref=save(self.h,raw,'explicit_invalid_model_fixture');update(self.h,analysis_results=[*refs,ref])
                bad=q.model_copy(update={'optimal_sensitivity':q.optimal_sensitivity.model_copy(update={
                    'model_results':[*q.optimal_sensitivity.model_results[:2],ref]})})
                with self.assertRaises(ValueError):opt.sensitivity_context(self.h,bad)
            bad=q.model_copy(update={'optimal_sensitivity':q.optimal_sensitivity.model_copy(update={
                'model_results':list(reversed(q.optimal_sensitivity.model_results))})})
            with self.assertRaisesRegex(ValueError,'BASELINE'):opt.sensitivity_context(self.h,bad)

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

    def test_radius_defaults_geometry_bounds_and_clearance(self):
        space=state(self.h)['spec']['family_space']
        from extensions.tendon_family.family_space import parameter_capabilities
        ref,c=self.generate(spans=[dict(last_segment=1,count=3)])
        params,domain=opt.family_parameters(state(self.h)['spec'],c,'spans.0.radius_m')
        radius=design.parameter_value(params,'spans.0.radius_m')
        self.assertEqual(radius,space['routing_domains']['radius_m']['default'])
        self.assertEqual(domain['bounds_source']['path'],'routing_domains.radius_m')
        self.assertEqual(domain['affected_tendon_indices'],[0,1,2])
        rows=parameter_capabilities(space,params)
        self.assertEqual(next(r for r in rows if r['parameter_id']=='spans.0.radius_m')['unit'],'m')
        with self.assertRaisesRegex(ValueError,'TOPOLOGY'):opt.family_parameters(state(self.h)['spec'],c,'spans.1.radius_m')
        models=[]
        for value in (.0175,.018,.0185):
            p=deepcopy(params);design.set_parameter(p,'spans.0.radius_m',value)
            result=design.generate_candidate(self.h,p,dict(origin='radius_geometry_fixture'))
            self.assertEqual(result['status'],'generated',result)
            changed=design.verify_candidate(self.h,result['candidate']);models.append(changed)
            for tendon in changed['configuration']['robot']['structure']['data']['tendons']:
                yz=tendon['points'][0]['attachment']['position_m'][1:]
                self.assertAlmostEqual(sum(v*v for v in yz)**.5,value)
        self.assertEqual(len({digest(c['configuration']['robot']['structure']) for c in models}),3)
        for value in (space['routing_domains']['radius_m']['maximum']+.001,space['routing_domains']['radius_m']['minimum']):
            p=deepcopy(params);design.set_parameter(p,'spans.0.radius_m',value)
            result=design.generate_candidate(self.h,p,dict(origin='radius_illegal_fixture'))
            self.assertEqual(result['status'],'invalid',result)

    def test_radius_real_models_t2_report_and_decision_delivery(self):
        """Three tiny real GVS builds and the existing T2 kernel; no worker/rollout."""
        from tools.research import analysis,reporter
        from tools.research.evidence_views import result_card
        from tools.research.research_context import mathematical_decision_view,compact_scientific_delivery
        from extensions.tendon_family.gvs_basis import resolve_basis
        refs=[];candidates=[];protocol=state(self.h)['spec']['analysis_protocol']
        for radius in (.018,.0175,.0185):
            ref,c=self.generate(segment_count=1,segments={'0':dict(cells=4)},spans=[dict(last_segment=0,count=3,radius_m=radius)])
            candidates.append(ref);cfg=c['configuration'];robot=cfg['robot']['structure']['data']
            binding=dict(candidate=ref,candidate_id=c['candidate_id'],configuration=c['configuration_reference'],
                effective_configuration_identity=digest(cfg),task_identity=digest(cfg['task']),source_identity=c['source_identity'],
                tendon_order=[t['id'] for t in robot['tendons']],tension_limits_n=[t['force_limit_n'] for t in robot['tendons']],
                basis=cfg['policy']['controller']['parameters']['data']['recipe']['basis'],
                coordinate_order=list(resolve_basis(robot,cfg['policy']['controller']['parameters']['data']['recipe']['basis']).coordinate_order))
            query=AnalysisRequest(candidate=ref,operation='linearization',model_source='gvs',operating_point='controller_start_input',
                scoring_window_s=protocol['windows_s'][0],protocol=protocol)
            raw=analysis.calculate(cfg,binding,plain(query))
            self.assertEqual(raw['status'],'computed',raw)
            raw.update(candidate=ref,implementation=state(self.h)['freeze'],requested_operation=plain(query))
            refs.append(save(self.h,raw,'radius_real_model_engineering_fixture'))
        update(self.h,analysis_results=refs)
        query=AnalysisRequest(candidate=candidates[0],operation='task_capability',model_source='gvs',
            operating_point='controller_start_input',protocol=protocol,capability_method=opt.CONIC,
            optimal_sensitivity=dict(variable='spans.0.radius_m',steps=[.0005],model_results=refs))
        self.assertEqual(opt.method_admission(state(self.h)['spec'],query)['status'],'admissible')
        self.assertEqual(len({digest(self.h.store.artifact(r)['model']['B']) for r in refs}),3)
        foreign,_=self.generate(segment_count=2,spans=[dict(last_segment=1,count=3,radius_m=.0185)])
        changed=self.h.store.artifact(refs[-1]);changed['candidate']=foreign
        badref=save(self.h,changed,'cross_topology_radius_negative_fixture')
        update(self.h,analysis_results=[*refs,badref])
        bad=query.model_copy(update=dict(optimal_sensitivity=query.optimal_sensitivity.model_copy(update=dict(model_results=[*refs[:2],badref]))))
        with self.assertRaisesRegex(ValueError,'SINGLE_PARAMETER'):opt.sensitivity_context(self.h,bad)
        update(self.h,analysis_results=refs)
        context=opt.sensitivity_context(self.h,query)
        raw=opt.calculate_sensitivity(context,query)
        self.assertEqual(raw['status'],'computed',raw.get('optimal_sensitivity'))
        result=raw['optimal_sensitivity']
        self.assertEqual(result['parameter_units'],'m')
        self.assertFalse(result['regularity']['differentiability_proven'])
        self.assertEqual(result['computation_cost']['conic_solves'],3)
        raw.update(candidate=candidates[0],implementation=state(self.h)['freeze'],charged_analysis_evaluations=5,charged_numerical_s=0.)
        ref=save(self.h,raw,'radius_t2_engineering_fixture');update(self.h,analysis_results=[*refs,ref])
        card=plain(result_card(self.h,ref));view=mathematical_decision_view(card)
        self.assertIn('optimal_sensitivity',view)
        self.assertTrue(all(q['unit']=='score/m' for q in card['mathematics']['quantities']))
        if not card['mathematics']['quantities']:
            self.assertEqual(result['direction_status'],'unresolved')
            self.assertEqual(result['reason'],'NUMERICAL_OPTIMALITY_INSUFFICIENT')
        report=reporter.assemble(self.h,[ref]);saved=dict(report=plain(report),interpretation_status='deferred',error=None)
        handoff=reporter.reporter_handoff_summary(self.h,ref,saved)
        brief=compact_scientific_delivery(dict(latest_reports=[handoff],action_trace=dict(recent=[])),decision_only=True)
        compact=brief['latest_reports'][0]['findings'][0]['mathematics']
        self.assertEqual(compact['optimal_sensitivity']['direction_status'],view['optimal_sensitivity']['direction_status'])
        self.assertEqual(compact['detail_query']['reference'],ref)
        self.assertNotIn('differences',compact['optimal_sensitivity'])


if __name__=='__main__':unittest.main()
