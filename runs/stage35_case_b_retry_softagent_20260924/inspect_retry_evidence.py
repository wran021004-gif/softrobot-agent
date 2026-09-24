"""Read-only compact dump of saved Case B retry decisions for audit authoring."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from extensions.tendon_family.route import view  # noqa: E402
from tools.platform_host import Host  # noqa: E402

run_dir = Path(__file__).resolve().parent
run_id = "stage35-case-b-retry-softagent"
host = Host(run_dir, run_id)
route_view = view(host)
with host.store.connect(True) as db:
    events = [json.loads(row[0]) for row in db.execute("SELECT body FROM events ORDER BY seq")]


def event(kind, request_id):
    return next((row for row in events if row["kind"] == kind and row.get("request_id") == request_id), None)


rows = []
include_nodes = "--nodes" in sys.argv[1:]
indices = [value for value in sys.argv[1:] if value.isdigit()]
wanted = {int(value) for value in indices} if indices else None
for index in range(route_view["usage"]["used"]["model_calls"]):
    if wanted is not None and index not in wanted:
        continue
    request_id = f"model-{index}"
    call = host.store.lookup(run_id, request_id)
    receipt = json.loads(call["receipt"])
    raw_event = event("model_raw_response", request_id)
    raw_wrapper = host.store.artifact(raw_event["outputs"][0]) if raw_event else {}
    raw = raw_wrapper.get("raw", raw_wrapper)
    message = raw.get("choices", [{}])[0].get("message", {})
    row = {
        "model_request": request_id,
        "model_status": receipt["execution_status"],
        "finish_reason": raw.get("choices", [{}])[0].get("finish_reason"),
        "content": message.get("content"),
    }
    if receipt["execution_status"] == "completed":
        decision = host.store.artifact(receipt["output"])
        tool_call = host.store.lookup(run_id, decision["request_id"])
        tool_receipt = json.loads(tool_call["receipt"]) if tool_call and tool_call["receipt"] else None
        if tool_receipt is None:
            tool_event = next(item for item in events if item["kind"] == "tool"
                              and item.get("request_id") == decision["request_id"]
                              and item["status"] == "rejected")
            tool_receipt = host.store.artifact(tool_event["outputs"][0])
        row.update({
            "tool_request": decision["request_id"],
            "tool": decision["tool_id"],
            "arguments": decision["arguments"],
            "reason": decision["reason"],
            "evidence": decision.get("evidence", []),
            "tool_status": tool_receipt["execution_status"],
            "tool_error": tool_receipt.get("error"),
            "tool_output": (tool_receipt.get("output") or {}).get("artifact_id"),
            "charged": tool_receipt.get("charged"),
        })
    rows.append(row)

print(json.dumps({
    "session_status": host.store.session(run_id)["status"],
    "usage": route_view["usage"],
    "decisions": rows,
    "route_nodes": [
        {
            "node_id": node["node_id"],
            "action": node["action"],
            "request_id": node["request_id"],
            "status": node["status"],
            "selection": node["selection"],
            "summary": node["summary"],
        }
        for node in route_view["route"]["nodes"]
    ] if include_nodes else [],
}, ensure_ascii=False, indent=2))
