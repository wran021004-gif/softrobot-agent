# 同一 v3 活动的结构续行

2026-10-07 附件 `9dae342a-539d-453e-a481-0fa61888934d` 授权在四次既有
实质修复之外再修复最多三次；累计上限七次。新记录追加于
`evidence/research_native_development_v3_20261007/structural_continuation_20261007/`，
原活动、同一 session、总预算、既有计费和 live 时间戳均保留。
截止时间仍为 `1791377029.4261196`（2026-10-07 12:43:49.426 UTC）。

第五次修复处理共享历史参数读取。`historical_parameter_projection` 用当前已授权
schema 解释旧选择器，保留旧 common selector 的非默认值，并核对源身份、原始
provenance 与实际截面/材料数值。原配置和 builder 身份仍供科学匹配及严格复用检查；
临时投影只供参数解释和遮罩比较。无法映射的历史记录保留且给出明确 unavailable
原因，不能当作新候选无效或“历史不存在”。准备和 known-point 循环共享这一边界。

离线 gate 的实际已接受方案为 `acf51de37cc32112...`，原生决定为
`9d47b0f3661a7243...`（model-4）：nominal、seed17，source 为历史 incumbent
`91c3ba1b01d6499fb26df8f95409401b`，近段比例 1.00/1.05，terminal/holding
速度权重均固定 0.05，稳定控制器 v7。这是模型拟定的有限枚举，非数值优化。

gate 使用隔离数据库副本并禁止实际 Host.invoke、提供方和物理后端入口。
首先复现旧错误，再验证真实准备、known-point、构建、注入执行/评价/profile 回执、
联合反馈和下一请求组装。验证 legacy 0.97、原始字节和 strict reuse、冻结初始化、
reach-pass/holding-fail、已完成回执恢复及 unknown 不重放。合成回执仅为工程夹具。

全链检查另发现反馈后输入超过原上限。第六次修复只将重复的输入内字典表示合并为
指向首次完整表示的 JSON pointer，并将已在原始档案保留的 claim history 作为可检索
详情；精确指标、事实标识、别名、失败、当前权限、原预算和模型/TLS 设置保留。
已完成纠正后的旧 rejected draft 单独归档，不重新打开纠正或重置已消费额度。

显式同会话迁移仅允许这三份共享基础设施文件的 source hash 变化：
`tools/candidate_parameters.py`、`tools/platform_search.py`、`tools/context_assembly.py`。
声明、schema、包版本、数值内核、输入、授权和账本不能借迁移变化。
原始迁移和旧失败快照均保留。入口为 `continue-structural`，直接恢复已接受计划，
不要求模型重复提案，也不重跑两次已完成 terminal 权重实验。

较早 Stage 359 整类回归仍含历史后端指纹拒绝和旧 reuse 预期失败；记录完整失败日志，
不放宽科学匹配或缓存规则。当前接受计划全链、现行 v3、参数 catalog、明确枚举基本
检查、context 和账本安全检查组成此次实际工程 gate。实跑结果与最终停止点随后追加。
