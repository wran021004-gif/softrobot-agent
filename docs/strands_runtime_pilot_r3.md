# Strands Harness R3 真实验证停止报告

**本轮 R3 未通过完整验收。** 真实请求记账、公共证据读取、框架摘要与外置、跨进程续接和精确原件取回已验证；正式决定没有通过业务校验，回执为空。达到授权的 40 次提供方尝试上限后停止，未创建新活动补额度，未从正文或草稿代写决定。

活动为 `strands-pilot-r3-20261009`，工作区 `D:\softrobot-agent\.worktrees\strands-pilot`，分支 `feat/strands-runtime-pilot`，起点 `c5b98d5e4efb5db3abc0320902b27b77772e2416`。准备从北京时间 2026-10-09 16:26:54 开始；原六小时期限为 22:26:54，模型发送截止为 21:56:54，未继承旧试点短期限。用户在外发风险说明后直接确认授权；此前两次自动审批拒绝发生在进程启动前，真实请求为零。

| 验收项 | 实际结果 |
|---|---|
| 真实发送边界和共用账本 | 40 次实际发送，40 份确认响应，0 个未知/在途尝试；包括 2 次摘要和所有纠正请求 |
| 实际请求配置 | `https://api.deepseek.com`、`deepseek-flash`、thinking enabled、reasoning effort high、32768 输出上限、600 秒超时均符合；工具选择为供应商默认 auto，未发送 required |
| 公共工具读取 | 通过 `Host.invoke` → `research.investigation_read` 读取三个既存 V1 原件及提取报告；61 次原生公共工具操作（包括失败），小于 512 |
| 框架摘要和外置 | 使用锁定版本公开 `Offload.summarize`、`Offload.truncate`，真实模型产生摘要，框架存储原件；没有预制摘要、人工替换历史或复制材料填满窗口 |
| 新进程续接 | 读取进程 PID 30304；摘要检查点 PID 26432 正常结束后，PID 32388 恢复相同活动、Strands 会话、账本和期限，发出 9 次真实请求 |
| 恢复历史字段 | 第一条恢复后普通请求含 52 个已配对工具结果 ID 和 23 个 assistant 思考字段；真实提供方接受请求 |
| 精确取回 | 恢复后 `retrieve_context` 取回联合验收原页及评价原页，逐对象等于先前公共证据接口输出，身份和精确数值保留 |
| 正式提交和唯一回执 | 7 次原生提交均被校验拒绝，业务效果为 0，回执两次查询均为空且不改变账本；不能把“相同空回执”写成提交防重成功 |
| 范围与职责退役 | 数学求解、机器人后端执行为 0；旧 Host 循环、历史拼装和工程恢复调度受运行边界禁止；旧 turn=0、model_notes=[]。R2 崩溃窗口防重证据原样保留，没有额外真实故障重演 |

供应商用量合计：输入 926,544，输出 60,129，总计 986,673 token；输出中的思考部分为 22,148 token，不能再加到输出/总计。逐次字段在原始响应与账本中保存。金额没有可靠账单依据，保持未知；40 次是请求次数上限，不是货币费用上限。Store 业务调用费用计入 27 次工具单位；61 次原生操作包含未进入业务预留的无效调用，由同一 Store 的派发事件计数约束 512 上限，二者含义不同。累计账本 wall_s 是请求/工具结算时间；整体六小时约束由准备开始的绝对期限执行。

## 科学判断与原件核对

| 项目 | 原件精确值 | 判定 |
|---|---|---|
| 到达 | 0.0031314437885609334 m，阈值 0.01 m | 通过 |
| 保持位置最大误差 | 0.0033622899352609014 m，阈值 0.01 m | 通过 |
| 保持最大速度 | 0.026817670846968282 m/s，阈值 0.02 m/s | 失败 |
| 联合结果 | `accepted=false`、`status=valid_failure` | 有效执行，但未联合达标 |

原始评价 `6314170…66892` 的 `/metrics/0/value`、保持报告 `400226…6ab13` 的 `/detail/sampled_settling`、联合记录 `558256…88627` 的 `/detail/components` 与 `/detail/status` 支持上述判断。原执行 `197bceb6ff8f44b48a35bc4f79b3528d`、候选 `fixed-radius`、原任务身份均保留。这些是既存 V1 记录，没有新机器人实验。独立审查认为模型初步正文的四项判断及这些引用正确；未通过的提交参数则存在对象/指针错误，两项结论分开报告。

原模型正文、思考、工具参数、工具反馈和 finish reason 均保留在 [raw_archive.json](../evidence/strands_runtime_pilot_r3_20261009/raw_archive.json) 及以 SHA-256 命名的 `.response.bin` 原始 JSON 响应文件中。**审查注释：**模型沿用了提取报告中的“live-model compatibility unassessed”。本轮已观察到锁定配置下的真实传输和续接兼容性；该表述不应被理解成“本轮没有真实模型调用”，也不意味着长期可靠性已证明。原回答没有被覆盖。

## 问题与本地修复

最初框架并发工具执行与既有 Host 文件锁冲突，造成部分 `PermissionError`，模型重复读取并尝试目录授权外的链接。读取阶段用了 29 次请求。之后改用框架公开的 `SequentialToolExecutor`，在可控传输下验证同一原生响应中的两次读均成功，再继续同一真实活动。发送截止曾被临时收紧以停止下一次发送；当时读取已结束，确认无在途请求后恢复到原绝对截止，没有延长原期限或重置预算。

恢复后的原件取回成功，但提交出现 `evidence_used` 超过原有 12 项、scope 不是 SourceFact 列表、把部分对象作为整对象值、错误 JSON pointer 等问题。原业务校验器返回具体反馈，模型纠正仍没有形成有效提交，最终耗尽 40 次请求。没有修改科学结论或缩减验证规则来强行通过。

耗尽之后，入口已改为直接向模型公布 `PrincipalDisposition` 完整原生 JSON schema，而非仅用泛型 `decision: dict` 和文字说明。该修复通过离线原生提交和 schema 检查，**未做新的真实模型验证**。它不能追溯改变本轮失败。最终增加了入口前预算检查和失败记录，避免耗尽后加载凭据/创建 agent 再尝试网络。

针对性检查：7 项真实边界替身测试及受影响的 A 场景通过；E 的框架外置/新进程恢复也通过。最后 schema 修复后仅重跑 7 项边界检查及 A（8 项），另对普通/摘要共享预算耗尽做了单项补查。没有启动完整测试套件或科学执行。见 [最终日志](../evidence/strands_runtime_pilot_r3_20261009/final_offline_checks.log)、[含 E 的前一轮日志](../evidence/strands_runtime_pilot_r3_20261009/offline_checks.log) 和 [验收观测](../evidence/strands_runtime_pilot_r3_20261009/acceptance.json)。

## 可运行命令与恢复边界

从试点工作区执行，继续使用原独立环境（依赖没有升级）：

```powershell
$pilotPython = 'D:\softrobot-agent\.pilot-env\Scripts\python.exe'
$r3Directory = 'runs/strands-pilot-r3-20261009'
$r3Evidence = 'evidence/strands_runtime_pilot_r3_20261009'
& $pilotPython -m tools.strands_pilot_r3 receipt --directory $r3Directory
& $pilotPython -m tools.strands_pilot_r3 audit --directory $r3Directory --evidence-directory $r3Evidence
& $pilotPython -m tools.strands_pilot_r3 export --directory $r3Directory --evidence-directory $r3Evidence
```

实际模型阶段为以下独立进程命令；它们是已执行链路的复现说明，当前活动已是 `stopped_budget`，继续发送会被拒绝。

```powershell
# 首次准备只执行一次。--started-unix 包含本轮实现前的准备时间。
& $pilotPython -m tools.strands_pilot_r3 prepare --directory $r3Directory --started-unix 1791534414
& $pilotPython -m tools.strands_pilot_r3 read --directory $r3Directory
& $pilotPython -m tools.strands_pilot_r3 checkpoint --directory $r3Directory --feedback 'The local Host lock issue is repaired using the framework sequential tool executor. The three permitted originals and extraction report have already been read; do not repeat failed or out-of-scope reads. Finish only a compact progress note for the planned restart, identifying an offloaded read_original reference key for exact retrieval after restart and the native submission work remaining. Do not submit yet. The framework performs its own summarization and saves this same conversation.'
# 上一进程结束后，再以新进程恢复同一会话。
& $pilotPython -m tools.strands_pilot_r3 resume --directory $r3Directory
```

`prepare` 对已存在目录拒绝重新创建；`resume` 不创建活动、不导入整段旧对话。已确认但未完成 SDK 转换的响应，使用同阶段命令加 `--recover-response`，由 Strands 恢复保存的会话并在相同请求处重放已保存字节，不增加付费尝试。若请求不相同，则阻止发送并保留原响应。无确认响应的尝试保持 unknown、预留与占用，阻止后续普通和摘要请求。这些异常恢复边界仅通过可控传输验证；真实运行只验证已保存检查点后的计划中断，未验证真实在途崩溃自动恢复。

上下文配置使用公开阈值：真实工具页超过 400 个框架估算 token 时外置、预览 64；检查点阶段 user/assistant 摘要阈值 150/400，保留最近一条。恢复阶段为 2000/2000，避免短摘要被每轮再摘要，同时让较长的初步正文由实际模型摘要。框架的估算值不是供应商实际 token 数；供应商实际用量以响应为准。

当前活动不能完成剩余正式提交：模型额度已耗尽。没有自动开始新活动、R4、V2 或机器人实验。后续如另行授权新的验证，需单独决定；本轮不申请或自行增加额度。
