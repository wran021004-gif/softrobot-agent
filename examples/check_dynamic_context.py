"""Read-only inspection using the exact dynamic resume request builder."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dynamic_campaign import DynamicCampaign, LEDGER
from tools.dynamic_context import RequestTooLarge
from tools.state_io import read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('runs/round9_reach'))
    args = parser.parse_args()
    # No constructor, load/save, API, solver or budget reservation.
    book = DynamicCampaign.__new__(DynamicCampaign)
    book.root = args.root.resolve()
    book.state = read(book.root / 'state.json')
    book.ledger = read(LEDGER)
    try:
        payload, metrics = book.build_model_request()
        context = json.loads(payload['messages'][1]['content'])
        print('Selected candidates:', ', '.join(c['candidate_id'] for c in context['candidates']))
    except RequestTooLarge as exc:
        metrics = exc.metrics
    print('Read-only: zero API/solver calls; no state, prompt or budget writes.')
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return int(metrics['total_bytes'] > metrics['limit_bytes'])


if __name__ == '__main__':
    raise SystemExit(main())
