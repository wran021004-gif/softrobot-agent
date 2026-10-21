"""New independently authorized SDK grant; reuse the original handoff driver."""
import argparse
import asyncio
from pathlib import Path
from tools.research.config import ROOT
from tools.state_io import read,atomic_json,digest
from tests.research.s127_4_sdk_continuation import run

SPEC=ROOT/'configs/research/study_s127_6_handoff.json'
OUT=ROOT/'evidence/s127_6_handoff'


def prepare():
    runtime=read(ROOT/'configs/research/runtime.json')
    runtime['provider']['max_tokens']=65536
    runtime_path=ROOT/'configs/research/runtime_s127_6_validation.json'
    raw=read(ROOT/'configs/research/study_s127_4_handoff.json')
    raw.update(study_id='s127-6b-sdk-20261021',runtime=runtime_path.name,
        evidence_destination='runs/s127_6_handoff_export',
        authorization='S12.7.6B preparation only. New independent scope approval required before any Provider request; no S12.7.4 authorization or budget reused.')
    raw['budgets'].update(provider_requests=12,public_operations=60)
    raw['execution_instructions']=raw['execution_instructions'].replace('S12.7.4B','S12.7.6B')
    raw['execution_instructions']=raw['execution_instructions'].replace('Prefer a low-cost structure generation or baseline control initialization where scientifically useful. ','')
    if (ROOT/'runs/research'/raw['study_id']).exists():raise ValueError('EXISTING_VALIDATION_STUDY_CANNOT_BE_REFROZEN')
    for path,value in ((runtime_path,runtime),(SPEC,raw)):
        atomic_json(path,value)
    scope=dict(stage='S12.7.6B',spec_identity=digest(raw),runtime_identity=digest(runtime),
        endpoint='https://api.deepseek.com/chat/completions',model=runtime['provider']['model'],
        thinking='enabled',reasoning_effort='high',max_output_tokens=65536,request_ceiling=12,
        automatic_retries=0,new_physical_ceiling=2,mathematics=0,nmpc=0,ppo=0,
        scientific_actions=raw['allowed_plan_actions'],new_session_scientific_action_ceiling=1,
        transfer_scope='Only new isolated original Reach task/FamilySpace, generated candidates/controls, own tool feedback/evidence/budgets and research_plan/evidence_read schemas. Existing S12/S12.6/S12.7 experiments are excluded. Own old-session history retains full reasoning/tool IDs within its invocation. New SDK session receives authoritative handoff, never copied old chat. Own raw physical samples may be read if the model chooses one of at most two fixed-input evaluations.',
        local_archive='Complete request/response bytes, reasoning, Store and SDK snapshots remain under ignored runs/research/s127-6b-sdk-20261021. No raw transcript upload to GitHub.',
        publication_scope='Code/configuration, derived metrics, hashes and precise references only.',
        status='awaiting_independent_authorization',independent_authorization_required=True)
    atomic_json(OUT/'scope.json',scope)
    return dict(scope=scope,scope_identity=digest(scope))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--offline',action='store_true');parser.add_argument('--authorization',type=Path)
    args=parser.parse_args()
    if args.prepare:print(prepare())
    elif args.offline or args.authorization:
        print(asyncio.run(run(args.authorization,offline=args.offline,spec_path=SPEC,out=OUT,stage='S12.7.6B')))
    else:parser.error('Choose --prepare, --offline or --authorization')
