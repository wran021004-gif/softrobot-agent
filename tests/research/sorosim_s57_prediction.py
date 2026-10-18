"""Explicit bounded S5.7 science driver; ordinary discovery runs no experiment."""
import json
from pathlib import Path

import numpy as np

from tests.research.sorosim_s56_refinement import initialize, finish, plan
from tools.research import core
from tools.research.nmpc_prediction_diagnostic import import_index
from tools.research.state import state, save, update
from tools.state_io import atomic_json, read

ROOT=Path(__file__).resolve().parents[2]


def norm(value):return float(np.linalg.norm(value))


def run():
    host,candidate,_=initialize('s57_prediction')
    source=import_index(host,'evidence/sorosim_s56/physics/study',read(ROOT/'evidence/sorosim_s56/physics/summary.json')['nmpc'])
    original=import_index(host,'evidence/sorosim_s5b/study',read(ROOT/'evidence/sorosim_s5b/summary.json')['result'])
    index=host.store.artifact(source);old=host.store.artifact(original)
    cases=[]
    for checkpoint in index['cases']:
        k=checkpoint['update_index'];rows={};grids=[]
        for n in (1,4,8,16,32):
            result=core.dispatch(host,plan('nmpc_prediction_diagnostic',nmpc_prediction_diagnostic=dict(
                candidate=candidate,source=source,update_index=k,substeps=n)),f's57-k{k}-n{n}')['result']
            value=host.store.artifact(result['reference']);raw=value.get('raw')
            rows[str(n)]=dict(reference=result['reference'],**{key:value.get(key) for key in
                ('status','complete','comparison','root_count','maximum_root_residual_inf','charged_numerical_s')})
            print(json.dumps(dict(update_index=k,substeps=n,**rows[str(n)])),flush=True)
        for a,b in ((1,4),(4,8),(8,16),(16,32)):
            left=host.store.artifact(rows[str(a)]['reference']);right=host.store.artifact(rows[str(b)]['reference'])
            if not (left.get('complete') and right.get('complete')):continue
            pair=dict(substeps=[a,b])
            for field,key,scale in (('position','tip_positions_m',.01),('velocity','tip_velocities_m_s',.02)):
                vector=(np.asarray(left['raw'][key][1])-right['raw'][key][1]).tolist()
                pair[field]=dict(vector=vector,norm=norm(vector),task_scale_ratio=norm(vector)/scale,
                    within_screen=norm(vector)<.1*scale)
            grids.append(pair)
        prior=next(c for c in old['cases'] if c['update_index']==k)
        comparison=dict(original_execution=old['source_execution'],earlier_execution=index['source_execution'],
            same_measured_state=prior['initial_state']==checkpoint['initial_state'],
            original_applied_tension_n=prior['applied_tension_n'],earlier_applied_tension_n=checkpoint['applied_tension_n'])
        for label,case in (('original',prior),('earlier',checkpoint)):
            p=case['accepted_prediction']
            comparison[label]={field:dict(vector=(np.asarray(p[key])-case['after'][key]).tolist(),
                norm=norm(np.asarray(p[key])-case['after'][key])) for field,key in
                (('position','tip_position_m'),('velocity','tip_velocity_m_s'))} if p else None
        cases.append(dict(update_index=k,time_s=checkpoint['time_s'],resolutions=rows,grid_differences=grids,
            grid_norms_decrease={field:all(y[field]['norm']<x[field]['norm'] for x,y in zip(grids,grids[1:]))
                for field in ('position','velocity')},controller_comparison=comparison))
        atomic_json(host.store.root/'partial_summary.json',dict(cases=cases))
    s=state(host)
    costs=dict(one_interval_allocations=s['mathematical_evaluations'],
        actual_integrations=sum(bool(host.store.artifact(row['reference']).get('raw')) for c in cases for row in c['resolutions'].values()),
        actual_roots=sum(row['root_count'] or 0 for c in cases for row in c['resolutions'].values()),
        numerical_s=s['numerical_s'],physics_steps=0,full_nlp=0,ppo_actions=0,provider_requests=0)
    summary=dict(stage='S5.7',source_freeze=s['freeze'],candidate=candidate,source_index=source,
        original_index=original,cases=cases,costs=costs,task_acceptance='no new physical evaluation',
        screen=dict(position_m=.001,velocity_m_s=.002,meaning='engineering screen, not continuous-time error bound'))
    atomic_json(ROOT/'evidence/sorosim_s57/summary.json',summary)
    # Keep this stage open for evidence-based interpretation, with no additional numerical allowance.
    save(host,summary,'s57_computed_summary')


def close(packet):
    from tools.platform_host import Host
    name='sorosim-s57-prediction-20261018';host=Host(ROOT/'runs/research'/name,name,actor='unified-research')
    ref=save(host,packet,'s57_scientific_feedback')
    update(host,scoped_context=[*state(host)['scoped_context'],ref])
    summary=read(ROOT/'evidence/sorosim_s57/summary.json');summary['feedback_reference']=ref
    finish(host,summary,'evidence/sorosim_s57')
    atomic_json(ROOT/'evidence/sorosim_s57/agent_feedback_packet.json',packet)


if __name__=='__main__':run()
