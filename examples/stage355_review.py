"""Amend review metadata only; verify the sealed identities before writing."""
from pathlib import Path
import hashlib
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.state_io import read, atomic_json


def amend():
    root = ROOT / 'evidence/stage354_milestone0_20261003'
    outcome = read(root / 'dual_context/outcome.json')
    refs = outcome['chain']
    artifact = lambda ref: read(root / 'dual_context/artifacts' / (ref['artifact_id'] + '.json'))
    revision, feedback, final = map(artifact, (refs['revised_report'], refs['feedback'], refs['final_response']))
    candidate = feedback['execution']['factual_result']['candidate']
    correct = candidate['candidate_id']
    submitted = 'improvement-744833040049'
    assert correct == 'improvement-744833804049'
    assert submitted in final['reasoning'] and submitted not in str(revision)
    assert correct in revision['report']['recommended_actions'][-1]
    assert final['feedback'] == refs['feedback'] and final['report'] == refs['revised_report']
    assert final['candidate_disposition'] == 'defer_selection' and final['selected_candidate'] is None
    review = read(root / 'scientific_review.json')
    review['prose_findings'] = [dict(run='dual_context', affected_fields=[
        'final_response.reasoning', 'resolved_calls.arguments.reasoning',
        'raw_calls.raw.choices[0].message.tool_calls[0].function.arguments (reasoning)'],
        submitted_candidate_name=submitted, correct_bound_identity=candidate,
        source_reference=refs['final_response'], feedback_reference=refs['feedback'],
        revised_report_reference=refs['revised_report'],
        explanation='Archived final decision prose transposes the candidate name. The revised report names the bound candidate correctly. Structured report/feedback bindings and defer_selection with selected_candidate=null remain valid. Original artifacts and outcomes are unchanged.',
        request_discrepancy='The request described the two names in reverse and located the typo in revised-report prose; sealed records establish the locations and direction recorded here.')]
    atomic_json(root / 'scientific_review.json', review)
    manifest = read(root / 'sha256_manifest.json')
    manifest['scientific_review.json'] = hashlib.sha256((root / 'scientific_review.json').read_bytes()).hexdigest()
    atomic_json(root / 'sha256_manifest.json', manifest)
    print('Verified review amendment; only review metadata and its checksum changed.')


if __name__ == '__main__':
    amend()
