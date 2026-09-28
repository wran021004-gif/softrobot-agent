"""Thin Stage 3.31 input path; execution uses gvs_nmpc_route_experiment.py."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.state_io import read, atomic_json


def revision_input(source):
    inp=read(source/'frozen_input.json')
    inp['run_id']='gvs-autonomous-design-revision'
    p=inp['policy']
    p['budget'].update(model_calls=64,tool_calls=160,backend_solves=6,wall_s=21600.,worker_calls=0)
    p['model'].update(adapter='deepseek',model='deepseek-flash',base_url='https://api.deepseek.com',
        thinking='enabled',reasoning_effort='high',max_tokens=65536,timeout_s=600.,
        max_turns=64,context_bytes=150000,length_recovery=dict(enabled=True,max_tokens=131072,timeout_s=900.))
    route=p['route']['data']
    route['max_trials']=6
    route['source']='User-authorized Stage 3.31 autonomous revision and fresh evaluation from supplied failure'
    route['guidance']=(
        'Choose a meaningful revision of the supplied failed design within the four declared decisions. '
        'Give a short evidence-based rationale, labeling intended effects as hypotheses; no mechanics derivation or proof is required. '
        'Start with build. Perform the required analysis.gvs_candidate_evaluate on that saved source_node using its frozen basis, '
        'then run the build with source_node and no combination. Cite previous route results after the first action. '
        'Read the automatic comparison and diagnostics, then revise again or deliver an evaluated candidate. '
        'All scientific and controller settings remain frozen. Section scale and numerical Young-modulus scenarios expand from '
        'the frozen baseline; density and bending viscosity stay unchanged. These are not validated real-world materials. '
        'Coverage requires length delta from baseline >=0.001 m, section-scale delta >=0.01, and nonbaseline material; '
        'coverage is separate from the original reach criterion. Settling is diagnostic only. '
        'The supplied historical execution is prior evidence, costs no new attempt, cannot be delivered, and must not be rerun. '
        'Change at least one of its decisions and obtain a fresh evaluation. No revision direction is prescribed. '
        'Ceilings: 64 provider requests, 160 tool calls, 6 fresh backend attempts, 21600 charged seconds, zero workers. '
        'Retain the 1800-second per-call reservation and final-delivery capacity. Use remaining resources to revise if useful; '
        'a covered revision passing the unchanged task can be delivered immediately. '
        'On finish copy selected candidate_facts into design_statement and factual_result into result_statement. '
        'Give a concise factual explanation: supplied prior case, tested revisions, selected result, and stopping reason. '
        'Distinguish original reach acceptance from settling and terminal motion, accepted plans from convergence, '
        'simulation duration from computation, and observations from hypotheses. Do not infer global infeasibility from failed samples.')
    return inp


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    atomic_json(args.output,revision_input(args.source))
