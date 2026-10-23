# S142 Reach/Hold 自主联合研究

本轮从 `origin/mainline/softarm-codesign@4de5d5d47` 建立独立 worktree 和
`research/s142-reach-hold-autonomous`，只开展一个新的 Study：
`s142-reach-hold-coldstart-20261023`。S140/S141 仅作只读方法边界，没有合并。

启动配置为 `configs/research/study_reach_hold_coldstart.json`，沿用原 robot、task、
control、runtime 文件。使用现有两段六腱 source-relative 生成器，段长、材料、截面及
两个已注册 NMPC 速度权重在原明确连续域中可变；总长没有另加固定约束。
任务仍为原目标、零初态、0–8 N 理想张力、0.35 s、0.01 s 控制周期、0.0005 s 物理步长。
独立终点与保持误差上限 10 mm，最后 0.05 s 的保持最大速度上限 0.02 m/s。
原冻结组合验收保持不变；控制权重不改变验收。

上限：Provider 36（6 收尾）、公共操作 160（16 收尾）、物理启动 8、NMPC 3、
数学内部评价 40、局部求解 8、PPO 2 阶段各最多 4096 effective actions（累计 8192）、
RL 独立评价 1、成功后额外确认 0。T1/PATH、T2 显式授权，内部子问题分别计账。
额度不是目标，不扩大离线 NLP/BDF 或诊断回放。

Cold-start：全新 Store、会话和证据目的地；历史 observations、mathematics 和
control seeds 均为空。唯一 supplied evidence 是来源明确的 S141 模型可信范围警告，
不含历史成功候选、控制或结构调整方向。原工程配置是公开先验，不能称为无先验随机初始化。
授权来源是 2026-10-23 本次用户 S142 完整指令；prepare/bind 后通过原 Store 的
`formal_study_authorization` 记录真实批准，并绑定新冻结身份，不复用旧 grant。

预检：配置 resolve、source-relative 控制准入、已有 CasADi/MuJoCo/CVXPY/CLARABEL、
Strands/harness 与凭据可用。实际科研解释器复用
`D:/softrobot-agent/.worktrees/s135-task-conditioned-control/.s135-env/Scripts/python.exe`；
RL 仍使用 runtime 指定的 `.rl-pilot-env`。没有请求 Provider 或运行物理预检。
5 项定向测试通过：正式批准绑定、完整 invocation 暂停边界、L1 硬指标保留、
Reach 终端/保持语义分离、由真实物理输出派生 Reach 诊断。
未改生产代码或新增测试；未运行全仓库测试。

结果将在同一 Study 完成或明确阻塞后追加。原始执行只保存于忽略的
`runs/research/s142-reach-hold-coldstart-20261023`，不声称存在公开原始归档。

启动时发现并最小修复一项生产缺陷：`working_set` 错把 family-space 的
`resolved_parameters.tendons` 当作所有候选必填项，导致 source-relative 新 Study
在 prepare 已保存后打印状态失败。现改为从候选实际 robot configuration 读取
柔性段与腱数量，其他身份/准入不变。一项新回归与原候选方法视图测试通过（共 2 项）。
随后 status 成功；同一 Store 得以保留，无科学执行、未 bind，不需要 implementation migrate。

真实启动在 CreateProcess 之前被自动审批拒绝：其理由是具体 Provider 目的地及
可能敏感的请求内容未在授权中明确点名。此次拒绝未发生任何发送或科学 worker。
离线核对确认既有目的地为 `https://api.deepseek.com/chat/completions`，
模型为 `deepseek-flash`；首个决策包约 36 KB，内容来自冻结任务、结构/设计域、
控制器默认与 Schema、预算、原始证据引用和研究说明，不注入仓库源码或 `.env` 内容；
已比较实际 API 密钥值并确认其不在决策内容中。认证密钥只由既有客户端用于认证。
核对记录已保存在本 Study Store 的 `supervision_egress_preflight` 事件。

该核对还离线复现了第二项真实缺陷：紧凑 `decision_packet` 无条件读取 family-space，
而 source-relative Study 没有该字段。现按原 start_mode 选择 family-space 或原冻结
reference_parameters/allowed_parameters/length_constraint；复用原配置权威，不新增解析器。
一项定向回归通过；测试 fixture 起初缺 profile.version 和 Registry，补全 fixture 后通过，
实际 S142 决策包已完整生成，未调用模型。此修复发生在绑定后，必须提交并按原 migrate 流程迁移，
保留原 Profile、冻结配置、批准身份及全部账本。
