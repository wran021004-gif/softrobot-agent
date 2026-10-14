"""Factual candidate identity for complete backend execution reports."""
from tools.platform_store import plain
from tools.state_io import digest

def candidate_facts(baseline,configuration,reference,candidate_id,owner_run_id=None,execution_id=None):
    baseline=plain(baseline);effective=configuration.get('effective',configuration)
    before={p['id']:p for p in baseline['robot']['structure']['data']['components'] if p['kind']=='flexible_segment'}
    rows=[]
    for part in effective['robot']['structure']['data']['components']:
        if part['kind']!='flexible_segment':continue
        old=before[part['id']]
        for name,unit,a,b in [('length_m','m',old['length_m'],part['length_m']),('young_pa','Pa',old['physics']['young_pa'],part['physics']['young_pa'])]:
            rows.append(dict(path='segments.'+part['id']+'.'+name,baseline_value=a,effective_value=b,baseline_delta=b-a,unit=unit))
        for i,station in enumerate(part['sections']):
            for key,v in station['section']['parameters'].items():
                a=old['sections'][i]['section']['parameters'][key]
                rows.append(dict(path='segments.'+part['id']+'.sections.'+str(i)+'.'+key,baseline_value=a,effective_value=v,baseline_delta=v-a,unit='m'))
    return dict(candidate_id=candidate_id,configuration=plain(reference),frozen_baseline_identity=digest(baseline),effective_identity=digest(effective),owner_run_id=owner_run_id,execution_id=execution_id,parameters=rows)
