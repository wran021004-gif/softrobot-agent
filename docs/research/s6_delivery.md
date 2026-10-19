# S6.0–S6.3 交付记录（2026-10-19）

本轮基线为 `68c9e61413e896e191000d47c0509eb7be6a4f1b`，目标分支为 `feat/sorosim-matlab-nmpc`。开始时目标工作树干净，fetch 后本地/远端差异为 0/0。IDE 中其他工作树没有参与修改。

工程接入复用既有 Strands、DeepSeek transport、Plan、Core、Store、预算、archive importer、candidate generator、physical replay 和原始验收。新模块 `research_context.py` 仅负责已授权历史的精确导入与紧凑研究视图；没有第二套执行器、缓存、预算或评价器。`control_search` 是新增明确动作，旧 `search` 保留原义；只有显式 `research_decisions.version=research_decision_v1` 的新 Study 启用决策审查。旧 Plan 序列化省略新增空字段。

P1 最优实际张力通过原 archive/member SHA256 验证，并与新候选的机器人、任务、seed、模型、设计、时序和腱顺序精确比较。历史观察保留旧执行身份；原始控制可以作为新搜索基线而不重复物理执行。只读测试恢复完整 35×4 实际输入；仅 0.30/0.33 s 速度超限，G=0.054502039，历史结果仍是有效失败。

通用接口 v2 从实际通道和时间网格确定维度；v1 保留旧 35×4 契约。指定修正窗口时，窗口外的基函数严格为零。局部响应仍评价全部终点和保持约束。当前数值优化器是 reach 任务工具，其他任务明确 unsupported；不声称实现障碍或接球物理平台。新结构可显式以旧同通道控制初始化，但重新绑定新设计/模型并由原独立评价器测量，不继承旧验收。

执行前，Core 从可信 Store 结果解析证据，拒绝未注册引用、跨任务证据、跨设计/模型推论及未获支持的全局结论；合法探索无需先获得数学可行证书。每次新物理评价仍逐次经公共 replay、Store 和共享后端额度准入。批处理也保护收尾操作额度，首个完整通过后停止。中断只封装已结算证据；不自动重启未知工作或声称恢复优化器内部状态。

预执行验证：72 项聚焦测试通过；随后新增公共搜索缓存/重复请求验证及独立公共能力检查，50 项相关测试通过。执行命令使用现有 `.mainline5-env/Scripts/python.exe`、仓库 PYTHONPATH 和已安装 MATLAB Engine 路径，三个数值线程环境变量均为 1。一次未设线程变量的回归被现有 NMPC 环境准入拒绝，设为冻结值后通过；没有在测试中运行真实 provider、NMPC、PPO 或物理步。早期 tempfile 测试触发 Windows ACL/SQLite 清理问题，改用仓库测试目录、独立 fixture grant 及 GC 后通过。一次测试初始化在 DB 建立前绑定了无实际科学消耗的 `s6-2-20261019` grant；它保留在本地 authority 中，未删除或重置。真实 Study 明确使用带 `-live-` 的 ID，测试此后使用独立 UUID fixture grant。

真实研究尚待启动。各 Study 的 provider、公开操作、共享后端及数学/NMPC/PPO 上限在 `configs/research/study_s6_*.json` 中冻结；S6.1 不启用数学、NMPC、PPO。S6.2/S6.3 不借用封存预算。真实模型动作、原始请求、反馈、成本和接受结果将由既有 export 及 `python -m tests.research.s6_audit` 归档，完成后更新本报告。当前没有新增物理成功结论。
