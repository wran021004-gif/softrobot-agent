"""Focused saved-evidence checks; zero provider requests and zero backend solves."""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager
import shutil
import unittest
from types import SimpleNamespace
from examples.gvs_revision_input import revision_input
from examples.gvs_nmpc_route_experiment import prepare
from extensions.tendon_family.historical_failure import bind_failure
from extensions.tendon_family.delivery_facts import bound_result_facts, check_result_statement
from extensions.tendon_family import route
from extensions.tendon_family.gvs_reporting import markdown
from tools.platform_host import Host
from tools.platform_models import input_for, payload_for, DeepSeekAdapter
from tools.state_io import read, atomic_json

SOURCE=Path('runs/stage329_multiphysics_design_20260928_202221')


@contextmanager
def workspace_folder():
    root=(Path('runs')/('stage330_test_'+uuid4().hex)).resolve()
    root.mkdir()
    try: yield root
    finally:
        if root.parent!=Path('runs').resolve(): raise ValueError('cleanup outside runs')
        import gc
        gc.collect()
        shutil.rmtree(root)



class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.inp=revision_input(SOURCE)
        self.prior=bind_failure(SOURCE,self.inp)

    def test_historical_measurements_and_compatibility(self):
        p=self.prior; f=p['factual_result']
        self.assertEqual(p['kind'],'supplied_historical_failure')
        self.assertTrue(p['compatibility']['scientific_conditions_match'])
        self.assertEqual(f['candidate']['candidate_id'],'build_covered_stiff_long')
        self.assertFalse(f['task_accepted']); self.assertTrue(f['valid_complete_execution'])
        self.assertAlmostEqual(f['signed_position_error_m'][0],.027883161726922123)
        self.assertAlmostEqual(f['signed_position_error_m'][2],-.027066931132417066)
        self.assertAlmostEqual(f['terminal_tip_speed_m_s'],.23423393816834698)
        self.assertFalse(f['sampled_settling']['passed'])
        self.assertEqual((f['accepted_plans'],f['initialization_selected'],f['accepted_noninitialization_plans'],f['converged_updates']),(35,35,0,0))
        self.assertTrue(all(r['minimum_n']==r['maximum_n'] for r in f['applied_tension_ranges']))
        self.assertEqual(f['one_step_prediction_summary']['aligned_count'],35)
        bad=deepcopy(self.inp);bad['task']['timing']['duration_s']=.4
        with self.assertRaisesRegex(ValueError,'MISMATCH'): bind_failure(SOURCE,bad)
        bad=deepcopy(self.inp);bad['policy']['controller']['parameters']['data']['recipe']['horizon']=11
        with self.assertRaisesRegex(ValueError,'MISMATCH'): bind_failure(SOURCE,bad)

    def test_reach_statement_shared_projection_and_binding(self):
        f=self.prior['factual_result']
        self.assertTrue(check_result_statement(f,deepcopy(f))['accepted'])
        for key,value in [('terminal_tip_speed_m_s',0.),('task_accepted',True),('coordinate_frame','robot_base')]:
            bad=deepcopy(f);bad[key]=value
            self.assertFalse(check_result_statement(f,bad)['accepted'])
        self.assertFalse(check_result_statement(f,None)['accepted'])
        index=read(SOURCE/'evidence_index.json');host=Host(SOURCE/'live',index['live_session'])
        state=host.store.session(host.run_id)['state'];final=state['route']['final']
        candidate=route.trial_facts(host.store,read(SOURCE/'frozen_input.json'),final)
        trial=dict(final,evaluation=final['evaluation_ref'])
        self.assertEqual(bound_result_facts(host.store,trial,candidate),f)
        bad=deepcopy(candidate);bad['owner_run_id']='new-session'
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):bound_result_facts(host.store,trial,bad)
        self.assertIn('"task_accepted": false',markdown(dict(final['profile_report_summary'],factual_result=f)))
        from extensions.tendon_family.candidate_comparison import feedback
        self.assertEqual(feedback(dict(trial,factual_result=f))['factual_result'],f)
        ctx=SimpleNamespace(store=host.store,host=host)
        delivery_trial=dict(trial,evaluation_data=final['evaluation'])
        child=SimpleNamespace(run_id=candidate['owner_run_id'])
        out=route.delivery(ctx,state['route'],child,delivery_trial,'Accurate failed reach, still moving.',candidate,f)
        self.assertTrue(out['result_statement_check']['accepted'])
        bad=deepcopy(f);bad['sampled_settling']['passed']=True
        with self.assertRaisesRegex(ValueError,'REACH_RESULT_STATEMENT_MISMATCH'):
            route.delivery(ctx,state['route'],child,delivery_trial,'Unsupported static settling.',candidate,bad)

    def test_fresh_context_no_historical_ownership_or_charge(self):
        with workspace_folder() as folder:
            root=Path(folder);atomic_json(root/'frozen.json',self.inp)
            host=prepare(root/'live',SOURCE,root/'frozen.json',historical_failure=SOURCE)
            model=input_for(host);ctx=model.context
            self.assertEqual(ctx['route']['historical_case']['source_session_id'],self.prior['source_session_id'])
            self.assertNotEqual(host.run_id,self.prior['source_session_id'])
            self.assertIsNone(ctx['route']['incumbent'])
            self.assertEqual(ctx['route']['historical_comparisons'],[])
            self.assertEqual(ctx['route']['experiment_progress'],dict(evaluated_candidate_count=0,remaining_execution_opportunities=3))
            self.assertEqual(ctx['route']['result_contract']['result_type'],'free_reach')
            self.assertIn('Free reach has no tracking metrics',model.content[0].text)
            self.assertEqual(host.store.remaining()['used']['backend_solves'],0)
            payload=payload_for(host,DeepSeekAdapter())
            self.assertEqual(payload['model'],'deepseek-flash')
            self.assertNotIn('plumbing',str(payload))
            self.assertEqual(host.store.session(host.run_id)['snapshot']['input']['task'],self.inp['task'])


if __name__=='__main__': unittest.main()
