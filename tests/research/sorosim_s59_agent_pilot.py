"""Explicit bounded S5.9 phases; existing Strands executor owns live choices."""
import argparse
import asyncio
from copy import deepcopy
import subprocess
from pathlib import Path
from tools.research import core, analysis, rl
from tools.research.agent import converse, decision_packet, pending, load_credential
from tools.research.feedback import import_experiment, result_view
from tools.research.holding_diagnostic import historical, snapshot_audit
from tools.research.numerics import archived, execution_source
from tools.research.state import state, save, update, guard
from tools.state_io import atomic_json, read, digest
from tools.platform_host import Host
from tests.research.sorosim_s56_refinement import plan

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/'configs/research/study_sorosim_s59_agent.json'
DEST=ROOT/'evidence/sorosim_s59'


def history():
    if (DEST/'historical_diagnostic.json').exists():value=read(DEST/'historical_diagnostic.json')
    else:
        value=historical();atomic_json(DEST/'historical_diagnostic.json',value)
    atomic_json(DEST/'short_probe_admission.json',snapshot_audit(value['results'][0]))


def prepare():
    host=core.prepare(SPEC)
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('s59_prepared'):return host
    s=state(host);history()
    raw=read(DEST/'historical_diagnostic.json');raw_ref=save(host,raw,'s59_historical_timeline')
    compact=dict(current_violation='holding speed > .020 m/s; S5.8 positions passed',
        raw_evidence=raw_ref,raw_pointer='/results',
        cases=[dict(source=r['source_result'],route=r['route'],peak=r['holding_peak'],
            reversals=r['late_vector_reversal_times_s'],displacement_m=r['late_displacement_m'],
            path_length_m=r['late_sampled_path_length_m'],scope=r['scope']) for r in raw['results']],
        effective_variables=['candidate length','Young modulus','routing (discrete)','holding/terminal tip speed weights','direct or residual PPO training settings'],
        ineffective_variables=['length-servo gain','motor stroke','motor speed limit'],
        minimal_falsifiable_experiment='After exact candidate math, change one effective variable and evaluate original task; snapshot probe unavailable.',
        support_and_counter_observations='Signed reversals and net displacement coexist; internal-mode and transient causation unknown.',
        short_probe=read(DEST/'short_probe_admission.json'))
    href=save(host,compact,'s59_compact_holding_diagnostic')
    baseline=read(ROOT/'evidence/sorosim_s56/physics/summary.json')
    params=deepcopy(archived('evidence/sorosim_s56/physics/study',baseline['candidate'])['parameters'])
    params['family_space_identity']=s['spec']['family_space_identity']
    candidate=core.dispatch(host,plan('generate',generation=params),'s59-engineering-B',origin='engineering')['result']['candidate']
    histories=[]
    for stage in ('s5a','s5b','s5rl','s56/physics','s56/rl','s58'):
        folder=f'evidence/sorosim_{stage}/study';summary=read(ROOT/f'evidence/sorosim_{stage}/summary.json')
        if stage=='s58':rows=[(r['reference'],r['route']) for r in summary['physical_results']]
        elif 'routes' in summary:rows=[(r['evaluation'],'rl') for r in summary['routes']]
        elif stage=='s56/physics':rows=[(summary['open_loop'],'fixed_tension'),(summary['nmpc'],'nmpc')]
        else:rows=[(summary['result'],'fixed_tension' if stage=='s5a' else 'nmpc')]
        histories += [import_experiment(host,folder,r,route) for r,route in rows if r]
    parent_id='sorosim-s58-agent-20261018';parent=Host(ROOT/'runs/research'/parent_id,parent_id)
    parents=[rl.import_continuation_source(host,parent,k) for k in state(parent)['rl_runs']]
    # Parent imports advertise legacy candidates; restore the fresh current ID map.
    candidates=state(host)['candidates'];current=host.store.artifact(candidate)
    candidates[current['identity']]=candidate;update(host,candidates=candidates)
    source=execution_source(dict(reference=baseline['nmpc']),'evidence/sorosim_s56/physics/study')
    o=archived(source['folder'],source['files']['controller_observations.json'])[29]
    control=archived(source['folder'],source['files']['control_spec.json'])
    old_cfg=archived(source['folder'],source['result']['candidate'])['configuration']
    cfg=host.store.artifact(candidate)['configuration']
    if cfg['robot']!=old_cfg['robot'] or cfg['task']!=old_cfg['task']:raise ValueError('HISTORY_STATE_REBIND_ROBOT_TASK_MISMATCH')
    tr=raw['results'][0]['timeline'][28]
    point=dict(candidate=candidate,configuration_identity=digest(cfg),x=o['measured_initial_state'],u=tr['actual_tension_n'],
        coordinate_order=control['specification']['coordinate_order'],tendon_order=control['specification']['tendon_order'],
        phase='interval_start_previous_applied_input',input_units='N',actual_time_s=o['time_s'],
        original_execution=baseline['nmpc'],original_state_pointer='/controller_observations/29',
        meaning='Exact archived projected GVS state; not a complete or exact MuJoCo integration snapshot.')
    point_ref=save(host,point,'s59_exact_projected_analysis_state')
    update(host,s59_candidate=candidate,s59_point=point_ref,holding_diagnostic_reference=href,
        stage_context=[dict(stage='S5.9 historical holding diagnostic',reference=href)],
        scoped_context=[href,*histories],s59_prepared=True,s59_parents=parents)
    atomic_json(DEST/'preparation.json',dict(candidate=candidate,point=point_ref,history_reference=href,
        history=histories,parents=parents,freeze=s['freeze'],ledger=host.store.remaining()))
    return host


def mathematics(host):
    s=state(host)
    if s.get('s59_math_complete'):return
    p=s['spec']['analysis_protocol'];base=s['s59_candidate'];refs=[]
    requests=[dict(candidate=base,operation='instantaneous_braking_v1',operating_point='saved_state',saved_state=s['s59_point'],protocol=p)]
    # Two declared static IFT comparisons: each has one baseline equilibrium,
    # plus/minus rebuilt residuals and two perturbed equilibrium verification solves.
    # Six equilibrium solves total; none is a trajectory NLP or physical replay.
    params=host.store.artifact(base)['parameters']
    for variable,step in [('length_m',.001),('young_pa',1000.)]:
        pair=[]
        for sign in (-1,1):
            generation=deepcopy(params)
            generation['segments']['0'][variable]+=sign*step
            key=f's59-{variable}-{sign}'
            pair.append(core.dispatch(host,plan('generate',generation=generation),key,origin='engineering')['result']['candidate'])
        requests.append(dict(candidate=base,operation='design_sensitivity',operating_point='fixed_input_equilibrium',protocol=p,
            design_sensitivity=dict(variable='segments.0.'+variable,step=step,minus_candidate=pair[0],plus_candidate=pair[1])))
    for i,request in enumerate(requests):
        response=analysis.dispatch(host,request,f's59-preparation-math-{i}',guard=guard,origin='engineering_preflight')
        value=host.store.artifact(response['reference']);view=analysis.decision_result(value,response['reference'])
        if value.get('sensitivity'):view['sensitivity']=value['sensitivity']
        refs.append(save(host,view,'s59_task_mathematical_summary'))
        atomic_json(DEST/f'math_{i}.json',dict(request=request,result=value,summary=view))
    update(host,task_math_references=refs,scoped_context=[*state(host)['scoped_context'],*refs],s59_math_complete=True,
        stage_context=[*state(host)['stage_context'],*[dict(stage='S5.9 task mathematics',reference=r) for r in refs]])
    atomic_json(DEST/'initial_research_packet.json',decision_packet(host))


def startup_correction(host):
    """Explicit confirmed pre-computation startup correction; all costs persist."""
    if state(host).get('s59_startup_corrected'):return
    refs=[]
    for i in range(3):
        old=read(DEST/f'math_{i}.json')
        if old['result'].get('error')!='UnicodeDecodeError' or old['result']['status']!='execution_incomplete':
            raise ValueError('ONLY_CONFIRMED_PRECOMPUTATION_STARTUP_FAILURE_CORRECTION')
        result=analysis.dispatch(host,old['request'],f's59-confirmed-startup-correction-{i}',guard=guard,origin='engineering_preflight')
        value=host.store.artifact(result['reference']);view=analysis.decision_result(value,result['reference'])
        if value.get('sensitivity'):view['sensitivity']=value['sensitivity']
        refs.append(save(host,view,'s59_corrected_task_math_summary'))
        atomic_json(DEST/f'math_startup_correction_{i}.json',dict(request=old['request'],result=value,summary=view,
            previous_failed_result=old['summary']['reference'],reason='Confirmed MATLAB startup failed inside sandbox before numerical evaluation; elevated environment-only startup succeeded.'))
    update(host,task_math_references=[*state(host)['task_math_references'],*refs],s59_startup_corrected=True,
        scoped_context=[*state(host)['scoped_context'],*refs],
        stage_context=[*state(host)['stage_context'],*[dict(stage='S5.9 corrected task mathematics',reference=r) for r in refs]])
    atomic_json(DEST/'corrected_initial_research_packet.json',decision_packet(host))


def export(host, blocker=None):
    if (DEST/'study/archive_manifest.json').exists():return
    s=state(host);actions=[];reads=[];usage=[]
    for e in host.store.events(host.run_id):
        if e['kind']=='model_original_tool_request':
            use=host.store.artifact(e['outputs'][0])['tool_use']
            actions.append(dict(tool_use=use,prior_reads=list(reads)))
            if use['name']=='evidence_read':reads.append(use['input'])
        elif e['kind']=='model_original_tool_feedback' and actions:actions[-1]['feedback']=host.store.artifact(e['outputs'][0])['result']
        elif e['kind']=='r3_response':usage.append(host.store.artifact(e['outputs'][0]))
    refs=[*s['results'],*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]
    summary=dict(study_id=host.run_id,freeze=s['freeze'],resolved_configuration_identity=s['spec']['resolved_identity'],
        research_status=s['research_status'],selected=s.get('selected'),final_disposition=s.get('final_disposition'),
        provider_requests=s['pilot']['live_model_requests'],resource_use=host.store.remaining(),
        mathematical_analyses=s.get('mathematical_evaluations',0),offline_nlp=s['offline_nlp'],mathematical_replays=s['bdf_replays'],
        nmpc_launches=s.get('nmpc_launches',0),physical_replay_launches=s.get('physical_replay_launches',0),
        results=[dict(reference=r,**result_view(host,r),raw=host.store.artifact(r)) for r in refs],
        rl=rl.allocation_feedback(host),short_probe=read(DEST/'short_probe_admission.json'),
        pending_science=s.get('pending'),pending_provider=pending(host),blocker=blocker,provider_usage=usage,money='unknown')
    atomic_json(DEST/'summary.json',summary)
    atomic_json(DEST/'decision_audit.json',dict(agent_actions=actions,guidance_reads=s.get('guidance_reads',[]),
        mathematical_summaries=s.get('task_math_references',[]),source_freeze=s['freeze']))
    core.export(host,DEST/'study')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['history','prepare','math','startup-correction','live','export']);args=parser.parse_args()
    if args.phase=='history':history();return
    if args.phase=='export':
        name=read(SPEC)['study_id'];export(Host(ROOT/'runs/research'/name,name,actor='unified-research'));return
    host=prepare()
    if args.phase=='prepare':return
    if args.phase=='startup-correction':startup_correction(host);return
    mathematics(host)
    if args.phase=='math':return
    if state(host)['research_status']=='stopped':export(host);return
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('CLEAN_COMMITTED_SOURCE_REQUIRED')
    load_credential(Path(state(host)['spec']['runtime']['credentials_reference']).expanduser())
    blocker=None
    try:asyncio.run(converse(host))
    except Exception as exc:
        blocker=dict(type=type(exc).__name__,reason=str(exc));save(host,blocker,'s59_live_blocker')
    export(host,blocker)


if __name__=='__main__':main()
