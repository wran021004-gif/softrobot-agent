"""Read-only P1 audit and deterministic restart; no new science is allowed."""
from copy import deepcopy
from tools.research import core
from tools.research.state import state
from tools.research.physical_replay import evaluate_schedule, schedule_identity
from tools.research.feedback import task_gap
from tools.research.control_correction import task_outputs
from tools.research.local_control_search import search
from tools.research_tasks import task_adapter
from tools.state_io import read, atomic_json, digest
from tests.research.sorosim_s56_refinement import plan
from tests.research.control_search_pilot import source_hashes


def main():
    host=core.prepare('configs/research/study_control_search_p1.json')
    before=host.store.remaining();saved_state=digest(state(host));identities=[];costs={};starts=[]
    for ref in state(host)['physical_replays']:
        r=host.store.artifact(ref);src=host.store.artifact(r['source_reference'])
        cfg=host.store.artifact(r['candidate'])['configuration'];raw=host.store.artifact(r['raw_reference'])
        assert task_gap(r)['valid_complete'] and raw['physics_steps']==700 and len(raw['samples'])==36
        identities.append(schedule_identity(cfg,src['trajectory']))
        method=src['provenance']['search']['algorithm'];costs.setdefault(method,dict(evaluations=0,numerical_s=0.))
        costs[method]['evaluations']+=1;costs[method]['numerical_s']+=r['charged_numerical_s']
        if src['provenance']['search']['label']=='baseline':
            adapter=task_adapter(cfg);limits=adapter.ranking_limits()
            starts.append(dict(id=src['provenance']['search']['start'],candidate=r['candidate'],schedule=src,limits=[8]*4,
                task_options=dict(target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
                    position_limit=limits['holding_max_error_m'],speed_limit=limits['holding_max_speed_m_s'])))
    assert len(identities)==len(set(identities))==24
    def cached(start,source,metadata):
        result,hit=evaluate_schedule(host,start['candidate'],source,plan)
        assert hit,'Never allow a new simulation in a read-only audit'
        return dict(reference=result['reference'],task_gap=task_gap(result),cost_s=0.,cache_hit=hit,
            outputs=task_outputs(host.store.artifact(result['raw_reference'])))
    restarted=[search(starts,cached,settings) for settings in state(host)['spec']['local_control_search']]
    original=read('evidence/control_search_p1/summary.json')
    assert [m['best']['reference'] for m in restarted]==[m['best']['reference'] for m in original['methods']]
    assert before==host.store.remaining() and saved_state==digest(state(host))
    assert source_hashes()==read('evidence/control_search_p1/source_audit.json')['before']
    atomic_json('evidence/control_search_p1/validation.json',dict(unique_complete_evaluations=24,
        invalid_evaluations=0,physics_steps=24*700,all_receipts_reused_on_restart=True,
        restart_requests=sum(len(m['candidates']) for m in restarted),ledger_unchanged=True,state_unchanged=True,
        sources_unchanged=True,cost_by_method=costs,ledger=before,original_task_passed=False))
    print('24 unique valid evaluations; 26 restart requests cached; state and charges unchanged')


if __name__=='__main__':main()
