"""Small scientific-detail views from selected original records, not whole trace exports."""
import csv
import json
from pathlib import Path
from build_evidence import *


def read_trace(tid):
    event=next(e for e in source(A,MASTER+'SOURCE_DATA/SELECTED_RESEARCH_EVENTS.json') if e['stage_id'].startswith(tid+'-'))
    p=Path(event['decision']['source'])
    return p,{e['event_id']:e for e in [json.loads(s) for s in p.read_text('utf-8-sig').splitlines() if s.strip()]}


def details():
    pairs=[('T01','T01-116','T01-115-native-central-dense-actuator-search','T01-119-native-smaller-radius-central'),
           ('T01','T01-127','T01-126-refine-minimum-radius-central','T01-130-native-reach-margin-central'),
           ('T01','T01-159','T01-155-continue-shared-positive-high-native','T01-159-native-positive-from-central-basin'),
           ('T07','T07-060','T07-35-refine-common-structure-M1-A','T07-062-native-isotropic-root-A'),
           ('T07','T07-074','T07-072-native-distributed-reach-A','T07-076-native-boundary-radius-best-root-A'),
           ('T07','T07-106','T07-092-native-current-common-root-M1_C','T07-106-native-current-C-from-A-basin')]
    rows=[];traces={}
    for tid,node,before,after in pairs:
        if tid not in traces:traces[tid]=read_trace(tid)
        path,events=traces[tid]
        v0=events[before]['output']['data']['nonlinear_capability']['J']
        v1=events[after]['output']['data']['nonlinear_capability']['J']
        rows.append(dict(improvement_id=node+'-J',node_id=node,task_id=tid,study_id=study(tid),metric_id='native_capability_signed_excess',
            before_value=v0,after_value=v1,delta_after_minus_before=v1-v0,improvement_before_minus_after=v0-v1,unit='dimensionless',
            evidence_scope='finite-budget native control-optimization diagnostic; not independent physical acceptance or fixed-input causality',
            before_source=portable(str(path))+'#'+before+'/output/data/nonlinear_capability/J',
            after_source=portable(str(path))+'#'+after+'/output/data/nonlinear_capability/J',
            controlled_comparison=False,confounds='structure and reoptimized control may both change; budgets/initialization can differ'))
    path,events=read_trace('T08')
    for direction in ['plus_x','minus_x']:
        metric=direction+'_stiffness_ratio'
        before='T08-005-physical-pair';after='T08-008-physical-pair'
        v0=events[before]['output']['data']['result']['acceptance']['metrics'][metric]
        v1=events[after]['output']['data']['result']['acceptance']['metrics'][metric]
        rows.append(dict(improvement_id='T08-006-'+direction,node_id='T08-006',task_id='T08',study_id='T08-FULL',metric_id='progressive_stiffness_ratio',
            before_value=v0,after_value=v1,delta_after_minus_before=v1-v0,improvement_before_minus_after=UNKNOWN,unit='dimensionless',
            evidence_scope='original bilateral passive physical protocol; development classification retained',
            before_source=portable(str(path))+'#'+before+'/output/data/result/acceptance/metrics/'+metric,
            after_source=portable(str(path))+'#'+after+'/output/data/result/acceptance/metrics/'+metric,
            controlled_comparison='same original protocol; payout modification',confounds='one recorded candidate per setting; no population inference'))
    write_csv('task_metrics/candidate_improvements.csv',rows)
    write_csv('figure_data/fig05_research_metrics.csv',[x for x in rows if x['task_id']=='T07'])
    # Asset locators refer to original MuJoCo models; no artificial robot illustration.
    assets=[]
    for tid,entries in source(A,MASTER+'SOURCE_DATA/MODEL_BINDINGS.json').items():
        if not isinstance(entries,list):continue
        for e in entries:
            assets.append(dict(task_id=tid,study_id=study(tid),candidate_id=e.get('candidate_ref',{}).get('artifact_id'),
                condition_id=e.get('condition_name'),model_xml_references=e.get('xml_files'),candidate_configuration=e.get('candidate_file'),
                source_store=e.get('store'),source_reference=locator(A,MASTER+'SOURCE_DATA/MODEL_BINDINGS.json','#/'+tid),
                render_status='source_model_indexed; uniform-camera panel not yet rendered'))
    assets.append(dict(task_id='PHS-2D',study_id='PHS-2D-9S',candidate_id='P3_real9_E80_full8',condition_id='final',
        model_xml_references=locator(C,NINE+'solution/model.xml'),candidate_configuration='task_metrics/phs9_final_structure.json',
        source_store=locator(C,NINE+'store_v2'),source_reference=locator(C,NINE+'solution/design.json'),
        render_status='original final XML indexed; intermediate XML resolution pending'))
    write_csv('task_metrics/visual_asset_index.csv',assets)
    nodes=list(csv.DictReader((OUT/'research_nodes/research_nodes.csv').open(encoding='utf-8-sig')))
    # Numeric improvements are owned once in candidate_improvements.csv.
    for n in nodes:
        n['improvement']=';'.join('task_metrics/candidate_improvements.csv#improvement_id='+r['improvement_id'] for r in rows if r['node_id']==n['node_id']) or UNKNOWN
    write_csv('research_nodes/research_nodes.csv',nodes)
    write_csv('figure_data/fig05_research_trajectories.csv',[n for n in nodes if n['task_id'] in ['T04','T07','T10'] or n['study_id']=='PHS-2D-9S'])
    ranks=list(csv.DictReader((OUT/'research_nodes/node_ranking.csv').open(encoding='utf-8-sig')))
    editorial={
      'T01-116':[3,2,3,3,3],'T01-127':[4,4,3,4,4],'T01-159':[3,4,2,4,2],
      'T02-004':[3,2,2,4,2],'T02-018':[3,4,3,3,3],'T03-005':[2,4,2,2,2],
      'T04-010':[3,2,4,3,4],'T04-216':[4,3,2,4,2],'T04-220':[3,4,4,4,4],
      'T05-005':[3,4,3,3,3],'T06-004':[3,4,3,3,3],
      'T07-060':[4,3,4,4,4],'T07-074':[4,4,3,4,4],'T07-106':[3,4,2,4,2],
      'T08-006':[4,4,3,4,4],'T08-009':[3,4,2,3,3],
      'T09-210':[4,3,4,4,4],'T09-213':[3,4,3,3,4],
      'T10-017':[3,2,2,4,2],'T10-210':[4,3,4,4,4],'T10-222':[3,4,3,3,3]}
    for r in ranks:
        score=editorial.get(r['node_id'])
        if not score:
            score=[4,3,4,4,4] if r['study_id']=='PHS-2D-9S' else [2,2,3,3,3] if r['study_id']=='PHS-2D-7S' else [2,4,2,2,2]
        for k,v in zip(['scientific_contribution','physical_evidence_strength','before_after_difference','research_decision_value','visual_presentation_potential'],score):r[k]=v
        r['editorial_priority']=sum(score)/5
        r['ranking_role']='editorial selection only; five equal weights; never a scientific performance score'
        r['ranking_rationale']='Mechanism/route change and actual metric contrast support priority; physical evidence score reflects recorded evidence scope. Visual potential is a recommendation, not a completed render.'
    write_csv('research_nodes/node_ranking.csv',ranks)
    # A single strongest display per task; other key nodes remain in the full node table.
    display=[]
    for tid in [x[0] for x in NAMES]:
        subset=[r for r in ranks if r['task_id']==tid and r['study_id']!='PHS-2D-9S']
        best=max(subset,key=lambda x:float(x['editorial_priority']))
        display.append(dict(task_id=tid,study_id=best['study_id'],selected_node_id=best['node_id'],
            display=best['recommended_display'],node_count=len(subset),priority=best['editorial_priority'],
            metric_reference='figure_data/fig02_task_portfolio.csv#task_id='+tid,source_reference=best['source_reference']))
    write_csv('research_nodes/task_display_selection.csv',display)
    print('Research improvements',len(rows),'visual asset bindings',len(assets))


if __name__=='__main__':details()
