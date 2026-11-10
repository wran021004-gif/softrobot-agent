# P3 运行过程、研究反馈与资格门槛审查

审查快照：2026-11-10 16:01 +08。当前同一 Study 的 27 份 Plan、14 份分析、请求及错误事件；对结果 2、9、10、14 的 plus_x 原始密集尾段重新统计。所有统计来自已有不可变 Store artifact，未调用 Provider、未积分、未更改冻结任务、运行代码或账本。Study 自身继续运行；快照时已使用 83/100 次请求。

数值和引用见 [process-audit-measurements-20261110.json](process-audit-measurements-20261110.json)。该文件保存原始引用、提取范围、决策、错误和冻结配置。此审查不是全仓库证明，也没有新做时间步收敛、延长保持或匹配动力学实验。

## 判断

Main 的总体物理目标正确：研究同一根腱的低载松弛、高载张紧，区分研究计算与独立验收，并尝试匹配干预。但存在已经影响搜索方向的解释错误，以及阻碍正确动作的工具契约问题。当前优先级应是修正机制反馈、恢复可用的搜索与诊断对照、减少昂贵重复，而不是全面删除稳定性门槛或重建整个框架。

### 1. 已证实：把“无合格松弛到张紧转换”当成“没有张紧”

结果 2（候选 68）的 plus_x 原始尾段显示 tendon_3：

| 观测 | low | high |
|---|---:|---:|
| 最小张力 N | 0.0206037587 | 0.4282965842 |
| 最大张力 N | 0.0206037588 | 0.4282965843 |
| 活动约束比例 | 100% | 100% |
| 最大长度超额 μm | 0.1041 | 2.1640 |

两阶段均已受力；低载张力超过 low_tension_max=0.005 N，且几何间隙不满足低载正松弛。`slack_to_taut=0` 是多个谓词的合取失败，不是“高载无张力”。但 Plan 3、5、7、10、11 等反复使用 non-engagement 解释，沿减小 payout、增加腱路增长的方向继续研究。这些方向没有得到该二值结果的支持；对过早参与受力的同一结构，继续减小 payout 可能反而更早张紧。

结果 9 的 low 张力约 0.087 N、high 约 0.338 N；结果 10 的 low 约 0.085 N、high 约 0.329 N，也不是高载完全不受力。不能把不同拓扑的所有失败都归成同一个原因。实际修改仍需同结构、同条件的证据，不应据此替 Main 写入某个正确参数。

工具原因：`extensions/reference/passive_evaluation_v2.py::stiffness` 最终只返回合取后的 `slack_to_taut` 和成功腱名；失败时没有逐腱逐谓词余量。其分母检查还先于转换计算，分母无效时连可独立观测的转换组成事实也不返回。`summary` 提供阶段最大张力和末态分类，缺少同一根腱 low/high 的完整配对谓词。原始数据可读，但紧凑反馈不足以阻止相反的解释。

建议：在已有结果视图中输出每根腱的低载张力上限、最小松弛、高载张力下限、高载残差、活动约束覆盖和每项失败原因；刚度不可解释时仍返回这些独立诊断事实。区分 early engagement、no high-load engagement、intermittent engagement、constraint violation、unresolved。保留正式合取判定。

### 2. 已证实：被声明可用的结构搜索在当前冻结配置上无法编译

5 次原始 `research_plan(action=search)` 均未进入搜索计算。前期含 schema/拓扑选择错误；补齐选择后，至少 3 次因同一 fidelity 错误被拒绝。原始事件和查询保存在测量文件。

冻结 fidelity：final_evaluation 为 12 cells/segment；screening 仅有 diagnostic=8、refined=16、fine=32。`tools/research/structure_intent.py::compile_search` 要求 screening 中恰好一个完整字典等于 final_evaluation，因而必然抛出 `Unique frozen final screening fidelity required`。使用已有搜索请求并解析 owned parent 后，零计算地复现了该错误。

还有后续静态代码阻塞：`tools/research/passive_search.py::problem` 对需要 paired mechanism 的任务拒绝 `passive_task_response`，返回 `PASSIVE_TASK_SEARCH_REQUIRES_SUPPORTED_UNPAIRED_COMPLETE_RESPONSE`。当前任务恰好需要 paired mechanism；即使修复 fidelity，尚不能宣称动态搜索已贯通。后者本轮按源码确认，未修改配置绕过首个阻塞再执行搜索。

建议：让 discovery/schema/admission 共用实际支持条件；对 exact fidelity 使用冻结正式离散模型，或显式声明不支持并给可行动反馈，不能自动改用 8/16/32。把 baseline 动态诊断和 paired mechanism 验证分开授权与表示，再通过当前 P3 冻结配置的端到端准入检查。不能只验证 schema 字段存在。

### 3. 已证实：探索被绑定到昂贵的全任务和配对流程

`structure_research.prepare_context` 要求 finite_time_task_response 完整双向加载，且本任务必须传入 passive_ablation；`execute_pair` 只检查 baseline 是否完成，不检查它是否值得做机制验证，所以低载已过早张紧、动态不合格或性能明显失败时仍运行两条 ablation 轨迹。最新轮 baseline 约 293 s、ablation 约 258 s，总 native 593 s；这是成本分解，不是承诺可直接省掉全部 258 s。

稀疏检查目前仅降低腱路几何检查频率，保留 640,000 积分步、95,008 次静力平衡 forward 和所有密集尾段、逐步 CSV。它解决了一个主要耗时来源，没有解决每次探索都做完整配对的问题。

建议：复用现有执行器，增加明确的 baseline-only 诊断范围；Main 根据实测机制决定是否配对。静态多载荷、单阶段或延长保持可作为另行声明的局部诊断，不能冒充原 20 s 任务或其验收。完整配对和原独立 Replay 保留。

### 4. 已证实：无正式标量目标时，交互对照提前停止，且旧基线重算

结果 10 和 11 的低/高位移、刚度、资格漂移完全相同；后者是针对同一候选申请的 interact。`structure_research.calculate` 的缓存为请求内局部 `cache={}`，新请求重新执行基线；随后分支 `dynamic and base.observation.value is None` 将 direction 标为 feasibility_comparison_only，跳过后面的 interact 对照循环。结果 11 仍花费约 2162 s native 时间、640,000 步，未获得原定三个新对照。

不发布无效目标的梯度是正确的。但“不能计算正式任务梯度”不等于“不能收集扰动后的诊断事实”。建议在准入时明确预计会跳过什么，或允许以诊断事实为目标的有限对照，返回独立可解释的分量；不能发布正式下降方向。对完全相同物理、协议、版本、初态、干预和检查范围的已有基线，显式引用复用并记账为零新增积分。独立 Replay 的新鲜执行要求不应复用。

### 5. 研究组织：研究假设有价值，但信息增益和归因不足

积极证据：Main 通常明确区分事实与假设，不宣称失败证明不可行；Plan 12/13 尝试匹配黏性干预；最新 Plan 27 仅将最新候选黏性从 0.0002 改为 0.0007，保持其他条件，以判别未稳定响应，属于合理的可检验假设，尚无结果。

问题：Plan 24–26 同时换全链拓扑、payout、材料模量和黏性，性能变化难以归因；同类低信息试验持续多轮，却没有先读取同一腱的直接证据。早期增黏性后的四段结构漂移也没有改善，故不能将最新所有失败直接归因于黏性不足。Plan 27 是新的匹配试验，不能把先前不同拓扑结果当作它已被证伪。

83 次请求快照：conversation=65，reporter=18。此前 82 次请求时有 26 份 Plan、8 个 tool_request_error、2 次 generation_failure、0 个 search_result。输入报文累计约 22 MB，最大约 740 KB；这些是字节，不是计费 token。Reporter、额外读取、SDK handoff 均有组织成本，不能把 conversation 请求全叫无效；也不能把所有等待全归因于积分。事件显示 Reporter 完成到下一轮生成之间还发生了数分钟的边界与恢复。其 CPU/I/O 归因需要专门 profile，本轮没有测出百分比。

建议：默认交付紧凑的逐谓词事实和失败余量，解释按新信息需要触发；避免每轮重复同一种“不合格但不能归因”的长报告。沿用现有 Store/知识/角色组织，修复事实投影和实际能力一致性，无需先重写整个架构。

## 资格检查是否多余或过严

当前规则仅检查每个 4 s 阶段末尾的 0.25 s 密集窗口；加载在阶段开始后的 0.5 s 内 ramp 完成。不是要求整个加载过程速度都小。middle 用于刚度的两段增量，因此只检查 high 不足以解释准静态渐进刚度。

最新结果 14 的 plus_x high：

| 检查 | 实测尾段最大值/漂移 | 门槛 | 超限倍数 |
|---|---:|---:|---:|
| tip speed | 203.679 mm/s | 1 mm/s | 203.7 |
| monitor speed | 172.791 mm/s | 1 mm/s | 172.8 |
| tail drift | 8.961 mm | 0.5 mm | 17.9 |
| generalized velocity | 0.13124 rad/s | 0.01 rad/s | 13.1 |
| zero-velocity static balance | 0.007077 N·m | 0.00001 N·m | 707.7 |
| tendon length excess | 2.602 mm | 0.05 mm | 52.0 |

最新失败并非微小门槛误差。结果 2–5 曾通过全部阶段资格，但仍缺少渐进刚度机制，所以这些门槛并非在此工具中普遍不可满足；这也不能证明它们对整个设计域已充分校准。

刚度分母：最新低到中、高到中的位移增量约 6.72、12.95 mm；已有尾段位置 spread 约 3.33 mm，冻结规则采用 10 倍 spread，分母门槛达 33.26 mm。拒绝给正式刚度比有明确数值原因；将保护去掉会把大幅变化的均值当作稳定刚度。是否调整倍率属于误差校准问题，不是补一个小 epsilon。

可以区分三类规则：

- 速度/漂移：对准静态刚度有实质意义。存在覆盖重叠；在相同连续轨迹和监测点上，1 mm/s 在 0.25 s 内最多移动 0.25 mm，小于现有 0.5 mm 漂移阈值。这是理想连续条件下的冗余，不是仅由有限采样证明的等价；tip 与 material monitor 的绑定、采样一致性也需核对。可简化诊断展示，但不是当前两个数量级速度失败的原因。
- generalized qvel 和绝对广义力矩残差：依赖离散坐标和材料阻尼，需要做不同网格、dt、加载尺度下的校准。结果 9 高载速度仅 0.0239 mm/s、漂移 0.00466 mm，而 static balance 为 2.12e-5 N·m，约为阈值 2.12 倍；恢复段约 2.23 倍。这是值得优先核查的边缘否决，但该候选同时有非法腱路、高载超限、早张紧，放宽该项仍不会成功。建议报告分量与相对尺度，并比较沿原轨迹的原始力平衡、置零速度重算、求解器容差和网格效应，才决定是否改正式阈值。
- length excess：MuJoCo unilateral limit 是软约束，不能把零超额当作理想硬约束直接推断；但超额必须受控，否则不可把结果解释为定长腱机制。最新 2.60 mm 对 0.05 mm 已达 52 倍，不能通过删除门槛得到可信刚度。需先分辨物理柔顺、数值软化及积分误差。

参考：MuJoCo 官方 Modeling 文档的 solver parameters 说明，solref/solimp 控制软约束响应；固定理想硬长度约束与其动态响应不是同一个模型。<https://mujoco.readthedocs.io/en/stable/modeling.html>

## 建议实施顺序

1. 先修已有结果的逐腱、逐阶段、逐谓词反馈，纠正“无转换=未参与受力”的解释；读取现有数据即可，不需重算。
2. 修复 search 的 fidelity 与 paired capability 契约，并用当前 P3 冻结配置验证可达路径与拒绝原因。
3. 拆分探索诊断、合格机制配对、独立正式验证；增加精确身份的显式基线复用，允许无正式标量时的诊断对照。
4. 再 profile 稀疏模式剩余的逐步观测、密集 static balance、序列化和 handoff，依据实测削减成本。
5. 单独做门槛校准。正式任务若改保持时间、绝对残差阈值或刚度误差倍率，须显式新版本及对照；不能回写旧结果为合格。

本轮交付仅为审查和原始事实重统计；上述代码修复和门槛校准尚未实施。没有向 Main 注入历史成功结构或指定正确候选参数。
