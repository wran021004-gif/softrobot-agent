"""Read-only request-size inspection for softrobot-agent commit 409e14e.

Run with the existing softagent environment:
    python round9_context_check.py --repo D:\\softrobot-agent

No API request, MATLAB startup, simulation, state save or budget reservation.
Prints sizes and candidate identifiers only, never prompt/evidence contents.
"""

import argparse
import json
from pathlib import Path
import sys


def encoded_size(value):
    # Same JSON/UTF-8 serialization as DynamicCampaign.run_model at 409e14e.
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def show_sizes(label, mapping):
    print("\n" + label + " (individual serialized values; not additive):")
    for name, value in sorted(mapping.items(), key=lambda item: encoded_size(item[1]), reverse=True):
        print(f"  {name}: {encoded_size(value):,} bytes")


def main():
    parser = argparse.ArgumentParser(description="Read-only Round 9 model request byte breakdown")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--root", type=Path, default=Path("runs/round9_reach"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    root = (args.root if args.root.is_absolute() else repo / args.root).resolve()
    if not (repo / "tools/dynamic_campaign.py").is_file():
        parser.error("--repo must point to the Round 9 softrobot-agent repository")
    sys.path.insert(0, str(repo))

    from tools.dynamic_campaign import DynamicCampaign, LEDGER
    from schemas.dynamic_workbench import native_tools

    # Intentionally bypass __init__, load, save, run_model and all backends.
    # At 409e14e, context() reads saved facts and remaining() does arithmetic.
    book = DynamicCampaign.__new__(DynamicCampaign)
    book.root = root
    book.state = read_json(root / "state.json")
    book.ledger = read_json(LEDGER)
    context = book.context()
    config = book.state["request"]["design_session"]
    prompt = (root / "inputs/system_prompt.md").read_text(encoding="utf-8")
    payload = dict(
        model=config["model"], thinking={"type": "enabled"}, max_tokens=8192,
        stream=False, tools=native_tools(),
        messages=[
            dict(role="system", content=prompt),
            dict(role="user", content=json.dumps(context, ensure_ascii=False)),
        ],
    )
    total = encoded_size(payload)
    limit = 60000  # Actual hardcoded guard in commit 409e14e.
    print("Read-only inspection: no API, no solver, no state/budget writes.")
    print(f"Saved status: {book.state['status']}")
    print(f"Saved model request records: {len(book.state.get('model_calls', []))}")
    print(f"Total candidates: {len(book.state['candidates'])}")
    print(f"Candidates included in context: {len(context['candidates'])}")
    print(f"Full request: {total:,} bytes; hardcoded limit: {limit:,} bytes")
    print(f"Result: {'OVER_LIMIT' if total > limit else 'WITHIN_LIMIT'}; excess: {max(0, total-limit):,} bytes")
    show_sizes("Request components", {
        "tools": payload["tools"], "system_message": payload["messages"][0],
        "user_message": payload["messages"][1],
    })
    show_sizes("Context fields", context)
    for candidate in context["candidates"]:
        show_sizes("Candidate " + candidate["candidate_id"], candidate)
    latest = context.get("latest_tool_result")
    if isinstance(latest, dict):
        show_sizes("Latest tool result", latest)
        if isinstance(latest.get("data"), dict):
            show_sizes("Latest tool result data", latest["data"])
    print("\nThis checks request construction, not API credentials or model output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
