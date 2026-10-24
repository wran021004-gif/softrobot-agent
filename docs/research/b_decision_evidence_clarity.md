# B 收尾：科研证据语义与决策成本的最小修复

2026-10-25（Asia/Shanghai）。从 `research/agent-math-decision-probe@16c9dc76d`
建立独立分支 `feat/b-decision-evidence-clarity`、同名独立工作树。
完成信息投影和说明修复；**离线测试只证明表达与引用正确，没有证明 Agent 决策质量提高。**
B 已结束。本轮 Provider、MuJoCo/NMPC/PPO、科研 worker、新 Study、A/B 重算均为 0。

## 核对与实际修改

已阅读 AGENTS、B 最终报告/冻结情境、A 结构敏感性报告及指定六个候选模块。
原 ResultCard 的 metrics 已有实际值、阈值、单位和原始引用；原数学摘要已有模型声明、
覆盖和最优性范围；方法目录已有授权/预算/参数准入状态。因此没有再建评分器或准入系统。
真正缺失的是精简反馈中的关联，以及目录裁剪掉的现有方法说明。

| 模块 | 最小修改 | 保持的边界 |
| --- | --- | --- |
| `feedback.py` | `task_gap.dominant_constraints` 把已有最大比值关联到约束、物理值、阈值、单位和源指针；含原独立评价 episode 指标 | 原 normalized_gap 的正部截断、components、valid_complete、accepted 不变；不重评任务 |
| `evidence_views.py` | 原生控制优化的 baseline/best 最差约束，关联冻结 task_analysis 的阈值/单位及两个原始引用 | 使用已保存 worst_constraint，不重新选取轨迹极值；scope=model_sample，不冒充独立物理验收 |
| `task_constraints.py` | 将已有 METHOD_MEANINGS.description 送入精简目录；调整六项说明、两类原生成本说明和提案语义 | 方法集合、Schema、授权、预算及实际准入不变；不注册自由文本组合实验 |

生产改动 **3 文件，+45/−12，净增33行**。没有修改数学/动力学/优化内核、Store、Schema、
Registry、Agent、评分规则或原证据；未开发交叉回放公共工具、预算平台或机制判断规则。
`analysis.py`、`native_analysis.py`、`control_correction.py` 等已有事实和计算可复用，未修改。

## 物理指标与预测范围

物理执行反馈从原 acceptance 数值和同一比值提取主导项，保留并列项、原单位及源指针。
缺少完整排名分量时不宣称已知主导项；缺失原单位保留 unknown，不猜成位置单位。
已通过时 normalized_gap 仍按旧规则为0，主导项可保留负的 signed excess，避免把截断后的
三个0误当任意并列。Reach/Hold 与原 tracking 的排序分量仍由旧规则确定。

原生优化 ResultCard 中，已保存的最差项可能是终点位置、保持位置或保持速度，
通过约束ID读取相应冻结阈值和单位，并随既有 mathematical_decision_view 进入主 Agent。
只读 C1 原归档核对的 baseline/best 主导项均为 holding_speed，阈值0.02 m/s，
原值分别为0.02320985264576029/0.01898530819333862 m/s；仍是 native model_sample。
这些是旧数组的读取与投影，没有重新积分或把数学通过改成实际验收。
J 无量纲，物理换算取决于同一活跃指标及阈值；活跃约束切换时不能一律换算成位置差。

说明现在明确区分：自身力平衡/离散重放残差与跨模型误差；瞬时速度导数与有限时域制动；
两种FD步长或两个积分步长与收敛证明；固定输入结构响应与重优化能力；可行见证与全局
最优控制；局部搜索/修正失败与结构不可行。条件数也不直接给出任务分数误差带。
原 `scoped_claim`、误差数据、证书验证和物理验收仍由原工具拥有，没有替 Agent 归因。

## 成本与执行准入

响应法完整更新的计数为 `S + Σ(D_i + 1)`：S个起点基线，每轮D_i个有效活动系数FD探针，
再加1个候选评价；都消耗同一个 evaluation_requests，部分/失败回调也消耗额度。
短响应两种输入FD步长每通道最多4个探针回放，另有1个基线及可选1个非线性候选。
实际数量仍取原计数，不把说明当成通用预测器。

原生 physics_steps 已包含必要的实际前缀重建与后缀回放；后缀每次步数取剩余时域/步长。
evaluation_callbacks 与 optimization_evaluations 描述同批回放，不能相加成额外运行。
完整独立 physical_replay 属另一个实际执行，其原 physics_steps 单独计入；不会因 native
结果中的 new_physical_evaluations=0 就把内部积分视为免费。未改变任何实际计费或账本。
只读 C1 旧结果核对：26 callbacks=26 optimization_evaluations=26 native rollouts，
对应18,200物理步，三个计数不是78次回放。

自由文本 selected_method 保留为科学提案，不代表执行准入。未列组合没有注册执行模板；
即使方法已列出且有研究授权，仍需原参数、状态、候选、冻结任务和剩余额度检查。
没有自动纠正提案、强迫科学路线或为B的三结构交叉设计新增工具。

## 离线验证、限制与交付

新增3项测试：物理主导项在速度/位置间切换、零截断与episode源指针；原C1数学结果经
ResultCard到L0仍标为预测且引用可读、原记录不变；目录范围、成本与条件准入保持。
另运行原 ResultCard/读取/SELECT隔离的8项回归及1项C1规划—执行准入回归，合计 **12/12通过**。
首次定向测试发现成本说明赋值早于目录条目创建，已修正后通过；失败时没有外部或科学请求。
测试只用内存夹具和原归档只读投影，无科学执行、Provider或Store写入；`git diff --check`通过。

剩余科研缺口仍包括：模型/控制/数值机制的因果区分、瞬时信息外推、活跃约束切换、
搜索初始化与最优性误读，以及实验完整成本核算。清楚的说明不能保证 Agent 会遵守边界，
本轮也没有评价新提示或证明决策收益。它为下一次**另行授权**的正式 Study 提供更清楚的
事实与方法入口，不替代模型验证或正式准入。本轮到交付即停止，不启动新对照或 Study。

改动只普通提交/推送到 `feat/b-decision-evidence-clarity`，不合并main、不强推；最终提交号
和独立工作树状态见交付消息。旧B分支、原费用、评分、冻结情境和A证据保持原样。
