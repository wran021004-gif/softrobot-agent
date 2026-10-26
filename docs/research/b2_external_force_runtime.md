# B2 外力执行接口（B1）

2026-10-26，Asia/Shanghai。基线 `research/mujoco-native-task-sensitivity@618fba9a11a1a1d0c9fca5228d25e873b7c8dddd`；独立 worktree `.worktrees/b2-load-force-runtime`，分支 `feat/b2-load-force-runtime`。未修改 A 线或 C 线工作区。

**Native 与独立 MuJoCo 张力回放已具备一致且可复核的定时质心外力执行能力。** 非零外力完整 36 个采样的位置/速度数组完全相同；原任务评价仍为有效失败。本结果不证明 B2 可行或结构变化有优势。

## 物理语义及最小修改

沿用 `task.environment.data.external_forces` 的既有 `TimedForce`，经 `assemble_physical` 冻结到 `scene['forces']`，不增加另一套输入 Schema。语义版本 `world_body_com_force_v1`：

- 在已命名机器人 body 的**质心**施加恒定世界向量 `force_n`，单位 N；不是 `tip_site` 点载荷。
- 窗口 `[start_s,end_s)`，边界在控制网格上且位于任务时域内。
- 每个实际 `mj_step` 前按子步起点刷新世界力；重叠力相加，窗口外清零。整数积分 tick 消除累计时间舍入造成的边界错位。
- `xfrc_applied[:3]` 为世界力，后三项为关于 body COM 的零力偶；广义力为 `J_com.T @ F`，自然产生关节力矩。同一子步内保持该世界力。
- 不实现附加物件质量/惯量、抓取接触、局部坐标力、tip 点载荷或复杂时变力；不支持的形式由原 schema / 适用性入口明确拒绝。

`scene.py` 保存语义；`backends.py` 的普通后端和 `playback_tensions` 共用绑定及施力函数。`mujoco_analysis.py` 接通初始化、restore、reconstruct、rollout、rollout_sequence；每次 forward 也按当前时间重建冻结外力。restore 拒绝额外 `qfrc_applied`，`xfrc_applied` 由冻结场景拥有；reconstruct 校验前缀外力、初态和网格。

`native_analysis.py` 接通原适用性检查并更新力平衡解释，`native_control.py` 仍使用原搜索器，所有候选克隆同一积分初态并使用同一冻结外力。力学输出单列 body 外力的广义力及末端加速度贡献，原 `qfrc_applied` 不改义。`physical_replay.py` 的原 model_context / binding 已能保留同一任务外力，零积分实测通过，无需新增传参接口。

绝对张力、ZOH、初态、控制/采样网格、原 evaluator 与复合验收均保留。接触、约束、非有限状态及引擎失败语义保留；未删除碰撞体/地面，未修改积分器或放宽物理参数。成功返回积分数与尝试数分别记录；失败调用内部部分进度仍为 unknown。

## 工程验证与真实结果

复用已有中性两段四腱机器人**配置**，不读取或注入旧成功张力。原 48 个具名 hinge、零初态、全部四腱恒定 0.2 N、0.35 s 时域、0.01 s 控制/采样、0.0005 s 积分、implicitfast；原重力、地面、碰撞及质量惯量均保留。

测试外力：现有 `payload` body 质心 `[0,0.02,-0.03]` N，窗口 `[0.10,0.25)` s。机器人本来就有名为 payload 的末端 body，本轮未添加其质量或惯量；实测其 COM 与 tip_site 相距 **0.00734846922835 m**。

| 比较 | 已保留匹配采样 | 最大位置差 m | 最大速度差 m/s | 最大时间差 s |
|---|---:|---:|---:|---:|
| 新 Native / 基线原 Native，零外力 [0,0.02] s | 3 | 0 | 0 | 0 |
| 新 Native / 独立零外力回放，同一短网格 | 3 | 0 | 0 | 1.39e-17 |
| Native / 独立回放，非零外力完整 [0,0.35] s | 36 | 0 | 0 | 2.22e-16 |
| 独立回放前缀 reconstruct，再 checkpoint restore / suffix | 26 | 0 | 0 | 0 |

另两次从相同 0.10 s 状态出发的 0.02 s 常输入 rollout 完全相同，且匹配完整序列在 0.12 s 的结果。非零完整序列的实际张力也逐项完全相同。

每个真实步的外力和质心力偶均审计：tick 200（0.1000 s）开始，tick 499（0.2495 s）为最后一次有力，tick 500（0.2500 s）起清零。两条完整非零路径各施力 **300 步**，其余 400 步为零，所有质心力偶为零。

相对同输入零外力完整回放，外力造成最大末端位置变化 **0.0121223554919 m**、速度变化 **0.0994149527147 m/s**，没有静默忽略外力。瞬时质量平衡残差 **6.93889390391e-18 N*m**，body 外力广义力无穷范数 **0.00997304644854 N*m**。

两个独立回放均完整、原 evaluator validity=valid，原复合验收均为 **valid_failure**，无 missing / issues，张力无越界、无求解器错误。固定 0.2 N 是接口测试，未优化控制：

| 条件 | 终点误差 m | 保持最大位置误差 m | 保持峰速 m/s |
|---|---:|---:|---:|
| 零外力 | 0.167146573604 | 0.194532314527 | 0.715628406676 |
| 非零外力 | 0.174739937791 | 0.204549912356 | 0.801545043026 |

## 全部积分成本及失败保留

原验证协议在 `4d66d04c3` 提交并 push 后才积分，预计 4,280 步，硬限 5,000。首次三次零外力执行各完成 700 步；之后工程脚本错误地向 evaluator 传入空 source 引用，在保存评价时退出。**2,100 步全部保留计费，非引擎数值失败。** 失败 summary、成本、完整零回放 samples/XML、逐步施力记录均保留在 evidence 根目录。

首次两个 Native 位置/速度数组未及保存，不能声称完整 36 点零外力已匹配。修复先保存 raw 和每段 Native 输出，并向 evaluator 传入真实内容摘要引用。`c8311b50f` 提交/push 后，显式恢复继承全部成本，只重验两个 Native 的前 0.02 s，复用已保存的完整零回放；原失败不覆盖。

| 实际阶段 | 新增积分尝试/完成步 |
|---|---:|
| 首次原 Native 零外力 | 700 |
| 首次新 Native 零外力 | 700 |
| 首次独立零外力回放（之后评价保存失败） | 700 |
| 恢复：原/新 Native 零外力短段 | 40 + 40 |
| 恢复：非零 Native / 独立回放 | 700 + 700 |
| 恢复：前缀重建 / 恢复后 suffix | 200 + 500 |
| 恢复：常输入 / 重复候选 | 40 + 40 |
| **总计** | **4,360 / 4,360** |

恢复阶段新增 2,260 步；余 **640 步不使用**。引擎数值失败 0；评价保存失败 1。逐阶段记录 wall 合计 **0.635578800004 s**，仅包括记录的执行/评价阶段，不包括阶段外模型构建、测试或部分证据 IO，不能当作完整进程总费用。`native_cost` 是模型累计快照，不能逐行重复相加；总步数按 phase 增量和逐步审计各自交叉核对。

**27 项不同定向测试通过，全部无 mj_step**，未跑全仓回归。覆盖外力边界、重叠相加、质心广义力、restore、非法形式、原 Native/控制边界、原接触诊断、有效任务失败与不完整执行区分，以及 task-only 配对与 replay binding。首次 24 项含 unittest 自动收集的 8 项既有 Reporting fixture 测试。任务组合检查还修正了草案的 sparse zero-rule 元数据；准备和 fixture 错误均无积分。

## 待冻结 task-only 配置与下一轮

[零外力草案](../../tasks/b2_load_hold_zero_v1.json) 与 [恒力草案](../../tasks/b2_load_hold_v1.json) 只包含任务、seed 和原 settling 协议；有力条件一层继承零条件。sparse 全零规则由既有 FamilySpace 配置/候选生成器展开为所选机器人全部具名零初态，然后绑定执行，不新增生成器。

两条件同目标 `[0.29,-0.035,0.19]` m、0.35 s 时域、同一结构；允许分别从 0.2 N 冷启动优化。原终点/保持位置阈值 0.010 m、速度阈值 0.020 m/s、末 0.05 s 保持窗口不变。有力草案暂设 payload COM `[0,0.02,-0.03]` N、窗口 **[0.10,0.35)** s，覆盖保持段。

**草案完整负载保持窗口尚未执行；目标、力大小和窗口均未正式冻结。** smoke 的 [0.10,0.25) s 窗口用于同时验证起止边界，不能替代草案可执行性审查。下一轮可复用现有 Native 控制搜索、绝对张力 seed、独立 replay 和原验收，开发固定程序的有界可行解搜索；须先检查/冻结任务，明确预算、停止规则及双条件同结构协议。本轮未实现该搜索，也未找到可行见证。

未启动 Agent Study、Provider、PPO、NMPC 或结构搜索；没有改 Agent、Reporter、Handoff、科研 Prompt、评价阈值，也未复制 B2 大批历史档案。参考报告从已有 B2 / A4.5 worktree 只读阅读。

## 提交、证据与复现

以下阶段均普通 commit / push 至 `origin/feat/b2-load-force-runtime`：

| 提交 | 内容 |
|---|---|
| `9dd56263d` | B1.1 统一 world body COM 语义与普通后端复用 |
| `62a05c19c` | B1.2 Native 外力执行、适用性、力学输出及成本 |
| `53362359c` | B1.3 独立张力回放与成本记录 |
| `4d66d04c3` | B1.4 积分前验证协议、测试、复现脚本、B1.5 草案 |
| `c8311b50f` | 评价引用修复、输出先保存、有界恢复协议；成功积分实现版本 |

最终交付提交另封存本报告、测试补充、草案零规则与以下新证据；最终 HEAD 见分支与交付消息。

[成功 summary](../../evidence/b2_external_force_runtime/recovery/summary.json)、[累计原始成本](../../evidence/b2_external_force_runtime/recovery/cost.json)、[零积分审计](../../evidence/b2_external_force_runtime/recovery/audit.json)、[输入](../../evidence/b2_external_force_runtime/recovery/inputs.json)、[逐步外力](../../evidence/b2_external_force_runtime/recovery/force_steps.json)、[Native 输出](../../evidence/b2_external_force_runtime/recovery/native_outputs.json)。独立零/非零回放、原评价和复合验收分别在 recovery 的 `zero_playback.json` / `force_playback.json`；原失败保持在上层目录。MuJoCo 3.13.0、NumPy 2.4.6、SciPy 1.17.1、Python 3.11.16，完整版本在 inputs。

在干净副本、已有本地基线提交及已安装环境中，一次正常复现预计 4,280 步；拒绝覆盖既有结果。不要在本交付工作区再次积分：

```powershell
$b1Python = 'D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe'
& $b1Python -m examples.b2_load_force_smoke --output runs/b2-force-fresh-copy
```

本次显式恢复命令（已执行，勿重跑）为 `--output evidence/b2_external_force_runtime/recovery --recover-zero-playback evidence/b2_external_force_runtime`。修复后的干净复现不会重现本次评价保存错误，不能用其较低费用覆盖本轮真实 4,360 步账本。
