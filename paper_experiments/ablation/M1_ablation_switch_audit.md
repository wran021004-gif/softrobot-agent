# M1 控制消融配置与能力开关审查

日期：2026-11-11。结论：**现有接口不足以表达两组严格独立的消融，暂不进入 M1 Pilot。** 本轮只完成离线解析、代码审查及 Mock 测试，没有启动 Study、Main、Provider、数学 Worker、优化或 MuJoCo。

Native T1 可以撤销独立授权；Direct 没有同等的方法级配置门禁。去掉整个 `analysis` 能同时关闭两者，并保留普通初始化、physical_response 和独立 Replay，但还会关闭其他数学分析，是范围更宽的替代方案。`physical_response` 没有独立开关，关闭其共享权限会同时破坏必要初始化及显式控制 Replay。因此没有将这些替代方案写成两个符合本次严格要求的 JSON。

## 1. 审查对象和冻结基线

| 对象 | 本轮实际使用的来源 |
|---|---|
| 文档提交仓库 | `D:\softrobot-agent`；开始时分支 `feat/gvs-dynamics`，HEAD `d629a80d0027209ef6d41d65fdb69b168727bff7` |
| 新文档/测试分支 | `codex/m1-ablation-switch-audit-20261111` |
| Full 实际执行代码 | `D:\softrobot-agent\.worktrees\core-temporal-resolution-20261111`，Core commit `7f034a60f1ea0be5ac3174c5b6c8908a8f56dd40`，只读审查 |
| Full 配置来源 | `paper_experiments/configs/m1_core_full_v1/study_m1_core_full_v1.json` 及同目录 defaults、FamilySpace、三任务和 runtime 引用 |
| 最终授权摘要 | `paper_experiments/m1_study_manifest.json`；Provider 上限 73，Native 结点上限 30，数学评价 16、物理评价 18 |
| 既有案例 | [Phase 0 的 M1 Full](https://github.com/wran021004-gif/softrobot-agent/blob/6a1e8ea21ee454b9f693361f460f2decb259f78e/paper_experiments/full_results/M1_full_results.md) 和 [能力盘点](https://github.com/wran021004-gif/softrobot-agent/blob/6a1e8ea21ee454b9f693361f460f2decb259f78e/paper_experiments/full_results/analysis_capability_inventory.md) |

原研究仓库当前代码树不是本次 M1 的独立 Core。测试显式从上述 Core 导入，避免误测旧研究仓库里的同名模块。原 Full 叶配置仍记载启动时的 48 次和 4 结点；测试只在内存中结合已有最终授权，将这两项规范化为 73 和 30，并绑定最终 Core 提交，未改写历史文件或 Store，也未给予新实验运行授权。

共同科学条件必须保留：同一两段六腱 FamilySpace、零关节初态、原重力与 10 g 载荷、原物理模型、三目标任务。目标依次为 `[0.285,0.035,0.185]`、`[0.275,-0.040,0.135]`、`[0.295,0,0.215]` m；位置阈值 0.01 m，最后 0.06 s 保持速度阈值 0.03 m/s。时长 0.6 s、物理步长 0.001 s、控制/采样周期 0.02 s，每条件独立合法控制，最终同结构联合 SELECT。Knowledge、Provider、预算/保留额度策略及原评价协议不作为消融因素。

## 2. 两个实验定义

No-Model-Based-Control：关闭 Native 非线性控制研究与 Direct 控制搜索，保留局部物理探针、普通控制初始化、结构生成、任务评价、独立 Replay、联合 SELECT。检验缺少模型驱动控制搜索时能否依靠局部物理实验完成三目标。

No-Physical-Probe：关闭 `initialize_control(method=physical_response)` 及等价的自动探针入口，保留 Native、Direct、普通初始化、结构生成和相同评价链路。检验缺少局部物理探针时模型驱动搜索能否完成三目标。两组分别运行，不能同时关闭两类能力。

下表是**要求的实验能力矩阵**，不是声称当前已有两份配置通过验证：

| Capability | Full | No-Model-Based-Control | No-Physical-Probe |
|---|---|---|---|
| Native | ON | OFF | ON |
| Direct | ON | OFF | ON |
| Physical Probe | ON | ON | OFF |
| Task Evaluator | ON | ON | ON |
| Physical Replay | ON | ON | ON |
| Joint SELECT | ON | ON | ON |

## 3. 真实调用路径

以下代码位置均属于上述冻结 Core，行号按本轮只读版本记录；可在本地 checkout 直接核对。

### Native 与 Direct

```text
research_analysis
  → agent.py:1021 的工具 handler（科学问题编译 / 原始请求绑定）
  → analysis.dispatch                       analysis.py:342
  → 方法授权、analysis 能力、额度/源/候选等准入
  → 数学 Worker → analysis.calculate         analysis.py:58
  → native_analysis.calculate                native_analysis.py:168
  → native_control.calculate                 native_control.py:calculate
```

Native 的请求 operation 为 `mujoco_nonlinear_task_capability_v1`，授权 key 为 `mujoco-nonlinear-task-capability-v1`；二者不同。`nonlinear_capability.py:18` 的 `METHODS` 只映射 T1、T2；`analysis.py:369` 据此检查冻结方法授权。删除 T1 key 后，原始请求返回 `EXPLICIT_FROZEN_MATHEMATICAL_METHOD_AUTHORIZATION_REQUIRED`，在候选准备和 Worker 前停止。

Direct 的 operation 为 `mujoco_direct_control_v1`。它没有进入上述 `METHODS` 映射，仍可经过通用 `analysis` 准入调用相同 Native 控制内核。`config.py:287` 的方法 key 白名单也不接受 Direct。因此删除 T1 授权不会关闭 Direct，添加一个臆造的 Direct 开关则解析失败。

`agent.py:1395` 在没有 `analysis` 时移除展示给 Main 的 `research_analysis`；更关键的是 `analysis.py:380` 对原始调用另有 `ANALYSIS_CAPABILITY_REQUIRED` 拒绝，不能仅凭工具是否可见判断能力已关闭。该拒绝发生在 `verify_candidate` 和科学执行前。

### 普通初始化与局部物理探针

```text
research_plan(action=initialize_control)
  → core._dispatch                          core.py:648
  → allowed_plan_actions + control_correction 检查  core.py:686
  → seed_control                            physical_replay.py:127
      baseline → _seed_control               physical_replay.py:145
      mathematical_response / physical_response
               → guided_seed                physical_replay.py:288
      capability_sequence → capability_seed
```

`contracts.py:938` 固定接受四种方法；现有配置没有方法白名单。`seed_control` 以方法名分派，没有读取探针专属授权。

`guided_seed` 的 physical 分支会创建/绑定基线，对通道逐一施加有限张力偏移，经 `evaluate_schedule`（`physical_replay.py:68`）调用 `core.dispatch(action=physical_replay)`，再进入真实独立评价。若某探针先通过原任务则提前返回，否则可能构造局部响应拟合。该方法会消耗真实物理预算，不是纯初始化。

普通 `baseline` 则只准备合法时序，可使用候选 pretension、显式 tensions 或合法已有 source；它不要求 Native 优化先成功。

## 4. 七项接口结论

| 问题 | 当前结论 | 代码依据 / 限制 |
|---|---|---|
| Native 可否单独禁用？ | **可以撤销 T1 方法授权** | 删除 T1 key，保留其他现有合法方法条目；原始 dispatch 也拒绝。Full 本来不允许家族 search action |
| Direct 可否单独禁用？ | **不能通过当前方法级配置实现** | Direct 不在冻结方法授权映射/配置白名单；analysis 开启时仍可用 |
| 两者可否同组同时关闭？ | **可以粗粒度关闭 `analysis`** | 保留 `control_correction`、`physical_replay` 即可阻止两类数学执行；但其他数学分析也关闭，不符合只移除两项能力的严格隔离 |
| physical_response 可否独立禁用？ | **不支持** | 方法枚举与分派没有配置级方法门禁 |
| 是否影响普通初始化？ | **现有粗粒度替代会影响** | 删除 `initialize_control` action 或 `control_correction` 均同时关闭 baseline，不能采用 |
| 是否影响必要任务评价？ | **关闭 analysis 本身不影响；关闭 control_correction 会影响** | 显式控制 Replay 另要求 `control_correction`，`physical_replay.py:525`；不能为禁探针而删除它 |
| 隐藏工具后能否间接调用？ | **可能，必须检查执行入口** | 删除 T1 不挡 Direct；探针 helper 内部可调用 Replay；初始化+显式时序+Replay 还能组合出探测行为 |

`mathematical_methods` 是授权说明字符串映射，不是任意 operation 的布尔字典；空字典和未知 key 不合法。`allowed_plan_actions` 只控制整个 action，不能控制 `initialize_control` 的子方法。`native_control_limits` 是次数、迭代和结点上限，不是方法禁用开关。不能用改为零预算替代消融开关，因为那会改变共同预算策略。

## 5. 配置差异设计与交付状态

| 项目 | No-Model-Based-Control | No-Physical-Probe |
|---|---|---|
| 严格目标差异 | 仅 Native、Direct 执行权限 OFF | 仅 physical_response/等价自动探针权限 OFF |
| 现有可表达的最近替代 | `capabilities` 去掉 `analysis` | 去掉整个初始化 action 或 `control_correction` |
| 不可接受的额外影响 | 结构机制、其他数学诊断也被关闭 | baseline 被关闭；去掉 control_correction 还阻止显式时序 Replay |
| 是否输出请求的有效 JSON | **未输出严格隔离配置** | **未输出：不存在独立配置开关** |

内存验证了 analysis-OFF 替代方案可以解析：有效 capabilities 为 `['control_correction','physical_replay']`，actions、任务、FamilySpace、物理配置、Knowledge、runtime、预算和 confirmation 均与规范化 Full 相同。它适合作为另一个更宽的 No-Analysis 设计参考，不冒充本次严格 No-Model-Based-Control。

本轮没有保存不存在的 `control_initialization_methods` 等字段。负向解析测试仅在 Mock 内存输入中使用一个未知字段，以确认现有 loader 会拒绝它。没有创建无效的 `ablation_m1_no_model_based_control.json` 或 `ablation_m1_no_physical_probe.json`。

另外，loader 要求 FamilySpace 模式的 defaults 与叶配置同目录（`config.py:314`），引用资源也有各自目录约束。未来将配置放入建议的 `configs/research/` 时，需要安排合法的现有依赖引用；直接将历史叶文件移动后改相对路径，不等于继承已验证。此次未扩充或复制整套历史资源。

## 6. 最终评价链路

```text
baseline / 明确合法控制 source
  → research_plan(physical_replay)
  → physical_replay.dispatch                 physical_replay.py:482
  → 真实独立物理执行（本轮不执行）
  → evaluate_playback                        physical_replay.py:633
  → 原任务注册 Evaluator                     physical_replay.py:681
  → 绑定原任务的结果、profile、acceptance certificate
  → 三条件公开读取与 joint_assessment         conditions.py:84
  → core select / register_joint_result       core.py:849、conditions.py:159
```

Evaluator 仍从冻结任务的 evaluator binding 解析。Replay 的门禁是 `physical_replay`，显式控制 source 还要求 `control_correction`；不依赖 `analysis` 或 T1 方法授权。数学最优结果不是 Replay 的必要输入，显式合法初始化也可提供控制。

联合选择检查三条件完整独立结果、同结构/离散/物理模型、原始来源与执行收据、原验收证书和公开读取；没有新增数学优化。`core.py:762` 将 SELECT 标为无执行/数值预约的选择操作。禁探针的正确实现不应改动以上任一链路，也不能改 Evaluator 阈值。由于探针专属开关尚不存在，本轮不能声称第二份配置已实现这条保留链路。

### 间接和等价入口的范围

Full 未允许 `search`、`control_search`、`execute` 或 RL，因此不能把这些路径自动开放给消融组。主动家族 Native search 另有 T1、analysis、search 等授权检查（`search.py:51`、`config.py:704`）。科学问题接口最终仍回到 `analysis.dispatch`，不是另一项执行授权。

目前只发现一个公开初始化方法将局部物理响应自动组织成探针：`physical_response → guided_seed → evaluate_schedule`。数学输入响应初始化读取已有证据；Native/Direct 自身的有限差分和 rollout 属于保留的模型驱动控制研究，不应为禁探针而一并关闭。

但保留 `baseline(tensions_n=...)` 和独立 Replay，就允许 Main 自行提交微小偏移的时序再评价，从而组合出类似物理实验。**仅隐藏 helper 或限制方法枚举无法保证语义上“完全没有局部物理探测”。** 后续需明确是移除自动探针能力，还是禁止所有自组织探针行为；后者需要额外实验协议和可审查的准入边界，不能声称一个方法开关已经解决。本轮不增加行为分类器或通用防御框架。

## 7. 最小离线验证

测试文件：`tests/test_m1_ablation_switch_audit.py`。8 项测试全部通过，范围如下：

| 测试 | 实际结果与边界 |
|---|---|
| Full 来源、继承、三条件解析 | 通过；读取已有本地来源，内存规范化最终授权；没有新 Study |
| 删除 Native T1 授权 | 原始请求在计算前拒绝；Direct 仍到达候选准入边界，证明并未禁用 |
| 将 Direct 当现有方法 grant | loader 拒绝，证明不能伪造现有配置开关 |
| 去掉 analysis 的粗粒度方案 | 解析通过；Native/Direct 原始请求都在候选/Worker 前被现有门禁拒绝；共同配置相等，原 Evaluator 可解析 |
| baseline / physical_response 分派 | 分别到达 Mock 的普通初始化/探针委托，证明当前没有方法级拒绝；没有实际准备控制或执行探针 |
| 伪造探针方法白名单 | loader 拒绝 UNKNOWN_CONFIGURATION_FIELD；未写 JSON |
| analysis-OFF 的显式控制 Replay | 经过实际 Replay 能力与 source 检查，在 Mock 的物理实验预检边界主动停止；没有 Worker |
| 联合 SELECT 的资格入口 | Full 和 analysis-OFF 均委托既有 joint_assessment；下游收据评估为 Mock，不是新的通过证据 |

测试阻止子进程、网络连接和 MuJoCo 导入；没有实例化 Host、Store、Agent，没有访问凭据正文。有效方法的测试在最早的必要边界用 Mock 停止，并未声称完成真实执行或科学验收。没有运行全量套件。

复现命令（显式依赖历史本地配置和冻结 Core，不是新运行配置）：

```powershell
$env:M1_AUDIT_CORE='D:\softrobot-agent\.worktrees\core-temporal-resolution-20261111'
$env:M1_AUDIT_FULL_CONFIG='D:\softrobot-agent\paper_experiments\configs\m1_core_full_v1\study_m1_core_full_v1.json'
$env:PYTHONDONTWRITEBYTECODE='1'
& 'D:\softrobot-agent\.f3-prestudy-env\Scripts\python.exe' tests/test_m1_ablation_switch_audit.py
```

用户要求的“两份有效配置解析/工具集合/原始禁用请求拒绝”验收目前为 **未满足**，不能用 8 个审查测试通过来替代这项结论。

## 8. 最小必要修改建议（仅建议，未实施）

1. **增加明确的细粒度执行权限。** 复用现有方法注册和权限机制，为 Direct 补齐与 Native 同等的冻结方法授权；同时为控制初始化增加方法级许可。配置 parser 必须真正识别、验证并冻结这些许可。缺省语义应兼容历史 Full，新的消融配置必须明确声明，不重新解释或改写旧 Store。
2. **在共同执行入口拒绝。** Native/Direct 在 `analysis.dispatch` 启动准备/Worker 前统一检查；初始化在 `seed_control` 产生条件克隆/基线之前检查，自动物理探针公共实现也复用同一许可，防止绕过展示层。无需改变控制搜索、拟合或物理算法。
3. **同步展示与准入。** `task_constraints`/科学问题的方法选择和 `agent.plan_schema` 的初始化方法枚举投影同一权限源。隐藏工具只改善可见性，不能替代服务端检查；不再另建工具注册框架。
4. **保留评价权限。** baseline、`control_correction`、`physical_replay`、Evaluator 和 SELECT 保持现有逻辑。不要用清零预算、关整个初始化或关物理后端实现方法级消融。
5. **补足同一小组离线测试。** 新开关获批实现后，用两份真实可解析配置验证目标矩阵及原始入口拒绝，同时验证普通初始化、Replay/SELECT 准入保留。当前测试不冒充这些尚未存在的通过结果。

具体字段名称和兼容方式需在获准修改接口后确定；本报告没有把未来设计写入当前 loader 不识别的 JSON。若仅接受 analysis-OFF 的更宽消融，则可不增加 Direct 开关，但应另行确认实验定义及其额外禁用范围。

## 9. Pilot 建议与提交范围

**暂不进入严格定义的 M1 Pilot。** No-Physical-Probe 缺少独立执行门禁；No-Model-Based-Control 只有会关闭其他数学分析的粗粒度实现。先确认最小权限接口修改，以及“等价探针”是指自动 helper 还是所有自组织实验，再完成两份配置的离线验收。

本轮仅提交本报告和 8 项离线审查测试。不修改历史 Full/P3、任务、生产算法或公开 Core；不增加任何运行授权。原研究仓库已有的环境、日志、Store 和其他未跟踪文件均不纳入提交。完成后停止，等待下一步安排。
