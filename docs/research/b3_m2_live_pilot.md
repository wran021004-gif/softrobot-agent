# B3 M2：有限真实自主科研试点

2026-10-26（Asia/Shanghai）。状态：**准备完成，自动审批拒绝启动，B/C 均未运行**。
本文件是准备与阻塞交接，不是已完成的 M2 科研报告。

基线 `feat/b3-t2-guided-design@fcdc0a4f47dea98afe3a355f491b15b1f7a51a6d`。
研究分支 `research/b3-m2-live-pilot`，复用原 M1 工作树与原 Store，保留 M1 分支和其他工作树。

用户附件 `68af1110-5541-410b-86e2-cc47f5b933b8/已粘贴的文本.txt` 及本次消息明确授权
M2 两组各一次真实研究、最小必要修复、原恢复机制、commit 和普通 push。
不追加第二次 Study，不重置预算，不把 B 本次结果注入 C，不替 Agent 选择科研方向。

## 冻结与运行入口

| 条件 | B | C |
|---|---|---|
| 原 Study | b3-t2-050-b-v2-draft | b3-t2-050-c-v2-draft |
| resolved_identity | 4a623b709812f4787383e4386a7d0deaec9ed76cb370f11312951d323423f554 | 4de5e88479238e3e5f478d8251aaf2a6951ec7fa7d6d06f379aba15f93a03093 |
| 原冻结实现 | dc773ea20aad9146a4f2080ec64b2d65b6b7d99f | 相同 |
| 结构 | 固定共同参考 | 至多两种独立物理结构，含共同参考 |
| Provider / 公开操作 / 数学 | 32 / 80 / 22 | 相同 |
| 共享独立物理 / NMPC / 完整回放 | 4 / 2 / 2 | 相同；每结构至多 1 NMPC + 1 回放 |
| 保护 Provider / 公开操作 | 4 / 6，包含在总额 | 相同 |
| native callbacks / iterations / knots | 8 / 2 / 4 | 相同 |
| PPO | 0 | 0 |

原 Store：本工作树 `runs/research/<study_id>`。初始全部使用为零、无 pending 请求或占用。
科学源码哈希、core 哈希和 Host compatibility 与原冻结实现全部一致，未重新 prepare、复制或重写 SQLite。
三条共同历史背景已存在，仅为背景，不作为本轮结果或控制种子。

NMPC **重规划/求解间隔 0.1 s**，horizon=10、substeps=1、max_iterations≤120、tolerance=1e-6。
控制与验收采样仍为 0.01 s、MuJoCo 积分仍为 0.0005 s；这三个时间尺度分开记录。
冻结 B3 0.50 s、目标、初态、保持窗口、位置/速度硬阈值和张力界保持不变。

原 C3 request-feedback Handoff 准入来源：
`evidence/c3_handoff_admission_20261025` 中
`aaaf83b7e9f8e2c8e573e42cc7bcef163197d83edcc9537322b97bfee4ac4a88`。
已用原 archived 校验归档及 member 身份，真实请求、反馈、切换与新进程恢复均 passed。
本轮两组分别通过原 formal_study_authorization/scope_identity 登记，准入引用原证明及本轮授权。

环境：使用原 s135 Python，numpy 2.4.6、scipy 1.17.1、casadi 3.7.2、MuJoCo 3.13.0、
CVXPY 1.9.3、CLARABEL 0.11.1，三种数值线程均为 1；只做导入检查，没有重复科学预检。
两项定向 unittest 通过（8.847 s）：原 request-feedback rotation、B/C 冻结公平配置与正式授权门禁。

持续监督：已创建本聊天每 5 分钟检查的 heartbeat `b3-m2`，因下述自动审批阻塞暂为 PAUSED。
明确授权满足审批要求后恢复；任务全部交付后停用。
原始请求、响应、决策、收据、worker 和结果继续由原 Store 保存，不建立第二套日志或账本。

## 进度与恢复交接

两组原 formal_study_authorization、原 Handoff 来源和共同参考均已登记：

| 原 Store 记录 | B | C |
|---|---|---|
| 本轮 scope 授权 | f70b0237cf570d86ad20d58773ed9c664e0d9b765e79dda4f3dbd536f83d94b6 | 0d45186f5fa6bc141a1396e56deaf13dcd3aeec2d906e117549f1278025cd9ce |
| 有来源的 Handoff 准入 | 8e3290af4cd224b524853c0fa8d9d8a201cc227033cbd2d458554b1431194038 | e79f10ddb3c2bbbc9e1084e0ecd9c2f6332d1917df8ad7594d246bccf247e72a |
| 本 Study 共同参考候选 | c884086ce2fc5a2ddfe61a19bf67fab01dcc440e0329be0a7ae317855809d2a7 | 123ba9d4accff3a08b8a7eaab7303f364ffaf50014174fc0d3320a37f366fa33 |

共同 physical_design_identity 为 `676cfa6149fd3f07deea5dca853fcb2ff990def0df7fcd46d79f8ed0a486ec04`。
这是原生成器的无科学结果工程种子，没有独立物理执行，没有复制历史控制。
后续不重复 prepare/bind、重置身份或重新生成种子。

`runs/m2_run.py` 是本轮操作脚本，仅在原 dispatch 前核对冻结求解设置、final fidelity 和
C 每结构独立物理机会；核对结果直接保存到原 Store event。没有生产源码修改、替代 Agent、
求解器、执行器、账本或证据系统，也不为 Agent 指定结构或研究方法。
原本各组 `execution_instructions` 已要求这些监督检查，脚本未改变冻结科学实现。

正常运行使用原 s135 Python 执行 `runs/m2_run.py <study_id>`；其内部调用原 converse，
session_handoff=True、handoff_request_bytes=160000、pause_exploration_remaining=4。
恢复前检查进程、原账本和未知发送；优先原 recover/restore-only，不重复 launch。

## 自动审批阻塞

两次提交同一隐藏后台启动操作均在 shell 进程创建之前被 auto-review 拒绝。
没有运行凭据加载、TCP 预检、Provider 请求或后台 study 进程。
第一次拒绝理由为尚缺向第三方地址发送私人 study 提示与仓库数据的明确授权。
随后只读核对了原冻结出口、数据包字段和本轮 scope，并经 GitHub get_repo 确认仓库 visibility=public。
第二次审批仍要求可信用户明确授权**具体地址与 payload 范围**，不接受助手对现有授权的解释。
原拒绝要点：

> The transcript does not contain trusted user authorization for that specific destination and payload.

原冻结 Provider 为 `deepseek-flash`，唯一模型出口为
`https://api.deepseek.com/chat/completions`。
请求范围为冻结 B3 任务、必要结构与控制参数、三条显式声明的共同历史背景、工具定义和本 Study
实际工具反馈；API key 仅供正常认证，不进入提示词、证据或日志；不检索其他工作区文件。
若用户明确批准该具体出口与数据范围，再提交同一原运行操作；不换出口、不间接绕行。
这是运行审批阻塞，不是模型网络故障、科学失败或平台已通过的证明。

## 科研结果

| 实际状态与费用 | B | C |
|---|---:|---:|
| 状态 | 未启动，审批阻塞 | 未启动，隔离等待 |
| Provider（含 Reporter） | 0 / 32 | 0 / 32 |
| 公开操作 | 0 / 80 | 0 / 80 |
| 数学总评价 / 模型 / CONIC / dual-face | 0 / 0 / 0 / 0 | 相同 |
| 独立物理 / NMPC / 完整回放 | 0 / 0 / 0 | 相同 |
| native 内部积分 / PPO | 0 / 0 | 相同 |
| pending / 占用 / 未消费响应 | 无 | 无 |

本轮模型**没有收到任何请求，因此没有科研决策**。T1/T2、分数平台、结构修改、
GVS—MuJoCo 差异和最佳独立硬指标均未测量，不能把旧证据记成本轮结果。
没有研究 Agent 的 SELECT/STOP，也未行政关闭这两份待运行 Store。
后续须完成每组实际决策与 wire 审计、资源结算、独立物理硬验收、标准导出及完整研究结论。

生产源码修改为零；新增本准备报告和一个操作脚本。没有扩大测试、修改冻结科学配置或扩展预算。
