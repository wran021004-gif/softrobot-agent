# 已完成实验的分析协议

样本：T01–T10 与 PHS2D，每项 K0S0、K1S0、K0S1、K1S1，共 44 单元。正式目录由 FORMAL_COHORT_MANIFEST.json 指定，旧的配置无效单元单独归档，费用在 summary/SETUP_INVALID_COSTS.csv，不作为消融科学失败。

研究决策模型记录为 gpt-5.6-sol，reasoning effort high；Main 和 Reporter 关闭。每个单元的初态身份、科学 specification、任务协议、预算、实现提交、Core 回执和终态均保留在 episode_manifests。分析只读 SQLite 和原始日志，禁止调用研究执行入口，禁止重置或重跑。

资源允许角色：K0S0 无，K1S0 knowledge，K0S1 skill，K1S1 二者。可用目录不是正文读取证据。RESOURCE_AVAILABILITY 是可用性目录，RESOURCE_TO_ACTION 是实际接口操作，RESOURCE_ACTION_CHAINS 保存原始自述评估和后续调用定位。科学结论由本单元原生物理验收及 SELECT 核验。

正式通过须 native selected 存在，且 success_gate.observed_task_pass 或已完成 research_plan 原生返回 selected=true 与 task_passed=true。兼容既有六个不同 gate 结构的旧回执，不能只查一个 gate 字段而漏计。研究 stopped、CLI ended、物理完成、原任务通过和 SELECT 分别记录。

本报告比较已记录的最终工作流结果。各单元的最终上下文和实际资源上限存在差异，物理预算原始值与最终值均逐单元列出；时间终止和接口中断也影响成本与可达阶段。因此这里的因子对比是描述统计，不能解释为严格固定资源、随机重复条件下的独立因果效应。

接受率边际差：K = ((K1S0 + K1S1) − (K0S0 + K0S1))/2；S = ((K0S1 + K1S1) − (K0S0 + K1S0))/2。交互项 K1S1 − K0S1 − K1S0 + K0S0。对每项任务先计算，再取 11 项均值。全矩阵和负/中性转变均保留。

物理违约使用原生记录的有效完整评估。offline_frozen_task_v1 先核查原生组件和来源绑定，再由 constraint_margins 计算 max(0, −margin/abs(limit))，满足零边界记 0，违反零边界且无尺度记未知。其他协议使用归档 Core 的纯 task_gap 读取逻辑。多工况汇总要求同一物理结构和所有 required 工况；T08/PHS2D 用证据内部完整协议，不把某个局部轨迹当作完整通过。状态、单位、边界和各组件原值完整保留。

费用取实际原生 shared ledger；物理启动计数另存，避免误当计费。数学完整性取 Core scientific_computation.complete。token 为现存已完成回合的去重记录，输入包含缓存，思考 token 不重复加总，不估算 provider 请求或缺失用量。

复现：先在本地完整原始目录中运行 publication/build_dataset.py，再依次运行 publication/audit_contexts.py、publication/analyze_and_plot.py 和 publication/verify_delivery.py。只重绘图可运行 publication/analyze_and_plot.py：没有全量原始日志时自动读取已交付的数学、干预和资源链紧凑表。只读全量提取需要原本地数据；当前 Core 阅读器源码另存 source_snapshot/FINAL_CORE_READER_SOURCE_f252213.zip。运行环境见 publication/ANALYSIS_ENVIRONMENT.json。
