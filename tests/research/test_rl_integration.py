"""Explicitly enabled real engineering chain; ordinary discovery launches nothing."""
from copy import deepcopy
import json
import os
from pathlib import Path
import time
import unittest

from tools.research.config import ROOT


@unittest.skipUnless(os.environ.get('SOFTROBOT_REAL_RL_TEST')=='1','set SOFTROBOT_REAL_RL_TEST=1 for the single declared real chain')
class RealRLChain(unittest.TestCase):
    def test_training_continuation_independent_evaluation(self):
        from tools.research.core import prepare, bind, read_evidence, export
        from tools.research.state import state, update, save
        from tools.research.rl import dispatch, reconcile
        from tools.rl.run import read_json, worker_alive, run_path
        existing=os.environ.get('SOFTROBOT_VALIDATION_RUN_ID')
        if existing:
            from tools.platform_host import Host
            h=Host(ROOT/'runs/research'/existing,existing,actor='unified-research')
            self.assertTrue(state(h).get('validation_extension_pending_binding'),'Requires an explicit unapplied user authorization addendum')
            initial_stages=state(h)['admitted_training_stages']
            bind(h,reason='User-authorized engineering addendum after incomplete high-tension evaluation; explicit low-tension initialization repair; all prior costs retained')
        else:
            h=prepare(ROOT/'configs/research/study.json',profile='rl_chain')
            self.assertFalse(state(h).get('rl_runs'),'This validation profile is single-use; inspect prior evidence rather than rerun')
            initial_stages=0
            bind(h)
        prefix='engineering-extension' if existing else 'engineering'
        candidate=state(h)['reference_candidate']
        def terminal(run_id):
            last=None
            while True:
                current=reconcile(h,run_id,lightweight=True)
                actions=current['consumed']['attempted_actions']
                if actions!=last:
                    print(json.dumps(dict(stage=run_id,status=current['status'],actions=actions)),flush=True)
                    last=actions
                if not current['worker_alive']:
                    break
                time.sleep(2.)
            result=dispatch(h,dict(operation='status',run_id=run_id,rationale='Read terminal engineering training facts'),run_id+'-terminal')
            summary=read_evidence(h,dict(reference=result['training_summary_reference']))
            self.assertEqual(summary['status'],'completed',summary)
            self.assertEqual(summary['consumed']['attempted_actions'],4096)
            self.assertGreaterEqual(summary['checkpoint']['inherited']['rollout_optimizations'],2)
            return result,summary
        started=time.perf_counter()
        first=dispatch(h,dict(operation='start',candidate=candidate,mode='direct',allocation=dict(actions=4096),
            **(dict(initial_tension_n=.2,training_overrides=dict(learning_rate=.00003,n_epochs=4,policy_kwargs=dict(log_std_init=-5.))) if existing else {}),
            rationale='Declared two-stage engineering validation; no task-success expectation'), prefix+'-start')
        first_status,first_summary=terminal(first['run_id'])
        generation=first_summary['checkpoint']['generation']
        initial_lr=.00001 if existing else .0001
        second=dispatch(h,dict(operation='continue',run_id=first['run_id'],checkpoint=generation,
            allocation=dict(actions=4096),training_overrides=dict(learning_rate=dict(kind='linear',initial=initial_lr,final=initial_lr/2),n_steps=512,batch_size=128,n_epochs=4,ent_coef=0. if existing else .001),
            reward_overrides=dict(holding_speed=1.25),rationale='Verify new stage schedule, rollout buffer and reward while preserving exact parent weights and Adam moments'), prefix+'-continue')
        second_status,second_summary=terminal(second['run_id'])
        record=read_json(run_path(second['run_id'])/'continuation.json')
        self.assertTrue(record['policy_preserved'])
        self.assertTrue(record['optimizer_moments_preserved'])
        self.assertTrue(record['optimizer_steps_preserved'])
        self.assertEqual(record['rollout_buffer_size'],512)
        self.assertEqual(record['optimizer_learning_rates'],[initial_lr])
        self.assertEqual(second_summary['checkpoint']['inherited']['lifetime_timesteps'],8192)
        evaluation=dispatch(h,dict(operation='evaluate',run_id=second['run_id'],checkpoint=second_summary['checkpoint']['generation'],
            rationale='One complete independent task evaluation of exact continued checkpoint'),prefix+'-evaluate')
        result=read_evidence(h,dict(reference=evaluation['reference']))
        self.assertTrue(result['independent_evaluation_executed'])
        self.assertEqual(len(result['episodes']),1)
        self.assertTrue(result['episodes'][0]['complete'],result)
        self.assertEqual(state(h)['admitted_training_stages'],initial_stages+2)
        self.assertEqual(h.store.remaining()['used']['model_calls'],0)
        self.assertFalse(any(worker_alive(run_path(k)) for k in state(h)['rl_runs']))
        stages=[]
        for status,summary in ((first_status,first_summary),(second_status,second_summary)):
            entry=state(h)['rl_runs'][summary['run_id']]
            cfg=h.store.artifact(entry['configuration'])
            stages.append(dict(run_id=summary['run_id'],configuration=entry['configuration'],candidate=entry['candidate'],
                ppo=cfg['ppo'],reward=cfg['reward'],requested_allocation=cfg['requested_allocation'],effective_allocation=cfg['budget'],
                lineage=cfg.get('lineage'),consumed=summary['consumed'],checkpoint=summary['checkpoint'],workers=summary['workers']))
        report=dict(engineering_chain_passed=True,task_passed=result['passed'],study_id=h.run_id,implementation=state(h)['freeze'],
            stages=stages,continuation=record,evaluation=dict(reference=evaluation['reference'],**result),
            counts=h.store.remaining(),elapsed_s=time.perf_counter()-started,
            original_resume='Contract/count/publication fixtures only; no live interrupted-stage recovery in this two-stage chain',
            original_failed_attempts_retained=initial_stages,authorization_addenda=state(h).get('validation_extensions',[]),
            workers_remaining=0)
        ref=save(h,report,'engineering_validation_complete')
        update(h,research_status='stopped',closed_unix=time.time(),final_disposition=ref)
        destination=ROOT/'evidence/research_count_20261015/engineering'
        destination.mkdir(parents=True,exist_ok=True)
        (destination/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        export(h)
        print(json.dumps(dict(engineering_chain_passed=True,task_passed=result['passed'],total_stages=initial_stages+2,total_evaluations=sum(e['evaluations'] for e in state(h)['rl_runs'].values()),elapsed_s=report['elapsed_s'])),flush=True)
