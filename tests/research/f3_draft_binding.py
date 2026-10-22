"""Bind an unapproved proposal to the final clean HEAD; never create a Study."""
import argparse
from pathlib import Path
import subprocess
from tools.state_io import read, atomic_json
from tools.research.config import ROOT, resolve


def bind(output, *, require_clean=True):
    if require_clean and subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('FINAL_CLEAN_COMMIT_REQUIRED')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    raw=read(ROOT/'configs/research/study_f3_pending.json')
    if not raw['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'):
        raise ValueError('UNAPPROVED_PROPOSAL_REQUIRED')
    raw['base_commit']=commit
    path=ROOT/'configs/research/.f3_pending_final.json'
    atomic_json(path,raw)
    spec=resolve(path)
    original=resolve(ROOT/'configs/research/study_s125_cold.json')
    for key in ('canonical_task','canonical_task_identity','family_space','family_space_identity'):
        if spec[key]!=original[key]:raise ValueError('ORIGINAL_TASK_AND_FAMILY_REQUIRED: '+key)
    if (ROOT/'runs/research'/spec['study_id']).exists():
        raise ValueError('PROPOSAL_MUST_NOT_HAVE_A_STUDY')
    proposal=read(ROOT/'evidence/f3_prestudy/f3_launch_proposal.json')
    proposal.update(code_commit=commit,specification=str(path),resolved_identity=spec['resolved_identity'],
        resolved_specification=spec,proposal_seed='configs/research/study_f3_pending.json')
    proposal['final_binding']='Bound to final clean HEAD. Valid resolved draft, no authorization or Study creation.'
    atomic_json(output,proposal)
    report=(ROOT/'docs/research/f3_prestudy_integration.md').read_text(encoding='utf-8')
    report+='\n## Final checkout binding\n\n'
    report+=f'Branch: `integration/f3-prestudy`. Final complete commit: `{commit}`.\n\n'
    report+=f'Final valid pending configuration: `{path}`.\n\n'
    report+=f'Resolved identity: `{spec["resolved_identity"]}`. Binding: `{Path(output).resolve()}`.\n\n'
    report+='No formal F3 Store was created; no approval or live-handoff flag was written.\n'
    (ROOT/'runs/f3_prestudy_integration_final.md').write_text(report,encoding='utf-8')
    return dict(commit=commit,configuration=str(path),resolved_identity=spec['resolved_identity'],
        binding=str(Path(output).resolve()),study_created=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'runs/f3-final-binding.json')
    args=parser.parse_args()
    print(bind(args.output))
