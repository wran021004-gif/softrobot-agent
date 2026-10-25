"""User-authorized bounded G1/G2 validation through the existing research interfaces."""
import argparse
import json
from pathlib import Path

from tests.research import c3_f1_f2_validation as prior
from tools.platform_host import Host
from tools.research import core
from tools.research.agent import load_credential

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/c3_g1_g2'
SOURCE = 'C:/Users/gugugaga/.codex/attachments/b47b5887-0227-426f-9031-13cbb0fdda25/已粘贴的文本.txt'
AUTH = ('2026-10-25 explicit user G1/G2 authorization: G1 continuity <=2 and paired decisions <=4 '
        'DeepSeek requests, mathematics=0; only after G1 passes G2 <=8 DeepSeek requests including '
        'Reporter and <=4 total mathematical evaluations including preparation/internal calls. '
        'All stages: independent physics=0, NMPC=0, PPO=0; no retries, budget resets, full A/B '
        'or unbounded search. Necessary frozen task/design and cited scientific excerpts only. ' + SOURCE)
CONTINUITY_ID = 'c3-g1-continuity-20261025'
DECISION_ID = 'c3-g1-decisions-20261025'
PROBE = ROOT / 'runs/c3-g1-decision-probe'


def host(study_id):
    return Host(ROOT / 'runs/research' / study_id, study_id, actor='unified-research')


def prepare_g1():
    h = prior.provision('continuity', study_id=DECISION_ID,
        instructions='Read-only paired evaluation turns; new Plan required every turn; no scientific dispatch.',
        overrides=dict(base_commit='5e5f6532406eb7616f8da2d8984d74ba3f63f9af',
            evidence_destination='evidence/c3_g1_g2/decisions'),
        budget_overrides=dict(provider_requests=4, mathematical_evaluations=0),
        source=SOURCE, authorization=AUTH)
    result = prior.decision_probe(out=PROBE, destination=OUT, authorization=AUTH,
                                 version='c3-g1-paired-decisions-v1')
    core.export(h)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare-g1', 'continuity', 'restore', 'probe-live'])
    args = parser.parse_args()
    if args.mode in ('continuity', 'restore', 'probe-live'):
        load_credential(Path('~/.codex/.env').expanduser())
    if args.mode == 'prepare-g1':
        result = prepare_g1()
    elif args.mode in ('continuity', 'restore'):
        result = prior.continuity(args.mode == 'restore', study_id=CONTINUITY_ID,
            destination=OUT / 'continuity', provider_requests=2, source=SOURCE, authorization=AUTH)
    else:
        h = host(DECISION_ID)
        try:
            result = prior.decision_probe(True, out=PROBE, destination=OUT, authorization=AUTH, formal_host=h)
        finally:
            core.export(h)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
