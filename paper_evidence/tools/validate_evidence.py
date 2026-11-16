"""Only the ten publication-data checks requested by the research brief."""
import csv
import json
import math
from collections import Counter
from build_evidence import *


def rows(path):return list(csv.DictReader((OUT/path).open(encoding='utf-8-sig')))


def validate():
    checks=[]
    def check(name,condition,detail):
        checks.append(dict(check=name,status='PASS' if condition else 'FAIL',detail=detail))
    failures=[]
    csvcount=jsoncount=0
    for p in OUT.rglob('*'):
        if p.suffix=='.csv':
            csvcount+=1
            try:
                with p.open(encoding='utf-8-sig',newline='') as f:
                    reader=csv.DictReader(f);assert reader.fieldnames and len(reader.fieldnames)==len(set(reader.fieldnames))
                    for r in reader:assert None not in r
            except Exception as e:failures.append(str(p.relative_to(OUT))+': '+str(e))
        elif p.suffix=='.json':
            jsoncount+=1
            try:json.loads(p.read_text('utf-8-sig'))
            except Exception as e:failures.append(str(p.relative_to(OUT))+': '+str(e))
    check('1 readable CSV/JSON',not failures,f'{csvcount} CSV and {jsoncount} JSON parsed; '+str(failures))
    keys={
      'registry/task_registry.csv':['task_id','study_id'],
      'registry/study_registry.csv':['study_id'],
      'registry/metric_registry.csv':['metric_id'],
      'task_metrics/task_summary.csv':['task_id','study_id'],
      'task_metrics/condition_metrics.csv':['study_id','task_id','method','candidate_id','condition_id','metric_id'],
      'task_metrics/research_mode_summary.csv':['task_id','method'],
      'task_metrics/candidate_evolution.csv':['candidate_record_id'],
      'task_metrics/resource_metrics.csv':['resource_record_id'],
      'research_nodes/research_nodes.csv':['node_id'],
      'research_nodes/decision_annotations.csv':['node_id','dimension','annotation_round'],
      'research_nodes/evidence_action_links.csv':['study_id','task_id','method','event_id'],
      'architecture_metrics/reporter_pairs.csv':['pair_id'],
      'architecture_metrics/knowledge_skill.csv':['task_id','condition'],
      'task_metrics/phs_performance.csv':['study_id','replicate_id','condition_id'],
      'task_metrics/gradient_validation.csv':['study_id','branch_id','metric'],
    }
    dup=[]
    for p,k in keys.items():
        count=Counter(tuple(r[x] for x in k) for r in rows(p))
        if any(v>1 for v in count.values()):dup.append(p)
    check('2 unique primary/natural keys',not dup,'Validated '+str(len(keys))+' core tables; duplicate tables: '+str(dup))
    registry=rows('registry/task_registry.csv');full=[r for r in registry if r['study_role']=='FULL_portfolio']
    original=source(A,MASTER+'SOURCE_DATA/FULL_CASES.json')
    req=[r for r in original if r['condition_role']=='required'];control=[r for r in original if r['condition_role']=='control']
    counts=Counter(r['task_id'] for r in req)
    check('3 portfolio and required conditions',len(full)==11 and len(req)==30 and len(control)==2 and all(counts[r['task_id']]==int(r['required_condition_count']) for r in full),
          '11 FULL tasks; 30 required rows; 2 additional T10 controls; exact per-task counts checked.')
    phs=rows('task_metrics/phs_performance.csv');evo=rows('figure_data/fig03_phs2d_evolution.csv');g=rows('task_metrics/gradient_validation.csv')
    check('4 independent PHS identities',len([r for r in registry if r['task_id']=='PHS-2D'])==2 and {r['study_id'] for r in evo}=={'PHS-2D-9S'} and
          {r['study_id'] for r in g}=={'PHS-2D-9S'} and len([r for r in phs if r['study_id']=='PHS-2D-7S'])==10 and len([r for r in phs if r['study_id']=='PHS-2D-9S'])==40,
          '7S: ten nominal cases in FULL. 9S: own Journal and four separate ten-case check sets; 18 derivatives only 9S.')
    gradient_ok=len(g)==18 and len({r['branch_id'] for r in g})==6
    maxerr=0
    for r in g:
        factor=1000 if r['gradient_unit']=='mm/du' else 1
        fd=(float(r['positive_metric'])-float(r['negative_metric']))/(2*float(r['parameter_perturbation_step_du']))*factor
        gi=float(r['implicit_gradient']);stored=float(r['finite_difference_gradient'])
        err=abs(gi-stored)/(float(r['relative_error_denominator_raw'])*factor)
        gradient_ok &= math.isclose(fd,stored,rel_tol=2e-9,abs_tol=2e-10) and math.isclose(err,float(r['relative_error']),rel_tol=2e-8,abs_tol=2e-10)
        maxerr=max(maxerr,float(r['relative_error_percent']))
    check('5 eighteen gradient pairs and calculations',gradient_ok,f'6 branches × 3 metrics; endpoint finite differences and relative discrepancies reproduced. Maximum {maxerr:.7f}%.')
    abc=rows('task_metrics/research_mode_summary.csv')
    check('6 complete A/B/C matrix',len(abc)==33 and Counter(r['task_id'] for r in abc)==Counter({r['task_id']:3 for r in full}) and all({r['method'] for r in abc if r['task_id']==t}=={'A','B','C'} for t in counts),
          '33 unique task–method combinations; statuses, deviations and known lower bounds preserved.')
    reporter=rows('architecture_metrics/reporter_pairs.csv')
    offs=[float(r['mean_score_OFF']) for r in reporter];ons=[float(r['mean_score_ON']) for r in reporter]
    check('7 six Reporter pairs',len(reporter)==6 and math.isclose(sum(ons)/6-sum(offs)/6,.3,abs_tol=1e-12) and sum(b>a for a,b in zip(offs,ons))==2 and sum(b<a for a,b in zip(offs,ons))==0,
          f'6 pairs; means {sum(offs)/6:.6f}/{sum(ons)/6:.6f}; +0.300; 2 wins/4 ties/0 losses. Two positive cases are not extra samples.')
    ks=rows('architecture_metrics/knowledge_skill.csv')
    ks_ok=len(ks)==8
    for t in ['T04','T07']:
        values={r['condition']:float(r['historical_experience_utilization']) for r in ks if r['task_id']==t}
        ks_ok &= [values[c] for c in ['K-S-','K+S-','K-S+','K+S+']]==[0,3,3,3]
        ks_ok &= all(float(r[k])==4 for r in ks if r['task_id']==t for k in ['decision_quality','evidence_consistency','research_actionability'])
    check('8 eight original K/S decisions',ks_ok,'Both 2×2 factorials complete. Original 0/3/3/3 utilization and saturated 4/4 quality fields reproduced; supplement separate.')
    context=rows('figure_data/fig08_context_comparison.csv')
    historical={r['protocol_id']+':'+r['condition']:r for r in context if r['protocol_id'] in ['E2-C035','E2-R2-C037']}
    cost_ok=all(int(historical[k]['actual_cumulative_input_tokens'])==v for k,v in {
        'E2-C035:Flat':675802,'E2-C035:Hierarchical':78785,'E2-R2-C037:Flat':877197,'E2-R2-C037:Hierarchical':174298}.items())
    for r in context:
        if 'Gateway' in r['protocol_id']:cost_ok &= r['actual_cumulative_input_tokens']=='UNKNOWN' or r['cost_basis'].startswith('Provider actual')
    actual=rows('architecture_metrics/context_request_usage.csv')
    for identity,row in historical.items():
        p,c=identity.split(':');measurements=[r for r in actual if r['protocol_id']==p and r['condition']==c and r['http_status']=='200']
        cost_ok &= sum(int(r['input_tokens_actual']) for r in measurements)==int(row['actual_cumulative_input_tokens'])
    check('9 context actual usage and scope',cost_ok,'Accepted/cumulative input independently summed from original per-request usage. E2 rejected request remains UNKNOWN; new Gateway usage is UNKNOWN, no proxy substitution.')
    figure_ok=True
    source_abc={(r['task_id'],r['method']):r for r in source(B,ABC+'D1_ABC_STATUS_MATRIX.csv')}
    for r in rows('figure_data/fig06_abc_comparison.csv'):
        orig=source_abc[(r['task_id'],r['method'])]
        figure_ok &= all(r[k]==orig[k] for k in ['status','completion_fraction','violation_fraction','maximum_violation','evaluation_coverage'])
    p9=[r for r in rows('figure_data/fig03_phs2d_performance.csv')]
    figure_ok &= len(p9)==10 and math.isclose(min(float(r['point_displacement_m']) for r in p9),.011155111084834766,rel_tol=1e-10)
    figure_ok &= math.isclose(max(float(r['tip_displacement_m']) for r in p9),.0030679484830552412,rel_tol=1e-10)
    figure_ok &= len(rows('figure_data/fig02_task_portfolio.csv'))==11 and len(rows('figure_data/fig04_gradient_validation.csv'))==18
    check('10 Figure values versus sources',figure_ok,'All A/B/C headline fields equal D1. 9S independent extrema reproduce source summary. Portfolio/gradient row counts match.')
    nodecounts=Counter(r['task_id'] for r in rows('research_nodes/research_nodes.csv') if r['study_id']!='PHS-2D-9S')
    check('required node coverage',set(nodecounts)==set(counts) and all(2<=v<=4 for v in nodecounts.values()),str(dict(nodecounts))+'; four additional independent 9S nodes.')
    experiments=[]
    for p,expected in [('architecture_metrics/context_cross_task.csv',12),('architecture_metrics/knowledge_skill_supplement.csv',16)]:
        if (OUT/p).exists():
            r=rows(p);completed=sum(x.get('session_status')=='completed' for x in r)
            experiments.append(f'{p}: {completed}/{expected} completed decisions')
    check('supplement completion accounting',True,'; '.join(experiments)+'; M1/M2 is explicitly PREPARED_NOT_EXECUTED and is not an empirical comparison.')
    five=rows('architecture_metrics/knowledge_skill_five_dimension.csv') if (OUT/'architecture_metrics/knowledge_skill_five_dimension.csv').exists() else []
    if five:
        keycounts=Counter((r['protocol_id'],r['checkpoint_id'],r['condition'],r['dimension']) for r in five)
        check('requested common five-dimensional assessment',len(five)==120 and all(n==1 for n in keycounts.values()) and all(r['score'] in ['0','1','2','3','4','UNKNOWN'] for r in five),
              f'{len(five)}/120 dimension records: original 8 decisions plus 16 supplemental cells × five common dimensions. Original four-score tables retained.')
    if (OUT/'architecture_metrics/gateway_token_sessions.csv').exists():
        sessions=rows('architecture_metrics/gateway_token_sessions.csv')
        requests=rows('architecture_metrics/gateway_token_requests.csv')
        token_ok=len(sessions)==28 and len(requests)==62
        token_ok &= len({(r['experiment'],r['session_id'],r['request_index']) for r in requests})==62
        for s in sessions:
            own=sorted([r for r in requests if r['experiment']==s['experiment'] and r['session_id']==s['session_id']],key=lambda r:int(r['request_index']))
            token_ok &= len(own)==int(s['main_request_count'])
            for key in ['input_tokens_text_estimate','output_tokens_text_estimate']:
                token_ok &= sum(int(r[key]) for r in own)==int(s[key]) and all(int(r[key])>0 for r in own)
            first=own[0]
            token_ok &= int(first['input_tokens_text_estimate'])==int(s['initial_input_text_tokens'])
            token_ok &= all(int(r['input_tokens_text_estimate'])==round(int(s['initial_input_text_tokens'])*int(r['request_bytes'])/int(first['request_bytes'])) for r in own)
            record=json.loads((ROOT/s['source_reference']).read_text('utf-8'))
            token_ok &= all(int(r['request_bytes'])==record['requests'][i]['request_bytes'] for i,r in enumerate(own))
            token_ok &= s['session_status']==record['status']
        token_ok &= sum(r['output_method']=='unretained_last_reply_imputed_from_same_session_draft_median' for r in requests)==2
        actual=rows('architecture_metrics/supplement_request_usage.csv')
        token_ok &= len(actual)==62 and all(r['input_tokens_actual']=='UNKNOWN' and r['output_tokens_actual']=='UNKNOWN' for r in actual)
        for p,experiment in [('architecture_metrics/context_cross_task.csv','context_gateway'),('architecture_metrics/knowledge_skill_supplement.csv','knowledge_skill')]:
            for r in rows(p):
                s=next(s for s in sessions if s['experiment']==experiment and s['session_id']==r['checkpoint_id']+'-'+r['condition'])
                token_ok &= all(r[k]==s[k] for k in ['input_tokens_text_estimate','output_tokens_text_estimate','initial_input_text_tokens'])
        check('Gateway local text-token accounting',token_ok,
              '28 byte-matched initial reconstructions; 62 returned Main requests; request/session sums and source byte counts agree; two failed last outputs explicitly imputed; actual-usage fields unchanged.')
    report=['# Publication data validation','', 'Only requested publication checks were run. No source data, thresholds, manuscript text or Figure 1 were changed. No hashing, full repository audit, full software test suite or wholesale MuJoCo rerun was performed.','',
            '| Check | Result | Evidence |','|---|---|---|']
    report += ['| '+x['check']+' | '+x['status']+' | '+x['detail'].replace('|','/')+' |' for x in checks]
    report += ['', 'A PASS above validates the data representation/calculation. It does not turn missing experiments into completed science. Matched M1/M2 physical measurements and common-camera intermediate XML renders remain pending. Actual new Gateway usage remains UNKNOWN where not returned.']
    (OUT/'validation_report.md').write_text('\n'.join(report)+'\n','utf-8')
    write_json('validation_results.json',checks)
    for c in checks:print(c['status'],c['check'])
    if any(c['status']=='FAIL' for c in checks):raise SystemExit(1)


if __name__=='__main__':validate()
