"""Archived request and engineering-only B3 checks; no scientific dispatch."""
from copy import deepcopy
import gzip
import json
from types import SimpleNamespace
import unittest
from uuid import uuid4

import httpx
from openai import AsyncOpenAI
from tests.research.c3_readiness_audit import C3Archive, serialized
from tests.research.test_c3_f1_f2 import archive
from tools.research import core
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest, ControlSeedRequest, Plan
from tools.research.research_context import agent_decision_brief, history_index, import_history
from tools.research.state import state
from tools.state_io import atomic_json, read


def projected_g2():
    """Use original G2 transcript/tools plus the production request-only L0 tail."""
    from tools.research.agent import live_model_class
    g=C3Archive(ROOT/'evidence/c3_g2_scientific_decision_loop/immutable_artifacts.tar.gz')
    b=archive('b')
    try:
        declarations=read(ROOT/'configs/research/study_b3_pilot_c_draft.json')['research_decisions']['background']
        rows=[];wires=[]
        # Initial decision and a request containing the actual SDK-offloaded read.
        for position in (0,3):
            event,meta,wire,packet,events=g.requests()[position]
            h,s=g.host(events)
            original=h.store.artifact.side_effect
            def artifact(ref,raw=False):
                try:return original(ref,raw=raw)
                except KeyError:return b.artifact(ref,raw=raw)
            h.store.artifact.side_effect=artifact
            s['spec']['research_decisions']['background']=declarations
            s['scoped_context'] += [e['reference'] for e in declarations]
            packet=deepcopy(packet);packet['research']=agent_decision_brief(h)
            boundary=SimpleNamespace(host=h,research_packet=packet)
            # No transport is called: use the same formatter that appends L0 AFTER
            # SDK Offload. The original saved preview and transcript stay intact.
            with_client=AsyncOpenAI(api_key='offline-fixture',base_url='https://offline.invalid',max_retries=0)
            model=live_model_class(boundary)(model_id=wire['model'],stream=False,client=with_client)
            tail=model.format_request([],[],None)['messages'][-1]
            projected=deepcopy(wire);projected['messages'][-1]=tail
            body=serialized(projected);delivered=json.loads(body)['messages'][-1]['content']
            l0=json.loads(delivered.split('\n',1)[1])['research']['research_history']
            rows.append(dict(boundary=position+1,original_request=meta['request'],
                original_bytes=len(serialized(wire)),projected_bytes=len(body),
                history_bytes=len(serialized(l0)),history=l0,
                original_transcript_preserved=wire['messages'][:-1]==projected['messages'][:-1],
                original_tools_preserved=wire['tools']==projected['tools']))
            wires.append(projected)
        return rows,wires
    finally:g.archive.close();b.archive.close()


def engineering_preflight():
    """Freeze inputs and construct bounded schedules only; never call a solver."""
    from tools.research.physical_replay import seed_control, binding
    from tools.research_tasks import task_adapter
    from tools.research.tool_readiness import execution_environment
    from tools.research.design import generate_candidate
    from extensions.tendon_family.gvs_nmpc import deadline_horizon
    drafts=[resolve(ROOT/f'configs/research/study_b3_pilot_{arm}_draft.json') for arm in 'abc']
    rows=[];run_root=ROOT/'runs'/('b3-readiness-'+uuid4().hex)
    for tag in ('035','050','070'):
        value=read(ROOT/('configs/research/study_b3_pilot_'+('b' if tag=='050' else 'c')+'_draft.json'))
        duration=int(tag)/100
        value.update(study_id='b3-engineering-'+tag+'-'+uuid4().hex,mode='engineering_numerical',
            task='../../tasks/reach_hold_b3_'+tag+'.json',scoring_window_s=duration,
            capabilities=['analysis','control_correction'],allowed_plan_actions=['generate','initialize_control','diagnose','stop'],
            nmpc_limits=dict(executions=0),physical_replay_limit=0)
        value['budgets'].update({k:0 for k in ('provider_requests','protected_provider_requests','public_operations',
            'protected_public_operations','physical_launches','mathematical_evaluations')})
        value['analysis_protocol'].update(windows_s=[.05,.1,duration],samples_s=[0.,round(duration-.05,2),round(duration-.01,2)])
        value['record_update_ids']=[0,round(duration/.01)-1]
        path=ROOT/'configs/research'/('.b3-engineering-'+uuid4().hex+'.json')
        atomic_json(path,value)
        try:h=core.prepare(path,directory=run_root/tag)
        finally:path.unlink()
        import_history(h)
        from tools.research.state import require_authorization
        try:require_authorization(h)
        except ValueError as exc:
            if str(exc)!='INDEPENDENT_FORMAL_STUDY_APPROVAL_REQUIRED_BEFORE_PROVIDER_OR_SCIENCE':raise
        else:raise AssertionError('Pending draft must not grant execution')
        p=read(ROOT/'configs/research/b3_reference_generation.json')
        p['family_space_identity']=state(h)['spec']['family_space_identity']
        generated=generate_candidate(h,p,dict(origin='engineering_geometry_only_no_execution'))
        if generated['status']!='generated':raise AssertionError(generated)
        c=generated['candidate'];cfg=h.store.artifact(c)['configuration']
        fixed_check=None
        if tag=='050':
            changed=deepcopy(p);changed['segments']['0']['young_pa']=10000000.
            rejected=generate_candidate(h,changed,dict(origin='engineering_fixed_structure_negative_check'))
            assert rejected['status']=='invalid' and rejected['reason']=='FROZEN_REFERENCE_STRUCTURE_REQUIRED'
            weights=deepcopy(p);weights['control_weights']['holding_tip_speed_weight']=.2
            allowed=generate_candidate(h,weights,dict(origin='engineering_control_only_positive_check'))
            assert allowed['status']=='generated'
            fixed_check=dict(changed_structure=rejected['status'],control_only=allowed['status'])
        control=seed_control(h,ControlSeedRequest(candidate=c,method='baseline'))
        source=h.store.artifact(control['source']);binding(cfg,source['trajectory'])
        adapter=task_adapter(cfg);requirements=adapter.analysis_requirements({})
        q=AnalysisRequest(candidate=c,operation='task_capability',operating_point='controller_start_input',
            capability_method='sampled-affine-conic-minimax-v1',protocol=state(h)['spec']['analysis_protocol'])
        old=h.store.artifact(value['research_decisions']['background'][0]['reference'])
        repeat=history_index(h,c,{**old['requested_operation'],'candidate':c})[0]
        from tools.research.task_constraints import mathematical_method_view
        method=mathematical_method_view(h,c)['methods']['sampled-affine-conic-minimax-v1']
        from tools.research.evidence_policy import admit_decision
        from tools.research.feedback import eligibility
        plan=Plan(action='diagnose',hypothesis='Engineering citation-scope fixture; no scientific claim.',
            expected_observation='Only empirical background citation admitted',weakening_observation='Scope transfer',
            fixed_conditions='Frozen B3',stopping_condition='No dispatch',interpretation='Offline test only',
            supporting_evidence=[value['research_decisions']['background'][0]['reference']],
            decision=dict(hypothesis_id='offline-scope',research_intent='DIAGNOSE',selected_method='scope_check',
                selected_candidate=c,claimed_inference='empirical_search'))
        admit_decision(h,plan)
        plan=plan.model_copy(update=dict(decision=plan.decision.model_copy(update=dict(claimed_inference='model_sampled_feasibility'))))
        try:admit_decision(h,plan)
        except ValueError as exc:
            if str(exc)!='EVIDENCE_TASK_IDENTITY_MISMATCH':raise
        else:raise AssertionError('Background must not establish a new-task mathematical claim')
        historical_selection=eligibility(h,value['research_decisions']['background'][1]['reference'])
        rows.append(dict(deadline_s=duration,hold_start_s=adapter.holding_start_s(),
            control_intervals=len(source['trajectory']['tensions_n']),control_end_s=source['trajectory']['times_s'][-1],
            physics_steps=round(duration/cfg['task']['timing']['timestep_s']),
            task_grid_end_s=requirements.time_grid_s[-1],constraint_samples={r.constraint_id:r.indices for r in requirements.constraints},
            terminal_prediction_intervals=deadline_horizon(duration,duration-.05,.01,10),
            evaluator=cfg['task']['evaluator'],settling=cfg['policy']['controller']['parameters']['data']['settling'],
            initializer=cfg['task']['initializer'],tension_limits_n=[t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']],
            history_task_matches=[r['task_match'] for r in history_index(h)],repeat_hint=repeat['repeat_hint'],
            conic_kernel_supported=method['kernel_supported'],conic_full_task_supported=method['full_task_supported'],
            formal_execution_authorized=method['formal_execution_authorized'],historical_select_eligible=historical_selection['eligible'],
            fixed_structure_check=fixed_check,
            mathematical_request_parsed=q.operation,results=state(h)['results'],physical_replays=state(h)['physical_replays'],
            mathematical_evaluations=state(h)['mathematical_evaluations'],store_root=str(h.store.root)))
    return dict(status='conditional',environment=execution_environment(drafts[0]),conditions=rows,
        common_task=all(s['canonical_task']==drafts[0]['canonical_task'] for s in drafts),
        same_b_c_budgets=drafts[1]['budgets']==drafts[2]['budgets'],
        same_b_c_control_limits=all(drafts[1][k]==drafts[2][k] for k in ('nmpc_limits','native_control_limits','physical_replay_limit')),
        draft_identities={arm:s['resolved_identity'] for arm,s in zip('abc',drafts)},
        authorization=[s['authorization'] for s in drafts],
        actual_resources=dict(provider_requests=0,mathematical_evaluations=0,model_preparations=0,internal_solves=0,
            independent_physical_launches=0,nmpc=0,ppo=0,geometry_and_schedule_constructions=3,fixed_structure_test_proposals=2))


class B3ReadinessTests(unittest.TestCase):
    def test_full_g2_wire_before_selection_and_after_offload(self):
        rows,wires=projected_g2()
        for row,wire in zip(rows,wires):
            self.assertTrue(row['original_transcript_preserved']);self.assertTrue(row['original_tools_preserved'])
            self.assertLess(row['history_bytes'],2048)
            tail=wire['messages'][-1]['content']
            for fact in ('c3-b-100ms-20261025','-0.19999999999954968','0.013754640667324113',
                         '0.2741264353343463','0.18173358255275762','braking','unresolved'):
                self.assertIn(fact,tail)
            history=json.dumps(row['history'])
            for field in ('applied_input_n','raw_primal','samples','model_identity'):
                self.assertNotIn('"'+field+'"',history)
            self.assertNotIn('[Truncated',tail)
        self.assertTrue(any('[Truncated' in json.dumps(m) for m in wires[1]['messages'][:-1]))

    def test_l1_l2_repeat_scope_and_historical_ownership(self):
        b=archive('b');self.addCleanup(b.archive.close);h,s=b.host()
        roots=[s['analysis_results'][-1],s['physical_replays'][0],s['results'][-1]]
        s['scoped_context']+=roots
        candidate=b.artifact(roots[0])['candidate'];request=b.artifact(roots[0])['requested_operation']
        index=history_index(h,candidate,request)
        self.assertEqual(len(index),3);self.assertEqual(index[0]['repeat_hint'],'same_configuration_and_request')
        self.assertEqual(index[0]['experimental_equivalence'],'unknown')
        self.assertTrue(index[0]['actual_result']['control_witness'])
        self.assertEqual(index[0]['evidence_scope'],'MODEL_WITNESS')
        self.assertEqual(index[1]['mathematical_source'],roots[0])
        self.assertEqual([r['evidence_scope'] for r in index[1:]],['PHYSICAL_OBSERVATION']*2)
        changed=deepcopy(request);changed['operating_point']='standardized_initial_pretension'
        self.assertEqual(history_index(h,candidate,changed)[0]['repeat_hint'],'unknown')
        from tools.research.task_constraints import mathematical_method_view
        method=mathematical_method_view(h,candidate)['methods']['sampled-affine-conic-minimax-v1']
        self.assertEqual(method['previous_work'][0]['repeat_hint'],'same_configuration_and_request')
        self.assertIn('never vetoes execution',method['repeat_guidance'])
        before=deepcopy({k:s[k] for k in ('results','physical_replays','analysis_results')})
        q=dict(reference=roots[0],view='working_set',pointer='/research_history_index')
        self.assertEqual(core.read_evidence(h,q,record_read=False),{r['source']['reference']['artifact_id']:r for r in history_index(h)})
        self.assertEqual(core.read_evidence(h,dict(reference=roots[0],view='full',pointer='/model'),record_read=False),b.artifact(roots[0])['model'])
        self.assertEqual(before,{k:s[k] for k in before})

    def test_b3_frozen_grids_thresholds_and_real_methods(self):
        result=engineering_preflight()
        self.assertTrue(result['common_task']);self.assertTrue(result['same_b_c_budgets']);self.assertTrue(result['same_b_c_control_limits'])
        self.assertTrue(all(s.startswith('PENDING_EXPLICIT_APPROVAL:') for s in result['authorization']))
        for row in result['conditions']:
            t=row['deadline_s'];self.assertAlmostEqual(row['hold_start_s'],t-.05)
            self.assertEqual(row['control_intervals'],round(t/.01));self.assertAlmostEqual(row['control_end_s'],t)
            self.assertAlmostEqual(row['task_grid_end_s'],t);self.assertEqual(row['terminal_prediction_intervals'],5)
            self.assertEqual(row['settling'],dict(position_limit_m=.01,speed_limit_m_s=.02,window_s=.05))
            self.assertEqual(row['evaluator']['extension_id'],'evaluate.reach');self.assertEqual(row['tension_limits_n'],[8.]*4)
            self.assertTrue(row['conic_kernel_supported']);self.assertTrue(row['conic_full_task_supported'])
            self.assertFalse(row['formal_execution_authorized']);self.assertFalse(row['historical_select_eligible'])
            for name,indices in row['constraint_samples'].items():
                self.assertEqual(indices,[round(t/.01)] if name=='terminal_error_m' else list(range(round(t/.01)-5,round(t/.01)+1)))
            self.assertFalse(row['results']);self.assertFalse(row['physical_replays']);self.assertEqual(row['mathematical_evaluations'],0)
            self.assertFalse(any(row['history_task_matches']))
        self.assertEqual(result['actual_resources']['internal_solves'],0)


if __name__=='__main__':
    import sys
    if '--audit' in sys.argv:
        rows,wires=projected_g2();out=ROOT/'evidence/b3_benchmark_readiness';out.mkdir(exist_ok=True)
        atomic_json(out/'offline_verification.json',dict(g2_projections=rows,engineering=engineering_preflight()))
        (out/'g2_projected_requests.json.gz').write_bytes(gzip.compress(serialized(wires),mtime=0))
        print(json.dumps(dict(status='conditional',output=str(out),provider_requests=0,scientific_workers=0)))
    else:unittest.main()
