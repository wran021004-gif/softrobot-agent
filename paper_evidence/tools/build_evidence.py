"""Publication tables from immutable Git sources; standard library only.

Run from any directory: python paper_evidence/tools/build_evidence.py
No simulation, source edits, hashing, or dependency installation.
"""
import csv
import io
import json
import re
import subprocess
from collections import Counter
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'paper_evidence'
A = '15d4667050351c1cbf84e6ade6f573286d6d8ed0'
B = 'b97bee811f0bbf1bf0de94ce40045e9c8e9e3db5'
C = '9d6d160e050c836b87d0563a497fc0ec1c3761a8'
AB = 'codex/m1-ablation-gates-20261111'
BB = 'paper/p0-dataset-20261114'
CB = 'research/phs2d-inverse-passive-design'
MASTER = 'paper_experiments/paper_results_master_20261113/'
ABC = 'paper_experiments/FINAL_ABC_DATASET_P0_20261114/'
ARCH = 'paper_experiment_data/architecture_ablation/'
NINE = 'evidence/phs2d_round3_20261028/'
WORK = Path('D:/softrobot-agent')
UNKNOWN = 'UNKNOWN'
MANIFEST = []


def portable(x):
    if isinstance(x, dict):
        return {k: portable(v) for k, v in x.items()}
    if isinstance(x, list):
        return [portable(v) for v in x]
    if isinstance(x, str):
        # Historical paths remain original source identifiers, expressed from repo root.
        x = re.sub(r'D:[/\\]+softrobot-agent[/\\]+', '', x, flags=re.I)
        x = re.sub(r'\\{1,4}', '/', x)
        if x.strip().lower() in ('', 'unavailable', 'unavailable_in_sealed_evidence', 'none', 'null', 'nan'):
            return UNKNOWN
    return UNKNOWN if x is None else x


@lru_cache(None)
def source(ref, path):
    raw = subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)
    text = raw.decode('utf-8-sig')
    if path.endswith('.csv'):
        return list(csv.DictReader(io.StringIO(text)))
    return json.loads(text) if path.endswith('.json') else text


def locator(ref, path, pointer=''):
    return f'git:{ref}:{path}' + pointer


def provenance(ref, path, study=UNKNOWN, task=UNKNOWN, run=UNKNOWN,
               candidate=UNKNOWN, condition=UNKNOWN, pointer='', notes=''):
    branch = {A: AB, B: BB, C: CB}[ref]
    MANIFEST.append(dict(study_id=study, task_id=task, source_branch=branch,
                         source_path=path, run_id=run, candidate_id=candidate,
                         condition_id=condition, source_locator=locator(ref,path,pointer), notes=notes))
    return locator(ref, path, pointer)


def write_csv(path, rows, fields=None):
    path = OUT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    assert fields, path
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='raise')
        w.writeheader()
        for row in rows:
            row = {k: portable(row.get(k)) for k in fields}
            w.writerow({k: json.dumps(v, ensure_ascii=False, separators=(',', ':'))
                        if isinstance(v, (dict, list)) else v for k, v in row.items()})


def write_json(path, value):
    p = OUT/path
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(portable(value),ensure_ascii=False,indent=2,allow_nan=False)+'\n','utf-8')


def study(task):
    return 'PHS-2D-7S' if task == 'PHS-2D' else task+'-FULL'


def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None


NAMES = [
 ('T01','Multi-target Reach-and-Hold','多目标到达与保持'),
 ('T02','Load-Conditioned Hold','带载受扰保持'),
 ('T03','Fast Target Reaching','快速到达'),
 ('T04','Figure-Eight Trajectory Tracking','双叶八字轨迹跟踪'),
 ('T05','End-Effector Position and Tool-Axis Alignment','末端位置与工具轴向对齐'),
 ('T06','Loaded Time-Indexed Pose Scanning','带载时序位置—姿态扫描'),
 ('T07','Shared-Morphology Multi-Task Design','共享形态多任务设计'),
 ('T08','Passive Progressive-Stiffness Response','被动渐进刚度响应'),
 ('T09','Guided Spring-Button Contact Manipulation','导向式弹簧按钮接触操作'),
 ('T10','Impact-Recovery Control','外部冲击恢复控制'),
 ('PHS-2D','Passive Tendon-Constrained Compliance and Tip Suppression','被动腱约束柔顺与末端抑制')]


def build():
    tasks = source(A, MASTER+'SOURCE_DATA/FULL_TASKS.json')
    cases = source(A, MASTER+'SOURCE_DATA/FULL_CASES.json')
    protocols = source(A, MASTER+'SOURCE_DATA/PROTOCOLS.json')
    d1 = source(B, ABC+'D1_ABC_STATUS_MATRIX.csv')
    d2 = source(B, ABC+'D2_ABC_CONDITION_METRICS.csv')
    d3 = source(B, ABC+'D3_ABC_EVIDENCE_ACTIONS.csv')
    summary9 = source(C,NINE+'summary.json')
    design9 = source(C,NINE+'solution/design.json')
    journal = source(C,NINE+'experiment_journal.json')
    registry=[]; summaries=[]; studies=[]
    for t in tasks:
        tid=t['task_id']; sid=study(tid); st=t['structure_type']
        name,zh=next((n,z) for i,n,z in NAMES if i==tid)
        src=provenance(A,MASTER+'SOURCE_DATA/FULL_TASKS.json',sid,tid,t['run_id'],pointer=f'#task_id={tid}')
        registry.append(dict(task_id=tid,study_id=sid,canonical_name=name,chinese_name=zh,
            task_family=t['task_category'],morphology=json.dumps(st,ensure_ascii=False),
            segment_count=st['flexible_segments'],tendon_count=st['tendons'],actuator_count=st['actuators'],
            required_condition_count=t['total_conditions'],study_role='FULL_portfolio',source_reference=src))
        c=next(x for x in d1 if x['task_id']==tid and x['method']=='C')
        margins=[-num(x['signed_normalized_violation']) for x in d2 if x['task_id']==tid and x['method']=='C'
                 and x['condition_role']=='required' and x['is_constraint']=='true' and num(x['signed_normalized_violation']) is not None]
        summaries.append(dict(task_id=tid,study_id=sid,method='C',run_id=t['run_id'],
            status=c['status'],required_condition_count=t['total_conditions'],passed_condition_count=t['passed_conditions'],
            required_condition_completion=c['completion_fraction'],evaluation_coverage=c['evaluation_coverage'],
            normalized_constraint_violation=c['violation_fraction'],maximum_normalized_violation=c['maximum_violation'],
            minimum_normalized_constraint_margin=min(margins) if margins else UNKNOWN,
            control_condition_count=len(t.get('control_conditions',[])),source_reference=src,
            comparison_source=locator(B,ABC+'D1_ABC_STATUS_MATRIX.csv',f'#task_id={tid}&method=C'),
            qualification_scope=t.get('physical_validation',UNKNOWN)))
        studies.append(dict(study_id=sid,task_id=tid,original_run_id=t['run_id'],role='FULL_portfolio',
                            source_branch=AB,source_commit=A,source_reference=src))
    registry.append(dict(task_id='PHS-2D',study_id='PHS-2D-9S',canonical_name=NAMES[-1][1],chinese_name=NAMES[-1][2],
        task_family='passive_compliance_tip_suppression',morphology='nine flexible segments; four passive tendons; eight massive guide plates',
        segment_count=9,tendon_count=4,actuator_count=0,required_condition_count=10,study_role='independent_mechanism_extension',
        source_reference=provenance(C,NINE+'solution/design.json','PHS-2D-9S','PHS-2D',pointer='#/configuration/robot')))
    studies.append(dict(study_id='PHS-2D-9S',task_id='PHS-2D',original_run_id='phs2d-inverse-passive-design-20261028-v1;v2',
        role='independent_mechanism_extension',source_branch=CB,source_commit=C,
        source_reference=locator(C,NINE+'summary.json')))
    summaries.append(dict(task_id='PHS-2D',study_id='PHS-2D-9S',method='independent_study',run_id='phs2d-inverse-passive-design-20261028-v2',
        status=summary9['status'],required_condition_count=10,passed_condition_count=10,required_condition_completion=1,
        evaluation_coverage=1,normalized_constraint_violation=UNKNOWN,maximum_normalized_violation=UNKNOWN,
        minimum_normalized_constraint_margin=UNKNOWN,control_condition_count=0,
        source_reference=provenance(C,NINE+'summary.json','PHS-2D-9S','PHS-2D'),comparison_source=UNKNOWN,
        qualification_scope=summary9['task_scope']))
    write_csv('registry/task_registry.csv',registry)
    write_csv('registry/study_registry.csv',studies)
    write_csv('task_metrics/task_summary.csv',summaries)
    # D1/D2 definitions are authoritative. Keep validity and missingness, omit irrelevant attribution/version fields.
    drop1={'source_classification','core_shas','core_sha_basis','configuration_version'}
    abc=[dict(study_id=study(x['task_id']),**{k:v for k,v in x.items() if k not in drop1},
              source_reference=provenance(B,ABC+'D1_ABC_STATUS_MATRIX.csv',study(x['task_id']),x['task_id'],x['run_id'],x['selected_candidate_id'],pointer=f'#task_id={x["task_id"]}&method={x["method"]}')) for x in d1]
    write_csv('task_metrics/research_mode_summary.csv',abc)
    conditions=[]
    for i,x in enumerate(d2,2):
        conditions.append(dict(record_id=f'ABC-CM-{i-1:04d}',study_id=study(x['task_id']),**x,
            normalized_constraint_margin=-num(x['signed_normalized_violation']) if num(x['signed_normalized_violation']) is not None else UNKNOWN,
            source_reference=locator(B,ABC+'D2_ABC_CONDITION_METRICS.csv',f'#row={i}')))
    provenance(B,ABC+'D2_ABC_CONDITION_METRICS.csv',notes='All 3160 constraint and observable rows. Original normalization and statuses preserved.')
    write_csv('task_metrics/condition_metrics.csv',conditions)
    # Physical FULL measurements retain observables that the constraint table does not contain.
    observables=[]
    for i,c in enumerate(cases):
        for metric,value in c['metrics'].items():
            if not isinstance(value,(int,float)):continue
            observables.append(dict(task_id=c['task_id'],study_id=study(c['task_id']),condition_id=c['condition_name'],
                condition_role=c['condition_role'],candidate_id=c['candidate_id'],metric_id=metric,value=value,
                source_reference=locator(A,MASTER+'SOURCE_DATA/FULL_CASES.json',f'#/{i}/metrics/{metric}')))
    write_csv('task_metrics/full_observables.csv',observables)
    # Scope-preserving resources; never combine these populations.
    resources=[]
    for scope,ref,path in [('ABC_original_run',B,ABC+'RESOURCE_COSTS.csv'),('FULL_original_measurement',A,MASTER+'RESOURCE_COSTS.csv')]:
        for i,x in enumerate(source(ref,path),2):
            drop={'codex_llm_tokens','source_classification','core_shas','configuration_version','source_reference'}
            resources.append(dict(resource_record_id=f'{scope}-{i-1:03d}',study_id=study(x['task_id']),measurement_population=scope,
                **{k:v for k,v in x.items() if k not in drop},provider_input_tokens=UNKNOWN,provider_output_tokens=UNKNOWN,
                original_source_reference=x.get('source_reference',x.get('cost_source')),source_reference=locator(ref,path,f'#row={i}')))
        provenance(ref,path,notes=scope+'; individual scopes retained; no cross-scope sum or mean')
    resources.append(dict(resource_record_id='9S-original-study',study_id='PHS-2D-9S',task_id='PHS-2D',
        measurement_population='9S_original_cumulative_development',candidate_count=summary9['budgets']['generation_attempts'],
        mathematical_calls=summary9['budgets']['math_requests'],integration_steps=summary9['budgets']['physics_step_attempts'],
        wall_time_s=summary9['budgets']['elapsed_numerical_s'],wall_time_scope='charged numerical elapsed; original summary',
        provider_input_tokens=UNKNOWN,provider_output_tokens=UNKNOWN,source_reference=locator(C,NINE+'summary.json','#/budgets')))
    write_csv('task_metrics/resource_metrics.csv',resources)
    # Candidate designs: source table contains actual stored configuration fields, no inferred parentage.
    candidates=[]
    for i,x in enumerate(source(A,MASTER+'CANDIDATE_EVOLUTION.csv'),2):
        candidates.append(dict(candidate_record_id=f'FULL-D{i-1:03d}',study_id=study(x['task_id']),**x,
                              extraction_scope='stored configuration',original_table_reference=provenance(A,MASTER+'CANDIDATE_EVOLUTION.csv',study(x['task_id']),x['task_id'],x['run_id'],pointer=f'#row={i}')))
    for i,x in enumerate(journal):
        g=x['generation']
        candidates.append(dict(candidate_record_id='9S-'+x['label'],task_id='PHS-2D',study_id='PHS-2D-9S',
            run_id=x['study_id'],structure_version_within_run=i+1,candidate_ids=x['label'],segment_count=g.get('segment_count'),
            tendon_count=g.get('tendon_count'),segment_lengths_m=[v.get('length_m') for v in g.get('segments',{}).values()],
            segment_young_pa=[v.get('young_pa') for v in g.get('segments',{}).values()],
            sections_json={k:v.get('sections') for k,v in g.get('segments',{}).items()},
            tendon_routes_json=g.get('route_overrides'),rigid_components_json=g.get('guide_hole_positions_m'),
            generation_json=g,original_hypothesis=x['hypothesis'],
            extraction_scope='original journal generation configuration; actual XML must verify render',
            source_reference=provenance(C,NINE+'experiment_journal.json','PHS-2D-9S','PHS-2D',x['study_id'],x['label'],pointer=f'#/{i}')))
    for i,x in enumerate(source(A,MASTER+'SOURCE_DATA/PHS_CANDIDATE_INDEX.csv'),2):
        original_path=Path(x['source_reference'])
        candidate=json.loads(original_path.read_text('utf-8-sig'))
        resolved=candidate['resolved_parameters'];structure=candidate['configuration']['robot']['structure']['data']
        segs=resolved['segments']
        candidates.append(dict(candidate_record_id='7S-'+x['candidate'],task_id='PHS-2D',study_id='PHS-2D-7S',
            run_id='psd2d-core-fresh-20261112',structure_version_within_run=x['candidate'],candidate_ids=candidate['candidate_id'],
            segment_count=len(segs),tendon_count=len(resolved['tendons']),segment_lengths_m=[s['length_m'] for s in segs],
            segment_young_pa=[s.get('physics',{}).get('young_pa') for s in segs],sections_json=[s.get('sections') for s in segs],
            tendon_routes_json=structure['tendons'],rigid_components_json=[s for s in structure['components'] if s.get('kind')!='flexible_segment'],
            fixed_payout_lengths_m=structure.get('fixed_payout_lengths_m'),source_reference=portable(str(original_path)),
            original_table_reference=provenance(A,MASTER+'SOURCE_DATA/PHS_CANDIDATE_INDEX.csv','PHS-2D-7S','PHS-2D',candidate=x['candidate'],pointer=f'#row={i}'),
            model_xml_reference=x['model_xml'],extraction_scope='actual stored candidate configuration; seven-segment Study history, not nine-segment Journal'))
    write_csv('task_metrics/candidate_evolution.csv',candidates)
    screens=[];predictions=[]
    for i,x in enumerate(journal):
        predictions.append(dict(study_id='PHS-2D-9S',candidate_id=x['label'],**x.get('mathematical_prediction',{}),
            source_reference=locator(C,NINE+'experiment_journal.json',f'#/{i}/mathematical_prediction')))
        for k,r in enumerate(x.get('observed_nonlinear_rows',[])):
            screens.append(dict(record_id=x['label']+'-N'+str(k),study_id='PHS-2D-9S',candidate_id=x['label'],
                evidence_scope='local_nonlinear_screen',**r,source_reference=locator(C,NINE+'experiment_journal.json',f'#/{i}/observed_nonlinear_rows/{k}')))
        if x['label']!='P3_real9_E80_full8':
            for j,group in enumerate(x.get('dynamic_observations',[])):
                for k,r in enumerate(group.get('rows',[])):
                    keep={key:r.get(key) for key in ['s','force_n','point_dx_m','tip_xy_m','ratio','status','valid','geometry','worst_violation','failed_checks','max_tail_residual_nm','max_tail_qvel_rad_s','reference']}
                    screens.append(dict(record_id=x['label']+'-D'+str(j)+'-'+str(k),study_id='PHS-2D-9S',candidate_id=x['label'],
                        evidence_scope='original_finite_dynamics',**keep,source_reference=locator(C,NINE+'experiment_journal.json',f'#/{i}/dynamic_observations/{j}/rows/{k}')))
    write_csv('task_metrics/phs9_candidate_screens.csv',screens)
    write_csv('task_metrics/phs9_mathematical_predictions.csv',predictions)
    write_csv('task_metrics/phs7_candidate_progress.csv',[dict(study_id='PHS-2D-7S',**x) for x in source(A,MASTER+'FIGURE_DATA/PHS_CANDIDATE_PROGRESS.csv')])
    # Nine-segment final geometry: keep normalized physical fields, not duplicate design/trace bodies.
    robot=design9['configuration']['robot']
    write_json('task_metrics/phs9_final_structure.json',dict(study_id='PHS-2D-9S',candidate_label=design9['label'],
        candidate_reference=design9['candidate'],robot=robot,physics=design9['physics'],
        generation_reference='task_metrics/candidate_evolution.csv#candidate_record_id=9S-P3_real9_E80_full8',payout_lengths_m=design9['payout_lengths_m'],protocol=design9['protocol'],
        source_reference=locator(C,NINE+'solution/design.json'),model_xml_reference=locator(C,NINE+'solution/model.xml')))
    phs=[];centerlines=[];tensions=[]
    for i,r in enumerate(source(A,MASTER+'SOURCE_DATA/PHS2D/TEN_CASE_RESULTS.csv'),2):
        phs.append(dict(study_id='PHS-2D-7S',task_id='PHS-2D',replicate_id=0,validation_scope='nominal_full_ten_case',
            condition_id=r['load_condition'],material_s=r['material_s'],force_n=r['force_x_n'],point_displacement_m=r['point_x_abs_m'],
            tip_displacement_m=r['tip_projected_m'],tip_to_point_ratio=r['ratio'],out_of_plane_m=r['max_plane_y_m'],
            passed=r['accepted'],geometry_status=r['route_status'],
            source_reference=provenance(A,MASTER+'SOURCE_DATA/PHS2D/TEN_CASE_RESULTS.csv','PHS-2D-7S','PHS-2D',r['run_id'],condition=r['load_condition'],pointer=f'#row={i}')))
    for j,group in enumerate(summary9['final_sets']):
        for k,r in enumerate(group['rows']):
            cid=f's{round(r["s"]*10)}_'+('positive' if r['force_n']>0 else 'negative')
            ref=locator(C,NINE+'summary.json',f'#/final_sets/{j}/rows/{k}')
            phs.append(dict(study_id='PHS-2D-9S',task_id='PHS-2D',replicate_id=group['replicate'],
                validation_scope='original_'+('holdout' if group['holdout'] else 'development')+'_loads',
                condition_id=cid,material_s=r['s'],force_n=r['force_n'],point_displacement_m=r['point_dx_m'],
                tip_displacement_m=r['tip_xy_m'],tip_to_point_ratio=r['ratio'],out_of_plane_m=r['out_of_plane_m'],
                passed=r['status']=='development_pass' and r['valid'],geometry_status=r['geometry'],
                perturbation=group.get('perturbation'),timestep_s=group.get('timestep'),
                source_reference=ref))
            if group['replicate']==1:
                for n,p in enumerate(r.get('positions',[])):
                    centerlines.append(dict(study_id='PHS-2D-9S',condition_id=cid,point_index=n,x_m=p[0],y_m=p[1],z_m=p[2],source_reference=ref+'/positions/'+str(n)))
                for n,t in enumerate(r.get('final_tensions_n',[])):
                    tensions.append(dict(study_id='PHS-2D-9S',condition_id=cid,tendon_index=n,tension_n=t,taut=r['taut'][n],source_reference=ref+'/final_tensions_n/'+str(n)))
    write_csv('task_metrics/phs_performance.csv',phs)
    write_csv('task_metrics/phs9_centerlines.csv',centerlines)
    write_csv('task_metrics/phs9_tensions.csv',tensions)
    gradients=[]
    for x in source(B,ABC+'PHS2D_9SEG_GRADIENT_FIGURE_DATA.csv'):
        gradients.append(dict(study_id='PHS-2D-9S',source_study_id=x['study_id'],**{k:v for k,v in x.items() if k!='study_id'},
            source_reference=locator(B,ABC+'PHS2D_9SEG_GRADIENT_FIGURE_DATA.csv',f'#branch_id={x["branch_id"]}&metric={x["metric"]}')))
    provenance(B,ABC+'PHS2D_9SEG_GRADIENT_FIGURE_DATA.csv','PHS-2D-9S','PHS-2D',notes='18 derivatives along one common Young modulus direction; local consistency, not physical acceptance')
    write_csv('task_metrics/gradient_validation.csv',gradients)
    nodes=build_nodes(tasks,cases,journal)
    build_architecture()
    build_registries(d2)
    # Preserve all evidence-action relations, failures and unlinked events.
    links=[dict(study_id=study(x['task_id']),**{k:v for k,v in x.items() if k not in {'core_sha','source_version'}},
                source_reference=locator(B,ABC+'D3_ABC_EVIDENCE_ACTIONS.csv',f'#event_id={x["event_id"]}')) for x in d3]
    write_csv('research_nodes/evidence_action_links.csv',links)
    provenance(B,ABC+'D3_ABC_EVIDENCE_ACTIONS.csv',notes='Original explicit relation and execution statuses; absence of an edge is not scored as execution.')
    figures(registry,phs,gradients,nodes,abc,candidates)
    # Exactly one manifest row per original record locator.
    unique={tuple(str(portable(v)) for v in x.values()):x for x in MANIFEST}
    write_csv('source_manifest.csv',list(unique.values()))
    print(json.dumps(dict(tasks=len(tasks),required=sum(t['total_conditions'] for t in tasks),
        conditions=len(conditions),abc=len(abc),nodes=len(nodes),gradients=len(gradients),candidates=len(candidates))))


def original_arguments(e):
    return e.get('exact_input',{}).get('arguments',e.get('exact_input',{}))


def build_nodes(tasks,cases,journal):
    selected=source(A,MASTER+'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json')
    indexed={e['stage_id']:e for e in selected}
    original=source(A,MASTER+'KEY_RESEARCH_NODES.csv')
    nodes=[]
    for x in original:
        if x['task_id']=='PHS-2D':continue
        event=indexed.get(x['stage_id']);follow=event['following_events'][0] if event else {}
        args=original_arguments(follow); tid=x['task_id']
        status=follow.get('status','UNKNOWN')
        output=follow.get('output')
        nodes.append(dict(node_id=x['stage_id'],task_id=tid,study_id=study(tid),sequence=int(x['stage_id'].split('-')[-1]),
            candidate_id=x['candidate_id'],observation=x['observation'],
            hypothesis=args.get('hypothesis',event['decision'].get('rationale') if event else UNKNOWN),
            hypothesis_origin='original formal request' if args.get('hypothesis') else 'original decision rationale',
            expected_observation=args.get('expected_observation'),weakening_observation=args.get('weakening_observation'),
            mathematical_evidence=portable(x['evidence_reference']) if follow.get('tool_name') in ['research.math','task.initial_state.construct'] else UNKNOWN,
            physical_evidence=portable(x['evidence_reference']),research_action=x['decision'],action_executed=status=='completed',
            execution_status=status,resulting_candidate_id=follow.get('candidate_id'),resulting_metric=x['measured_result'],
            outcome_scope='retrospective indexed outcome; not necessarily immediate action or causal effect',
            improvement=UNKNOWN,actual_design_change=original_arguments(follow).get('generation',{}),
            source_reference=provenance(A,MASTER+'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json',study(tid),tid,x['run_id'],x['candidate_id'],pointer=f'#stage_id={x["stage_id"]}'),
            original_evidence_reference=x['evidence_reference'],visual_asset_reference=UNKNOWN,
            original_action_id=follow.get('event_id'),run_id=x['run_id']))
    # Sparse tasks get a distinct independent evaluation node, drawn from the actual trace.
    for tid in ['T03','T05','T06']:
        event=next(e for e in selected if e['stage_id'].startswith(tid+'-'))
        path=Path(event['decision']['source'])
        trace=[json.loads(s) for s in path.read_text('utf-8-sig').splitlines() if s.strip()]
        evals=[e for e in trace if original_arguments(e).get('action')=='physical_replay' and e.get('output') is not None and e.get('status')=='completed']
        if not evals:continue
        e=evals[-1];args=original_arguments(e)
        nodes.append(dict(node_id=tid+'-EVAL',task_id=tid,study_id=study(tid),sequence=999,candidate_id=e.get('candidate_id'),
            observation='Independent original-task evaluation following control search.',hypothesis=args.get('hypothesis'),hypothesis_origin='original formal request',
            expected_observation=args.get('expected_observation'),weakening_observation=args.get('weakening_observation'),mathematical_evidence=UNKNOWN,
            physical_evidence=portable(str(path))+'#'+e['event_id'],research_action='Independent complete original-task physical replay',
            action_executed=True,execution_status=e['status'],resulting_candidate_id=e.get('candidate_id'),
            resulting_metric=next(t for t in tasks if t['task_id']==tid)['primary_metrics'],outcome_scope='independent full-task evaluation',
            improvement=UNKNOWN,actual_design_change={},source_reference=portable(str(path))+'#'+e['event_id'],
            original_evidence_reference=portable(str(path))+'#'+e['event_id'],visual_asset_reference=UNKNOWN,original_action_id=e['event_id'],run_id=e.get('study_id')))
    # Four representative 7S nodes from its own index, never from the nine-segment Journal.
    seven=[x for x in original if x['task_id']=='PHS-2D']
    for index in [0,3,6,len(seven)-1]:
        x=seven[index]
        nodes.append(dict(node_id='7S-'+x['stage_id'],task_id='PHS-2D',study_id='PHS-2D-7S',sequence=index+1,
            candidate_id=x['candidate_id'],observation=x['observation'],hypothesis=x['hypothesis'],
            hypothesis_origin='retrospective source index; contemporary hypothesis UNKNOWN',
            expected_observation=UNKNOWN,weakening_observation=UNKNOWN,mathematical_evidence=x['evidence_reference'],physical_evidence=x['evidence_reference'],
            research_action=x['decision'],action_executed=UNKNOWN,execution_status=UNKNOWN,resulting_candidate_id=UNKNOWN,resulting_metric=x['measured_result'],
            improvement=UNKNOWN,outcome_scope='indexed outcome; consult original evidence for execution',actual_design_change={},
            source_reference=provenance(A,MASTER+'KEY_RESEARCH_NODES.csv','PHS-2D-7S','PHS-2D',x['run_id'],x['candidate_id'],pointer='#stage_id='+x['stage_id']),
            original_evidence_reference=x['evidence_reference'],visual_asset_reference=UNKNOWN,run_id=x['run_id']))
    # Distinct visual mechanisms in the nine-segment Study's own history.
    for index in [9,15,31,43]:
        x=journal[index];dyn=x.get('dynamic_observations',[]);nonlinear=x.get('observed_nonlinear_rows',[])
        nodes.append(dict(node_id='9S-'+x['label'],task_id='PHS-2D',study_id='PHS-2D-9S',sequence=index+1,
            candidate_id=x['label'],observation=journal[index-1].get('next_recorded_hypothesis',{}),
            hypothesis=x['hypothesis'],hypothesis_origin='original independent Study Journal',expected_observation=UNKNOWN,weakening_observation=UNKNOWN,
            mathematical_evidence=x.get('mathematical_prediction'),physical_evidence=[{k:r.get(k) for k in ['s','force_n','status','valid','point_dx_m','tip_xy_m','ratio','geometry','reference']} for r in nonlinear],
            research_action=x['generation'],action_executed=True,execution_status='journal_records_generated_and_evaluated',
            resulting_candidate_id=x['label'],resulting_metric=[dict(all_pass=d.get('all_pass'),all_valid=d.get('all_valid'),rows=[{k:r.get(k) for k in ['s','force_n','point_dx_m','tip_xy_m','ratio','status','valid']} for r in d.get('rows',[])]) for d in dyn],
            outcome_scope='local nonlinear screen and explicitly recorded dynamics kept separate',improvement=UNKNOWN,actual_design_change=x['generation'],
            source_reference=locator(C,NINE+'experiment_journal.json',f'#/{index}'),original_evidence_reference=locator(C,NINE+'experiment_journal.json',f'#/{index}'),
            visual_asset_reference=locator(C,NINE+'solution/model.xml') if index==43 else UNKNOWN,run_id=x['study_id']))
    write_csv('research_nodes/research_nodes.csv',nodes)
    # Initial model-assisted annotations are evidence-limited, not expert ratings.
    annotations=[];ranks=[]
    for n in nodes:
        specific=n.get('expected_observation') not in [None,UNKNOWN] and not str(n['expected_observation']).startswith('A complete registered result')
        contemporary='retrospective' not in n.get('hypothesis_origin','')
        scores={'Hypothesis Testability':3 if specific else 1 if contemporary else 0,
                'Evidence Grounding':3 if contemporary else 2,
                'Method Appropriateness':2,
                'Research Adaptation':3 if n['node_id'] in ['T01-127','T04-216','T07-074','T07-106','T10-210'] else 2 if contemporary else UNKNOWN,
                'Evidence-to-Action':3 if n['action_executed'] is True else 1 if n['action_executed']==UNKNOWN else 0,
                'Rejection Quality':3 if n['node_id'] in ['T07-074','T04-216'] else UNKNOWN}
        for dimension,score in scores.items():
            rationale={
                'Hypothesis Testability':'Specific expected and weakening observations present.' if specific else 'Original expectations are generic or absent; no retrospective falsification criterion added.',
                'Evidence Grounding':'Original request/index locator retained. Local predictions and later full-task outcomes have different scopes.',
                'Method Appropriateness':'Method named; solver/physical applicability requires the exact original result. Conservative first-pass score.',
                'Research Adaptation':'Explicit recorded route/control/geometry revision.' if scores['Research Adaptation']==3 else 'Related research step; adaptation attribution remains partial or unknown.',
                'Evidence-to-Action':'Recorded action completion supports execution; full acceptance is separately identified.' if n['action_executed'] is True else 'No verified completed action in this extracted record.',
                'Rejection Quality':'Earlier failed approach motivates recorded revision.' if score==3 else 'No explicit candidate rejection established in this node.'}[dimension]
            annotations.append(dict(node_id=n['node_id'],dimension=dimension,score=score,rationale=rationale,
                supporting_evidence_reference=n['source_reference'],confidence='medium' if score!=UNKNOWN else 'low',
                uncertain_fields='solver applicability; immediate numeric change; causal attribution',annotation_round='initial_model_assisted'))
        # Physical outcome is quantitative and explicitly not another ordinal score.
        annotations.append(dict(node_id=n['node_id'],dimension='Physical Outcome',score=UNKNOWN,
            rationale='Use physical metrics in research_nodes.resulting_metric / condition_metrics; no subjective physical-outcome score.',
            supporting_evidence_reference=n['source_reference'],confidence='medium',uncertain_fields='immediate before-after metric pairing',annotation_round='quantitative_only'))
        weights=[3,3 if n['action_executed'] is True else 1,3 if n.get('actual_design_change') else 2,3,4 if n['study_id']=='PHS-2D-9S' else 2]
        ranks.append(dict(node_id=n['node_id'],task_id=n['task_id'],study_id=n['study_id'],
            scientific_contribution=weights[0],physical_evidence_strength=weights[1],before_after_difference=weights[2],
            research_decision_value=weights[3],visual_presentation_potential=weights[4],editorial_priority=sum(weights)/5,
            ranking_role='editorial only; provisional until independent review',recommended_display='same-scale structure and evidence sequence' if n.get('actual_design_change') else 'control/evidence sequence',
            source_reference=n['source_reference']))
    write_csv('research_nodes/decision_annotations.csv',annotations)
    write_csv('research_nodes/node_ranking.csv',ranks)
    write_csv('annotation/annotation_results.csv',annotations)
    return nodes


def build_architecture():
    reporter=source(B,ARCH+'reporter_on_off/pairwise_results.csv')
    pairs=[dict(pair_id=x['snapshot_id'],protocol_id='Reporter-six-pair',study_id='Reporter-six-pair',task_id='T01' if x['snapshot_id'].startswith('M1') else 'T08',**x,
        source_reference=provenance(B,ARCH+'reporter_on_off/pairwise_results.csv','Reporter-six-pair',task='T01' if x['snapshot_id'].startswith('M1') else 'T08',pointer='#snapshot_id='+x['snapshot_id'])) for x in reporter]
    write_csv('architecture_metrics/reporter_pairs.csv',pairs)
    positives=[]
    for x in source(B,ARCH+'reporter_on_off/figure_data/reporter_positive_cases.csv'):
        cid=x['case_id']
        positives.append(dict(case_id=cid,task_id='T01' if cid.startswith('M1') else 'T08',study_id='Reporter-six-pair',off_decision=x['reporter_off_decision'],on_decision=x['reporter_on_decision'],
            reporter_interpretation=x['reporter_interpretation'],evidence_gap='direction-specific paired mechanism evidence' if cid=='P3-A' else 'unverified initialization and frozen iteration budget',
            constraint_boundary=x.get('iteration_budget') if cid=='M1-C' else 'complete passive structure benchmark, directional ablations and full acceptance',
            proposed_experiment=x['action_difference'],score_off=x['off_score'],score_on=x['on_score'],score_delta=x['score_delta'],
            action_status=x['action_status'],supporting_evidence=x['supporting_evidence'],source_reference=locator(B,ARCH+'reporter_on_off/figure_data/reporter_positive_cases.csv','#case_id='+cid)))
    write_csv('architecture_metrics/reporter_positive_cases.csv',positives)
    ks=source(B,ARCH+'knowledge_skill/figure_data/factorial_results.csv')
    rows=[];clips=[]
    for x in ks:
        row=dict(protocol_id='E1-original-four-cells',**x,source_reference=provenance(B,ARCH+'knowledge_skill/figure_data/factorial_results.csv',task=x['task_id'],pointer=f'#task_id={x["task_id"]}&condition={x["condition"]}'))
        rows.append(row)
        if x['condition'] in ['K+S-','K-S+']:
            decision=source(B,portable(x['decision_source_file']))['decision']
            clips.append(dict(task_id=x['task_id'],resource_type='Knowledge' if x['condition']=='K+S-' else 'Skill',
                condition=x['condition'],resource_entries=x['experience_entries_delivered'],observed_influence=x['experience_integration'],
                actual_decision=decision,physical_followup_executed=False,source_reference=portable(x['decision_source_file'])+'#/decision',
                score_reference=portable(x['score_source'])))
    write_csv('architecture_metrics/knowledge_skill.csv',rows)
    write_csv('architecture_metrics/knowledge_skill_cases.csv',clips)
    effects=source(B,ARCH+'knowledge_skill/figure_data/factorial_effects.csv')
    write_csv('architecture_metrics/knowledge_skill_effects.csv',effects)
    contexts=[]
    for protocol,path in [('E2-C035','context_flat_vs_l0_l3/figure_data/context_comparison_table.csv'),('E2-R2-C037','context_flat_vs_l0_l3_v2/figure_data/pairwise_results.csv')]:
        for x in source(B,ARCH+path):
            contexts.append(dict(protocol_id=protocol,study_id='PHS-2D-7S',**x,
                source_reference=provenance(B,ARCH+path,'PHS-2D-7S','PHS-2D',pointer='#snapshot_id='+x['snapshot_id'])))
    write_csv('architecture_metrics/context_pairs.csv',contexts)
    write_csv('architecture_metrics/context_retrieval_path.csv',source(B,ARCH+'context_flat_vs_l0_l3_v2/figure_data/retrieval_path.csv'))
    request_usage=[]
    paths=[('E2-C035','context_flat_vs_l0_l3/figure_data/token_request_accounting.json'),
           ('E2-R2-C037','context_flat_vs_l0_l3_v2/figure_data/token_accounting_per_request.csv')]
    for protocol,path in paths:
        data=source(B,ARCH+path)
        requests=data['requests'] if isinstance(data,dict) else data
        for i,r in enumerate(requests):
            request_usage.append(dict(protocol_id=protocol,checkpoint_id=r['snapshot_id'],condition=r['condition'],session_id=r['session_id'],
                request_index=r.get('turn',r.get('request_turn')),http_status=r['http_status'],input_tokens_actual=r.get('input_tokens_actual'),
                output_tokens_actual=r.get('output_tokens_actual'),usage_status=r['usage_status'],cached_input_tokens_actual=r.get('cached_input_tokens_actual'),
                source_reference=locator(B,ARCH+path,f'#/requests/{i}' if isinstance(data,dict) else f'#row={i+2}')))
        provenance(B,ARCH+path,'PHS-2D-7S','PHS-2D',notes='Actual per-Main-request usage; estimates deliberately kept out of this normalized actual-usage table.')
    write_csv('architecture_metrics/context_request_usage.csv',request_usage)


def build_registries(d2):
    symbols=[('τ','Task'),('d','Robot morphology/design'),('D','Admissible design space'),('θ','Controller parameters'),('U','Control input sequence'),('q','Generalized coordinates'),('gτ,i','Task constraint'),('Vτ(d)','Re-optimized task violation'),('sk','Research state'),('Hk','Working physical hypothesis'),('Ek','Accumulated evidence'),('ak','Research action'),('Pk','PPRP'),('Ik','Selected parameter group'),('Ok','Selected physical observables'),('σk','Selected analysis semantics'),('Bk','Research budget'),('E_math','Mathematical Evidence'),('E_phys','Physical Evidence'),('M0: m(d)','Mechanism Sensitivity'),('M1: yτ(d,U0)','Fixed-input Physical Response'),('M2: Vτ(d)','Re-optimized Task Capability'),('M3: Jτ,H(d,θ)','Closed-loop Performance')]
    write_csv('registry/symbol_registry.csv',[dict(symbol=s,meaning=m,notation_rule='I_k is selected parameters; D is admissible design space. M0–M3 are complementary semantics.',source_reference='user specification §4.1') for s,m in symbols])
    definitions=[
      ('required_condition_completion','Required Condition Completion','Cτ','fraction','higher','passed required conditions / frozen required count'),
      ('evaluation_coverage','Evaluation Coverage','Eτ','fraction','higher','D1 evaluated constraints / expected constraints; independent of valid completion'),
      ('normalized_constraint_violation','Normalized Constraint Violation','vτ','fraction','lower','D1 violation_fraction = violated constraints / expected constraints; missing and pre-execution cases retain D1 conventions'),
      ('maximum_normalized_violation','Maximum Normalized Violation','vmax','dimensionless','lower','maximum positive D2 normalized violation with original bound, scale and tolerance; unknowns remain unknown'),
      ('minimum_constraint_margin','Minimum Constraint Margin','mmin','dimensionless','higher','min(-signed_normalized_violation) over known required constraint rows; original normalization retained'),
      ('terminal_error_m','Terminal Position Error','eT','m','lower','original task terminal-position measurement'),
      ('holding_max_error_m','Holding Position Error','eh','m','lower','maximum Euclidean position error during frozen holding interval'),
      ('holding_max_speed_m_s','Holding Velocity','vh','m/s','lower','maximum tip speed during frozen holding interval'),
      ('trajectory_rmse_m','Trajectory RMSE','eRMS','m','lower','original time-indexed task RMSE'),
      ('tracking_max_error_m','Maximum Tracking Error','emax','m','lower','maximum original trajectory position error'),
      ('tool_axis_error_rad','Tool-Axis Angular Error','eaxis','rad','lower','original directed local-to-world tool-axis angular error'),
      ('contact_depth_error_m','Contact Depth Error','ed','m','lower','original frozen depth-hold error'),
      ('contact_force_error_n','Contact Force Error','eF','N','lower','original frozen force-hold error'),
      ('impact_recovery_error_m','Impact Recovery Error','eimpact','m','lower','original post-impact holding/recovery metric; required and controls separate'),
      ('point_displacement_m','Passive Point Displacement','δp','m','higher','absolute signed-force-direction displacement of force application point'),
      ('tip_displacement_m','Passive Tip Displacement','δtip','m','lower','projected tip displacement relative to independently qualified unloaded baseline'),
      ('tip_to_point_ratio','Tip-to-Point Displacement Ratio','r','dimensionless','lower','tip displacement / point displacement within the same load case and Study'),
      ('progressive_stiffness_ratio','Progressive-Stiffness Ratio','κ','dimensionless','higher','original task passive_response stiffness-ratio definition; retain original load stages'),
      ('physical_interpretation','Physical Interpretation','UNKNOWN','score 0–4','higher','Five-dimensional blind rubric: physically appropriate mechanisms and interpretations, scoped to available evidence'),
      ('evidence_consistency','Evidence Consistency','UNKNOWN','score 0–4','higher','Faithful task bounds, measurements, applicability and supported claims; retain original protocol identity'),
      ('limitation_recognition','Limitation Recognition','UNKNOWN','score 0–4','higher','Recognition of local math, incomplete physical coverage, qualification, geometry and numerical scope'),
      ('evidence_reference_accuracy','Evidence Reference Accuracy','UNKNOWN','score 0–4','higher','Blind assessment that cited original references support the decision claims'),
      ('decision_quality','Decision Quality','UNKNOWN','score 0–4','higher','Original E1 definition: appropriateness and informativeness of the next route/action; not relabeled physical_interpretation'),
      ('historical_experience_utilization','Historical Experience Utilization','UNKNOWN','score 0–4','higher','Specific correct positive use of identifiable historical facts/procedures, not citations or access declarations alone'),
      ('blind_decision_quality','Blind Decision Quality','UNKNOWN','score 0–4 mean','higher','Mean of the five named Context blind dimensions within a protocol; no pooling with Reporter or E1 four-score means'),
      ('key_evidence_recall','Key Evidence Recall','R_evidence','fraction','higher','Correctly used pre-frozen key evidence / frozen key-evidence count; UNKNOWN if checklist assessment incomplete'),
      ('critical_evidence_omission','Critical Evidence Omission','UNKNOWN','count','lower','Number of critical checklist items omitted according to blind review; retain original checklist and protocol'),
      ('unsupported_claims','Unsupported Claims','UNKNOWN','count','lower','Evidence-specific unsupported conclusions identified by the independent blind review'),
      ('main_request_count','Main Request Count','UNKNOWN','count','lower','Actual Main sends under the stated accepted/all-attempt protocol; failed transport records are separate when usage is absent'),
      ('evidence_retrieval_count','Evidence Retrieval Count','UNKNOWN','count','lower','Number of successfully returned original evidence records; count is not a quality score'),
      ('actual_cumulative_input_tokens','Actual Cumulative Input Tokens','UNKNOWN','tokens','lower','Sum Provider-returned prompt/input tokens over every Main request in the declared scope; UNKNOWN if any required usage is missing'),
    ]
    for n in ['Hypothesis Testability','Evidence Grounding','Evidence-to-Action Conversion','Method Appropriateness','Research Adaptation','Rejection Quality','Candidate Improvement','Research Actionability']:
        definitions.append((n.lower().replace('-','_').replace(' ','_'),n,'UNKNOWN','score 0–4' if n!='Candidate Improvement' else 'task-specific','higher','Fixed annotation rubric; model-assisted, never physical outcome' if n!='Candidate Improvement' else 'paired within-task physical metric difference; no cross-unit aggregation'))
    for mid,name,unit in [('candidate_count','Candidate Count','count'),('mathematical_calls','Mathematical Calls','count'),('physical_evaluations','Physical Evaluations','count'),('integration_steps','Integration Steps','count'),('provider_input_tokens','Provider Input Tokens','tokens'),('provider_output_tokens','Provider Output Tokens','tokens'),('wall_time_s','Wall-clock Time','s')]:
        definitions.append((mid,name,'UNKNOWN',unit,'lower','Original measured scope only; no sum or average across incompatible scopes. Actual Provider usage only; proxies are separate.'))
    rows=[dict(metric_id=i,canonical_name=n,symbol=s,unit=u,higher_or_lower_is_better=b,calculation_definition=d,
        applicable_task_family='task-specific; see condition_metrics task_id',threshold_source='frozen original task protocol / D2 threshold; no new thresholds',
        source_reference=locator(B,ABC+'DATA_DICTIONARY.md'),display_precision=0 if u in ['count','tokens'] else 6 if u in ['m','m/s'] else 4) for i,n,s,u,b,d in definitions]
    architecture_ids={'physical_interpretation','evidence_consistency','limitation_recognition','evidence_reference_accuracy','decision_quality','historical_experience_utilization','blind_decision_quality','key_evidence_recall','critical_evidence_omission','unsupported_claims','main_request_count','evidence_retrieval_count','actual_cumulative_input_tokens'}
    for r in rows:
        if r['metric_id'] in architecture_ids:
            r['source_reference']=locator(B,ARCH+'knowledge_skill/e1_review.py','#RUBRIC') if r['metric_id'] in ['decision_quality','historical_experience_utilization'] else 'supplementary_experiments/e1_five_dimension_protocol.json; supplementary_experiments/context_protocol.json; original Context protocol tables'
            r['threshold_source']='fixed blind scoring anchors / pre-frozen checklist; no physical acceptance threshold'
            if r['unit'].startswith('score'):r['display_precision']=1
        elif r['unit'].startswith('score'):
            r['source_reference']='annotation/annotation_rubric.md';r['threshold_source']='fixed 0–4 model-assisted annotation anchors';r['display_precision']=1
    known={x['metric_id'] for x in rows}
    for metric in sorted({x['metric_id'] for x in d2}-known):
        x=next(x for x in d2 if x['metric_id']==metric)
        rows.append(dict(metric_id=metric,canonical_name=metric,symbol=UNKNOWN,unit=x['unit'],higher_or_lower_is_better=x['bound_type'],
            calculation_definition='Original D2 metric and signed normalization; see bound_type, normalization_scale, normalization_basis, acceptance_tolerance and strict in each row.',
            applicable_task_family=';'.join(sorted({y['task_id'] for y in d2 if y['metric_id']==metric})),threshold_source='D2.threshold per original condition',
            source_reference=locator(B,ABC+'D2_ABC_CONDITION_METRICS.csv','#metric_id='+metric),display_precision=6))
    write_csv('registry/metric_registry.csv',rows)


def figures(registry,phs,gradients,nodes,abc,candidates):
    # Derived plotting views, never independently edited.
    tasksummary={r['study_id']:r for r in csv.DictReader((OUT/'task_metrics/task_summary.csv').open(encoding='utf-8-sig'))}
    choices={'T01':[('holding_max_error_m','m','max'),('holding_max_speed_m_s','m/s','max')],
             'T02':[('holding_max_error_m','m','max')],
             'T03':[('terminal_error_m','m','max'),('holding_max_error_m','m','max')],
             'T04':[('tracking_rmse_m','m','max'),('max_error_m','m','max')],
             'T05':[('tool_position','m','max'),('tool_axis_direction','rad','max')],
             'T06':[('tracking_max_error','m','max'),('tool_axis_direction','rad','max')],
             'T07':[('holding_max_error_m','m','max'),('tool_axis_direction','rad','max')],
             'T08':[('stiffness_ratio','dimensionless','min'),('low_minimum','m','min'),('high_maximum','m','max')],
             'T09':[('max_hold_depth_error_m','m','max'),('max_hold_contact_force_error_n','N','max')],
             'T10':[('final_hold_max_error_m','m','max')],
             'PHS-2D':[('min_point_m','m','reported_min'),('max_tip_m','m','reported_max'),('max_ratio','dimensionless','reported_max')]}
    portfolio=[]
    taskdata={r['task_id']:r for r in source(A,MASTER+'SOURCE_DATA/FULL_TASKS.json')}
    for x in registry:
        if x['study_role']!='FULL_portfolio':continue
        t=taskdata[x['task_id']];s=tasksummary[x['study_id']]
        metrics={}
        for i,(key,unit,agg) in enumerate(choices[x['task_id']],1):
            if x['task_id']=='PHS-2D':value=t['primary_metrics'][key]
            else:
                values=[v[key] for condition,v in t['primary_metrics'].items() if isinstance(v,dict) and key in v and condition in t['required_conditions']]
                value=(min(values) if agg=='min' else max(values)) if values else UNKNOWN
            metrics.update({f'metric_{i}_id':key,f'metric_{i}_value':value,f'metric_{i}_unit':unit,f'metric_{i}_aggregation':agg})
        portfolio.append(dict(**x,**metrics,status=s['status'],required_condition_completion=s['required_condition_completion'],
            normalized_constraint_violation=s['normalized_constraint_violation'],minimum_normalized_constraint_margin=s['minimum_normalized_constraint_margin'],
            physical_metric_scope='original task-specific metrics over required conditions; never average heterogeneous units'))
    write_csv('figure_data/fig02_task_portfolio.csv',portfolio)
    selected={'P1_b200_r8_h85','P2_dense22_z40','P2_real_guides_3','P3_real9_E80_full8'}
    write_csv('figure_data/fig03_phs2d_evolution.csv',[x for x in candidates if x['study_id']=='PHS-2D-9S' and x.get('candidate_ids') in selected])
    write_csv('figure_data/fig03_phs2d_performance.csv',[x for x in phs if x['study_id']=='PHS-2D-9S' and x['replicate_id']==1])
    write_csv('figure_data/fig04_gradient_validation.csv',gradients)
    write_csv('figure_data/fig05_research_trajectories.csv',[x for x in nodes if x['task_id'] in ['T04','T07','T10'] or x['study_id']=='PHS-2D-9S'])
    write_csv('figure_data/fig06_abc_comparison.csv',abc)
    reporter=list(csv.DictReader((OUT/'architecture_metrics/reporter_pairs.csv').open(encoding='utf-8-sig')))
    ks=list(csv.DictReader((OUT/'architecture_metrics/knowledge_skill.csv').open(encoding='utf-8-sig')))
    write_csv('figure_data/fig07_reporter_knowledge_skill.csv',
        [dict(panel='A',protocol_id='Reporter-six-pair',task_id=x['task_id'],checkpoint_id=x['snapshot_id'],condition='paired_OFF_ON',
              score_off=x['mean_score_OFF'],score_on=x['mean_score_ON'],score_delta=x['mean_score_delta'],source_reference=x['source_reference']) for x in reporter]+
        [dict(panel='B',protocol_id='E1-original-four-cells',task_id=x['task_id'],condition=x['condition'],
              experience_utilization=x['historical_experience_utilization'],decision_quality=x['decision_quality'],evidence_consistency=x['evidence_consistency'],research_actionability=x['research_actionability'],source_reference=x['source_reference']) for x in ks])
    # Historical protocols have different cost populations; emit one row per condition.
    context=list(csv.DictReader((OUT/'architecture_metrics/context_pairs.csv').open(encoding='utf-8-sig')))
    rows=[]
    for x in context:
        first=x['protocol_id']=='E2-C035'
        for cond,prefix in [('Flat','flat'),('Hierarchical','hierarchical' if first else 'hier')]:
            rows.append(dict(protocol_id=x['protocol_id'],checkpoint_id=x['snapshot_id'],task_id='PHS-2D',study_id='PHS-2D-7S',condition=cond,
                actual_cumulative_input_tokens=x[prefix+('_accepted_cumulative_input_tokens_actual' if first else '_cumulative_input_tokens_actual')],
                output_tokens=x[prefix+'_output_tokens_actual'],main_request_count=x[prefix+'_provider_requests'],
                evidence_retrieval_count=x[prefix+('_reads' if first else '_evidence_reads')],
                blind_decision_quality=x[prefix+'_score'],key_evidence_recall=UNKNOWN if first else x[prefix+'_key_evidence_coverage'],
                cost_basis='accepted inference only; rejected Hierarchical request has UNKNOWN usage' if first else x['cost_basis'],
                source_reference=x['source_reference']))
    write_csv('figure_data/fig08_context_comparison.csv',rows)


if __name__=='__main__':
    build()
