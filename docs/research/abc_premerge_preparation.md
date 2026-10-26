# A/B/C 汇合状态与 A 外力集成验收

2026-10-26，Asia/Shanghai。用户在原只读准备后明确要求“开展A的集成任务”。**B 的通用外力运行时已选择性集成到 `integration/research-next`，14 项针对性检查通过，新增物理积分和 Provider 请求均为零。** 这是 A 分支工程集成，不是 main 合并或正式自主科研 Study 通过。

## 分支与提交

起始经认证 GitHub `git/ref/heads` 核对，三线远端均与给定 HEAD 相同、三个 worktree 干净；主工作区其他环境及 runs 未改。

| 线 | 分支 | 起始本地/远端 HEAD | 本阶段本地结果 |
|---|---|---|---|
| A | `integration/research-next` | `2316fe2883f4aa438464c974dd1a35fb1fd0222b` | 本报告所在提交集成五个生产文件和两个测试文件 |
| B | `feat/b2-load-force-runtime` | `ed3e0d46e8754506ef4aa04aec62f78e87f1f3d9` | `26aaa0b` 冻结规范/入口；`23d3d4b` 失败检查点；结果报告 HEAD `a4861ede647beff8a778d257fb094645026cf6bd` |
| C | `feat/c32-readonly-live-probe` | `c7642d97eaf742555ca5d982fa0c497f443ec44e` | 真实配对完成；结果报告 HEAD `a555ac23b24ba17c6cf1bad834a68b4cf51d3ea8`；生产代码及冻结两版未改 |

新增提交目前仅在本地。此前普通 B push 被自动审批拒绝：目标和待发送内容的外发授权未获认可；操作未执行，未用连接器绕过。需明确批准具体仓库/分支及非敏感提交范围后再普通推送。

## A 最小集成范围

补丁来源为数学主干 `618fba9a11a1a1d0c9fca5228d25e873b7c8dddd` → B 外力工程 `ed3e0d4` 的真实差异。先完成七文件 apply check，再按新授权应用，没有整分支覆盖。

| 文件 | 实际集成 |
|---|---|
| `extensions/tendon_family/scene.py` | `world_body_com_force_v1` 世界坐标 body COM 定时恒力语义 |
| `extensions/tendon_family/backends.py` | 共用力绑定/施加，每积分子步刷新，独立回放与成本 |
| `extensions/tendon_family/mujoco_analysis.py` | Native 初始化/restore/重建/rollout/sequence 外力，COM Jacobian 力学贡献、尝试数与失败诊断 |
| `tools/research/native_analysis.py` | 外力适用性与力平衡解释；保留 A 的旧模量/截面授权兼容及 spec/family_variable_authorized |
| `tools/research/native_control.py` | 控制结果附冻结外力来源与语义，沿用原搜索器 |
| `tests/research/test_native_external_force.py` | 七项原外力回归适配 A 的通用 fixture；新增六通道绑定检查 |
| `tests/research/test_native_task_sensitivity.py` | 接触失败 fixture 仅补 scene/xfrc_applied 两字段，保留 A 其余回归 |

四个运行时文件（scene/backends/mujoco_analysis/native_control）归一化文本与 B 实现一致；native_analysis.structure_context 的 AST 与 A 起始 HEAD 完全相同。原 physical_replay 的 model_context/binding 无需新接口。

A 的 analysis、nonlinear/optimal capability、task constraints、contracts、config、预算、证据、原任务评价及 SELECT/STOP 代码在本次外力提交中未改。16 项方法及 T1/T2 保留，Native 外力支持不授予 affine/GVS 新物理能力；有限失败不表示结构不可行，T1/T2 不提供全域/重优化最优/硬件保证。没有新增优化器、Store、Reporter、Handoff 或调度器。

未引入 B2 研究脚本、任务快照、旧 Study、隐藏成功结构/控制。六通道回归是普通 FamilySpace 默认布局，并非隐藏成功布局。C3.1 已在 A，C3.2 live/review 分支无需整体合并。

## 定向验收

14 个不同测试通过（先 13 项，再新增六通道一项），没有重跑原 A 28/B 27 项、C MockTransport 或全仓测试。所有检查无真实 mj_step，模拟轨迹不计科研结果。

- 八项外力测试覆盖起止/重叠/清零、合法性拒绝、restore、COM 力平衡、重建拒绝变更、双任务 binding、原验收状态、六通道自有边界。
- 两项检查 T1 L0 有限失败/来源/成本、T2 零新增成本与失败非下界。
- 四项检查 A 参数授权、Native 边界及原目录、接触失败诊断、非线性方法授权/原请求/成本。

身份和结果见 `evidence/abc_premerge_preparation/integration_checks.json`；diff 空白检查通过。零积分回归验证代码契约与绑定，不等于在 A 重跑完整动态搜索或鲁棒性；B 原工程/科学证据按来源保留，不重复消耗预算。

## B 与 C 科学状态

**B 已冻结且取得完整独立可行见证。** 同一机器人双条件原复合评价 accepted；新增 899,500 步（1,262 Native rollout、23 独立回放），首次完整通过即停。固定程序首轮失败，最终由助手适应性调用现有工具找到，不是自动冷启动或数学预言结构更优。结构辨别力及数学工具的因果效率收益未建立。

详见 B `docs/research/b2_first_feasible_pair.md` 和 `evidence/b2_feasibility_search/summary.json`。精确结构/控制仅在 B 忽略目录，A 不接收隐藏答案。下一步是独立冻结公平重优化、双起点和必要等驱动资源对照；尚未执行，不自动继承可行解预算余额。

**C 已完成 12 次真实请求，未观察到可信判断改善。** 输入/输出/合计 Tokens 为 512,651/130,520/643,171；公开工具 25、读取 20、查询错误 2，科学执行全为零。输入/评分/模型/权限不变，无重试或补抽样。

详见 C `docs/research/c32_live_scientific_review.md`。本会话按冻结 rubric 建议 fail，主要是动作/方法错配、遗漏授权和费用前提、局部估计过度解释；不是独立盲评。原自动 review 未评分的 insufficient_evidence 保持原样，没有确认新的生产证据泄漏/丢失。用户随后允许小修复；后续另记实际修改/回归，不改原 Treatment 或在原冻结集刷分。

六份原请求逐字节哈希再次核对一致，起始哈希及协议身份保留在 status.json。原请求/响应/推理/Store 未纳入公开提交。

## 门禁与下一步

| 门禁 | 当前结果 |
|---|---|
| A+B 工程集成 | A 分支最小闭包已集成，14 项关键检查通过；main 未合并 |
| B2 冻结任务与完整见证 | 已建立，原阈值及身份保留 |
| 结构辨别力 | 未建立，不得称结构设计优势 Benchmark |
| C 真实科研判断 | 实验完成，未通过改善门禁；后续修复与独立新验证分开 |
| 正式 Agent Study | 未就绪：处理决策问题、隐藏答案隔离，另冻 Provider/数学/控制/物理预算 |

A 本轮新增 Provider/科学积分为 0；B/C 各自完整成本保留，不记入 A 或清零。工程集成已完成，不扩大数学工具框架。
