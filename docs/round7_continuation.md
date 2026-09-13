# 第七轮：有限上下文与兼容续接

在现有 `softagent` 环境使用同一个 DeepSeek 决策模型。数值执行仍为原 Harness、MATLAB、MuJoCo 和固定 C1；没有更改任务、评分阈值、探索范围或物理定义。

## 继续已准备的运行

`runs/round7_ready` 已从第六轮真实记录继承两个候选、两次评价和全部已用预算，并复用保存数据完成比较和 c001 动画。旧目录未改写。当前状态 `WAITING_FOR_KEY`，新增真实模型请求和新增仿真均为零。

```powershell
conda activate softagent
$deepseekSecret = Read-Host 'DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $deepseekSecret).Password
python examples/workbench.py resume runs/round7_ready
```

不需要重算 c000/c001。模型收到候选成绩、`eval:c001` 和证据目录，按提示先读最新候选结果，再自主选择修改或停止。剩余 **11 次模型请求、1 个候选、1 次仿真、3 次 MATLAB 数学调用、16 次工具执行、15 次决策**。所有数值调用按尝试预扣，失败不返还。不会自动追加预算或反复重试。

## 从旧运行创建新续接

需要另一份续接时选择尚不存在的目录：

```powershell
python examples/workbench.py continue runs/round6_ready --root runs/my_continuation
```

`continue` 与 `resume` 不同：前者复制证据到新运行，保存父运行的 request/state/源码快照/页面/报告/提示词到 `lineage/`，允许本次会话组织代码或模型配置变化；后者只恢复同一份冻结代码、运行环境和配置。`--steps 0` 只准备运行，`--steps N` 在 N 次决策后暂停。已保存但尚未执行的模型响应应先在原运行恢复到完整边界。

续接检查原证据哈希、候选设计哈希、原数值运行封存记录，以及数值代码、任务、评分、物理、依赖和 Python 版本是否兼容。可变化的会话文件明确列于 `tools/design_continuation.py` 的 `SESSION_FILES`；其他源码/配置变化会报告 `INCOMPATIBLE_COMPUTATION`。续接不能提高任何预算或重试上限。完成过的候选评价直接复用，即使新 request 的哈希不同也不会重算。

## 思考模式

在创建或续接前编辑 `configs/deepseek.yaml`，或用 `--model-config <yaml路径>` 指定配置。配置只在新运行创建时生效，不修改已冻结 request。

```yaml
thinking: enabled      # enabled 开启；disabled 关闭（默认）
context_turns: 2       # 每个协议会话片段的完整往返数，范围 1–6
max_tokens: 2048       # 思考与输出可能需要更多生成预算，可配置至 8192
max_input_bytes: 60000 # UTF-8 请求 JSON 上限，仍可配置，本轮未提高
```

开启时发送 `thinking: {type: enabled}`，省略无效的 temperature 参数。响应中的 `reasoning_content` 与 `content`、`tool_calls` 一起保存到 `response.json` 和状态，片段内每次请求原样回传；暂停恢复同样从落盘响应恢复。依据：[DeepSeek 官方思考模式与工具调用协议](https://api-docs.deepseek.com/guides/thinking_mode/)。

达到 `context_turns` 或整包超限时，整体结束旧会话片段，从保存事实新开会话；新片段不回放旧 assistant/tool 消息。正在回放的片段内不会截短或删除思考字段，也不会留下孤立的工具回复。最后一次有限反馈随新片段状态保留。若精简后的新片段仍超限，保存 `blocked_request.json` 和组成大小，明确停止，不伪装成成功。

默认关闭模式已准备实际续接；开启模式通过注入协议检查，因本进程无密钥，尚未完成真实 API 验证。

## 精简输入与按需证据

默认输入是原任务目标/阈值、必要环境条件、允许修改范围与关系约束、候选关键参数/实际及预测成绩、最近三项行动摘要、必要反馈、剩余预算。完整原始数据仍在原结果文件、模型请求/响应、状态和归档中。

| 标识 | 内容与读取方式 |
| --- | --- |
| `eval:c001` | c001 的真实评价包装；也可直接用于工具调用的 `evidence` |
| `catalog:c001` | c001 所有已登记证据及字段提示；读 `/entries` 分页查看 |
| `catalog:all` | 全部证据目录，包括任务、历史请求、回复与归档 |
| 原结果相对路径 | 继续兼容；同一候选真实仿真文件与评价包装归一到同一个 `eval:cNNN` |

例如读取第二个候选的模型/仿真对照诊断：

```json
{
  "evidence_id": "eval:c001",
  "pointer": "/data/diagnostics/compare_model_sim/metrics",
  "offset": 0,
  "limit": 10,
  "max_bytes": 3000,
  "reason": "核对预测与真实末端差异后再决定是否修改设计",
  "evidence": ["eval:c001"]
}
```

`pointer` 是 JSON Pointer；每次选择一个字段或子对象。`offset/limit` 控制对象条目或数组元素，`next_offset` 指向下一页。单次内容最多 6000 字节，默认 3000。更大字段返回明确标记的 `json_text_fragment`，按 `next_byte_offset` 读取后续片段；片段不是完整 JSON。返回的 `candidate_id`、`evaluation_id`、`cite_as` 明确归属，模型可把 `cite_as` 直接放入下次 `evidence`，但不能用 c000 的结果解锁 c001 的修改。

## 查看请求、比较和轨迹

```powershell
python examples/workbench.py observe runs/round7_ready
```

打开 <http://127.0.0.1:8765>，或直接打开 `runs/round7_ready/index.html`。页面顺序展示原始请求、回复、对应决策、工具结果、拒绝原因与停止原因；展开详情时暂停自动刷新，便于逐条阅读。请求显示 UTF-8 字节数和系统指令、工具定义、当前状态、历史回复/工具反馈、思考字段的组成，状态内部再列出候选/目录/反馈等大小。

候选表分别说明计算状态、任务是否达标以及轨迹/动画状态。`TASK_FAILED` 的已完成计算不会显示成没有轨迹；没有生成 GIF 与确实没有可用轨迹分开显示。保存轨迹观察、导出均不启动新仿真。

`design_report.json` 从原评价记录生成比较与最佳候选，同时报告 `workflow_completed`、`task_achieved`、继承用量和本运行新增请求/仿真预留。本轮离线比较和观察标记为 `authorized_saved_data_closeout`，不计为模型调用或模型自主决策。最终模型 `stop_design` 尚待密钥后的续接。

当前证据包见 [workbenches.zip](evidence/round7/workbenches.zip)，包含原第六轮实际运行与新续接。仅在目录不存在时解压至仓库根目录；已有记录直接保留。测试依赖此真实第六轮记录，限定检查命令为 `python -m unittest tests.test_round7_context -v`，不运行历史全量测试或旧实验。
