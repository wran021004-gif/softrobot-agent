"""Read-only saved-state context comparison and S7 delivery verification."""
from copy import deepcopy
from pathlib import Path
import argparse, json, hashlib, tarfile
from tools.state_io import read, atomic_json, digest
from tools.research.config import ROOT
from tools.research.numerics import archived
from tools.research.research_context import bounded_context, compact_evidence
from tools.research.agent import plan_schema
from tools.research.contracts import Plan

LIMITS=dict(candidates=3,recent=4,pareto=3,samples=6,evidence=3)


def context_comparison():
    rows=[]
    for stage in ('s6_2','s6_3'):
        folder='evidence/'+stage+'/study';manifest=read(ROOT/folder/'archive_manifest.json')
        snapshot=archived(folder,dict(artifact_id=next(r['sha256'] for r in manifest['members'] if r['name'].startswith('snapshot/'))))
        for event in snapshot['events']:
            if event['kind']!='model_decision_packet':continue
            old=archived(folder,event['outputs'][0]);new=deepcopy(old)
            if 'research' not in old:continue
            new['research']=bounded_context(old['research'],LIMITS)
            new['candidates']=new['candidates'][-LIMITS['candidates']:]
            control=snapshot['session']['state']['spec']['configuration']['policy']['controller']['parameters']['data']
            new['controller_capabilities']=dict(recipe_defaults=control['recipe'],solver_defaults=control.get('solver'),
                patch='Generation v2 controller_recipe/controller_solver sparse patches use registered owner validation; settling remains task-owned')
            a=old['research'];b=new['research']
            facts=dict(task=a['task']==b['task'],task_identity=a['task_identity']==b['task_identity'],
                best_identity=(a['best_valid'] or {}).get('reference')==(b['best_valid'] or {}).get('reference'),
                best_gap=(a['best_valid'] or {}).get('task_gap')==(b['best_valid'] or {}).get('task_gap'),
                budget=a['budget']==b['budget'],methods=all(a.get(k)==b.get(k) for k in ('method_remaining','method_used','method_limits')),
                actions=a['actions']==b['actions'],fresh_citations=[r['reference'] for r in a['observations'] if not r['historical_only']]==b['all_fresh_results'],
                failure_samples=all(r in a['best_valid']['violations']['samples'] for r in b['best_valid']['violations']['samples']) if a['best_valid'] else True)
            assert all(facts.values()),facts
            size=lambda x:len(json.dumps(x,separators=(',',':'),ensure_ascii=False).encode())
            rows.append(dict(stage=stage,original_packet=event['outputs'][0],old_bytes=size(old),new_bytes=size(new),
                reduction=1-size(new)/size(old),retained_facts=facts,
                tool_feedback_old_bytes=size(old['research']['best_valid']),
                tool_feedback_summary_bytes=size(compact_evidence(old['research']['best_valid'],event['outputs'][0]))))
    actions=['generate','initialize_control','physical_replay','control_search','diagnose','select','stop']
    return dict(version='s7_context_comparison_v1',states=rows,
        old_plan_schema_bytes=len(json.dumps(Plan.model_json_schema())),new_plan_schema_bytes=len(json.dumps(plan_schema(actions))),
        measurements='Exact serialized UTF-8 bytes. Conservative byte-based context estimate only; NOT provider token savings.',
        provider_usage='Separately reported from original response usage; no provider request in this audit',
        installed_api=dict(strands_agents='1.59.0',strands_harness='0.2.0',before_model_event='cancel is the only writable field',
            chosen='Retain existing system-prefix mechanism with bounded dynamic packet and public Offload retrieval; no message surgery'))


def verify_package(path):
    package=read(path);identity=package.pop('content_identity')
    assert digest(package)==identity
    manifest=read(Path(path).parent/package['archive_manifest'])
    archive=Path(path).parent/'immutable_artifacts.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    with tarfile.open(archive) as tar:
        for member in manifest['members']:
            assert hashlib.sha256(tar.extractfile(member['name']).read()).hexdigest()==member['sha256']
    assert not package['accepted'] or package['acceptance']['accepted'] is True
    if package.get('control'):
        from tools.research.physical_replay import binding
        binding(package['configuration'],package['control']['trajectory'])
    return dict(study_id=package['study_id'],accepted=package['accepted'],status=package['status'],
        content_identity=identity,archive_members_verified=len(manifest['members']),new_backend_launches=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--context-output',type=Path);parser.add_argument('--package',type=Path)
    args=parser.parse_args()
    if args.context_output:
        result=context_comparison();atomic_json(args.context_output,result)
        print(json.dumps(dict(states=len(result['states']),reductions=[round(r['reduction'],4) for r in result['states']])))
    if args.package:print(json.dumps(verify_package(args.package)))
