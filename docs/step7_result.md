# 步骤 7 与第一遍架构收尾

基线 `feat/independent-spatial-dynamics` / `ba7afc0`，初始工作区干净，无适用 AGENTS.md。本轮未 commit、push、merge，历史证据未修改。七层职责与边界见 [platform.md](platform.md)；完成指接口可调用、路线可保存恢复，不表示算法成熟或达到任务容差。

## 两处修复

- 公共 `crosscheck` 从来源 CandidateInput 构造实际复核快照；来源、任务、设计、模型、控制、后端数值配置共同决定 `*-cc-<digest>` 身份。相同输入复用封存回执；新数值配置形成新会话。优化和复核共用规范输入一致性检查 `ensure_session`，不覆盖旧快照。原 tendon-family crosscheck CLI 已转接此公共路径。
- `run_search` 在求解前比较完整有效配置，重复提案引用原候选，不重新求解/评分；单列 proposals、distinct_candidates、actual_solves。边界 `1.0 → 1.0 → 0.8` 的无积分检查验证三次提案、两个不同候选、两次计费调用。完整坐标巡回无新配置时停止，检查点保留去重与停止状态。

## 可执行路线

`platform route prepare/start/status/resume/result/call/diagnose/video` 复用 workbench/platform 入口。prepare 生成可编辑的 `inputs/route.json` 与项目预算；开始后以 Store 冻结输入为准，修改源 JSON 不会改变恢复中的任务。允许的完整计算组合位于 `policy.route.data.combinations`；模板和参数范围来自 `candidate.family` 的空间。示例包含同一模型/控制下的两个后端；用户可在开始前配置其他已实现控制选择，编译检查通过才可执行。

真实调用边界：已有 DeepSeekAdapter / OfflineAdapter → 原 `run_loop` → ToolRequest → `Host.invoke(route.advance)` → 结构化组合/变更校验 → 冻结子会话 → `optimization.optimize` / 公共 crosscheck → 原 `simulation.run`、`evaluation.run`、保存诊断/视频 → Store 回执和结果引用 → 下一次模型选择。`route.inspect` 返回当前可执行组合、任务、范围与共享预算；源码生成目录已包含两个公共工具，非仅提供 Python 函数名。

模型不能提交 SessionInput 替换任务或扩大预算。模型选择 build/optimize/diagnose/crosscheck/video/finish，自主决定是否继续或调整；后续决策须引用已完成节点的结果或工具输出。模型上下文保留紧凑结构、评价和诊断摘要；详细配置/轨迹经 `evidence.read` 按 pointer/offset 分页。视频默认不运行，文本适配器不声称已观看。

路线状态存在原 `state.route`，原 `route_node` 事件封存每次投影。节点关联 node_id、工具请求/执行、候选、结果、理由与证据。子会话沿用 parent_run_id，Store 同时检查项目/父路线/子会话额度；外层计一次工具调用，求解和等待耗时只在内层计账。模型请求、求解、评价、派生产物沿用原账本。

恢复复用 pending 和已封存回执；未封存执行仍为 unknown，不自动重发或重演。完成路线再次 resume 不发模型请求、不积分、不评分。正常 finish 保存明确候选；预算或其他明确终止时 Host 可汇总最近一次有效搜索，注明“宿主收尾”，不冒充模型决定。

## 本机唯一物理贯通

本次使用明确标注的 [离线协议夹具](../configs/platform/route_offline.json)，**不是实际 LLM 决策**。任务为 `family-multisegment-dev`：目标 `[0.29,0.035,0.19] m`、容差 0.01 m、时长 0.35 s、积分步长 0.0005 s、控制/采样周期 0.01 s，离散 near=3、far=2。选择 `tube_distal`；近段长度范围 `[0.14,0.20] m`。模型 `model.serial_bending_cells@1.0.0`，MuJoCo `1.1.0`，`controller.family@1.0.0` / tip_feedback，增益 5、阻尼 0.015、最大关节更新 0.025 rad。

| 候选 | near 长度 / m | position_error / m | 达标 |
|---|---:|---:|---|
| search-0 | 0.160 | 0.01909213871680844 | 否 |
| search-1 | 0.172 | 0.03037268908508553 | 否 |
| **search-2** | **0.148** | **0.015735781822628483** | **否** |

最佳仅指本次三个有效候选中的最佳。搜索子会话 `family-route-6ad21f9d2ea182f9`；完整 CandidateInput `565039f794138976337e80dcab6b5bdd25faf95559dfda615c1687ce0014419a`，评价 `2548b20b813d80c99aa6c75030197f9f1362153072b37f35973b8373d026bf7e`。

MATLAB 独立复核在启动 `MATLAB.exe` 时发生 `MATLAB_STARTUP_FAILED / CreateFile 拒绝访问`，未进入积分；失败回执保留，不重复调用，不增加项目额度。最终明确为 **not_reviewed**，没有本轮独立复核数值。夹具下一步使用失败调用的 `$last_output` 导致提交被拒，随后按夹具停止；Host 保存已有最佳候选的终止摘要（`selection_basis` 明示宿主收尾）。正常工具 finish 及来源对应另由无积分协议检查验证。没有把历史 MATLAB 结果冒充本轮复核。

保存诊断有 3 个 near_zero_tension 事件：near_t2 的 0.01–0.34 s、far_t1 的 0.27–0.34 s、far_t2 的 0.01–0.34 s，记录张力均为 0 N；相位 pre_step_solver，判据 ≤0.001 N 且持续至少 0.05 s。数据无缺失，有效状态覆盖 0.01–0.35 s。这些观测不证明松弛、裁剪或故障。来源结果 `777f7a568b3548a9ffd8e1151d18a0e68b3a6705b0a2f11650ec7f2215681d8a`。

本机文件（runs 仍被 git 忽略）：[路线状态](../runs/family_step7/route_status.json)、[最终交付与预算](../runs/family_step7/final_result.json)、[完整配置](../runs/family_step7/best_configuration.json)、[恢复与对应检查](../runs/family_step7/verification.json)、[Store](../runs/family_step7/platform.sqlite)。失败节点、实际输入及全部回执在同一 Store 内。

## 验证与预算

6 项不同的定向无积分检查通过：本轮 3 项（配置变更复核、公共模型循环/重复配置/封存后中断恢复、冻结输入限制），复用 3 项既有搜索/控制检查。合成后端输出仅用于协议测试，不计作物理验证。集中检查后没有运行历史全套测试。实物链路同一路线再次恢复，事件与费用均未增加；最终候选、完整配置、评价及原始执行引用一致。

真实 DeepSeek 请求 **0**：只检查环境变量是否存在，当前进程没有 `DEEPSEEK_API_KEY`；未读取/输出密钥，未尝试联网或反复连接。prepare 沿用 `configs/deepseek.yaml` 的模型、地址、thinking、max_tokens、超时和上下文限制；未换客户端或供应商。另用本地合成响应检查 DeepSeek 工具声明/解码与 thinking 设置传递，不发送 HTTP；当前不声称完成真实 LLM 自主路线验证。

物理贯通：**3 次完整 MuJoCo 积分 + 1 次 MATLAB 启动失败**；原账本共计 **4 次 backend_solves 尝试**（`counts.solves` 是计费口径，不等于成功积分数），额外故障重跑 **0**。评分 **3**、保存诊断 **1**、视频 **0**、真实 LLM **0**，离线回复 **5**；工具调用 **12**，账本 wall_s 约 **6.420 s**。停止后不为误差或复核追加预算。无视频链路实质变更，未重新生成视频；旧结果因源码依赖变化不满足执行复用条件，未修改旧证据迁就新快照。

生成目录：35 个顶层契约、58 个负载契约、76 个扩展。七层职责、公共入口和主要未实现项已更新；没有新增物理模型、控制/优化算法、任务、前端或工作流框架。

## PowerShell 入口

```powershell
Set-Location D:\softrobot-agent
conda activate softagent
# 查看和恢复本轮已结束路线；不产生新求解或模型请求
python examples/workbench.py platform route status runs/family_step7
python examples/workbench.py platform route result runs/family_step7
python examples/workbench.py platform route resume runs/family_step7
# 保存结果按需派生，消耗工具额度，不重新求解/评分；本轮未再运行
python examples/workbench.py platform route diagnose runs/family_step7
python examples/workbench.py platform route video runs/family_step7
```

下一次明确任务使用新目录；先确保既有模型服务环境和 MATLAB 启动权限可用。以下是本机真实 LLM 命令，不使用离线夹具：

```powershell
python examples/workbench.py platform route prepare runs/my_next_route
notepad runs/my_next_route/inputs/route.json
# 编辑任务、空间、组合、预算；开始后以冻结快照为准
python examples/workbench.py platform route start runs/my_next_route
python examples/workbench.py platform route status runs/my_next_route
python examples/workbench.py platform route resume runs/my_next_route
python examples/workbench.py platform route result runs/my_next_route
```

源文件主要是 `extensions/tendon_family/{route,crosscheck,optimization,manifest}.py`、`tools/platform_{host,models,search,view}.py`、`schemas/platform.py`、两个 platform CLI 转接、`examples/platform_route.py` 和 `tests/test_family_route.py`。诊断/视频继续使用原实现与 ExportBundle。下一阶段按具体任务改善精度、控制效果、优化效率及物理支持范围；本轮停止扩展。

建议提交命令（本轮未执行）：

```powershell
git add schemas/platform.py tools/platform_host.py tools/platform_models.py tools/platform_search.py tools/platform_view.py
git add extensions/tendon_family/route.py extensions/tendon_family/crosscheck.py extensions/tendon_family/optimization.py extensions/tendon_family/manifest.py
git add examples/platform_route.py examples/development_platform.py examples/platform_family_optimization.py configs/platform/route_offline.json tests/test_family_route.py
git add docs/platform.md docs/platform_recovery.md docs/step7_result.md docs/platform_generated
git commit -m "feat: add persistent bounded cross-layer routes and fix search/review reuse"
```
