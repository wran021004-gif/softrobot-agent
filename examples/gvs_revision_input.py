"""Thin Stage 3.30 input path; execution uses gvs_nmpc_route_experiment.py."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.state_io import read, atomic_json


def revision_input(source):
    inp=read(source/'frozen_input.json')
    inp['run_id']='gvs-autonomous-design-revision'
    p=inp['policy']
    p['budget'].update(model_calls=32,tool_calls=80,backend_solves=3,wall_s=10800.,worker_calls=0)
    p['model']['max_turns']=32
    route=p['route']['data']
    route['max_trials']=3
    route['source']='User-authorized Stage 3.30 autonomous design revision from supplied historical failure evidence'
    route['guidance']=('Use the supplied failed case to propose and execute a different authorized design. '
        'Distinguish observations from hypotheses. Explain what the modification is intended to improve or test. '
        'Compare the revised execution with the prior failure, then decide whether to revise again or deliver. '
        'Your initial action should lead to a revised build or a specific evidenced blocker; further analysis is optional. '
        'Do not simulate the historical design again. In reason/next_step state relevant observed facts, a working hypothesis explicitly labeled as such, '
        'and the proposed change and what execution tests. Choose all revisions yourself; no direction or sequence is prescribed. '
        'Only four declared decisions are authorized: near/far length, common section scale, and material scenario. '
        'Section scale multiplies transverse dimensions at every station relative to frozen source. Material Young-modulus factors are '
        'baseline 1, compliant 0.9, stiff 1.1; density and viscosity unchanged. All scientific/control settings are frozen. '
        'Coverage is separate from the original reach evaluator: length delta from baseline >=0.001 m, section-scale delta >=0.01, nonbaseline material. '
        'A meaningful repair requires at least one decision changed relative to the supplied failure and a fresh complete evaluation. '
        'Use build then run; run takes source_node and omits combination. Cite previous node results after the first action. '
        'Historical case is attributed prior evidence, not a current selectable execution. Comparisons appear automatically after each run. '
        'A covered revised design passing the unchanged task may be delivered immediately. If a revision fails and resources remain, '
        'revise based on evidence or identify a concrete stopping reason. One failed point never proves the authorized space infeasible; '
        'maximum values are not presumed optimal. Constant tensions do not imply static equilibrium. Accepted feasible plans are not convergence. '
        'Zero convergence does not prove reach impossible; 10 ms deadline misses are diagnostics in this offline experiment. '
        'Ceilings: 32 provider requests, 80 platform tool calls, 3 fresh backend attempts including failures/retries, zero workers, '
        '10800 charged wall seconds; retain the 1800-second per-call reservation and final-report budget. Historical execution costs zero fresh attempts. '
        'On finish copy candidate_facts into design_statement (including parameters and physical_changes) and free_reach factual_result into result_statement. '
        'Do not search for tracking-only metrics. Keep final reason factual and concise: historical starting case, revisions actually tested, '
        'actual changes, selected evaluated design, original reach result, separate settling/convergence/computation diagnostics, '
        'supported conclusions, uncertainty, and stopping reason. No optimality/global infeasibility/static equilibrium/dominant-cause claim without evidence. '
        'Use existing compact context and retained detail references. Do not claim independently generating the supplied historical failure.')
    return inp


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    atomic_json(args.output,revision_input(args.source))
