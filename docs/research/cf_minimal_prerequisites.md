# C-F 最小动作前提修复

2026-10-27，Asia/Shanghai。基于 `research/c4-prestudy-action-repair@c41350922`。
原 C4-R 修复和封存失败不改写；本次不运行 Provider-only 评分或模型对照。

## 实际修改

- `native_control.py`：规划与准入共享初态时间、任务截止、合法完整窗口及必需采样覆盖事实。
- `native_analysis.py`：标准初态的只读适用性检查明确采用 0 s，即使附有其他初态元数据。
- `task_constraints.py`：在原候选方法目录及其组合查询加入最薄 `action_prerequisites`。包含候选、已登记控制源、标准初态、合法窗口、未选参数、Native 方法上限和真实剩余额度。源及设置仍由 Agent 选择；晚状态由原准入解析。
- `budget.py`：区分 Plan 的完整物理回调声明上限、Native 内部 rollout 上限、回放方法子额度及受共享账本/保留额度/公共操作限制的可用回放数。没有新增额度。
- `research_context.py`：原 L0/L1 保留前提字段；无 worker 的不适用反馈明确返回原原因和窗口事实。
- `analysis.py`：沿用原 contained worker 的生命周期记录，失败反馈保留真实错误、已观测启动状态、数学支出、数值时间及已知 Native 成本；缺少记录为 unknown。
- `agent.py`：Reporter 交付不再丢弃方法失败反馈；异常反馈分开计数变化与已观测 worker 启动状态。

没有新工具、研究路线推荐、实验自动组装、科学评分门禁或第二套上下文/账本。
原任务、FamilySpace、权限、独立评价及硬/软准入语义保持。

## 最小验证

`tests.research.test_cf_prerequisites.PrerequisiteTests` 5 项通过：标准初态与全任务窗、晚窗拒绝、Plan/Native 回调单位、共享/回放子额度、失败原因与启动/成本。
另 4 项相关回归通过：原 Native 目录/冻结上限兼容检查一项，以及 C3.3 精确错误反馈三项。
最初定向检查暴露两个测试 fixture 的 session 签名不兼容及时间网格末端浮点容差问题；修正后只重跑该五项。
Provider=0、科学 worker=0、物理积分=0；fixture 不作为科研证据。

## 后续执行

先提交本修复，再在原授权所有者执行 checkout 通过原 `bind` 迁移同一
`c4-coldstart-reach-hold-20261026`。保留 spec/profile（若原迁移判定更新版本则记录）、Store、额度、历史及授权身份。
原空候选池 Cold-start 继续使用冻结 DeepSeek Flash；不等待 A 集成。
首次完整独立通过由 Agent 合法 SELECT 停止，否则保留有效最佳结果并依法收尾。
迁移、正式数值首动作、完整费用及决策转折另记 `c4_coldstart_formal_study.md`。

## 正式执行中发现的通用示例修正

正式审计确认：初版 C-F 将 `action_prerequisites` 加入通用模板查询示例，
但 endpoint 等非 Native 方法没有该字段。Agent 在第6次请求照此读取 endpoint 时被拒绝；
这项额外字段错误归属工程表达，不能全部计为模型缺陷，原费用保留。
最小修正是从通用示例移除这个可选字段，Native 方法自己的精确组合查询继续包含它。
一项离线检查验证所有方法均拥有通用示例字段、Native 精确查询仍提供动作前提；零 Provider/积分。
独立开发工作区准备此修正，运行中的原执行 checkout 保持 `af5f5bca4`，不热覆盖或重写原实验。
若在实际清洁恢复边界接入则走原 bind；否则仅作为研究结束后可选择性集成的工程补丁，
不能把它的潜在收益归入此前已发生的研究。

## 正式执行中发现的交接摘要缺失

只读核对原 Store 的真实反馈与交接 preparation，发现部分较大的 `evidence_read`
结果在原 3000-byte 摘要回退中仅保留 status/task_acceptance，丢失了本次已选子对象
的 J、stop_reason、best_metrics 等字段；summary envelope 甚至可能只剩 reference。
这与纠正错误反馈原样送达是两个不同问题，不能据后者断言所有读取交付完整。

`session_handoff.py` 在原 `pending_feedback_delivery` 内保留已选对象的标量与能放入
原体积限制的小字段，明确列出省略键；summary 查询仍标明原 preview 语义。
原精确反馈分支、L0/L1/L2、工具 schema、配置、Store 原件、查询指针及 read credit 均不变。
这不加入研究建议、候选参数或实验派发。2项新离线回归及1项原真实 SDK/模拟 HTTP
交接与恢复检查通过；真实 Provider=0、科学 worker=0、物理积分=0。
