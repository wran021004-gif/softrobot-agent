# C3.2 真实配对执行入口就绪

2026-10-26，Asia/Shanghai。基线 `891c877a94823076222a8ffae52a5bc6a4950f45`，
独立分支 `feat/c32-readonly-live-probe`。本轮工程入口已就绪，**未开展真实科研决策对照**。
没有针对 C3.2 的新外发授权；实际 Provider 请求、输入/输出 Tokens、科学预算消耗全部为 **0**。

## 复用的冻结输入

直接使用原工作区：

`D:/softrobot-agent/.worktrees/c32-scientific-decision-probe/runs/c32-final/`

六份 `*-1-request.json`、六份原离线审计及 `frozen.json` 均存在，未重新生成。
测试前后逐字节比较原目录全部文件，内容一致。原 C3.2 报告、公开汇总、评分协议和历史档案未修改。

- Control：`2aedb99c6ef222f6f84e0731561339b0c9883914`。
- Treatment：`e52b71c9e62fef7d4a34b145ec63789db44d0bb5`。
- 场景 N/K/M、source_state、任务阈值、原数学授权缺口、native 成本未知和未来引用闭包保持原样。
- 原数学权限缺口不由 Provider 外发批准补齐；合法提案和实际执行继续分别表述。

入口读取已保存请求，不重新构造历史状态。发送前核对原提交中的协议/评分及公开事实、两个工作树的
HEAD/生产目录、原请求与保存投影及请求大小。首轮在新输出目录保存输入绑定；第二轮要求同一绑定和授权记录。
没有新增哈希链、Provider 客户端、预算框架或 Store 实现。

## 脚本与只读边界

修改 `tests/research/agent_math_decision_probe.py` 和对应原测试文件，新增：

- `c32-live`：沿用 `c3_live` 的同一循环、LiveBoundary、原始响应保存和真实 usage 结算。
  首轮发送六份已有请求，完整保留模型、推理设置、Schema、Prompt 和其余冻结参数。
- `c32-review`：核对 Store 原请求/原响应/只读反馈与本地记录，汇总总量及逐场景/版本 usage、
  tool_calls、evidence_read、错误查询、无效工具 JSON、空对象读取、同内容复核和契约合法提案。
  同时输出原始回答、反馈来源及冻结评分表；科学评分和首次可信提案成本留待审阅，绝不按 Schema 自动评分。

原 `c3_readiness_audit.py` 无修改。只读反馈仍在相应 Control/Treatment 工作树中执行：
evidence_read 沿原闭包读取；Plan 检查 Schema、契约和 evidence/intent admission；
AnalysisRequest 检查 Schema 和候选身份。完整 worker 适用性、资源及执行准入仍明确为未检查。
提案另附冻结目录中的方法授权状态，不授予新权限；预计实际成本保持原核准前的 unknown，不假装为零。
diagnose 只记录提案，包括带 local_diagnostic 的 Plan，均不派发。

真实请求/响应及反馈保存在独立输出目录的原 Store，使用独立 grant
`c32-scientific-decision-probe-12`。原 R1/C3 科学账本不写入；Provider-only 账本只计发送，
模型公开工具调用另从真实 tool_calls 统计，不能把该账本 tool_calls=0 当成模型没有调用工具。

## 未来执行所需最小授权

需要用户明确批准：把上述六份冻结输入中的任务、候选/控制来源、必要科学证据、工具 Schema 和决策上下文，
以及第二轮各自真实回答与合法只读反馈，发送至 `https://api.deepseek.com/chat/completions`，
沿用冻结的 `deepseek-flash`、high reasoning、thinking enabled；本轮独立上限 **12 次**，
先六次再核查，不重试、不换模型、不重新抽样、科学执行为零。原 C3/C3.1 授权不能继承。
不包含向 GitHub 公开原始请求、响应、推理或 Store 的授权。

`--approval-file` 是已取得用户批准后的本地记录，不会自行产生用户授权。
本轮未创建真实批准文件，也未绑定真实 C3.2 grant。以下是**未批准模板**，不能据此运行：

```json
{
  "experiment": "C3.2",
  "approved": false,
  "user_approval": "PENDING_EXPLICIT_C32_USER_AUTHORIZATION",
  "endpoint": "https://api.deepseek.com/chat/completions",
  "model": "deepseek-flash",
  "max_requests": 12,
  "commits": {
    "control": "2aedb99c6ef222f6f84e0731561339b0c9883914",
    "treatment": "e52b71c9e62fef7d4a34b145ec63789db44d0bb5"
  },
  "frozen_inputs": "D:/softrobot-agent/.worktrees/c32-scientific-decision-probe/runs/c32-final",
  "data_scope": "six_frozen_inputs_and_read_only_followup",
  "scientific_execution": false,
  "no_retries": true
}
```

取得实际批准后，将原文/来源记入 user_approval，并在忽略的 runs 目录保存 approved=true 的 UTF-8 JSON。
授权缺失、不匹配或仍为 pending 时，在读取凭据、建立账本和发送之前拒绝。

## CLI 与停止规则

在本工作区运行，使用现有 Python 环境。以下 live 命令只可在取得上述批准后执行。

```powershell
$c32Python = 'D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe'
$c32Inputs = 'D:/softrobot-agent/.worktrees/c32-scientific-decision-probe/runs/c32-final'

# 第一轮；完成六次即返回，不自动进入第二轮
& $c32Python -m tests.research.agent_math_decision_probe c32-live --frozen-inputs $c32Inputs --out runs/c32-authorized-live --approval-file runs/c32-approval.json

# 复核，无 Provider 请求；review.json 是自动生成的未评分视图
& $c32Python -m tests.research.agent_math_decision_probe c32-review --frozen-inputs $c32Inputs --out runs/c32-authorized-live

# 仅在首轮有效后执行预定第二轮；仍使用同一授权和账本
& $c32Python -m tests.research.agent_math_decision_probe c32-live --frozen-inputs $c32Inputs --out runs/c32-authorized-live --approval-file runs/c32-approval.json --followup
```

首轮顺序保持 N旧/新、K新/旧、M旧/新。第二轮逆序；只拼接各自首轮完整原始消息
（包括 reasoning_content）、真实只读反馈及既有共同结束轮说明，不增加模拟科学观察。

- 首轮必须恰好六次请求、六份确认回执，状态 first_six_complete；不存在未处理响应或未知发送。
  Store 原请求、原响应及原只读反馈须与本地记录一致，输入/评分/授权绑定不变，才允许第二轮。
- HTTP/传输错误、截断或无法处理的输出、内部反馈失败立即停止，原始 bytes/usage/错误保留；不补发。
  模型工具参数 JSON 或 Schema 错误若能形成原有合法错误反馈，则作为真实结果保留，可按原协议进入第二轮。
- 第二轮最多再六次，总计不超过十二次。完成或中途失败后不自动恢复、换样或重发；
  已有账本/已结算结果阻止重新启动。不能换输出目录复制额度。

## 定向验证与实际消耗

四项测试函数通过：三项新增 C3.2 回归及原 C3 十二次硬额度/零 dispatch 回归。
使用 MockTransport 及独立 mock grant，未使用真实 C3.2 grant：

- 六次首轮和六次预定第二轮控制流、原请求一致、消息/反馈不串组。
- 原只读反馈实际覆盖合法读取、闭包外引用拒绝、旧版空 fields、DIAGNOSE、未获数学执行授权的
  AnalysisRequest，以及无效工具 JSON；提案没有产生新科学观察，正式授权状态未混同。
- 未授权、错误端点/额度/基线、修改冻结输入或评分均在发送前拒绝。
  第一轮后的本地响应或反馈被修改也不能进入第二轮。
- 未知发送仅记一次尝试，保留 unknown usage，阻断首轮重启和第二轮；原回归继续拒绝第十三次。

模拟完整运行的 12 次响应和 180 tokens 是测试 fixture 计数，不是真实费用或科学证据。
首次定向运行暴露空 occupied 字典的键假设，已修正并重跑受影响路径。
无全仓测试、科学回放、历史重新冻结或 Provider 调参。
git diff --check 通过；生产目录、原协议/报告/汇总与基线无差异。

独立只读 readiness 检查成功读取六份原输入，状态 not_started：真实 Provider **0**、真实 Tokens **0**，
真实 C3.2 grant 绑定数 **0**；原冻结目录没有 Provider Store。
数学/native/MuJoCo/GVS/NMPC/RL/Reporter/独立物理执行及原科学预算支出均 **0**。
入口就绪和 mock 通过不改变原“科研能力证据不足”的结论。
