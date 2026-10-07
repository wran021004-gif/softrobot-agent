"""Concrete future-task risks: holding, provenance, missing evidence and replay."""
from copy import deepcopy
import unittest

from extensions.tendon_family.gvs_profile import reach_input
from schemas.platform import SessionInput, EvidenceRef, Signal, SignalSpec, BackendResult, Payload
from tools.platform_registry import registry
from tools.research_tasks import (task_adapter, assemble_acceptance,
    aggregate_acceptance, compare_acceptance, stop_interpretation)


class ResearchTasksTests(unittest.TestCase):
    def setUp(self):
        self.cfg = reach_input('research-task-check')
        self.cfg['policy']['controller']['version'] = '7.0.0'
        self.ev = dict(validity='valid',task_success=True,evaluator='evaluate.reach',
            source=dict(artifact_id='a'*64,media_type='application/json'), comparison_identity='check',
            source_execution_id='fresh',metrics=[dict(name='position_error',value=.005,units='m')],
            constraints=[dict(name='task_bound',satisfied=True,observed=.005,limit=.01,units='m')])
        self.profile = dict(complete=True,execution_id='fresh',solver_error_count=0,
            evaluation=dict(artifact_id='b'*64,media_type='application/json'), simulation=self.ev['source'],
            force_bound_violation_n=0., real_time_demonstrated=False,deadline_misses=35,
            sampled_settling=dict(available=True,passed=True,window_s=.05,position_limit_m=.01,
                speed_limit_m_s=.02,max_error_m=.005,max_speed_m_s=.01))

    def acceptance(self, profile=None, ev=None):
        return assemble_acceptance(self.cfg, self.ev if ev is None else ev,
                                   self.profile if profile is None else profile,
                                   evaluation_reference=self.profile['evaluation'],
                                   profile_reference=dict(artifact_id='c'*64,media_type='application/json'))

    def test_terminal_success_does_not_replace_hold_and_timing_is_diagnostic(self):
        good = self.acceptance()
        self.assertTrue(good['accepted'])
        self.assertFalse(good['timing']['real_time_required'])
        bad = deepcopy(self.profile)
        bad['sampled_settling'].update(max_speed_m_s=.03,passed=False)
        result = self.acceptance(bad)
        self.assertEqual(result['status'],'valid_failure')
        self.assertTrue(result['components']['task_evaluator']['passed'])
        self.assertFalse(result['components']['holding_speed']['passed'])
        bad['force_bound_violation_n']=.1
        self.assertFalse(self.acceptance(bad)['components']['force_bounds']['passed'])

    def test_missing_incomplete_and_identity_mismatch_preserve_components(self):
        missing = deepcopy(self.profile)
        missing['sampled_settling']['available']=False
        result = self.acceptance(missing)
        self.assertEqual(result['status'],'missing_evidence')
        self.assertIsNone(result['accepted'])
        self.assertTrue(result['components']['task_evaluator']['passed'])
        missing['complete']=False
        self.assertEqual(self.acceptance(missing)['status'],'incomplete')
        wrong = deepcopy(self.profile)
        wrong['execution_id']='other'
        self.assertEqual(self.acceptance(wrong)['status'],'invalid')
        wrong = deepcopy(self.profile)
        wrong['sampled_settling']['speed_limit_m_s']=1.
        self.assertIn('HOLDING_DEFINITION_MISMATCH',self.acceptance(wrong)['issues'])

    def test_partial_motion_grid_never_passes(self):
        duration=self.cfg['task']['timing']['duration_s']
        rows=[dict(time_s=duration-.05+i*.01) for i in range(6)]
        self.assertTrue(assemble_acceptance(self.cfg,self.ev,self.profile,motion=rows)['accepted'])
        rows.pop(2)
        out=assemble_acceptance(self.cfg,self.ev,self.profile,motion=rows)
        self.assertEqual(out['status'],'missing_evidence')

    def test_frozen_schedule_includes_replays_and_absent_slots(self):
        result=self.acceptance()
        receipt=dict(execution_id='fresh',cache_hit=False,charged=dict(backend_solves=1),tool_id='simulation.run')
        records=[dict(case_id='nominal',seed=17,repetition=0,acceptance=result,receipt=receipt),
                 dict(case_id='nominal',seed=18,repetition=1,acceptance=result,receipt=receipt)]
        aggregate=aggregate_acceptance(records,3)
        self.assertEqual(aggregate['accepted'],1)
        self.assertEqual(aggregate['joint_acceptance_fraction'],1/3)
        self.assertEqual(aggregate['unrecorded'],1)
        self.assertEqual(aggregate['entries'][1]['status'],'not_new_repetition')
        records[0]['receipt']={**receipt,'cache_hit':True,'charged':dict(backend_solves=0)}
        self.assertEqual(aggregate_acceptance(records[:1],1)['accepted'],0)
        missing=deepcopy(result)
        missing.update(execution_id=None,accepted=None,status='missing_evidence')
        entry=aggregate_acceptance([dict(case_id='nominal',seed=17,repetition=0,
            acceptance=missing,receipt=receipt)],1)['entries'][0]
        self.assertTrue(entry['fresh_execution'])
        self.assertEqual(entry['status'],'missing_evidence')
        self.assertFalse(entry['counted_accepted'])

    def test_componentwise_tradeoff_and_stop_meanings(self):
        first=self.acceptance()
        second=deepcopy(first)
        second['metrics'].update(terminal_error_m=.003,holding_max_speed_m_s=.015)
        self.assertEqual(compare_acceptance(second,first)['relation'],'tradeoff')
        cheap=deepcopy(first)
        cheap['metrics']['simulation_wall_s']=1.
        costly=deepcopy(first)
        costly['metrics']['simulation_wall_s']=100.
        self.assertEqual(compare_acceptance(cheap,costly)['relation'],'equivalent')
        stopping=stop_interpretation(first,'budget_exhausted',budget_exhausted=True,remaining_work=3)
        self.assertTrue(stopping['legal'])
        self.assertTrue(stopping['success_claim_supported'])
        self.assertEqual(stopping['optimality'],'not_assessed')

    def test_reach_and_tracking_keep_reference_and_evaluator_semantics(self):
        from examples.gvs_tracking import tracking_input
        # Explicit reference avoids even a model compilation in this interface check.
        ref=dict(frame='world',units='SI',interpolation='quintic',start_s=0.,end_s=.4,
            start_m=[.28,0.,.15],end_m=[.278,.024,.142],outside='clamp_position_zero_velocity',provenance='interface fixture')
        tracking=tracking_input(reference=ref)
        adapter=task_adapter(tracking)
        reach=task_adapter(self.cfg)
        self.assertEqual(reach.describe()['family'],'task.reach')
        self.assertEqual(adapter.describe()['family'],'task.tracking')
        self.assertIsNone(adapter.describe()['holding'])
        self.assertNotEqual(adapter.operating_point(.1)['reference_position_m'],adapter.operating_point(.3)['reference_position_m'])
        self.assertEqual(reach.operating_point(.1)['reference_position_m'],reach.operating_point(.3)['reference_position_m'])
        inp=SessionInput.model_validate(tracking)
        times=[i*.01 for i in range(1,41)]
        positions,_=adapter.reference_at(times)
        signals=[Signal(spec=next(s for s in inp.task.observations if s.name=='tip_position'),times_s=times,values=positions.tolist())]
        signals.extend(Signal(spec=SignalSpec(name='tendon_tension',entity=entity,dimension=1,units='N',frame='path',phase='pre_step_solver'),
            times_s=[t-.01 for t in times],values=[[0.]]*40) for entity in inp.task.evaluator.parameters.data['tension_limits_n'])
        result=BackendResult(solver_status='completed',backend_id='backend.family_mujoco',model_id='fixture',signals=signals,
            data=Payload(contract='platform.empty',data={}),limitations=[],initial_state=Payload(contract='platform.empty',data={}),seed=17)
        evaluation=registry().get('evaluate.tracking',kind='evaluator').resolve()(inp.task,result,EvidenceRef(artifact_id='a'*64),registry(),'interface')
        profile=dict(complete=True,execution_id='tracking-fixture',solver_error_count=0,force_bound_violation_n=0.)
        accepted=assemble_acceptance(tracking,evaluation,profile,
            evaluation_reference=dict(artifact_id='b'*64,media_type='application/json'),
            profile_reference=dict(artifact_id='c'*64,media_type='application/json'))
        self.assertTrue(accepted['accepted'])
        self.assertEqual(accepted['protocol_id'],'offline_tracking_v1')
        self.assertEqual(self.acceptance()['protocol_id'],'offline_reach_hold_v1')
        self.assertNotIn('holding_speed',accepted['components'])
        self.assertEqual(compare_acceptance(deepcopy(accepted),accepted)['relation'],'equivalent')
        tracking['policy']['controller']['version']='7.0.0'
        support=task_adapter(tracking).check_compatibility()
        self.assertEqual(support['technical_compatibility']['status'],'unsupported')
        self.assertIn('TRACKING_CONTROLLER_VERSION_REQUIRED',support['technical_compatibility']['reason'])
        self.assertFalse(reach.lifecycle()['controller_restore_supported'])


if __name__=='__main__':
    unittest.main()
