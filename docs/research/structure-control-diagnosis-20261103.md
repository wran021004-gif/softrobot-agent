# 结构—控制诊断与自主联合优化：交付记录

适用分支：`codex/m1-knowledge-physics-reasoning`。开发基线 `d9b357fe8019bf0afbb092eb974b9cfd1edf7be4`。全部新运行属于隔离工程验证；没有继续原 Study、迁移其实现、调用 Provider、增加正式预算、独立 Replay 或训练 PPO。

## 1. 原 Study 的真实状态

直接以 SQLite `mode=ro`/`query_only` 核验 `m1-low-tendon-speed004-20261102-campaign3`，未以报告摘要代替 Store。

- h43 正式 STOP：`3ec35242a5b96f6a0be2d2ef220506f0159ef6b066c3865cb46f9def9d172912`；`stopped`，无 SELECT/成功门禁。
- 必须引用的 39 条结果全部被原 STOP 引用；其中 37 computed、2 incomplete。Store 登记 26 个候选对象，包含工况派生对象；原六结构×三工况的完成记录和末尾中断记录完整保留，不能将这些对象数当作独立结构数。
- 完成 Native T1 21 条、Direct 12 条；累计数学评价 58 个原费用单位，无累计次数配额。
- Provider 144/152，公共操作 134/569，Replay 0/18；账本累计 wall_s=6607.1134794857935。这里是原账本口径，不是货币价格。
- pending、Provider pending、SDK 未消费响应、未封口调用、资源占用均为空。原监督器结段、Provider 收尾保护、中断和正式 STOP 是不同事件。
- 2244 件原制品的 ID、类型和长度与最终封存清单逐项一致。原工作树干净，HEAD 与 Study freeze 均为上述 d9b357f；历史结果保留各自当时的实现身份。
- 开发前后数据库 SHA-256 均为 `47350c5c56f87a2b1b28e206b38de77b4f2baa568b6b331b48cf60839f68d833`。本提交发布后，新代码与原冻结实现有意分离；未自动迁移原 Study。

## 2. 接口可靠性与修复边界

共同根因是四层契约没有始终对齐：科学选择与执行方法；公开/选定 Schema 与编译字段；结果、控制、状态、工况和模型身份；中断后的原请求与已结算反馈。

复用了已有科学意图编译、选定方法 Schema、控制源准入、Store、Worker 和恢复路径。本次新增字段贯通公开 V4 选择、内部 AnalysisRequest 和选定方法 Schema，缺少来源、网格不符、跨工况来源等在 Worker 前拒绝。已有 `saved_state`/`execution+update_id` 互斥、Conic/Native 区分、原编译恢复和 STOP 门禁保留。

新接口：

- 多起点：`source_selection.additional_control_sources` → `control_optimization.additional_sources`。
- 工作点：`saved_state=<完成的 Native 结果>` 配合 `native_state_selection={kind: best_peak_speed | best_holding_start | best_pre_hold_peak_speed | best_sample, time_s: ...}`；显式时刻只用于 best_sample，必须位于实际控制网格。
- 科学搜索力度可传递差分步长、最小半径和活动系数；窗口外及窗口端点系数不能偷偷激活。
- 明确区分“最好模型预测”与“下一个独立验证提案”；二者不同时保留单独的最好控制序列引用。

能力仍有前提：T2 必须有原准入认可的匹配 T1；Conic 仍是其原采样仿射模型；RL 仍须正式授权。没有把未满足前提的能力显示成已可执行。

## 3. 联合诊断与真实工作点

L1 公共入口为 `evidence_read(reference=<候选或结果>, view=working_set, pointer=/bottleneck_diagnosis)`。沿用原结果卡片和 L0 交付，保留候选/工况、指标、主导约束、起点、搜索力度、边界、饱和、停止事实、机制来源和进一步查询；原数组、模型与完整状态仍在 L2。

诊断允许同时出现“控制搜索证据不足”和“结构驱动疑点”，默认保留“未决”。结构疑点必须引用相关最佳控制状态上的原机制计算；不会从局部失败、秩阈值或缺失数据宣布结构不可行，也不替 Main 决定下一步。

原真实 Direct 结果 `bf9a694bb2c369ff20b9e1835142ed7da374363b40724ae03fa28246317d723c` 的指标逐项对照原证据：终点误差 0.018485143085758732 m、保持期位置误差 0.020512068445096853 m、速度 0.08204985464421453 m/s，最大归一化违反量 1.0512463661053633。原机制来自 baseline，诊断明确指出它不能解释最佳轨迹失败。

隔离 Worker 从该真实最佳控制重建 t=0.54 s 的完整非零速度状态：540 个实际物理步、1 次机制评价，剩余原任务时间 0.06 s。瞬时最小 d(speed)/dt 为 -202.3672428668949 m/s²；这表示该点在合法张力范围内存在瞬时减速作用，不能据此保证剩余保持期达标。该新观察未写入原 Study。

新搜索直接保留最佳控制的可信检查点；已保存机制记录中的同一检查点也可复用，实际验证恢复为 0 物理步。缺少检查点时才重建精确前缀，并逐样本核对已保存输出。完整状态绑定配置、物理模型、XML/引擎身份、时间、通道和张力前缀。前缀验证失败仍上报实际已尝试成本；终点状态明确为零剩余时域。

## 4. 优化能力

沿用 `local_control_search.search(starts, ...)`。Native 高层现在可接收 Main 明确选择的多个合法起点，并保留各起点结果。相同实际输入在一次搜索内复用，缓存命中不当作新积分/新局部信息。完成操作的回执恢复不重新启动 Worker。

真实隔离验证选了两条不同完整控制及一个重复起点：3 个已选起点、4 个回调、3 次真实 rollout、1800 物理步。2 knots 的 4 维系数改为 4 knots 的 8 维系数；同时更改了实际搜索半径及差分步长。输入始终使用原 0.02 s 网格、0–8 N 物理界限。

停止事实区分回调/迭代额度、实际半径、退化方向、系数边界、输入饱和、数值失败及采样目标通过。没有新全局优化器，也未证明多起点或更多 knots 在此任务上一定改善性能。有限局部搜索仍可能停滞。

## 5. T1/T2 与 RL

T2 的只读准备入口为 `evidence_read(reference=<候选>, view=working_set, pointer=/t2_preparation)`；数学目录提供该查询。列出参数域、已有负/正候选、基准与扰动 T1、缺失项、被原准入拒绝的 stencil 及原 generate/initialize_control/T1 准备操作。既不生成扰动，也不自动执行 T1、修改步长或强制使用 T2。

隔离 fixture 实际完成同一参数的基准/负扰动/正扰动 T1，再执行 T2：复用 3 条 T1，0 次新 rollout、0 物理步。有限额度下方向结论为 unresolved；不是严格最优结构梯度。缺失或错误匹配会被拒绝。原六结构是坐标变化谱系，未因此被宣称为正负结构导数。

RL 修复了冻结三工况的任务绑定；stage、配置、checkpoint 元数据和 evaluation 可保留真实 condition。三工况 Direct 各作 1 个环境步；Native 完整控制作为 Residual 参考再作 1 步。总计 80 个环境物理步，训练动作/阶段均为 0；未重新开展旧预检或训练。

普通 RL evaluation 不具备本任务的三工况联合验收信用。新增封存实际施加张力 CSV 的来源适配：完成且有已结算回执的独立 evaluation，可由 Main 显式 `initialize_control(candidate, source=<RL evaluation>, parent=<同一 candidate>)` 转成无验收信用的完整控制序列，然后对每个冻结工况走原 independent physical_replay、完整证书读取与联合 SELECT。准入检查完整性、时间/通道、真实输入界限和候选/任务/配置；不继承策略验收或稳健性结论。

该 RL 轨迹转换用定向 fixture 验证；尚无获授权的新训练 checkpoint，因此未实测“训练→evaluation→Replay→联合 SELECT”的整链。技术输入/来源准备已完成，正式策略表现和端到端验收仍未验证。RL 失败不会被解释为结构不可行。

## 6. 验证、制品与后续授权

- 55 项定向离线测试覆盖原搜索、T1/T2、Native 恢复、M1 契约、RL 来源及新增诊断边界。例子中的合成数值均是 fixture。
- 10 个隔离数学 Worker 完成并保留 request/result/runtime/boundary/log：最终主验证链 7 个、原最佳轨迹机制 1 个，另 2 个为接口修正前的工程检查。合计 10140 个原生物理积分步；另有上述 80 个 RL 环境步。均非正式 M1 新证据。
- 7 个最终完成操作均用原请求/回执再读，新增 Worker 和数学评价为 0；跨工况控制源在预留/Worker 前拒绝；公共 L1 诊断与 T2 准备读取、真实 L0 投影均检查通过。
- 完整原始依据保存在原 Store；本 chat 的交付包括只读审计、工程验证 JSON、L0、公共交接验证、测试日志、代码补丁和隔离 Worker 证据包。工程引用不会导入原正式结果集合。

后续正式研究须使用原授权机制：明确批准原 nonpass STOP 的续研与新提交实现身份迁移，保留原冻结任务/历史费用；按 Main 实际选定的候选、工况、控制源、回调/迭代和 Worker 安全范围批准科学运行。原剩余 8 次 Provider 不被擅自重新分配。若选择 RL，还须明确授权 RL capability、对齐 PPO rollout 的动作/阶段预算、独立 evaluation 与三工况 Replay 预算、可用训练解释器及 Worker 保护。此次没有发起这些正式动作。
