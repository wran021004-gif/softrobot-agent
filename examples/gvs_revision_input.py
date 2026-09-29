"""Thin evidence-guided revision input; execution uses gvs_nmpc_route_experiment.py."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.state_io import read, atomic_json


def revision_input(source):
    inp=read(source/'frozen_input.json')
    inp['run_id']='gvs-evidence-guided-design-exploration'
    p=inp['policy']
    p['budget'].update(model_calls=64,tool_calls=160,backend_solves=6,wall_s=21600.,worker_calls=0)
    p['model'].update(adapter='deepseek',model='deepseek-flash',base_url='https://api.deepseek.com',
        thinking='enabled',reasoning_effort='high',max_tokens=65536,timeout_s=600.,
        max_turns=64,context_bytes=150000,length_recovery=dict(enabled=True,max_tokens=131072,timeout_s=900.))
    route=p['route']['data']
    route['max_trials']=6
    route.pop('historical_case',None)
    route['source']='User-authorized Stage 3.32 evidence-guided design exploration using three supplied Stage 3.31 cases'
    route['guidance']=(
        'Priority: find a covered fresh design passing the unchanged reach evaluator within budget. '
        'Read the supplied prior cases, exploration_summary and sampled motion feedback. '
        'At least one fresh complete evaluation must meaningfully change a previously constant length (>=0.001 m from the supplied cases). '
        'Choose which segment or both and choose the actual values independently within the four declared decisions. '
        'Give a short evidence-based rationale, labeling intended effects as hypotheses; no mechanics derivation or proof is required. '
        'Start with a length-varying build, then run it with source_node and no combination. Cite previous route results after the first action. '
        'analysis.gvs_candidate_evaluate is optional for this free-reach controller: use it for a specific question. '
        'Analytical comparisons must identify state/input conditions and limitations; zero-state results do not predict closed-loop reach. '
        'Read the automatic comparison and diagnostics, then revise again or deliver an evaluated candidate. '
        'All scientific and controller settings remain frozen. Section scale and numerical Young-modulus scenarios expand from '
        'the frozen baseline; density and bending viscosity stay unchanged. These are not validated real-world materials. '
        'Coverage requires length delta from baseline >=0.001 m, section-scale delta >=0.01, and nonbaseline material; '
        'coverage is separate from the original reach criterion. Settling is diagnostic only. '
        'Historical executions are prior evidence, cost no new attempt, cannot be delivered, and must not be rerun. '
        'Baseline coverage does not establish exploration of every variable. Earlier sampled entry into tolerance does not replace endpoint acceptance or prove settling. '
        'Do not assume longer always reaches better: saved samples can enter the target neighborhood and move away. '
        'Ceilings: 64 provider requests, 160 tool calls, 6 fresh backend attempts, 21600 charged seconds, zero workers. '
        'Retain the 1800-second per-call reservation and final-delivery capacity. After failure continue when a concrete legal untested hypothesis and resources remain; '
        'a covered revision passing the unchanged task can be delivered immediately. '
        'On finish copy selected candidate_facts into design_statement and factual_result into result_statement. '
        'Give a concise factual explanation: supplied cases, tested revisions, selected result, comparison to best historical, and stopping reason. '
        'Distinguish covered fresh pass, insufficient remaining execution-and-delivery budget, specific capability/execution blocker, or voluntary early stop. '
        'A bound does not prove useful directions exhausted. State unused resources if stopping voluntarily. '
        'Distinguish original reach acceptance from settling and terminal motion, accepted plans from convergence, '
        'simulation duration from computation, and observations from hypotheses. Do not infer global infeasibility from failed samples.')
    return inp


def independent_lengths_input(source):
    inp=revision_input(source)
    inp['run_id']='gvs-bounded-recovery-independent-lengths'
    inp['policy']['model']['protocol_recovery']=dict(max_total=4,max_consecutive=2)
    route=inp['policy']['route']['data']
    route['source']='User-authorized Stage 3.33 autonomous independent-length exploration with seven selected historical evaluations'
    route['guidance']=route['guidance'].replace(
        'At least one fresh complete evaluation must meaningfully change a previously constant length (>=0.001 m from the supplied cases). ',
        'Read the seven-case comparison and length_coupling summary. The FIRST fresh design must meaningfully break the historical relationship: abs((near_length - far_length) - 0.04 m) >= 0.001 m. Choose actual segment changes and values yourself. This is an exploration assessment, not a physical constraint or replacement task criterion. ')
    return inp


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    atomic_json(args.output,revision_input(args.source))
