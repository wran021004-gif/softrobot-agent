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
