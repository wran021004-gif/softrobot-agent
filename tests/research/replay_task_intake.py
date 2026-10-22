"""Offline comparison of immutable S130 receipts with the current parser/compiler.

Requires the local ignored evidence directories. Never calls a Provider or changes
historical files. Derived Reach fixtures are explicitly NOT new model evidence.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from schemas.task_intake import AcceptanceView, IntakeProposal
from tools.state_io import read
from tools.task_intake import compile_draft, parse_response


ROOT = Path(__file__).resolve().parents[2]
HISTORY = [ROOT / 'runs' / name for name in
           ('s130-live-final-20261022', 's130-live-nonthinking-20261022')]
REPORT = ROOT / 'docs/research/s130_live_validation.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def replay(output):
    historical = read(REPORT)
    cases = historical['cases']
    evidence = [REPORT, REPORT.with_suffix('.md')]
    for root in HISTORY:
        for case in cases:
            evidence.extend(p for p in (root / case['case']).iterdir() if p.is_file())
    before = {str(p.relative_to(ROOT)): sha(p) for p in evidence}
    # Verify second-round hashes against the already committed audit, not just
    # against a newly generated snapshot. First-round receipts are also hashed.
    for case in cases:
        for filename, key in [('response.txt', 'raw_response_sha256'),
                              ('result.json', 'result_sha256'),
                              ('request_messages.json', 'request_messages_sha256')]:
            assert sha(HISTORY[1] / case['case'] / filename) == case[key]
    output.mkdir(parents=True, exist_ok=False)
    reference = read(ROOT / 'runs/s130-n2/reference.json')
    protocol = read(ROOT / 'runs/s130-n2/analysis_protocol.json')

    def compile_review(draft):
        return compile_draft(draft, trusted_reference=reference,
            reference_label='explicit reach_free full snapshot', analysis_protocol=protocol)

    rows = []
    for round_index, root in enumerate(HISTORY, 1):
        for case in cases:
            folder = root / case['case']
            text = (folder / 'task.txt').read_text(encoding='utf-8')
            raw = (folder / 'response.txt').read_text(encoding='utf-8')
            old = read(folder / 'result.json')
            receipt = old['provider_receipt']
            context = (AcceptanceView.model_validate(read(folder / 'context.json'))
                       if (folder / 'context.json').exists() else None)
            new = parse_response(text, raw, finish_reason=receipt['finish_reason'], context=context)
            try:
                IntakeProposal.model_validate_json(raw, strict=True)
                format_pass = True
            except ValueError:
                format_pass = False
            compiled = compile_review(new.draft) if new.draft else None
            artifact = f'round{round_index}_{case["case"]}.json'
            save(output / artifact, dict(evidence_kind='offline_replay', provider_requests=0,
                intake=new.model_dump(mode='json'),
                compilation=compiled.model_dump(mode='json') if compiled else None))
            rows.append(dict(round=round_index, case=case['case'],
                original_evidence=str(folder.relative_to(ROOT)),
                raw_response_sha256=sha(folder / 'response.txt'),
                old_recorded_format_pass=case['format_pass'] if round_index == 2 else False,
                old_recorded_status=old['status'], old_recorded_error=old['error'],
                offline_format_pass=format_pass, offline_status=new.status, offline_error=new.error,
                unquoted_spans=[g.model_dump() for g in new.draft.unquoted_spans] if new.draft else None,
                compilation_status=('not_run_parse_failed' if compiled is None else
                    'draft_preview' if compiled.configuration_preview else 'blocked'),
                diagnostics=compiled.diagnostics if compiled else [],
                capabilities=compiled.capabilities if compiled else None,
                historical_semantic_review=({key: case[key] for key in
                    ('intent_correct', 'explicit_requirements_preserved', 'temporal_semantics_correct',
                     'missing_definitions_correct', 'hallucinated_conditions', 'semantic_correct', 'verdict')}
                    if round_index == 2 else None),
                replay_artifact=artifact))

    # A separately labelled integration fixture, with every edit disclosed.
    # This does not repair the raw response in place or approve any task.
    folder = HISTORY[1] / '01_reach_hold'
    text = (folder / 'task.txt').read_text(encoding='utf-8')
    proposal = json.loads((folder / 'response.txt').read_text(encoding='utf-8'))
    context = AcceptanceView.model_validate(read(folder / 'context.json'))
    original_quote = proposal['temporal_relations'][2]['quote']
    start = text.index('最终保持窗口')
    end = text.index('；采用参考配置')
    proposal['temporal_relations'][2]['quote'] = text[start:end]
    quote_fixed = parse_response(text, json.dumps(proposal), context=context)
    assert quote_fixed.draft is not None, quote_fixed.error
    quote_preview = compile_review(quote_fixed.draft)
    assert quote_preview.configuration_preview is None
    reviewed = deepcopy(proposal)
    removed_rows = [r for r in reviewed['requirements'] if r['source'] == 'llm_candidate']
    reviewed['requirements'] = [r for r in reviewed['requirements'] if r['source'] != 'llm_candidate']
    removed_edge = reviewed['temporal_relations'].pop(0)
    draft = parse_response(text, json.dumps(reviewed), context=context).draft
    compiled = compile_review(draft)
    assert compiled.configuration_preview is not None, compiled.diagnostics
    derivative = dict(evidence_kind='counterfactual_review_fixture_not_provider_or_approval',
        original_case='01_reach_hold', user_text_unchanged=True, provider_requests=0,
        edits=[dict(path='temporal_relations[2].quote', old=original_quote, new=text[start:end]),
               dict(removed_candidate_questions=removed_rows), dict(removed_inferred_order=removed_edge)],
        quote_only_diagnostics=quote_preview.diagnostics,
        candidate_status=compiled.candidate_task.status,
        authorization=compiled.capabilities['authorization'],
        acceptance_components=list(compiled.acceptance_spec['pending_evidence']['components']),
        temporal=compiled.capabilities['temporal'])
    save(output / 'reach_quote_only.json', dict(proposal=proposal,
        compilation=quote_preview.model_dump(mode='json')))
    save(output / 'reach_review_fixture.json', dict(proposal=reviewed, edits=derivative,
        compilation=compiled.model_dump(mode='json')))
    assert before == {str(p.relative_to(ROOT)): sha(p) for p in evidence}, 'HISTORY_CHANGED'
    summary = dict(evidence_kind='offline_replay_only', baseline_commit='c5bba8ff',
        provider_requests=0, new_provider_tokens=0, historical_requests=12,
        historical_tokens=45737, historical_monetary_cost=None,
        historical_files_unchanged=True, historical_sha256=before,
        cases=rows, reach_integration_fixture=derivative)
    save(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New directory; existing paths are refused')
    args = parser.parse_args()
    with (patch('openai.OpenAI', side_effect=AssertionError('offline only')),
          patch('socket.socket.connect', side_effect=AssertionError('offline only'))):
        summary = replay(args.output)
    print(json.dumps(dict(provider_requests=0, historical_files_unchanged=True,
        cases=[{k: r[k] for k in ('round', 'case', 'offline_status', 'compilation_status')}
               for r in summary['cases']]), indent=2))
