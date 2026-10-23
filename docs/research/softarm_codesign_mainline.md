# 软臂结构—控制联合设计主线

2026-10-23，Asia/Shanghai。推荐共同基线：`mainline/softarm-codesign`，
worktree：`.worktrees/mainline-softarm-codesign`。本轮是集成与工程验证，未启动正式 Study。

## 集成与职责

S137.1 `4fe9f9e0` 为基线；S138 `fc509271`、S139 `3e4694a8` 均以保留历史的
merge 集成，S135 `dcbca1b3` 能力仍在祖先链中。合并提交为 `316cb8ca`、
`3ccca4ea`；生产精简和时间网格回归为 `d2cbdaa8`。未修改旧 main、源开发分支、
冻结 F3、原 Store 或已封存实验；未 force push 或 rebase。

任务规范 → 结构候选 → 数学分析 → Agent 决策 → 控制优化 → 物理执行 →
独立评价 → 后续修改。仍使用 `python -m tools.research`，没有新增 CLI、
orchestrator、配置系统、Registry、Store 或科研 Agent。

| 生产入口 | 权威职责 |
| --- | --- |
| `tools/research/config.resolve` | 仅新配置解析源文件并冻结有效输入；旧 Study 使用已保存配置 |
| `tools/state_io.effective_input` | 轻量提取有效输入、input/configuration 包装和冻结快照；旧 config 导入兼容 |
| `tools/research_tasks.task_adapter` | 任务条件、参考、评价绑定、数学绑定、执行需求和组合验收 |
| `tools/research/design`、`generated_serial`、`family_space` | 已授权结构生成、维度、通道顺序、合法初态和物理结构 |
| `task_constraints`、`analysis`、`optimal_capability` | 方法准入、条件覆盖、局部模型、T1/T2/PATH 成本与证据 |
| `search`、`core.packet`、`research_context` | 条件违反量搜索、独立物理排名、Agent 的设计空间/控制/预算视图 |
| `gvs_profile`、`gvs_trajectory`、`gvs_nmpc` | 同一候选模型准备、三类参考、离线优化及合法闭环执行 |
| `scene`、`backends`、`physical_replay` | 物理场景与控制参考分离、真实位置/速度/张力/时钟、固定张力回放 |
| 注册 evaluator、`assemble_acceptance` | 独立任务评价与冻结组合协议；RL reward 无验收权 |

## 冲突修复与精简

- `generated_serial.checked_control(inp, *, execution=True)` 是唯一控制检查实现。
  `gvs_profile` 只转发，两个模块的 `checked_reach` 都保留浅别名。
  `mathematical_numerical` 显式使用 `execution=False`，保留结构、量纲、
  有界张力、初态、参考及算法适用性检查，仅放开物理路由/开发状态限制。
  数学准备不会自动添加 Study grant，也不解除正式调度的冻结授权。
- S137 的递归快照提取与 S139 的轻量导入合为一个无重依赖 helper。
  修复自动合并遗漏的条件视图局部 `plain` 导入；任务条件和评价绑定均保留。
- 合并 Tracking 的多条件排名与 Reach 的完整配置要求。
  NMPC 场景准备直接复用已检查的 control，消除同一调用内的第二次完整检查。
  搜索的重复参数判断直接比较已验证字典，删除每个比较重复生成的 digest。
- 固定张力回放按 duration/control_period/timestep 推导样本和子步数；移除固定
  36 样本与 20 子步假设。数学预测模型身份、时间戳、样本数和输出形状必须匹配；
  物理时长/周期/步长不能形成整数网格时明确拒绝。
- 保留候选/模型/任务/完整执行身份，以及 S139 独立物理场景身份；它们绑定不同
  科学实体。Store receipt、幂等恢复、冻结授权、预算、物理输入界、数值失败检测
  和独立评价均保留，没有新增 SHA 清单或第二份科研状态缓存。

S138 的 [structure_precheck.json](../../evidence/s138_task_conditioned/structure_precheck.json)
为约 3.97 MB 的可复现数组/中间结果，但仍被 `test_s138_research` 直接使用，
历史报告也直接链接，因此原样保留。稳定来源为
[S138 原提交](https://github.com/wran021004-gif/softrobot-agent/blob/fc509271b8ff03a3e83675483b1f919504fe8fda/evidence/s138_task_conditioned/structure_precheck.json)。
其结论仍是控制重优化有效、未显示结构增益。数学结构预检仍只有原入口：
`python -m tests.research.s138_structure_precheck --output runs/<新文件>.json`。
S135 的一次性物理 runner 与该数学预检职责不同，保留用于历史复现。
本轮临时验证脚本留在忽略的 runs，并随验证归档保存，不新增生产执行平台。

## 方法边界

- Reach/Untimed/Timed 的真实生成结构在相同结构、初态与张力顺序下给出一致的
  A/B/C/D/drift/x0/u0；使用真实 GVS/CasADi 验证。
- Reach 保持原终端、保持窗口和绝对速度限值；Untimed 没有隐含 deadline；
  Timed 仅支持离线参考，物理与 RL 路由仍拒绝。SoRoSim 的现有准备器仍需常量目标。
- T1/T2 按模型、条件、冻结授权和预算准入；PATH 内部多分支费用保留。
  21 点两段路径 T1=20（1 次模型准备 + 19 次内部求解）；T2 单/双步长=59/99
  （包含 dual-face 尝试，匹配结构模型准备另计）。
  自由进度代理并不覆盖独立几何评价的全部五项条件，`full_task_supported=false`。
- 可用 NMPC 计划不代表收敛，完整物理执行不代表任务通过。
  线性化、Gramian、局部敏感度与数值见证不证明全局可行性或结构改进。

## 验证

61 个不同的定向测试最终通过，包含 3 个新集成测试；分批执行，没有跑全套。
覆盖 S137 条件/配置/授权、S138 数学准备/成本/搜索、S139 场景/速度/评价、
S135 三类参考真实离线 IPOPT、数学准入、Tracking 数学和搜索恢复。
详见 [validation.json](../../evidence/softarm_codesign/validation.json)。
初轮环境问题为新 worktree 尚无 runs、测试模块拼写及科研解释器缺 gymnasium；
创建本地 runs、纠正命令并复用现有 `.s135-env` 后相关测试通过，未安装依赖。
已有 CLARABEL 合成用例精度 warning 保留，不升级为严格最优性证据。

S138 报告的三项 mixed-search 旧失败逐项复现：历史配置哈希、
`runtime_unresolved`/`runtime_unavailable` 断言、校准环境保护的检查次序；
失败内容与源报告一致，未改历史哈希、保护逻辑或标为通过。
原轻量 `.rl-pilot-env` 完成 Reach XML/reset/109 维观测，未导入 Pydantic、
CasADi、科研 config 或 Store；物理步数 0。

历史 [Reach/Tracking 重算](../../evidence/softarm_codesign/historical_recheck.json)
均与原始信号得到相同指标和验收组件，结论仍为 `valid_failure`。
Reach 原 35/35 计划可用、700 步；末端误差 3.120 mm、保持误差 3.139 mm 达标，
保持速度 23.210 mm/s 超过 20 mm/s。35 次均为 `Maximum_Iterations_Exceeded`。
只读提取原 Store 并新增 [便携评价归档](../../evidence/softarm_codesign/historical_reach_evaluation.zip)，
没有重跑 Reach。重算 evaluator 自身不复制原 Host 的 execution ID 元数据，
来源记录单独保留；指标、组件和验收结论不变。

新的 [固定张力回放](../../evidence/softarm_codesign/fixed_tension_summary.json)
使用原两段六腱结构、Untimed Tracking 几何、合法零初态与候选预张力。
控制/采样周期 0.01 s、物理步长 0.001 s，共 40 个区间、400 个真实步，完整。
真实初末状态、实际张力、Jacobian 速度、引擎时钟、BackendResult 和独立 evaluator
见 [原始归档](../../evidence/softarm_codesign/fixed_tension_evidence.zip)。
耗时 0.513 s；组合验收 `valid_failure`，无 NMPC 求解。

新的 [Untimed Tracking 闭环](../../evidence/softarm_codesign/tracking_summary.json)
完整执行 0.4 s、400 个真实步、20/20 个可用计划；20 次均为
`Maximum_Iterations_Exceeded`，迭代上限仍为 12，0 solver exception、0 张力越界。
实际张力范围 0.0000031–5.289 N。任务、结构、控制 recipe 与原 S135 输入相同，
仅 run ID 不同；真实位置序列与原归档逐值相同。路径/覆盖/起点/终点误差分别为
18.201/16.573/4.842/22.008 mm，均超出 4 mm；回退 1.920 mm 通过。
组合验收仍为 `valid_failure`。模拟工具耗时 149.125 s，平均完整控制更新 7.234 s，
不满足 0.02 s 实时周期。没有调参重跑或改变容差。

[闭环原始归档](../../evidence/softarm_codesign/tracking_evidence.zip) 包含实际 XML、
BackendResult、运动、真实末端速度、实际输入、20 份完整控制计划记录、共享问题定义、
求解状态、耗时及独立评价。已从归档重新调用 evaluator，验证指标/验收组件一致。
原始 Store 留在 `runs/codesign_development/tracking`，仅新增工程 Host，未创建正式 Study。

本轮预算共用 **2/3 次新物理启动、1/2 次完整 NMPC、800 个真实物理步**；
保留 1 次物理启动和 1 次 NMPC 额度，未使用。Provider、PPO、MATLAB、硬件与正式 Study
全部为 0。离线数值失败/迭代上限和三项历史回归失败均保留。
[验证记录](../../evidence/softarm_codesign/validation.json) 和
[一次性 driver 源码](../../evidence/softarm_codesign/validation_drivers.zip) 可追溯执行过程。

## 后续 Study 准备意见

当前已具备小规模开发型自主结构—控制研究的最低工具链能力：Agent 可在冻结授权内
选择结构候选、匹配任务的数学方法、控制调整和独立物理验证，再依据原验收决定继续或停止。
本轮未测新的 Provider 决策质量，未启动正式 Study。

可实际修改的变量由选定生成器和 Study 域共同限定：源相对段长、Young 模量、
截面站点尺寸；授权拓扑的腱路径/导向孔/张力参数；family v2 的段数、腱数、
逐段材料与截面、离散单元、极坐标跨段路径、角偏移及显式路由。
并非所有声明组合都可执行，必须通过几何、模型与数值运行准入；总长耦合等约束保留。
控制 recipe 可在冻结域内调整；任务阈值和评价协议不由 Agent 放宽。

数学工具可以按任务条件比较结构作用，区分固定控制与重新优化的响应；
现有 S138 预检未发现可归因的结构收益。下一次研究应预先固定可表达条件和比较协议，
同时保留未覆盖的独立评价项。最多三项实质限制：

1. PATH 代理与完整几何验收仍有覆盖缺口，不能据代理通过授予完整任务支持。
2. 当前真实 Reach/Tracking 验收失败且 IPOPT 未收敛；模型—物理偏差、控制表现和
   结构收益尚需明确区分，没有实时性、鲁棒性或硬件证据。
3. 正式 Study 仍需独立审核任务、冻结设计/方法 grant 和预算；本轮工程授权不能转用。

## 交付

`mainline/softarm-codesign` 已按普通 push 发布至 `origin/mainline/softarm-codesign`；
最终验证和文档由本报告所在提交交付（`git log -1 -- docs/research/softarm_codesign_mainline.md`）。
真实执行采用的代码提交为 `d2cbdaa8`，完整标识见 validation.json。
代码入口及模块说明已更新，后续从该主线继续，不合并旧 main。
