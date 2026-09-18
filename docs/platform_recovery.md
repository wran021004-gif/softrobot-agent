# 版本、证据、预算与恢复

## 持久路线与独立复核

`family.route_policy` 随 SessionInput 冻结。`state.route` 保存顺序节点、当前节点、下一步、选择理由/证据、结果引用和最终交付；原 Store 的 `route_node` 事件封存每次状态投影。没有单独工作流数据库。`platform route status/result` 只读；`resume` 使用原 Host 的 pending 请求/回执机制。已完成路线再次 resume 不发模型请求；没有封存的执行仍按 unknown 保留预留，不重演。预算/轮数等明确终止时，Host 可汇总最近一个有效搜索的最佳候选，明确标为宿主收尾，不冒充新模型决定。

`route.advance` 的子会话带原有 `parent_run_id`，每次内层求解同时检查项目、子会话、父路线额度。外层只计自己的工具调用，求解/评分/派生产物引用内层回执，不重复收取等待耗时。查看入口报告实际求解、评价、真实模型请求、诊断与视频次数。

公共 `extensions.tendon_family.crosscheck.crosscheck` 从来源 CandidateInput 形成复核快照，替换明确选择的另一后端，保留设计、任务、模型和控制；来源、完整规范输入与父路线决定新身份。相同输入复用会话和请求回执，改变 execution.json 的有效数值设置形成新的 `*-cc-<digest>` 会话。优化与复核共同调用 `ensure_session`，已有同名会话输入不一致时明确拒绝，不覆盖旧结果。

搜索层在请求求解前比较完整有效 SessionInput（包含实际设计、任务、控制、模型和数值条件），不同标签不再让相同配置重复求解。重复提案记录 `original_candidate`，保留原候选和评价归属；`proposals`、`distinct_candidates`、`actual_solves` 分开报告。恢复读取同一检查点；完整坐标巡回没有新配置时以 `no_new_candidate` 封存停止。现有仿真缓存规则保持原样。

## 存储及费用

每个项目有自己的 `platform.sqlite`，授权路径由 `runs/.platform_authorities.sqlite` 绑定。复制项目目录可以只读查询，但不能在复制位置继续执行；同一 grant 不能重新绑定到另一路径获取额度。二者都是本地可信宿主状态，不能防止有权限的人整体替换数据库，不是身份认证服务。

SQLite 的 `BEGIN IMMEDIATE` 事务将项目／会话额度检查、原子预留和事件一起提交。事务表管理工具调用、真实模型请求、数值求解、工作者与实际耗时；排他资源按声明容量检查。离线模型回复、合成参考执行和真实后端分别计数。

成功或明确失败后按实际耗时结算，调用和求解次数不退款。实际耗时可能超过协作式超时声明；账本照实记录，不宣称覆盖未受控的外部启动时间。未知中断保留整个预留及仍未确认释放的资源。不能同时把未知额度退款并自动重做昂贵操作。

## 请求重试与结果复用

| 情形 | 身份与行为 |
| --- | --- |
| 相同 request_id、同参数、同调用者 | 返回同一 execution_id 和已封存回执；不再次收费或执行 |
| 相同 request_id 改参数／调用者 | REQUEST_ID_COLLISION |
| 新 request_id、cache=reuse | 输入、版本及实际依赖匹配时复用不可变输出；工具调用收费，新求解为零 |
| 新 request_id、cache=new | 用户显式要求新计算，产生新执行身份并按新计算预留 |

评价是显式操作，工具缓存默认关闭；新的评价请求形成新事件和执行身份，原轨迹不变。相同评价内容可以共用内容摘要，但评价的执行身份分别保留。

`simulation.run` 已声明开启缓存；`ToolRequest.cache` 默认是 `reuse`，也可显式填写。复用范围为同一会话、同一候选名、相同规范参数及证据引用、冻结输入／种子、精确版本与实际依赖。预检仍构建和检查本次有效输入，并核对原始 `candidate_input` 完全一致；`cache=new` 或影响计算的参数变化进入正常后端执行。

仅选择有已完成封存回执的原始计算，排除缓存读取记录及 failed/cancelled/unknown 求解结果。仿真 `solver_status=completed` 但随后评价 `task_success=false` 的有效轨迹仍可复用。缺少必要原始来源的旧结果不命中；旧证据保持不变，读取和兼容性检查仍遵守既有边界。

每次新请求复用保留独立 `request_id` 和 `execution_id`；回执 `cache_hit=true`，`original_execution_id` 直接指向原始求解调用，不形成缓存链。原始回执该字段指向自身。`state.result_executions[execution_id]` 保存本次请求、候选、有效输入引用和原始执行；`result_provenance` 事件的输出是不可变来源记录。来源随完成事务持久保存，重新打开同路径会话仍可查询。

评价调用传入 `result=本次回执.output` 和 `execution_id=本次回执.execution_id`。评价结果 `source_execution_id` 是所选调用，`original_execution_id` 是实际产生轨迹的调用；通过来源记录的 `candidate_input` 读取有效输入。多个调用共享同一结果时必须显式选执行身份。导出轨迹及文件仍归原始执行，可通过原始 execution_id 的 simulation 事件读取；复用不复制轨迹或创建后端工作目录。

缓存命中预留、结算本次 `tool_calls=1` 与实际处理耗时，`backend_solves=0`，资源列表为空，不占求解器槽位。正常仿真仍使用原共同账本。相同请求重试则直接返回原封存回执：其中 charged 表示原调用费用，不是本次重试新增费用，也不新增执行或事件。

## 原子性边界

- 输出字节、回执、费用和相关事件存入同一 SQLite 提交时，可按请求身份完整恢复。
- 仿真来源登记（正常执行与复用）、不可变来源事件也随完成事务一起提交。后端已导出但尚未封存时不登记为可复用成功，仍按 unknown 处理。
- 有效工具请求原文（参数、理由、证据及精确版本）也按内容身份保存，预留与拒绝事件均引用它，避免只有不可读的请求摘要。
- 后端工作目录／视频文件／技能版本文件不是 SQLite 的一部分。它们不是多文件事务；输出可能已完成而回执尚未提交。
- 没有封存回执的工具请求标为 unknown；原额度保留，不自动重演。人工应检查导出、日志与外部进程，决定新运行或实现版本化对账，不能伪造完成。
- 工作者有 `output.json` 或 `failure.json` 后，由 collect 显式检查并结算；只读 status 不结算。没有可靠进程句柄和封存输出时保留 unknown。取消只能确认当前宿主持有句柄的本地工作者已终止。
- 主会话模型保存 pending 决定后再调用工具；恢复再次使用相同请求身份，不重复评价或合并。若模型请求本身未知，不自动重发 API。

## 版本与缓存

公共基线版本是 `1.0.0`。当前采用精确版本匹配；新增兼容版本也必须显式登记或编写迁移器，不接受宽泛通配或猜字段。不兼容版本使用新会话；旧运行只读保留。

快照同时记录 Git 提交和实际计算依赖。缓存包含输入、任务实例、种子、契约 Schema、实现版本、声明源码／资产及运行环境。已界定闭包的数学扩展只记录相关文件；未可靠界定传递依赖的适配保守记录源码／配置树并注明原因。`docs/` 不在计算依赖中，纯文档修改不会导致全局重算。声明 sources 的开发者负责完整列出传递依赖；遗漏依赖不能借缓存掩盖。

## 历史入口与迁移检查

```powershell
python examples/workbench.py platform history runs/round9_reach
python examples/workbench.py platform compatibility runs/my_platform signal-hold
python examples/workbench.py platform resume runs/my_platform signal-hold
```

history 校验已有数值证据，单独列出旧 state／budget／working_memory 可变文件；不修补历史字段、不触发求解、不消费旧预算。旧 dynamic / workbench 命令仍使用其原 `source/runtime` 检查。平台接口升级不解除原检查。

当前没有自动迁移已执行任务科学语义、未知外部副作用或授权锚点的工具。检查失败时建立明确新版本与新配置，或由集成者交付可审查迁移器；不能改写旧身份来“恢复成功”。
