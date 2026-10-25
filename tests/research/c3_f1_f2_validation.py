"""This task's bounded validation driver. No autonomous Study or physical dispatch."""
import argparse
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from tools.platform_store import Store, plain
from tools.research import core, analysis
from tools.research.agent import record, converse, load_credential
from tools.research.state import state, update, guard, save, require_authorization
from tools.state_io import atomic_json, digest, read
from tests.research.test_c3_f1_f2 import archive, boundary_projection, ROOT

OUT=ROOT/'evidence/c3_f1_f2'
SOURCE='C:/Users/gugugaga/.codex/attachments/65d82eb1-e845-4e70-b3f2-8d2d894c2ece/已粘贴的文本.txt'
AUTH='2026-10-25 user F1/F2 authorization: feedback <=4 Provider requests, paired decisions <=4; radius <=10 total mathematics; no new physics/NMPC/PPO or full A/B. '+SOURCE


def historical_host(arm='b'):
    name=f'c3-{arm}-100ms-20261025'
    return SimpleNamespace(store=Store(ROOT.parent/'c3-math-search-readiness/runs/research'/name),run_id=name)


def authorize(h, *, source=SOURCE, authorization=AUTH):
    s=state(h);scope=dict(study_id=h.run_id,resolved_identity=s['spec']['resolved_identity'],
        budgets=s['spec']['budgets'],capabilities=s['spec']['capabilities'],provider=s['spec']['runtime']['provider'],
        nmpc_limits=s['spec']['nmpc_limits'],rl_limits=s['spec']['rl_limits'],
        egress='Frozen task, necessary structure and cited historical excerpts; no credentials or unrelated files')
    ref=record(h,'formal_study_authorization',dict(user_approval=True,source=source,approval_text=authorization,
        scope=scope,scope_identity=digest(scope)))
    require_authorization(h)
    return ref


def provision(kind,*,instructions='Bounded numerical radius validation only; no Provider or physics.',
              study_id=None, overrides=None, budget_overrides=None, source=SOURCE, authorization=AUTH):
    name=study_id or ('c3-f2-radius-20261025' if kind=='math' else 'c3-f1-live-20261025')
    path=ROOT/'runs/research'/name
    if (path/'platform.sqlite').exists():raise ValueError('EXISTING_TEST_ID: inspect/recover, never reset or auto-resend')
    cfg=read(ROOT/'configs/research/study_c3_search_admission.json')
    cfg.update(study_id=name,base_commit='1879b79976bbc267f09406f18be40001dd01de70',
        mode='engineering_numerical' if kind=='math' else 'engineering_investigation',
        authorization='PENDING_EXPLICIT_APPROVAL: '+AUTH,nmpc_replan_period_s=.1,
        evidence_destination='evidence/c3_f1_f2/'+kind,execution_instructions=instructions,
        capabilities=['analysis'] if kind=='math' else ['investigation'],allowed_plan_actions=['generate','diagnose','stop'] if kind=='math' else ['diagnose','stop'])
    cfg['budgets'].update(provider_requests=0 if kind=='math' else 4,protected_provider_requests=0,
        public_operations=16,protected_public_operations=0,mathematical_evaluations=10 if kind=='math' else 0)
    cfg.update(authorization='PENDING_EXPLICIT_APPROVAL: '+authorization, **(overrides or {}))
    cfg['budgets'].update(budget_overrides or {})
    for key in ('defaults','family_space','task','control','runtime'):
        cfg[key]=str((ROOT/'configs/research'/cfg[key]).resolve())
    # Existing config owner needs a temporary adjacent leaf, removed before bind.
    leaf=ROOT/'configs/research'/('._'+name+'.json');atomic_json(leaf,cfg)
    try:h=core.prepare(leaf,directory=path)
    finally:leaf.unlink()
    core.bind(h);authorize(h,source=source,authorization=authorization)
    return h


def offline():
    from tools.research.evidence_views import diagnostic_relations
    from tools.research.rl import measured_nmpc_trajectory
    from tools.research.physical_replay import binding
    rows=[];nmpc=[]
    for arm,index in [('a',20),('b',42)]:
        a=archive(arm)
        try:
            h,s,wire,delivery,facts=boundary_projection(a,index)
            facts['feedback']=[{k:r[k] for k in ('tool_id','tool','query','status','delivery','feedback_reference')} for r in delivery['items']]
            facts['carried_fact_bytes']=len(json.dumps(delivery).encode());rows.append(facts)
        finally:a.archive.close()
        h=historical_host(arm);s=state(h);tr,origin=measured_nmpc_trajectory(h,s['results'][-1])
        binding(h.store.artifact(origin['candidate'])['configuration'],tr)
        nmpc.append(dict(arm=arm,origin=origin,intervals=len(tr['tensions_n']),times=[tr['times_s'][0],tr['times_s'][-1]],
            replan_s=s['spec']['nmpc_replan_period_s'],period_s=s['spec']['canonical_task']['timing']['control_period_s'],
            physics_dt_s=s['spec']['canonical_task']['timing']['timestep_s'],actual_input_binding='passed'))
    h=historical_host();s=state(h);d=diagnostic_relations(h,s['results'][-1])
    output=dict(boundaries=rows,nmpc=nmpc,relations=[{k:r[k] for k in ('kind','status','left','right','missing_conditions') if k in r} for r in d['relations']],
        comparison=d['search_comparisons'],bottleneck=d['task_diagnosis']['violated_constraints'],
        critical_samples=d['task_diagnosis']['critical_samples'],provider_requests=0,new_mathematics=0,physical_launches=0)
    atomic_json(OUT/'offline.json',output)
    return dict(boundaries=rows,nmpc=nmpc,bottleneck=output['bottleneck'])


def mathematics():
    from tools.research.design import generate_candidate
    from tools.research.evidence_views import result_card
    h=provision('math');spec=state(h)['spec'];old=historical_host();os=state(old)
    original=old.store.artifact(os['analysis_results'][-1]);params=old.store.artifact(original['candidate'])['parameters']
    candidates=[];models=[];geometry=[]
    for i,radius in enumerate((.018,.0175,.0185)):
        request=deepcopy(params);request['spans'][0]['radius_m']=radius
        result=generate_candidate(h,request,dict(origin='authorized_radius_fixture',historical_candidate=original['candidate']))
        if result['status']!='generated':raise ValueError(result)
        candidate=result['candidate'];candidates.append(candidate)
        c=h.store.artifact(candidate);geometry.append(c['configuration']['robot']['structure']['data']['tendons'])
        result=analysis.dispatch(h,dict(candidate=candidate,operation='linearization',operating_point='controller_start_input',
            scoring_window_s=spec['analysis_protocol']['windows_s'][0],protocol=spec['analysis_protocol']),
            'radius-model-'+str(i),guard=guard,origin='engineering_preflight')
        if result['status']!='computed':raise ValueError(result)
        models.append(result['reference']);print('registered radius model',radius,flush=True)
    assert geometry[0]!=geometry[1] and geometry[0]!=geometry[2]
    q=dict(candidate=candidates[0],operation='task_capability',operating_point='controller_start_input',protocol=spec['analysis_protocol'],
        capability_method='sampled-affine-conic-minimax-v1',optimal_sensitivity=dict(variable='spans.0.radius_m',steps=[.0005],model_results=models))
    result=analysis.dispatch(h,q,'radius-t2',guard=guard,origin='engineering_preflight')
    raw=h.store.artifact(result['reference']);card=plain(result_card(h,result['reference']))
    proof=record(h,'bounded_radius_validation',dict(geometry_changed=True,radii_m=[.018,.0175,.0185],
        candidates=candidates,models=models,result=result['reference'],result_card_available=bool(card),
        count=state(h)['mathematical_evaluations'],scope='New math only; no independent physical support'))
    core.export(h)
    output=dict(study_id=h.run_id,store=str(h.store.root),validation=proof,result=result['reference'],
        geometry_changed=True,count=state(h)['mathematical_evaluations'],unused=10-state(h)['mathematical_evaluations'],
        sensitivity=raw.get('optimal_sensitivity'),actual_calls=raw.get('actual_mathematical_calls'),status=raw['status'])
    # Do not save a duplicate mathematical report: the original result lives in the standard export.
    atomic_json(OUT/'math_summary.json',{k:v for k,v in output.items() if k!='sensitivity'})
    return {**{k:v for k,v in output.items() if k!='sensitivity'},'sensitivity_keys':list(output.get('sensitivity') or {})}


def continuity_instructions(query):
    return ('Independent read-only feedback-continuity validation. The following startup obligation applies ONCE to this entire Study, '
        'not once per SDK Session or invocation. Check current read_state and pending_feedback_delivery first. '
        'Only if this Study has not completed the specified read, call evidence_read with exactly '+json.dumps(query)+
        '. If the read is completed and its feedback is delivered or present in pending_feedback_delivery, use that evidence to continue; '
        'a new SDK Session does not restart the Study or its startup obligation. Immutable delivered evidence does not need rereading '
        'to satisfy startup. A scientifically motivated recheck remains legal; explain its purpose. '
        'After feedback, state in Chinese which constraint failed, the observed value, unit and threshold, the original source and '
        'a falsifiable next research question with competing mechanisms. Finish the invocation with plain text. '
        'No scientific tool execution or STOP/SELECT. Historical excerpt is not this test Study\'s newly generated result.')


def continuity(restore=False, *, study_id='c3-f1-live-20261025', destination=OUT,
               provider_requests=4, source=SOURCE, authorization=AUTH):
    from tests.research.agent_math_decision_probe import provider_usage
    if restore:
        from tools.platform_host import Host
        name=study_id;h=Host(ROOT/'runs/research'/name,name,actor='unified-research')
        asyncio.run(converse(h,session_handoff=True,restore_only=True));core.export(h);return provider_usage(h)
    old=historical_host();s=state(old);ref=s['results'][-1];p=old.store.artifact(ref)
    excerpt=dict(kind='historical_scoped_evidence',owning_study=old.run_id,original_reference=ref,
        candidate=p['candidate'],acceptance=p['acceptance']['components'],
        scope='Historical B execution only; no candidate or science executed in this independent test')
    query=dict(reference=dict(artifact_id=digest(excerpt),media_type='application/json'),view='full',pointer='')
    h=provision('continuity',instructions=continuity_instructions(query),study_id=study_id,
        overrides=dict(evidence_destination=str(destination.relative_to(ROOT))),
        budget_overrides=dict(provider_requests=provider_requests),source=source,authorization=authorization)
    assert save(h,excerpt,'authorized_historical_excerpt')==query['reference']
    # Keep the same source legally readable after the existing closeout filter.
    update(h,scoped_context=[*state(h).get('scoped_context',[]),query['reference']])
    approval=next(e['outputs'][0] for e in h.store.events(h.run_id) if e['kind']=='formal_study_authorization')
    admission=record(h,'session_handoff_admission',dict(authorization=approval,purpose='bounded_independent_semantic_validation',boundary='request_feedback'))
    pilot=deepcopy(state(h)['pilot']);pilot.update(session_handoff_live_admitted=True,session_handoff_boundary='request_feedback',session_handoff_admission=admission)
    update(h,pilot=pilot)
    asyncio.run(converse(h,session_handoff=True,handoff_before_next_request=True,pause_after_completed_invocations=1))
    events=h.store.events(h.run_id);uses=[h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='model_original_tool_request']
    result=dict(**provider_usage(h),tool_queries=[v['tool_use'] for v in uses],
        original_turns=[e['outputs'][0] for e in events if e['kind']=='model_original_turn'],store=str(h.store.root))
    atomic_json(destination/'continuity_summary.json',result);core.export(h)
    return result


def decision_probe(live=False, *, out=None, destination=OUT, authorization=AUTH, formal_host=None,
                   version='c3-f1-f2-historical-decision-v1'):
    from tests.research import agent_math_decision_probe as probe
    from tools.research.evidence_views import diagnostic_relations, recorded_control_diagnostics
    out=out or ROOT/'runs/c3-f2-decision-probe';probe.SUMMARY=out/'summary.json'
    if live:
        result=asyncio.run(probe.live(out,host=formal_host))
        atomic_json(destination/'decision_summary.json',result)
        return {k:result[k] for k in ('status','actual_requests','usage')}
    if out.exists():raise ValueError('EXISTING_PROBE: frozen inputs and original attempts must remain unchanged')
    h=historical_host();s=state(h);ref=s['results'][-1];p=h.store.artifact(ref)
    d=diagnostic_relations(h,ref);math=s['analysis_results'][-1];m=h.store.artifact(math)
    replay=s['physical_replays'][0];v=h.store.artifact(replay)
    controls=recorded_control_diagnostics(h,p)
    data=read(ROOT/'tests/research/fixtures/c3_math_decision_template.json')
    data.update(version=version,authorization=authorization,binding_status='bound_verified_input_v1',
        baseline_commit=s['freeze'],
        task=dict(owning_study=h.run_id,historical_only=True,frozen_task_identity=p['acceptance']['task_identity'],
            task=p['acceptance']['timing'],conditions=d['task_diagnosis']['task_conditions']),
        engineering_prior=dict(candidate_reference=p['candidate'],historical_only=True,
            structure=h.store.artifact(p['candidate'])['parameters'],
            initial_state='Historical all_candidate_dofs_zero_v1; not a current test candidate',
            method_catalog='Same production METHOD_MEANINGS in both arms; requests are descriptions only'),
        costs=dict(source='Original frozen method catalog and independent proposal budget',
            model_preparation=1,sampled_conic_with_new_model=2,
            instantaneous_braking_from_exact_saved_state=1,native_dynamics_from_exact_saved_state=1,
            unknown_wall_cost=None,
            control_search='each baseline, finite-difference probe and candidate consumes a physical replay; no new control search executed',
            native_short_response='one math evaluation plus internally counted native physics steps; independent physical evaluation remains separate'))
    case=data['cases']['c3_next_decision']
    case.update(proposed_next_action_budget=dict(mathematical_evaluations=2,physical_launches=1,nmpc=0,ppo=0,
            execution='Hypothetical next experiment requiring separate authorization; this probe executes none'),
        common=[dict(fact_id='historical_nmpc_failure',source=dict(reference=ref,pointer='/acceptance'),
            candidate=p['candidate'],metrics=p['acceptance']['metrics'],components=p['acceptance']['components'],
            independent_physical_observation=True),
            dict(fact_id='historical_fixed_sequence_failure',source=dict(reference=replay,pointer='/acceptance'),
                metrics=v['acceptance']['metrics'],independent_physical_observation=True,control='Different fixed open-loop input from NMPC'),
            dict(fact_id='frozen_execution_grids',replan_s=.1,control_and_sampling_s=.01,physics_dt_s=.0005)],
        evidence=[dict(fact_id='sampled_affine_witness',source=dict(reference=math,pointer='/trajectory'),
                candidate=m['candidate'],method=m['trajectory']['method_version'],
                score=m['trajectory']['replayed_violation'],optimality=m['trajectory']['optimality_status'],
                numerical_replay=m['trajectory']['replay']['numerically_valid'],
                horizon=m['trajectory']['horizon'],operating_point=m['operating_point'],
                scope='Local sampled affine model only; no nonlinear physical success'),
            dict(fact_id='math_physics_alignment',**{k:d['relations'][0][k] for k in
                ('left','right','status','kind','alignment','missing_conditions','mathematical_aggregates','supported_scope','unsupported_conclusions')}),
            dict(fact_id='search_resolution',comparison=d['search_comparisons'][0])],
        round2=[dict(fact_id='scheduled_historical_feedback',source=dict(reference=p['profile']['motion'],pointer='/34'),
            final_time_s=.35,final_speed_m_s=d['task_diagnosis']['critical_samples'][-1]['observed']['speed_m_s'],
            holding_max_time_s=.31,holding_max_speed_m_s=p['acceptance']['metrics']['holding_max_speed_m_s'],
            exact_saved_update_ids=[r['update_id'] for r in controls['relevant_updates'] if r['complete_update_available']],
            new_execution=False,origin='Original B history, independent of both proposed actions; identical feedback in both arms')])
    data['sources_offline_only']['binding_rule']='All facts above retain original B Store references; no transfer into a new scientific candidate or acceptance.'
    cases=ROOT/'runs'/(out.name+'-inputs')/'cases.json';atomic_json(cases,data)
    probe.freeze(out,cases_path=cases,provider=s['spec']['runtime']['provider'],authorization=authorization)
    atomic_json(destination/'decision_protocol.json',data)
    return dict(status='frozen',request_ceiling=4,cases=str(cases),rubric=data['rubric_offline_only'])


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['offline','math','continuity','restore','probe-freeze','probe-live'])
    args=parser.parse_args()
    if args.mode in ('continuity','restore','probe-live'):load_credential(Path('~/.codex/.env').expanduser())
    value=(offline() if args.mode=='offline' else mathematics() if args.mode=='math' else
        decision_probe(args.mode=='probe-live') if args.mode.startswith('probe-') else continuity(args.mode=='restore'))
    print(json.dumps(value,ensure_ascii=True))
