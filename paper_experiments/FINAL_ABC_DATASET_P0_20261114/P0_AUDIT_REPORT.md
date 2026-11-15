# Softrobot-Agent 论文实验 P0 审计

审计结论：PASS_WITH_DISCLOSED_LIMITATIONS。本次仅解析已有文件、只读 Store、清洗与计算派生指标；未启动 Provider/Study，未运行 MuJoCo、KKT、QP，未生成候选、绘图或修改论文。原始文件保留在原位。

## 正式数据与数量变化

| 数据集 | 原数量 | 当前数量 | 变化依据 |
|---|---:|---:|---|
| D1 | 33 | 33 | 11 任务 × 3 方法，唯一组合；替换两项 B |
| D2 | 3679 | 3160 | 移除 594 条非 required；排除旧两项 B 的 30 条；加入新 B 28 条；恢复 T04 原始资格记录 17 条；补入 60 条未测资格约束占位 |
| D3 | 597 | 1927 | 原表是决策级视图；排除旧两项 B 的 11 条。其余原始 Trace 展开为 1710 条事件，新 B 加入 217 条原始事件 |
| 资源表 | — | 33 | 只对应当前 33 条正式 task-method 结果 |

D2 的恒等式为 3679−594−30+28+17+60=3160，没有为匹配历史行数补造观测。
D3 的 1710+217=1927；调用 start/return、原决策、实际工具事件分别保留，未按相邻时间生成因果边。

状态分布：`{"QUALIFICATION_FAILED":4,"PASS":12,"VALID_FAILURE":12,"INCOMPLETE":4,"PASS†":1}`。

## 两项 B 替换与协议

- T03-B：PASS†；9/9 原始物理检查；位置 0.136211 mm，保持速度 0.00244839 m/s；50 次直接数学调用，0 次 Provider，1 次最终物理验收。另有一次未完成的自动 GVS 元数据投影入口尝试，单列 automatic_profile_attempts=1，协议偏离不消除。
- T05-B：PASS；8/8 原始物理检查；位置 0.430093 mm，轴角 0.122439°；50 次数学调用，0 次 Provider，1 次最终物理验收。
- 两项正式 D1/D2/D3/资源表的旧 B 数值、事件与引用排除检查：通过。旧文件保留并在来源清单标记 ARCHIVED_REPLACED_B。
- 新 B 是 Codex 直接求解，其他 B 是原 LLM direct-tools 运行。method_variant 与每段 1 单元、4 坐标的离散配置均保留，不能据此宣称同网格因果优势。

## 发现及修正口径

- T04-B 原选中 c7 的资格残差为 5.673729409815388e−5 N.m，原边界 1e−7 N.m，joint_limits 亦失败；22 秒轨迹未执行。D1 使用 QUALIFICATION_FAILED，保留旧汇总 VALID_FAILURE 供追溯。未使用另一次补充运行的数值替代。
- T04-A/C 的准备状态资格数据通过原始 initializer 精确匹配确认；读取既有资格输出，没有重新求解。三方法均纳入原资格检查。
- T08-A 原表缺少 60 条资格约束位置，现在用原阈值、UNKNOWN 观测补齐，三个方法的覆盖率分母一致。T08-C 保留 development_valid 与 development_not_registered_SELECT。
- 原 D2 的有阈值约束与无阈值辅助观测分开；同一资格检查的数值和布尔副本不重复计入违反分母。未知或未执行不填零。
- C 的多版本 Core SHA 与配置版本原样保留，不统一改成当前 Core。七段 PHS C 的配置记录 base_commit=2c83f8b7bd654328dd7648f844295c54a7c15223；抽取 Trace 中没有单独的选中执行 SHA，core_sha_basis 明确注明这一缺口。

## 核查结果

- D1 唯一组合、D2 唯一候选/工况/指标、D3 事件唯一键、资源表唯一键：通过。同 task/method/condition 的候选 ID 唯一。T01/T02/T07/T10 的 C 使用不同工况绑定配置 ID，已精确核对各组 robot.structure 与 discretization 相同，保留原始 ID，不强行合并为一个。跨工况引用同一共享设计不当作重复样本。
- 原始事件 ID+类型+运行+Trace 的重复键：0 组，详情见 validation_report.json；未擅自删除原始重复记录。
- 直接数值核对 2859 条；数值冲突 0；未能定位原始数值的数值型记录 0。其余 31 条为原始类别等非数值观测，不强制转换。
- 已读取并核对存在性的 Store Artifact：237 个唯一 store/artifact 对；缺失 0。D1/D2/D3 每行可回溯到来源清单；无法追溯 0 行。
- 68 份物理 CSV、6,336,000 条记录：列数、有限时间、单调性和固定步长异常 0 份。CSV 行数不冒充累计积分成本。
- SHA256 清单覆盖 84,394 个指定原始文件、46,238,300,835 字节；重复路径 0，读取期间变化 0，缺失 SHA256 0。仅覆盖实验来源，未扫描整个仓库。
- 独立九段梯度 CSV 精确复制：18 行、6 个 branch；来源 SHA256 `91e296f37f56750df3fc59fbbe01f2191da2b2482b0e6012e8740d861af0d6bc`。未混入七段 C 的 ABC 数据。
- 显式 evidence-to-declared-action 关系 377 条，分布于 240 条事件；选中运行 317 条，前驱研究 60 条。旧表的 133 是人工 reviewed 决策行数，不能与关系边数直接比较。声明联系不证明效果或执行成功。

## 缺失与适用范围

33 条资源记录中的 UNKNOWN 数量：`{"llm_tokens":25,"wall_time_s":0,"integration_steps":1,"mathematical_calls":0,"physics_evaluations":0,"physics_cpu_s":32}`。完整按字段统计位于 validation_report.json。
T08-A 累计积分总数仍 UNKNOWN，仅保留原始确认下界 1,727,990。Main Token、Codex Token、CPU、墙钟缺失不估填。
原生执行没有显式 execution_id 的记录保留 UNKNOWN，来源文件和 artifact 仍可追溯。
连续量零边界缺少原始同量纲尺度时 signed/scale 为 UNKNOWN；满足原始判据的正向违反量为确定的零，未伪造观测。
不同来源的 charged numerical wall、累计研究墙钟、Codex 任务墙钟作用域不同，资源比较必须保留 wall_time_scope。

## 交付

D1_ABC_STATUS_MATRIX.csv、D2_ABC_CONDITION_METRICS.csv、D3_ABC_EVIDENCE_ACTIONS.csv、PHS2D_9SEG_GRADIENT_FIGURE_DATA.csv、RESOURCE_COSTS.csv、SOURCE_MANIFEST.csv、DATA_DICTIONARY.md、P0_AUDIT_REPORT.md、validation_report.json。
_build 保存只读抽取脚本、行数对照、原始引用核对及 timestep 审计明细，便于复核。本阶段没有图表或论文改动。


## 独立分支发布检查（2026-11-15）

发布范围严格为上述九份交付文件；原始证据与 `_build` 不提交。发布检查发现 SOURCE_MANIFEST、D1、D2、D3、RESOURCE_COSTS 和 validation_report 含本地工作区绝对路径，已统一替换为仓库相对来源标识；未发现个人用户目录、凭据赋值、常见访问令牌或私钥标记。此检查仅针对九份交付文件，不扩展为全仓库审计。

已先保留九份冻结文件的精确本地副本（`_build/local_frozen_before_publication_20261115/`，不上传）。发布版 CSV 的非路径字段逐格核对不变，来源 SHA256 与快照元数据逐项保留，D1/D2/D3/资源表/来源清单行数仍为 33/3160/1927/33/84394，九段梯度 CSV 字节不变。原始审计结论和已披露限制保持不变，未重新计算实验或原始证据 SHA256。

相对来源路径用于本地离线证据追溯；清单中的原始文件大多不包含在本次公开分支提交中，不能把清单路径解释为已公开上传的文件。
