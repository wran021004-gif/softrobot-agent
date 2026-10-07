"""Saved accepted v3 plan through actual host path; synthetic receipts only."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
from uuid import uuid4
from contextlib import closing
import gc
from unittest import TestCase
from unittest.mock import patch

from examples import research_model_v1 as pilot
from examples import research_campaign_v3 as campaign
from tools.platform_host import Host
from tools.platform_store import Store, plain, zero
from tools.platform_search import prepare_offline_batch, run_live_batch
from tools.live_batch_execution import LiveBatchExecution
from tools.state_io import digest, read

ROOT=campaign.ROOT
LIVE=ROOT/'runs/research_native_development_v3_20261007'


class StructuralHistoryContinuationTests(TestCase):
    def setUp(self):
        self.live_usage=Store(LIVE).remaining()
        self.directory=ROOT/'runs'/('structural-fixture-'+uuid4().hex)
        self.directory.mkdir()
        source=Store(LIVE)
        with closing(source.connect(True)) as src, closing(Store(self.directory).connect()) as dst:
            src.backup(dst)
        production_guard=Store.check_root
        def fixture_guard(store,db):
            if store.root==self.directory:return
            return production_guard(store,db)
        self.guard=patch.object(Store,'check_root',fixture_guard);self.guard.start()
        self.w=pilot.restore(LIVE)
        self.w.directory=self.directory
        self.w.store=Store(self.directory)
        self.w.host=Host(self.directory,self.w.host.run_id)
        from tools.context_assembly import EvidenceArchive
        saved=read(LIVE/'working_state.json')
        shutil.copytree(LIVE/'context_assembly',self.directory/'context_assembly')
        self.w.context_archive=EvidenceArchive(self.directory/'context_assembly',scope=self.w.working['archive_scope'],stores=(self.w.store,))
        for entry in read(ROOT/saved['source_manifest'])['sources']:
            entry=deepcopy(entry)
            if 'store_root' in entry:entry['store_root']=self.directory.relative_to(ROOT).as_posix()
            if 'path' in entry:
                entry['path']=(self.directory.relative_to(ROOT)/Path(entry['path']).relative_to(LIVE.relative_to(ROOT))).as_posix()
            self.w.context_archive.sources[entry['reference']['artifact_id']]=entry
        self.w.freeze=deepcopy(self.w.freeze)
        self.w.freeze['final_reporting']=False
        self.w.status='running';self.w.stop_reason=None
        self.w.freeze['experiment']['evidence_directory']=str(self.directory/'evidence')
        self.w.freeze['implementation']=campaign.seal()
        shutil.copyfile(LIVE/'live_clock.json',self.directory/'live_clock.json')
        self.w.records=deepcopy(self.w.records)
        for r in self.w.records:
            if Path(r['source_store']).resolve()==LIVE.resolve():r['source_store']=str(self.directory)
        if getattr(self,'needs_original_batch',True):
            self.original_batch=deepcopy(self.w.store.session(self.w.host.run_id)['state']['search_batch'])
            self.plan=self.original_batch['plan']
        self.original_bytes={r['facts']['configuration']['artifact_id']:
            self.w.store.artifact(r['facts']['configuration'],raw=True) for r in self.w.records}
        self.blockers=[patch('tools.model_transports.deepseek.request_completion',side_effect=AssertionError('OFFLINE_PROVIDER_PROHIBITED')),
            patch('extensions.tendon_family.backends.MujocoBackend.run',side_effect=AssertionError('OFFLINE_BACKEND_PROHIBITED')),
            patch.object(Host,'invoke',side_effect=AssertionError('OFFLINE_REAL_HOST_DISPATCH_PROHIBITED'))]
        for p in self.blockers:p.start()

    def tearDown(self):
        for p in self.blockers:p.stop()
        self.guard.stop();gc.collect()
        self.assertEqual(Store(LIVE).remaining(),self.live_usage)
        if not self.directory.resolve().is_relative_to((ROOT/'runs').resolve()):raise ValueError('UNSAFE_FIXTURE_CLEANUP')
        shutil.rmtree(self.directory)

    def prepare(self):
        with self.w.store.transaction() as db:
            state=self.w.store.session(self.w.host.run_id,db)['state']
            state.pop('search_batch',None)
            self.w.store.update_state(db,self.w.host.run_id,state)
        record=self.w.store.artifact(self.plan)
        source=next(r for r in self.w.records if r['facts']['candidate']==record['bindings']['subject'])
        return prepare_offline_batch(self.w.host,self.plan,mode='live',starting_facts=source['facts'],
            retained_baseline=self.w.baseline,historical_results=self.w.records)

    def test_recorded_failure(self):
        self.prepare()
        from tools.candidate_parameters import parameter_value
        def old_read(original,policy,paths):
            return dict(available=True,values={p:parameter_value(original,p) for p in paths})
        with patch('tools.candidate_parameters.historical_parameter_comparison',side_effect=old_read):
            with self.assertRaisesRegex(ValueError,'CONSTRAINED_PARAMETER_MISSING: design/near_section_scale'):
                run_live_batch(self.w.host,stop_after_stage='apply')
        batch=self.w.store.session(self.w.host.run_id)['state']['search_batch']
        self.assertEqual(batch['proposals'],[])
        self.assertIsNone(batch['pending'])

    def injected_stages(self):
        calls=[]
        def stage(executor,name,candidate):
            child=executor.candidate_host(candidate);request='complete-'+name
            self.assertEqual(child.store.root,self.directory)
            old=child.store.lookup(child.run_id,request)
            if old:return json.loads(old['receipt'])
            calls.append((candidate['candidate_id'],name))
            row,_=child.store.reserve(child.run_id,request,digest(candidate),child.actor,
                {**zero(),'tool_calls':1,'backend_solves':int(name=='simulation'),
                 'wall_s':dict(simulation=900,evaluation=30,profile=60)[name]})
            return child.store.complete(row,dict(request_id=request,execution_id=row['execution_id'],
                caller=child.actor,tool_id='offline.synthetic.'+name,tool_version='1.0.0',
                execution_status='completed',charged=zero()),dict(synthetic_engineering_fixture=True),.01)
        def facts(executor,candidate):
            from tools.research_tasks import assemble_acceptance
            from extensions.tendon_family.gvs_profile import execution_scope
            child=executor.candidate_host(candidate)
            receipt=json.loads(child.store.lookup(child.run_id,'complete-simulation')['receipt'])
            f=deepcopy(self.w.baseline);f.update(candidate={k:candidate[k] for k in ('candidate_id','configuration')},
                execution_id=receipt['execution_id'],configuration=candidate['configuration'])
            f['candidate'].update(owner_run_id=child.run_id,execution_id=f['execution_id'])
            speed=.03 if candidate['changes']['design/near_section_scale']==1.05 else .01
            f['sampled_settling'].update(max_error_m=.004,max_speed_m_s=speed,passed=speed<=.02)
            f.update(terminal_error_m=.004,task_accepted=True,terminal_tip_speed_m_s=speed)
            cfg=child.store.artifact(candidate['configuration'])['effective']
            ev=deepcopy(child.store.artifact(self.w.baseline['evaluation']))
            ev.update(candidate_id=child.run_id,source_execution_id=f['execution_id'],original_execution_id=f['execution_id'],
                task_success=True,source=receipt['output'])
            ev['metrics'][0]['value']=.004
            ev['constraints'][0].update(observed=.004,satisfied=True)
            profile=dict(complete=True,execution_id=f['execution_id'],solver_error_count=0,force_bound_violation_n=0.,
                sampled_settling=f['sampled_settling'],execution_scope=execution_scope(cfg),task=cfg['task'],official_task_success=True)
            acceptance=assemble_acceptance(cfg,ev,profile)
            return dict(factual_result=f,configuration=candidate['configuration'],acceptance=acceptance,
                receipts={name:json.loads(child.store.lookup(child.run_id,'complete-'+name)['receipt'])
                    for name in ('simulation','evaluation','profile')},synthetic_engineering_fixture=True)
        return calls,patch.object(LiveBatchExecution,'stage',stage),patch.object(LiveBatchExecution,'facts',facts)

    def test_saved_plan_complete_path_and_restore(self):
        from tools.candidate_parameters import parameter_value
        batch=self.prepare()
        from tools.structural_continuation import migrate,retire_settled_draft
        start=read(LIVE/'structural_repair_start.json')
        migrate(self.w,start['authorization'])
        retire_settled_draft(self.w)
        request_start=read(LIVE/'structural_request_repair_start.json')
        self.w.store.complete(request_start['reservation'],dict(request_id=request_start['reservation']['request_id'],
            execution_id=request_start['reservation']['execution_id'],caller='engineering',tool_id='offline.synthetic.repair',
            tool_version='3.5.0',execution_status='completed',charged=zero()),dict(synthetic_engineering_fixture=True),.01)
        self.assertTrue(all(r['parameter_comparison']['available'] for r in batch['historical_results']))
        self.assertEqual(batch['parameters']['initial'],{'design/near_section_scale':.95})
        calls,stages,facts=self.injected_stages()
        with stages,facts:
            paused=run_live_batch(self.w.host,stop_after_stage='simulation')
            self.assertIsNotNone(paused['pending'])
            restored=Host(self.directory,self.w.host.run_id)
            result=run_live_batch(restored)
            again=run_live_batch(restored)
        self.assertEqual(result['accounting']['new_backend_attempts'],2)
        self.assertEqual(len(calls),6)
        self.assertEqual(again['accounting'],result['accounting'])
        self.assertEqual([p['changes'] for p in result['proposals']],
            [{'design/near_section_scale':1.},{'design/near_section_scale':1.05}])
        for c in result['candidates']:
            cfg=self.w.store.artifact(c['configuration'])['effective']
            source=self.w.store.artifact(batch['base_configuration'])['effective']
            self.assertEqual(cfg['task'],source['task']);self.assertEqual(cfg['seed'],17)
            self.assertEqual(parameter_value(cfg,'design/far_section_scale'),.95)
            self.assertEqual(parameter_value(cfg,'control/recipe/terminal_tip_speed_weight'),.05)
        failure=result['candidates'][1]
        self.assertTrue(failure['execution']['acceptance']['components']['task_evaluator']['passed'])
        self.assertFalse(failure['joint_acceptance'])
        self.assertFalse(failure['feedback']['physical_metrics']['joint_reach_holding_passed'])
        for identity,body in self.original_bytes.items():
            self.assertEqual(body,self.w.store.artifact(dict(artifact_id=identity),raw=True))
        # Use the accepted native row and real unified feedback/next-request assembly.
        row=deepcopy(next(r for r in self.w.rounds if r.get('accepted_decision',{}).get('artifact_id')=='9d47b0f3661a7243e45d339c206e297f158f636f5893df229ef2186d8c80354f'))
        self.w.previous_decision=row['accepted_decision']
        row.update(index=len(self.w.rounds),execution_only_continuation=True);self.w.rounds.append(row)
        with patch.object(pilot.reusable,'persist'),patch.object(pilot,'persist'):
            pilot.reusable.execute(self.w,row)
            campaign.previous.append_results(self.w,row)
            packet=pilot.configure(self.w)
            from tools.platform_models import payload_for
            from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
            try:payload=payload_for(self.w.host,EvidenceDrivenAdapter())
            except ValueError:
                from tools.context_assembly import assemble_working_context
                view=assemble_working_context('research_decision',self.w.working,archive=self.w.context_archive)['view']
                print('BOUND_SECTIONS', {k:len(json.dumps(v)) for k,v in view['bound_evidence'].items()})
                print('WORKING_SECTIONS', {k:len(json.dumps(v)) for k,v in view['working_context'].items()})
                raise
        outcomes=packet['current_feedback']['content']['outcomes']
        self.assertEqual([r['acceptance']['accepted'] for r in outcomes],[True,False])
        self.assertIn('research_decide',[t['function']['name'] for t in payload['tools']])
        self.assertEqual(self.w.store.remaining()['used']['model_calls'],6)
        from tools.structural_continuation import verify_migration
        session=self.w.store.session(self.w.host.run_id)
        migration=self.w.store.artifact(session['state']['structural_read_migration'])
        before=self.w.store.artifact(migration['before_snapshot'])
        changed=deepcopy(session['snapshot']);changed['input']['policy']['budget']['model_calls']+=1
        with self.w.store.transaction() as db:
            ref=plain(self.w.store.put(db,changed))
            db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref['artifact_id'],self.w.host.run_id))
        with self.assertRaises(ValueError):verify_migration(self.w.store,self.w.host.run_id,digest(before),digest(changed))

    def test_unavailable_projection_keeps_evidence_and_strict_reuse(self):
        from tools.candidate_parameters import historical_parameter_comparison,historical_parameter_projection
        from tools.study_history import scientific_match
        from tools.platform_tools import _candidate
        from schemas.platform import SessionInput
        source=self.w.store.artifact(self.original_batch['historical_results'][0]['facts']['configuration'])['effective']
        policy=self.w.store.artifact(self.original_batch['base_configuration'])['effective']['policy']
        altered=plain(_candidate(SessionInput.model_validate(source),{'design/section_scale':.97},self.w.host.reg))
        comparison=historical_parameter_comparison(altered,policy,['design/near_section_scale'])
        self.assertEqual(comparison['values'],{'design/near_section_scale':.97})
        projected=historical_parameter_projection(altered,policy)
        self.assertEqual(projected['robot'],altered['robot'])
        match=scientific_match(projected,altered)
        self.assertTrue(match['scientific_match']);self.assertFalse(match['reuse_eligible'])
        self.assertFalse(match['builder_binding_equal'])
        bad=deepcopy(altered);bad['policy']['candidate_builder']['parameters']['data']['semantic_source']['components'][0]['length_m']*=1.1
        unavailable=historical_parameter_comparison(bad,policy,['design/near_section_scale'])
        self.assertFalse(unavailable['available']);self.assertIn('SOURCE_IDENTITY_MISMATCH',unavailable['reason'])
        bad=deepcopy(altered);bad['robot']['structure']['data']['components'][0]['sections'][0]['section']['parameters']['semi_y_m']*=1.01
        unavailable=historical_parameter_comparison(bad,policy,['design/near_section_scale'])
        self.assertFalse(unavailable['available']);self.assertIn('PHYSICAL_VALUE_MISMATCH',unavailable['reason'])
        self.assertFalse(historical_parameter_comparison(altered,policy,['design/section_scale'])['available'])
        # Unmappable historical evidence remains in preparation; it is not
        # silently removed or relabelled as an invalid current candidate.
        from extensions.tendon_family.gvs_profile import execution_scope
        historical=deepcopy(self.w.records[0]);eid='offline-unmappable-history'
        with self.w.store.transaction() as db:
            ref=plain(self.w.store.put(db,dict(effective=bad)))
        historical.update(execution_id=eid,execution_scope=execution_scope(bad))
        historical['facts'].update(configuration=ref,execution_id=eid)
        historical['facts']['candidate'].update(configuration=ref,execution_id=eid)
        self.w.records.append(historical)
        batch=self.prepare()
        retained=next(r for r in batch['historical_results'] if r['execution_id']==eid)
        self.assertFalse(retained['parameter_comparison']['available'])
        self.assertFalse(retained['reusable_under_plan'])
        self.assertTrue(retained['available_for_reasoning'])

    def test_unknown_pending_work_is_never_redispatched(self):
        self.prepare()
        paused=run_live_batch(self.w.host,stop_after_stage='apply')
        candidate=paused['pending'];executor=LiveBatchExecution(self.w.host)
        child=executor.candidate_host(candidate)
        child.store.reserve(child.run_id,'complete-simulation',digest(candidate),child.actor,
            {**zero(),'tool_calls':1,'backend_solves':1,'wall_s':900.})
        with patch.object(LiveBatchExecution,'stage',side_effect=AssertionError('UNKNOWN_WORK_MUST_NOT_REPLAY')):
            result=run_live_batch(Host(self.directory,self.w.host.run_id))
        self.assertEqual(result['stop_reason'],'unresolved_execution')
        self.assertEqual(result['accounting']['new_backend_attempts'],1)
        self.assertEqual(result['candidates'][0]['stages']['simulation']['execution_status'],'unknown')
