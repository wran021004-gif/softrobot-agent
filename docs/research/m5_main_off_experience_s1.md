# M5 Main-Off 经验辅助 Study：S1 交付（2026-10-28）

1. **S1 准备与授权**

   从 `39a828e690b37b079deee91c8771c8fab6c8671e` 新建本地分支
   `codex/m5-main-off-experience-s1`，未合并分支或修改封存研究。
   独立 Study 为 `m5-main-off-experience-20261028-s1`，Store 为
   `runs/research/m5-main-off-experience-20261028-s1/platform.sqlite`。
   叶配置为 `configs/research/study_m5_main_off_experience_v1.json`。
   实际绑定提交见同目录 `implementation_freeze.json`，正式授权仍为 pending。

   原 M5 任务、独立评价器、控制界、物理参数和时间网格保持原值：
   0.6 s、积分步长 0.001 s、控制/采样间隔 0.02 s，
   原评价窗口 0.58–0.60 s，位置阈值 0.008 m，有向轴角阈值
   0.05235987755982988 rad。完整执行覆盖与原采样验收仍分别检查。
   基于 F1 Base-only FamilySpace，将执行域收窄为两段、六独立腱通道、
   每段 12 cells；初始候选由 Main 以 `agent_choice` 决定。
   本次没有生成真实科研候选或预置成功控制。

   Main：`deepseek-flash`、Thinking disabled、reasoning_effort none。
   保留 research_roles_v2、english_decision_v1、recent_round_trace_v1、
   on_demand_tools_v1、bound_scientific_variables_v2。
   Reporter 保留原自动机制，Thinking enabled / low，费用共享 Provider 总额。
   不启用 NMPC/PPO/RL；自动重试及成功后额外确认均为零。

   | 资源 | 冻结上限 |
   |---|---:|
   | Provider（含 Main、路由、Reporter） | 48，内含收尾 8 |
   | Public Operations（含已有子操作计费） | 160，内含收尾 16 |
   | 数学/Native 共享分析额度 | 4 |
   | 单次 Native 控制搜索回调 | 100 |
   | 单次搜索迭代 / knots 数量上限 | 16 / 4 |
   | 完整独立物理回放（共享物理启动额度） | 4 |

   四次满额 Native 控制搜索按每回调最多 600 步计为 240,000 步；
   再为每次请求保守留 600 步前缀重建，加四次 600 步独立回放，
   配置覆盖约 244,800 次积分尝试。短窗 Native 诊断也共享上述分析额度，
   配对结构分析按现有子操作收费。此为现有额度与固定时间网格的保守估算，
   没有新增全局积分账本或声称存在全局运行时步数硬门禁。

   六张原卡的 Task、Trace、Special、Know-how 已逐项保留到本 Study
   私有 experience 目录；去除了原始 Store 路径和 Evidence 定位段。
   新增的仅是现有 experience.py 对显式、Study 限定本地索引的兼容：
   路径限定在本 Study 的 experience 目录，不开放查询任意文件。
   私有 case 保留独立 private_owner_authorized 状态，不伪装成公开 procedure。
   使用原有精确读取回执、内容身份与 experience_disposition，不另建记忆库。
   六卡正文、索引、原始回执、Store 和授权草案均被现有忽略规则排除，
   不加入代码提交或公开发布。

   最终精简 Main 视图原先遗漏经验提示，现已透传简短入口、类别与六项精确查询，
   不注入卡片正文。实际解释器冻结为已有的
   `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`；默认 mainline5
   环境缺少自动 Handoff 所需 tokenizers，未安装额外依赖。
   F3 环境的解释器/单线程/依赖检查通过；完整 M5 的现有 SOCP 不适用，
   未授权该方法，不要求先做 SOCP。

   八项定向用例最终分别通过：三项新增私有经验/隔离/Main 实际请求检查，
   原有通用经验回执、Handoff 全文读取凭证、工具回执恢复、F1 错误修复、
   旧配置兼容各一项。MockTransport 验证真实 SDK 保存/零发送恢复；
   research_analysis 在候选、合法 diagnose 和正式范围的合成前置条件满足后可发现。
   累计 16 次用例执行，前期五次失败属于测试环境依赖或断言修正；
   未重跑全部 34 项、全仓回归或压力测试。

   真实 S1 Store 的零网络/零 Worker 检查已搜索并精确读取六张卡，
   reader 明确为 s1_preflight。s1_preflight.json 保存对应回执、依赖状态、
   Native 适用性、原配置比对和空待恢复状态，耗时约 4.562 s。
   最终实现绑定在提交后执行，并另存实际绑定与兼容性结果。

2. **S2 真实研究 Trace**

   未启动。附件明确要求独立的数据外发及科学执行授权，当前没有此授权。
   只有 S1 配置解析、六卡预检读取和空状态恢复检查；没有 Main 科研决策轨迹。
   `s2_authorization_scope.pending.json` 是待批准范围，不是授权事件。

3. **工具错误审计**

   未发生真实 Main 工具调用，因此其首个生成、计算、回放所需请求数及错误率
   均尚不可测。离线 F1 三种错误形状检查通过，不代表真实 Main 已能自行纠正。
   预检修复精简视图漏经验提示；补充必要的冻结网格子域表达。
   初始测试中还识别 MATLAB fixture 依赖、tokenizers 缺失、Windows 换行比较
   和 research_analysis 按需显示的测试前置条件问题，未改动科研算法或门禁。

4. **经验使用审计**

   六卡在真实现有接口可搜可读；SDK 合成请求确认六入口可发现且正文未预注入。
   真实 Main 尚未读取任何卡，adopted/rejected/context_only 均无实际记录。
   结论是“可用但使用未证实”，不能推断经验提高成功率或决策质量。

5. **工程链路验收**

   S1 本地准备通过，独立授权仍待补充。完整自主科研链路尚未验证。
   现有 Handoff/恢复离线路径通过；正式 Store 未写入发送授权或 live Handoff 准入。
   授权后应按同一冻结身份登记正常准入，再绑定校验后启动一次 Study。
   如果需改冻结代码，应停止并如实保存，不热修补后冒充未变更实验。

6. **M5 科学结果**

   accepted 未测量；位置/轴误差未测量，无独立物理结果，无 SELECT/STOP。
   当前无法回答 Main-Off 加经验能否独立完成整条真实科研链路。
   S3 所需的真实研究记录尚不存在，没有用历史赢家或合成测试补作科学证据。

7. **实际成本账本**

   本次真实 Store：Main / Reporter / 路由 Provider 均 0，输入/输出/缓存 Token 0，
   Public Operations 0，数学/Native 执行与回调 0，MuJoCo 积分尝试/完成步数 0，
   独立回放 0，NMPC/PPO/RL 0。S1 直接本地经验预检读不消耗生产对话操作额度。
   MockTransport 请求只存在于独立测试 Store，不计作真实 Provider 或科研成本。
   已知新增 Provider/科学 Worker 费用为 0；本地测试与 Codex 编排成本未进入
   仓库 Provider 账本，费用未知，不能声称整体成本为零。各阶段墙钟不重叠相加。

8. **下一步建议与所需授权**

   先批准本次具体范围，再执行唯一一次 M5，随后只读审计；目前没有证据支持
   直接进入 M1/M2 或新增规划器、数学引导结构选择、Main Thinking。

   需要独立批准：向 https://api.deepseek.com/chat/completions 发送本次冻结
   M5 任务/设计空间、当前候选结构和控制信息、Main 自主计划/科研假设/实际请求
   与工具反馈、必要测量结果/Trace/Recall/证据摘要，以及 Main 实际选择读取的
   六张私有短卡对应内容；并执行上表内的 Provider、Native 和独立回放预算，
   允许同 Study 既有 Handoff 与精确恢复。此范围不包括完整私有 Store、历史赢家
   结构参数、成功张力数组、原始成功控制轨迹、完整 Codex 搜索日志或私有数据发布。
   依据是用户附件的“S1 → S2 授权门槛”；此前 C3 授权不复用。
