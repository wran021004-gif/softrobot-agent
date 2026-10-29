"""Read existing offline fixtures and historical sources; never start a Worker.

Reuse a completed fixture via --fixture-store. Output contains synthetic interface examples,
not scientific evidence, and scoped historical code-availability observations.
"""
import json
import argparse
from pathlib import Path
import subprocess

from tools.platform_host import Host
from tools.platform_store import Store
from tools.research.config import ROOT
from tools.research.nonlinear_capability import T1, T2
from tools.research.research_context import agent_decision_brief, research_decision_brief_v3, information_flow_brief
from tools.research.task_constraints import mathematical_method_view, analysis_capabilities, describe_analysis_requirements
from tools.research import reporter
from tools.research.state import state
from tools.state_io import atomic_json, read


def historical_support():
    rows=[];cost_examples=[]
    for name in ('m1','m2','m3','m4','m5','m6'):
        path=ROOT/f'memory/cases/{name}_research_v1/success_trace.json';trace=read(path)
        source=trace['source_identity'];store=Store(Path(source['original_store']).parent)
        selected=store.artifact(source['selected']);candidate=store.artifact(selected['candidate'])
        s=store.session(source['original_study_id'])['state'];cfg=candidate['configuration']
        requirements=describe_analysis_requirements(cfg,{})
        capabilities=analysis_capabilities(cfg,requirements,s['spec']['analysis_protocol'])
        if name=='m1':
            for ref in s.get('analysis_results',[]):
                raw=store.artifact(ref);cost=raw.get('native_dynamics',{}).get('cost',{})
                if cost.get('physics_steps') and cost.get('kernel_wall_s'):
                    cost_examples.append(dict(reference=ref,candidate=raw['candidate'],
                        operation=raw['operation'],cost=cost,charged_numerical_s=raw.get('charged_numerical_s'),
                        source_store=source['original_store']))
                if len(cost_examples)==2:break
        rows.append(dict(case=name.upper(),historical_status=trace['final_result']['status'],
            source=str(path.relative_to(ROOT)),source_store=source['original_store'],
            candidate=selected['candidate'],task_family=cfg['task']['family'],
            historical_study_status=s['research_status'],current_study_executable=False,
            execution_gap='Historical ownership and stopped budget confer no current Study execution grant.',
            current_code_applicability=[{k:r[k] for k in ('operation','planning_status','full_task_supported','reasons')}
                for r in capabilities if r['operation'] in ('mujoco_direct_control_v1','trajectory_feasibility','task_capability')]))
    branches={}
    for branch in ('research/phs2d-inverse-passive-design','codex/passive-progressive-stiffness',
            'codex/p3-spatial-fidelity','codex/p3-knowledge-integration','HEAD'):
        files=subprocess.check_output(['git','ls-tree','-r','--name-only',branch,'tools','extensions'],cwd=ROOT).decode().splitlines()
        relevant=[p for p in files if any(token in p for token in ('passive','phs','stiffness'))]
        branches[branch]=dict(commit=subprocess.check_output(['git','rev-parse',branch],cwd=ROOT).decode().strip(),
            passive_source_files=relevant,
            local_files_available=all((ROOT.parent/branch.split('/')[-1]/p).is_file() for p in relevant) if relevant else None)
    return dict(active_cases=rows,passive_code=branches,historical_resource_examples=cost_examples,
        remaining_cases=dict(C1='Historical same-XML multi-task batch; component task tools, no single C1 T1/T2 adapter.',
            PHS='Development passive witness; kernels on research/phs2d-inverse-passive-design, no current AnalysisRequest/task integration.',
            P3='Original and two-cell development pass, four-cell INVALID; local passive source available, no current AnalysisRequest/task integration.'),
        remote_check=dict(PHS='9d6d160e050c836b87d0563a497fc0ec1c3761a8',
            P3_source_branches='git ls-remote returned no matching refs on 2026-10-29; local availability is distinct.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-store',type=Path,help='Read an existing completed fixture; never rerun its calculations')
    parser.add_argument('--wire-store',type=Path,help='Read an existing Mock HTTP request; copied as a separate exact excerpt')
    parser.add_argument('--examples-only',action='store_true',help='Leave the historical nine-task audit unchanged')
    args=parser.parse_args()
    h=None
    roots=([args.fixture_store] if args.fixture_store else
        sorted((ROOT/'runs').glob('p63a-fixture-*'),key=lambda p:p.stat().st_mtime,reverse=True))
    for root in roots:
        if not (root/'platform.sqlite').is_file():continue
        candidate_host=Host(root,root.name);s=state(candidate_host)
        if len(s.get('analysis_results',[]))==6 and reporter.entries(candidate_host):
            h=candidate_host;break
    if h is None:raise ValueError('Pass --fixture-store pointing to an existing completed fixture')
    s=state(h);refs=s['analysis_results'];base=h.store.artifact(refs[0])['candidate']
    view=mathematical_method_view(h,base);research=view['research_opportunities']
    report_ref,saved=reporter.entries(h)[-1]
    brief=agent_decision_brief(h)
    example=dict(label='OFFLINE SYNTHETIC INTERFACE FIXTURE; NOT SCIENTIFIC EVIDENCE',
        fixture_store=str(h.store.root),candidate=base,
        l0_kind='derived_projection_without_dynamic_tool_directory; not a complete Provider wire',
        l0=information_flow_brief(brief,research_decision_brief_v3(brief)),
        l1={**research,'parameters':[p for p in research['parameters'] if p['parameter_id'] in ('segments.0.length_m','segments.1.length_m')]},
        requests=dict(T1=h.store.artifact(refs[0])['requested_operation'],T2=h.store.artifact(refs[-1])['requested_operation']),
        reporter_main_handoff=reporter.reporter_handoff_summary(h,report_ref,saved),
        accounting=dict(synthetic_mathematical_admissions=s['mathematical_evaluations'],
            ledger=h.store.remaining()['used'],real_provider_requests=0,real_mathematical_workers=0,
            real_physical_workers=0,NMPC=0,RL=0))
    if args.wire_store:
        wire_host=Host(args.wire_store,args.wire_store.name)
        event=next(e for e in reversed(wire_host.store.events(wire_host.run_id)) if e['kind']=='r3_request')
        metadata=wire_host.store.artifact(event['outputs'][0]);wire=wire_host.store.artifact(metadata['request'])
        delivered=json.loads(wire['messages'][-1]['content'].split('\n',1)[1])['research']
        example['mock_provider_request']=dict(label='Exact recorded Mock HTTP L0 and tool Schema excerpt; no live Provider',
            source_store=str(wire_host.store.root),source_reference=metadata['request'],
            model=wire['model'],l0=delivered,tools=wire['tools'],
            scope='Original request excerpt, including dynamic tool loading. Other wire fields remain in the source artifact; its candidate may differ from the five-point fixture.')
    atomic_json(ROOT/'docs/research/p63a_interface_examples.json',example)
    if not args.examples_only:atomic_json(ROOT/'docs/research/p63a_tool_support.json',historical_support())
    print(json.dumps(dict(examples='docs/research/p63a_interface_examples.json',matrix='docs/research/p63a_tool_support.json',
        fixture=h.run_id,real_executions=0)))


if __name__=='__main__':main()
