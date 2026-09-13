# 第六轮：使用 DeepSeek 自动设计机器人

本轮在 `feat/round5-design-workbench@5fe79f8` 上增加单模型设计循环，分支为 `feat/round6-deepseek-design`。模型提出参数修改和工具调用；Python 工作台执行检查、计算、评价、比较和观察，任务成绩仍由原评价程序决定。

## 填写密钥并启动

使用现有 `softagent` 环境。在本机普通 PowerShell 终端执行以下命令，密钥只保存在当前进程环境，不进入代码或命令历史中的明文赋值：

```powershell
conda activate softagent
$deepseekSecret = Read-Host 'DeepSeek API Key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $deepseekSecret).Password
python examples/workbench.py run --deepseek
```

默认目录为 `runs/deepseek_design`，已有目录不会被覆盖。没有密钥也可以先运行：创建初始候选和冻结请求后停在 `WAITING_FOR_KEY`，模型调用和仿真次数均为零。填好密钥后继续同一任务：

```powershell
python examples/workbench.py resume runs/deepseek_design
```

本轮已准备好待密钥的任务 `runs/round6_ready`。填写环境变量后，只需：

```powershell
python examples/workbench.py resume runs/round6_ready
```

若已删除运行目录，可以直接使用上面的 `run --deepseek` 新建。不要把密钥写进 YAML、提示词、`.py` 文件或决策 JSON；工作台不会读取密钥配置字段，也不会记录环境变量。HTTP Authorization 只在发请求时构造，不写入请求证据；响应和异常会移除密钥本身。

## 模型和预算配置

配置文件为 `configs/deepseek.yaml`。可复制并通过 `--model-config <文件>` 指定，但新配置只在创建任务时生效；同一次恢复运行继续使用其冻结配置和已用预算。

官方文档在实施时给出的 Chat Completions 模型包括 `deepseek-flash` 和 `deepseek-v4-pro`，本轮默认 `deepseek-flash`。服务地址使用 `https://api.deepseek.com`，也接受官方 `/v1` 地址；不允许把密钥发到其他域名。采用非流式 `POST /chat/completions`、原生 Function Tool Calls、`thinking: disabled`、`tool_choice: required`；每轮只执行一个工具。客户端不启用 Beta strict，也不依赖 SDK 自动重试。依据：[官方 API 文档](https://api-docs.deepseek.com/api/create-chat-completion/)、[官方工具调用说明](https://api-docs.deepseek.com/guides/tool_calls/)。

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| candidates | 3 | 包含初始候选；创建失败的已预留尝试也计入预算 |
| simulations | 3 | 真实评价尝试最多三次，不能超过候选上限 |
| model_calls | 18 | 包括模型请求失败和显式恢复重试 |
| max_tokens | 2048 | 每次模型回复的最大生成量 |
| max_input_bytes | 60000 | 每次请求 JSON 的 UTF-8 字节上限，超限停止 |
| model_failure_retries | 1 | 整次任务最多一次模型请求失败后的显式恢复重试；无后台反复重试 |
| computation_retries | 0 | 默认不重新计算失败候选；可配置为 1，仍计入三次评价总预算 |
| tool_calls / decisions | 24 / 24 | 工具尝试及决策总上限；拒绝请求也计决策 |
| timeout_s / tool_timeout_s | 90 / 180 秒 | 单次 HTTP / 单次计算或观察工具上限 |

一次完整候选评价预扣 1 次仿真、3 次 MATLAB 数学调用：M0 工作空间、M1 PCC 规划和 PCC 形状。前置硬门控失败可能只实际执行部分调用；预留不退还，实际次数从原 trace 核对。模型版本查询和会话启动另有记录。创建候选、检查、比较和轨迹回放不执行动力学。

## 模型能读到和能修改什么

初始上下文从原 TaskContract、任务、环境和探索 envelope 读取，并保存到 `inputs/task_context.json`。模型收到实际目标位置、容许误差、环境/重力、固定设计字段、可改字段的范围和关系约束、工具描述、候选历史、真实评价、拒绝原因和剩余预算。没有维护第二份目标或评分阈值。

权威范围来自 `capabilities/robot_families/tendon_driven_continuum/envelope.yaml`：长度 0.05–0.80 m、腱索布置半径 0.002–0.018 m、腱索数量 3–8，且布置半径小于截面半径。其余设计字段保持初始值；控制固定 C1，物理仍为未标定 surrogate。运行生成的 `inputs/experiment.yaml` 只是原授权的子集，仍由既有 ExperimentPolicy 校验。

模型可调用：

1. `check_candidate(candidate_id)`：指定候选独立检查和 IR / PCC 局部分析。
2. `evaluate_candidate(candidate_id)`：指定候选必须已有自己的通过检查；原 Harness 完成数学分析、控制生成、编译、仿真、评价和诊断。
3. `create_candidate(parent_id, changes)`：仅在最新候选已有本轮评价后创建，必须引用该评价结果；只接受允许字段的实际变化，不接受重复设计。
4. `compare_candidates(candidate_ids)`：比较已有真实成绩，不能把未执行或历史成绩混进来。
5. `observe_candidate(candidate_id)`：从该候选保存轨迹导出 GIF / PNG。
6. `read_evidence(evidence_id)`：读取已登记 JSON。`stop_design` / `capability_missing` 结束运行。

每个原生工具调用还必须提供 `reason` 和 `evidence`。父候选检查不能解锁子候选评价；缓存包含候选编号、参数哈希、对应检查与输入身份。后续设计由模型在收到评价之后提出，生产代码没有固定参数序列、运行时编程助手或第二个决策模型。

## 中文观察与证据

在另一个终端运行：

```powershell
python examples/workbench.py observe runs/deepseek_design
```

打开 <http://127.0.0.1:8765>。页面每 5 秒刷新当前阶段、模型动作与依据、候选参数变化、检查/计算状态、实际误差、预算和停止原因。可打开每个候选的原运行、评价、诊断、轨迹动画和曲线。任务结束也可直接打开目录内 `index.html`。

查看本轮已经完成的新计算，不启动仿真：

```powershell
python examples/workbench.py observe runs/round6_compute
```

保存结构继续沿用第五轮：`request.json` 和源码快照定位版本；`state.json` 保存候选、调用预算与决策；`model_calls/*/request.json`、`response.json` 保存无密钥的真实 API 请求和响应；工具反馈以原 tool_call_id 返回模型，拒绝原因也返回。`attempts/*/execution/<run_id>/` 保存原 Harness 的完整证据；`design_report.json` 从真实评价记录生成最佳候选和达标状态，不采信模型自报分数。

`live_model_feedback_modifications` 只统计官方模型响应引起的候选修改；`live_model_feedback_loop_verified` 还要求修改后的候选完成本轮真实评价。开发测试回复不计入这个标志。`NOT_RUN`、本轮新计算与第五轮历史回放分别标记。

## 暂停、恢复和错误

`--steps N` 可在若干决策后暂停；使用 `resume` 接着处理。计算、API 调用均在开始前持久扣预算。Ctrl+C 或异常后，已封存结果可接纳；没有完成证据的尝试记为中断，不返还预算。API 响应与决策序号在工具执行前保存，恢复不会重复执行已经提交的模型动作。进程锁阻止同时接管同一运行。停止后的工作台不会重开，参数或软件版本变化也不能混合恢复。

`WAITING_MODEL_RETRY` 表示网络或接口调用失败：核对密钥、账户/API 状态或网络后，再用同一 resume 命令消耗剩余重试。达到失败上限即停止。没有密钥不会消耗重试。

第五轮的字符错误实际为 Windows 拒绝创建 MATLAB 进程，本地编码错误又被 Engine 当成 UTF-8 解码。本轮保留原失败证据，新增可读的 `MATLAB_STARTUP_FAILED` 原始错误报告，并在允许启动 MATLAB 的环境完成真实评价。运行时应使用可正常启动本机已安装 MATLAB 的终端；代码不绕过操作系统权限、不自动提权，也不静默替换成伪计算。

## 主要文件

| 文件 | 职责 |
| --- | --- |
| examples/workbench.py | 启动、观察、上下文读取及恢复 |
| configs/deepseek.yaml | 单模型与调用预算配置，不含密钥 |
| configs/prompts/design_system.md | 集中管理中文决策提示词 |
| schemas/workbench.py | 模型配置、决策和工具参数合同 |
| tools/deepseek_adapter.py | 官方 HTTP、原生工具往返、调用预算及恢复 |
| tools/workbench.py | 原执行器：权限、候选绑定、缓存、锁与持久状态 |
| tools/design_session.py | 权威任务上下文、候选谱系、范围与反馈检查、最终成绩 |
| tools/design_actions.py | 候选检查、原 Harness 评价、比较及观察适配 |
| tools/workbench_catalog.py | 统一工具 Schema、前置条件、成本与说明 |
| tools/workbench_view.py | 中文候选表、模型阶段、成绩与证据链接 |
| tools/matlab_tools.py | 原数学工具及启动错误的正确显示 |

尚未完成真实模型联调，因为没有密钥。填写密钥即可继续验证；不承诺任何模型一定能提出更优设计或达到一厘米精度。已恢复的真实计算和具体次数见[本轮结果](round6_result.md)。
