# S131：F3 封存与独立 Task Intake

基线远端于 2026-10-23 核对：F3 `b87f8aae`、S129 `d17852c3`、S130 `2e9b8a93`，均与交付检查点一致。使用独立工作树，未重开 Study、重算预算或调用 Provider/科学 worker。

## F3 只读核验

[来源索引](../../evidence/f3_formal/closeout_20261023/sources.md)、[核验记录](../../evidence/f3_formal/closeout_20261023/audit.json) 和 [精确导出的数值 artifacts](../../evidence/f3_formal/closeout_20261023/artifacts.json) 区分远端材料与本地完整归档。归档 1,255 个成员与 manifest 的字节数和 SHA256 全部匹配；最终 manifest 中每份文件匹配。只读 SQLite 前后 SHA256 相同。完整 SDK/原始 Provider/worker 归档继续留在原 F3 工作树，没有纳入 Git。

保存的 36 个测量点、6 个含端点保持样本、700 个物理步确认原验收：终点 9.2446286 mm，保持位置最大 9.7717543 mm，保持速度最大 0.0191342833 m/s。Provider 63/128、物理 27/80、NMPC 5/6 均未变。

### 实际控制输入

最终 `local_control_search_v2` 的原执行源为 `0c9c5912c92955954b38cbf575bef6a68e29020e9507826bc8d596c152fdad5a`；[完整执行表](../../evidence/f3_formal/closeout_20261023/executed_schedule.json) 含 36 个时间边界、35×4 个输入和腱顺序。每行与保存测量中下一边界的实际输入逐值相等。

节点修正以 0 和 0.30 s 两个 knot 线性插值、叠加到原 baseline 并裁剪到 [0,8] N；每 0.01 s 产生一个离散值，再在该周期内零阶保持，物理积分步长 0.0005 s。0 s 行为 `[1.2098746742,8,8,0]` N，0.30 s 行为 `[6.1026294419,4.4238195329,6.4470233981,1.6142017318]` N，后者保持至 0.35 s。保持评价窗口 [0.30,0.35] s 包含 6 个边界测量，0.30 s 测量反映前一控制周期。两种插值/保持层次兼容。

复现必须直接加载原执行表，并绑定导出 candidate 的结构、环境、初始状态、task/model/design identity；不能从 Agent 的“两段恒张力”文字重新生成输入。本次仅核验保存结果，未再次运行物理重放；原始 Agent 决策保留。

这证明一次完整原任务采样仿真通过，以及 Agent 使用物理反馈找到有效方案；局部搜索在同一候选和评价版本上取得实际改善。不证明全局最优性、严格因果、重复性、鲁棒性、连续时间或硬件表现；SOCP/T2/PPO 没有本次成功的直接贡献证据。

## 上下文与当前证据语义

17 个保存请求含完整工程修正，重复内容主要是逐样本 NLP 残差和五次 NMPC 末步详情。只改变 `agent_decision_brief` 的修正投影：保留严格 predicate、solver 状态、各约束最大残差及其原路径、无效预测标记、实际 fallback 标记、静态数值和 Reporter 修订关系；逐样本详情通过原 correction artifact 的 full query 获取。数学授权已由另一个字段提供，移除这份投影中的重复副本。

三个实际请求（接续前、接续后、最终）离线替换比较均减少 **12,640 字节 / 4,840 tokenizer tokens**。这是 pinned 官方 tokenizer 对序列化输入的本地估算，不是实际计费节省；F3 没有重发。每个请求系统指令只有一份；旧工具消息、推理历史、工具 Schema 由 SDK 持有，本次原样保留。现有 L0 已处理 Reporter/latest 同源合并、候选目录与 STOP 索引按需读取，因此不改动这些机制。

| 旧解释 | 当前有效结论与证据 |
| --- | --- |
| NLP strict false 即无解 | 原 false 保留，速度残差约 1.59e-14 m/s，不能证明不可行；零 slack 与原 solver 状态并列，未改成功判定 |
| 旧预测汇总证明模型误差 | 五次末步三维形状及计划/实际输入不一致，汇总不可用于该诊断；原更新引用仍可读取 |
| 标量广播意味着 fallback | 原记录 plan_accepted=true、failure_response_used=false；广播缺陷与 fallback 分开，修复不证明反事实成功 |
| numerical_failure 是实际终止 | termination 是配置选项；实际 solver raw status 才是本次终止证据 |
| 多参数变化是单因素因果 | 保留候选 resolved facts/完整差异，机制解释仍为假设 |
| 静态成功或坐标文字替代数值 | 保留世界坐标、残差、张力与 solver status，局部计算不等于物理验收 |
| Reporter 原拒绝等于来源无效 | 保存原 unavailable revision 和离线 revalidated revision，不倒填历史交付 |

以上均绑定 [原 correction artifact](../../evidence/f3_formal/closeout_20261023/artifacts.json)，原结论、更新路径和修正来源可检索。未知机制保留，不建新记忆系统；Live Handoff、Store、receipt 和预算内核没有修改。

## S130 集成与六项人工审核

仅按 S130 分支差异移植 `schemas/task_intake.py`、`tools/task_intake.py`、两个 `test_task_intake*`、`replay_task_intake.py`，以及九份原说明/验证记录（14 文件，原字节内容不变）。不覆盖 F3 代码。Task Intake 保持 Study 前可选 CLI，N2 Reach-only、`executable=false`，未加入 Agent 常规工具循环；未新增审核程序、Schema、批准状态机或 Study 创建逻辑。

第三轮原始 Reach 响应从 S130 原路径回读，哈希见 audit；六个问题与 14 条要求保留。原 draft 仍 needs_review、无配置预览。下面是 Codex 对可信快照与源码的人工审核，不修改原响应或制造新的 LLM 成功。

| 原疑问 | 已有依据、建议配置与结论 |
| --- | --- |
| 保持窗口 | 快照 settling.window_s=0.05、duration=0.35，采用 [0.30,0.35] s 含端点，已有事实回答 |
| 距离度量 | evaluate.reach 使用末端/目标三维欧氏距离；保持段使用 tip error 的同一 m 范数；采用原实现，已有事实回答 |
| 位置/速度观测 | tip_position 为 world/m/post_step；保持速度是保存世界平移速度范数 m/s，由原物理 profile 提供；采用原仿真信号，硬件估计器未定义 |
| 采样覆盖 | sample_period=0.01 s，原 offline_reach_hold_v1 验证六个保持网格点和完整执行；采用原协议，不推导连续时间要求 |
| 碰撞/接触 | 原 reach_free 环境未声明避障、捕获或必须接触；采用原自由空间任务。若新增全身避障/接触判据，需要另立任务，不能由此审核补出 |
| 外部扰动 | 原 external_forces=[]，采用原无外部施力场景；这不证明对扰动鲁棒。若研究者要求扰动，需要另行指定施力与验收 |

已有事实回答了原参考下的窗口、度量、仿真信号和采样；新增碰撞、扰动、硬件估计和正式新任务要求仍由研究者决定。沿用参考只用于开发审核，不替代正式 Study 授权。

## 验证

结果由离线 unittest 记录；初轮 82 项中 76 项通过、6 项缺历史 Store 路径。补充指向原 s129-integration 保存 Store 的本地测试路径后重跑受影响项；未改测试接受条件。最终测试数量及 SHA 见本次提交记录和最终交付。所有新证据是只读核验，不是新科研试验。
