from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.platform_config import load

# 复用完整的开发任务定义，创建自己的练习配置。
folder = ROOT / "configs/platform/learning_peak"
folder.mkdir(parents=True, exist_ok=True)
session = load(ROOT / "configs/platform/signal_hold/session.yaml")
session["run_id"] = "force-peak"
policy = session["policy"]
policy["allowed_tools"] = []
policy["tool_bindings"] = {
    "analysis.force_peak": "1.0.0",
    "evidence.read": "1.0.0",
    "session.control": "1.0.0",
}
policy["search"] = None
policy["timeout_s"] = 5.0
budget = dict(tool_calls=12, model_calls=0, backend_solves=0,
              worker_calls=0, wall_s=60.0)
policy["budget"] = budget.copy()
project = dict(
    project_id="learning-force-peak",
    grant_id="learning-force-peak-local-v1",
    purpose="development",
    authorization_source="用户独立数学工具练习，仅离线计算，不使用历史研究预算",
    budget=budget.copy(),
    exclusive_resources={},
)
request = dict(
    tool_id="analysis.force_peak", tool_version="1.0.0",
    arguments=dict(values_n=[1.0, -4.0, 3.0]),
    reason="计算给定样本的力峰值", cache="reuse",
)
decisions = [
    dict(tool_id="analysis.force_peak", arguments=request["arguments"], reason="调用新工具"),
    dict(tool_id="evidence.read", arguments=dict(reference="$last_output", pointer="/peak_n"),
         reason="读取刚刚保存的峰值"),
    dict(tool_id="session.control", arguments=dict(status="stopped", reason="练习完成"),
         reason="结束离线演练"),
]
files = {
    "session.yaml": session,
    "project.yaml": project,
    "request-1.yaml": dict(request, request_id="peak-1"),
    "request-2.yaml": dict(request, request_id="peak-2"),
    "offline.yaml": dict(decisions=decisions),
}
for name, value in files.items():
    (folder / name).write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False), encoding="utf8")
print("练习配置已生成：configs/platform/learning_peak")
