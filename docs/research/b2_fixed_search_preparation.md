# B2 冻结规范与固定程序准备

2026-10-26，Asia/Shanghai。起始本地及远端 HEAD 均为 `ed3e0d46e8754506ef4aa04aec62f78e87f1f3d9`，工作区干净。远端由 GitHub git/ref/heads API 核对。仅修改 B 工作区，没有合并 A/C/main。

**任务契约已在搜索前冻结，物理可行性与结构辨别力均未知。** 本阶段新增真实 Provider、数学求解、Native rollout、独立物理回放及积分尝试均为 0。旧 B1 的 4,360 步不变，其 640 步余量不沿用。

## 冻结内容

新增两份完整 task-only 快照，不改旧草案或封存研究：

- `tasks/b2_load_hold_zero_frozen_v1.json`
- `tasks/b2_load_hold_force_frozen_v1.json`

物理数值与原草案相同，仅 task_id/name/source 区分正式规范；`development_valid` 是既有任务 Schema 状态，不是可行性证明。

| 条件 | 冻结值 |
|---|---|
| 目标 / 坐标 | `[0.29,-0.035,0.19]` m，world |
| 时域 / 控制 / 采样 / 积分 | 0.35 / 0.01 / 0.01 / 0.0005 s |
| 终点 / 保持位置 / 保持速度阈值 | 0.010 m / 0.010 m / 0.020 m/s |
| 保持段 | 末 0.05 s，包含 0.30 至 0.35 s 的六个采样 |
| 外力 | 既有 payload body COM，世界向量 `[0,0.02,-0.03]` N，`[0.10,0.35)` s |
| 双条件 | 同一个物理结构，各自从合法常张力冷启动重新优化 |

外力不是新增质量，也不是 tip_site 点载荷。0.35 s 的终点样本是最后一个受力积分区间结束后的状态，窗口结束时力按原接口清零。原重力、地面、碰撞、质量、惯量、模型网格、张力约束和验收均保留。

FamilySpace 的中性结构为两段四腱：段长 0.16/0.11 m，模量 7.2/5.4 MPa，12 cells/段、48 hinge DOF，四腱 0 至 8 N、pretension 0.2 N。四腱等角、均跨两段；中性腱路半径 0.018 m。仅候选半径改为 0.014、0.023 m，其余结构固定。这是小规模合法参数筛选，不声称覆盖结构空间。

`configs/research/b2_fixed_search_v1.json` 固定任务、源配置的八份 UTF-8/LF 归一化 SHA-256（兼容 Git 的 CRLF checkout）、候选顺序、控制起点、现有搜索器参数与预算提案；计划身份为 `630414e96e3d1f5fe248cc35e4d798fc44adabcbcd656a800bdfbd06fbf3b948`。修改冻结输入将拒绝启动。后续结果不能用于移动这些任务阈值；如另开任务版本，保留本版本全部结果。

零积分审计记录在 `evidence/b2_fixed_search_preparation/preflight.json`：三结构×双条件均通过 SessionInput、实际 FamilySpace 生成、Native 适用性、完整具名零初态、控制序列 binding 和真实 MuJoCo 模型构建；检查 0/0.10/0.30/0.35 s 的 COM 受力及零力偶。记录 6 次模型构建、30 次 forward、0 rollout/积分。没有执行完整负载保持窗口，数值稳定性与完整可行解仍待科学预算验证。该审计足以冻结合法规范，不能当作动态可执行或任务通过证据。

## 固定程序与预算

入口 `examples/b2_fixed_search.py` 直接复用 FamilySpace 的 `generate_family`、原 `native_control.calculate`、原 `playback_tensions`、`evaluate_playback` 与 `assemble_acceptance`。无新优化器、Store、Reporter、Agent 或数学接口；只保存独立固定程序的输入、原始输出、原评价和增量成本文件。

现有 response 搜索：四个 knots `[0,.12,.23,.34]` s，最多 60 个完整 Native rollout/条件、2 iterations，绝对合法张力、ZOH；每次均克隆本候选具名零初态。每个条件的 best-found 控制另做一次完整独立回放，由原复合验收的 `accepted` 决定通过。模型局部通过不代替该验收。

| 模式 | 最大完整 Native rollout | 最大独立回放 | 积分尝试硬限 |
|---|---:|---:|---:|
| neutral：只中性结构，0.2 N 起点 | 120 | 2 | 85,400 |
| feasibility：中性→小半径→大半径，0.2 N 起点 | 360 | 6 | 256,200 |
| contrast：三结构×0.2/0.4 N 两起点，独立对照 | 720 | 12 | 512,400 |

每条完整轨迹为 `0.35/0.0005=700` 步。feasibility **包含** neutral 的 85,400 步，后两结构最多再用 170,800 步；两行不是连续运行的两个新增额度。建议首次只批准 neutral，或一次批准分阶段 feasibility；不能以更换目录重新获得额度。找到同结构双条件首个独立通过即退出可行解搜索；数值求解失败停在诊断，不据此宣称结构不可行。保留 baseline/best、停止原因、逐次控制与原始反馈，判断有限搜索是否仍在改善。

contrast 需要先提供本计划下的完整独立见证目录及独立批准；不使用见证控制初始化对照。两起点、算法、张力、网格、次数上限相同，允许同一成功阈值触发相同早停。比较实际费用和有限预算 best-found，并检验第二起点；不宣称全局结构优势。neutral 通过或优势不稳定均保留。当前尚未运行任何对照。

真实单次完整轨迹的积分数可由冻结网格精确计算；旧 B1 wall time 不涵盖全部构建/IO，不能直接外推总运行时间。新程序按阶段记录 wall_s，另记录全过程 scientific_wall_s，逐 mj_step 计尝试与成功数。失败的引擎内部部分进度仍按原诊断为 unknown；不清零或补发。异常保留已有 raw、进度、成本和 summary，禁止覆盖输出或自动恢复。

## 运行与独立授权

使用现有 `D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe`，无需安装依赖。

```powershell
$b2Python = 'D:/softrobot-agent/.f3-prestudy-env/Scripts/python.exe'
# 零积分，输出目录必须是新的
& $b2Python -m examples.b2_fixed_search --output runs/b2-audit-new
# 下列科学命令仅在另获明确批准后可执行
& $b2Python -m examples.b2_fixed_search --mode feasibility --approval-file runs/b2-approval.json --output runs/b2-hidden-feasibility
& $b2Python -m examples.b2_fixed_search --mode contrast --approval-file runs/b2-contrast-approval.json --witness-directory runs/b2-hidden-feasibility --output runs/b2-hidden-contrast
```

待批准文件模板如下；必须先有用户明确批准，文件本身不产生授权。`implementation` 填批准时提交的完整 HEAD，程序拒绝未提交的生产修改。同一批准记录跨输出目录只允许使用一次。

```json
{
  "experiment": "B2-fixed-search-v1",
  "approved": false,
  "user_approval": "PENDING_SEPARATE_USER_APPROVAL",
  "implementation": "填写批准时实际提交的完整HEAD",
  "mode": "feasibility",
  "plan_identity": "630414e96e3d1f5fe248cc35e4d798fc44adabcbcd656a800bdfbd06fbf3b948",
  "physics_step_attempts": 256200
}
```

## 验证、隔离与剩余门禁

新增 6 项定向测试通过，未重跑旧 27 项或全仓测试。模拟轨迹只用于检查原 Native 搜索→原评价→双条件成功即停、单条件通过不计见证、耗尽后保存尝试数、冻结数值与批准绑定。测试中的 `physics_steps=700` 是明确的假数据完整性字段；测试没有调用真实 mj_step。初次三项 fixture 目录因 Windows 临时目录 ACL 失败，发生在搜索之前；改用普通工作区测试目录后通过。模拟输出没有封存为科学结果。

预检的模型构建/forward 如上；测试也做了少量真实模型构建，未单独计构建总数或完整 wall time。所有阶段真实积分尝试/完成、科学 rollout、Provider 请求/Tokens、NMPC/RL/Reporter 执行均为 **0**。没有把模拟成本或旧 4,360 步计入本轮科学消耗。

后续科学结果只写忽略的 `runs/b2-hidden-*`；不得提交成功控制、成功结构指认、原始结果或向 Agent 的 supplied_evidence/历史闭包提供它们。新 Cold-start Study 另用干净 checkout 与独立 Store，只给冻结任务、合法 FamilySpace 和工具；独立验收方持有隐藏见证。当前尚无成功答案；公开的合法候选集合不是成功结构答案。

生产外力代码未改。B2 合法规范冻结和可复现入口已准备；完整可行见证、结构效应、有限搜索实际成本全部未决。下一步需要**新的 B2 科学预算**；Provider 仍为零，不需要也未申请 B2 Agent 外发。
