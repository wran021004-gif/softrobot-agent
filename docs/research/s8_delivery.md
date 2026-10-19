# S8 交付与未达标结果（2026-10-20）

S8.0–S8.2 的实现、工程联调、回归及两项 S8.3 真实 DeepSeek/Strands 研究已执行。**没有找到新任务的完整可行解，实测 Agent 效率也未达到预期。** 第二目标获得一次有效的四系数子空间搜索改善；镜像任务只完成数学研究，没有开展新物理评价，也没有使用本轮新增初始化、子空间或多起点能力。因此不能把本轮称为全部 S8 科学验收通过或跨任务可行解发现成功。

交付包括可用工程能力、完整有界失败、原始请求/响应、独立验证、费用及可恢复失败设计包。没有修改任务阈值、扩大冻结预算、重开封存 Study 或生成成功标签。

## A. 仓库、提交和实现冻结

目标为 `D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc` 的 `feat/sorosim-matlab-nmpc`，起始本地/远端均为 `5b5777ce9f703fb4a76cf265b7c057aef49a28ce`，目标工作树开始时干净。未修改 IDE 指向的 rl-control-pilot、其他工作树或根目录用户文件。fetch 和 commit 因共享 `.git` 写保护使用已授权的提权权限；全部 push 均为普通 push。

| 提交 | 内容 |
|---|---|
| `bc8408c0` | S8.0 预检、工具准入、紧凑拒绝及工程证据 |
| `8778e4cd` | S8.1 任务相关控制初始化及类型契约 |
| `1cc2fdc6` | S8.2 稀疏系数、多起点和预算反馈 |
| `e26224ce` | S7 原始请求审计、配置、研究协议 |
| `4784cbda` | 真实工程联调及正式科学冻结 |
| `86980438` | 第二目标原始有界失败 |
| `f851ae41` | 依据第二目标暴露的问题修正摘要和合法 pointer 展示 |
| `a1536b1e` | 镜像任务原始数学研究及 STOP |
| `13d096a592ec543899cb24211986421f1bc7097a` | 最终数学结果展示、独立重构、计费和回归 |

第二目标冻结 `4784cbda555b5f94f992dcd98d99c9abe5f6a5ac`；镜像最初绑定相同实现，在 **0 Provider、0 物理评价** 时明确迁移到 `f851ae410ae76032f4939484595006a0d8005072`。迁移的 changed_scientific_dependencies 为空、material_behavior_change=false，任务、评价版本、预算与已用费用保持不变，见 [迁移记录](../../evidence/s8_verification/mirror_migration.json)。两项 Study 结束后才进行最后的数学摘要修正，未迁移或重跑封存研究，不能将该修正的潜在收益归入已完成实验。

最终实现 SHA 为上表 `13d096a5…`；本文及最终清单另作最后文档提交，避免文档提交 hash 自引用。最终提交与远端 SHA、干净状态及 push 结果在交付消息和本机 `runs/s8_work/final_git_receipt.json` 核对。远端目标保持 `origin/feat/sorosim-matlab-nmpc`。

## B. 文件变更与复用

生产 Python 相对起点 **+431/-46，净增 385 行**。新增生产模块恰为两个，没有为凑建议行数增加代码。完整逐文件路径、增删行数和用途见 [change_inventory.json](../../evidence/s8_verification/change_inventory.json)；其统计截止最终实现提交，本文及清单自身在最终文档提交中增加。

| 生产文件 | + / - | 用途及复用 |
|---|---:|---|
| `extensions/tendon_family/sorosim_session.py` | 5 / 0 | 原 Session 增加启动阶段；仍由同一会话启动、网关和退出 |
| `tools/research/tool_readiness.py` | 104 / 0 | 独立工程预检，复用 Store 预留和 contained worker；无全局引擎 |
| `tools/research/control_seed.py` | 29 / 0 | 纯有界正则化最小二乘；无 Store、调度或第二套控制器 |
| `tools/research/__main__.py` | 6 / 2 | 原公共 CLI 增加显式 readiness 命令 |
| `tools/research/config.py` | 6 / 0 | 将预检报告冻结进原 resolved configuration |
| `tools/research/contracts.py` | 37 / 4 | 原 Plan/控制请求增加初始化、严格活动索引及多个起点；省略时保留旧序列化 |
| `tools/research/agent.py` | 55 / 3 | 条件 Schema、紧凑错误、精确子字段、动态准入；保留 Harness/LiveBoundary/Offload |
| `tools/research/research_context.py` | 52 / 5 | 精确候选/来源、维度/时间/费用、工具状态及有界摘要 |
| `tools/research/physical_replay.py` | 70 / 1 | 原种子、binding、evaluate_schedule 接入目标引导和逐次收费 |
| `tools/research/local_control_search.py` | 44 / 29 | 原优化循环的系数子集及公共多起点；原收据恢复与排名 |
| `tools/research/core.py` | 3 / 1 | 原 dispatch 接线、预检准入；已结算操作优先精确恢复 |
| `tools/research/analysis.py` | 16 / 1 | 原分析准入、故障状态、实际数学证据路径及静态输入摘要 |
| `tools/research/mechanics.py` | 2 / 0 | 已计费启动故障之后标记运行时不可用 |
| `tools/research/execution.py` | 2 / 0 | 原完整执行保留失败并更新运行时状态 |

`budget.py`、`evidence_policy.py`、`design.py`、`rl.py`、控制校正器、任务评价器和物理后端沿用现有实现。没有第二套 Agent、Store、预算、物理评价器、排名、MATLAB 服务或全局优化器。新增 `s8_study.py` 是显式工程联调，`s8_audit.py` 是只读审计，不是新研究循环。至少四条实质语句的新函数 AST 精确函数体检查未发现重复，范围和限制见 [reuse_audit.json](../../evidence/s8_verification/reuse_audit.json)。

## C. MATLAB/数学工具真实预检

预检使用 `.mainline5-env/Scripts/python.exe`、同一工作目录、已有 MATLAB R2024a Engine、固定 SoRoSim `24d573a3…` 和三个值为 1 的数值线程变量。SciPy=1.17.1、CasADi=3.7.2；Engine 路径和上游逐文件 hash 在报告中。

第一次 contained 启动在写沙箱内复现 S7 的 UnicodeDecodeError，停在 engine_start，尚未计算机器人。原阶段、异常和 traceback 保存在 [初始预检](../../evidence/s8_readiness/initial/report.json)。一次针对进程权限边界的受控诊断，使用相同解释器/依赖/目录/环境，在允许 MATLAB 正常写运行环境的权限下，依次完成依赖校验、Engine 启动、environment 网关、sqrt(4)=2、Engine shutdown，结果为 [ready](../../evidence/s8_readiness/verified/report.json)。没有修改编码或重装软件；这支持“该运行权限下可启动”，不是对所有启动故障根因的排除证明。

两次预检均为 **0 Provider、0 科学后端、0 注册分析**，各占独立工程 Store 的一个操作预留。正式运行采用预检成功的权限方式。随后工程分析 1 次、正式分析 3 次均完成，未再发生 MATLAB 启动失败。预检不构造候选可行性证书。候选数学问题仍需自身适用性、数值验证和独立物理验收；真实运行发生已识别启动故障时，原收据/费用保留并暂禁后续相同工具启动。

## D. 上下文、真实 token 与错误成本

[S7 原始请求审计](../../evidence/s8_verification/s7_payload_audit.json) 逐条拆分固定指令、工具 Schema、当前 packet、历史模型消息、历史工具结果和协议部分。镜像累计规范化序列化 5,586,625 字节，其中历史工具结果 2,301,478、历史模型消息 1,980,075；第二目标累计 3,949,354 字节，其中两项分别 2,001,804 和 705,391。原始 S7 archive 成员 hash 均验证。

初版拒绝格式离线回放的错误正文合计：镜像 192,565→4,458 字节，第二目标 155,529→3,195 字节。最终 formatter 的 [同请求离线投影](../../evidence/s8_verification/s7_error_projection.json) 只替换已知错误 tool message，其他指令/Schema/历史完全保留：累计请求镜像 5,586,625→3,766,167 字节，第二目标 3,949,354→2,265,040 字节。科学执行是否开始在该离线投影明确设为 unknown，未由最终状态反推。**上述是序列化字节，不是 token 节省或决策等价证明。**

| 实际 S8 Study | Provider | Prompt token | Completion | Reasoning（已含在 completion） | Cache hit | 模型工具调用/错误 |
|---|---:|---:|---:|---:|---:|---:|
| 第二目标 | 24 | 1,695,171 | 76,374 | 68,901 | 101,888 | 43 / 16 |
| 镜像 | 24 | 1,396,303 | 51,347 | 40,044 | 96,256 | 38 / 11 |
| 合计 | 48 | 3,091,474 | 127,721 | 108,945 | 198,144 | 81 / 27 |

真实总 token 为 **3,219,195**。usage 逐请求取自 Provider，未自行估价，货币账单未知。错误率分别约 37.21% 和 28.95%，包括非法 pointer、错误视图/枚举、受保护阶段不允许的引用、未注册证据和 STOP 引用缺失。完整分解、字节、预算和 usage 在 [accounting.json](../../evidence/s8_verification/accounting.json)。

**S8 第二目标的请求、token 和错误均未比 S7 同名历史任务改善，且物理预算使用更少；不能声称整体效率提升。** S7 与 S8 的策略、源码、起始证据、结果和预算使用不同，只能作历史参考。镜像先进行了展示修复，也不能当成该修复的受控对照。

原始 reasoning_content、HTTP 响应 body、tool ID 和 Store 证据保留。逐个实际请求的工具配对均检查，已有已接收响应精确重放、未知结果不重发的回归通过。没有新记忆系统、辅助模型总结请求或消息历史手术。默认摘要和现有公共 Offload 继续工作，但完整结果的 offload 以及“工具摘要字段被误当成存储字段”仍造成了实际读取成本。两次展示修正均有边界和测试；最终数学摘要修正只验证了离线行为，尚未证明新的 Provider 效率收益。

## E. 控制初始化的实际证据

历史输入继承仍通过原 seed_control 完成，执行候选绑定、明确通道映射、零阶保持重采样和张力界校验。跨任务只转移结构/输入，task_acceptance=unmeasured，不继承通过。

独立 [工程联调](../../evidence/s8_engineering/integration_checks.json) 使用当前第二目标和原 S6 输入作为工程基线。模型请求为 0，完整物理回放 5/8、注册敏感性分析 1/1，公共操作 10/40：

- **物理响应引导：** 原输入 G=1.5045801264；对工程选定的 tendon_0 作一个完整差分回放，G=1.4356794862；有界拟合初始化再独立回放后 G=1.3328987762。该路径共 3 次完整评价，最后仍失败。选定通道和工程步骤不是 LLM 自主贡献。
- **数学响应引导：** 注册 input_sensitivity 验证通过，生成合法静态局部响应种子，记录 operating point、输入/模型/任务身份、矩阵、正则化、限幅和证据。其生成没有额外物理回放；该种子没有完整动态任务通过结果，保持 unmeasured。
- **常张力/历史来源与多起点：** 工程另比较一个常输入和历史来源，公共批次复用既有基线并新增 2 次回放。并非多起点算法优于单起点的科学比较。

所有生成输入、诊断、预测残差、真实成本和验证状态在原 Store archive。响应退化、无输入余量、非 reach 端点任务等返回诊断/不适用，不把失败强制变成“正确控制”。正式两个模型均未选择新引导初始化；因此不能声称它们改善了本轮自主研究结果。

## F. 参数子空间、多起点与预算

公共 control_search 在原请求上接受 additional_starts，每个起点先校验候选、任务、输入、通道顺序和网格。不同维度/顺序/网格拒绝；同次批次共享 evaluation_requests 和原 Study 总预算。已完成回放使用原 Store 收据。首个完整通过会终止包括后续起点在内的批次，既有成功门禁要求精确 SELECT。

第二目标模型自主选择一个起点、两个节点 `[0.2,0.3] s`，四个活动索引 `[4,5,6,7]`（knot-major，均为第二节点的四腱），response 方法、7 轮、36 次请求上限、差分 0.05 N、初始半径 0.4 N、系数界 1 N。未声明 correction_window，采用既有全网格插值语义：末节点之后保持最后偏移，不能把模型“final-window”文字解释为额外硬窗口。

实际 36 次 callback = 21 次新物理 + 15 次缓存复用；28 次差分 callback 中 16 次为新物理，另有 7 个局部提议。4 个活动系数之外始终精确为零。局部预测和实际反馈、信赖半径/solver 状态均保留在搜索原结果。缓存不计新科学评价；探针命中缓存可能意味着输入被边界截断或与已有序列相同，不能都解释为新增方向信息。

[独立重构](../../evidence/s8_verification/search_reconstruction.json) 对每个 callback 从起点、基函数和系数重建实际输入；验证非活动系数、声明窗口外不变、差分计数及缓存。工程多起点是真实接口验证；正式模型没有选择 additional_starts，不能归因多起点科学收益。

## G. 实际模型决策与科学自治范围

原始决策分别在 [第二目标](../../evidence/s8_variant/decisions.json) 和 [镜像](../../evidence/s8_mirror/decisions.json)。正式研究仍使用 `python -m tools.research run`、原 Harness、DeepSeekModel、LiveBoundary 和 Store。

第二目标模型提出以较小晚期系数子空间修正历史剩余速度/位置误差，自主选择上述节点、变量、方法和预算，读取反馈后又选择 target_equilibrium 分析。数学静态平衡位置残差约 1.80e-9 m，但未被转化成新动态控制；达到请求边界后由工程保护关闭，未接受模型 STOP。

镜像模型先读取结构和历史输入，选择 target_equilibrium，得到静态位置残差约 1.24e-8 m，再选择 linearization 并读取相关矩阵/指标。最后原生 STOP 成功，包含两项新数学结果的引用。没有新物理回放、新设计生成、引导初始化或控制搜索，不能声称完成结构—控制闭环研究。

完整 family_space_s7 可执行域保持开放，未限制为人工挑选的小组结构参数。NMPC、直接/残差 PPO、数学优化仍为可选能力；正式运行新 NMPC、NLP、重积分、PPO 训练和评价均为 0。工具可用不等于模型会有效选择或使用。

## H. 两项正式冻结研究及停止

| Study | 原目标 world m | Provider / 上限 | 公共操作 / 上限 | 新物理 / 上限 | 数学分析 / 上限 | 停止 |
|---|---|---:|---:|---:|---:|---|
| `s8-variant-live-20261019` | `[0.28,0.02,0.20]` | 24/24 | 64/150 | 21/64 | 1/4 | 请求耗尽，工程关闭，非模型 STOP |
| `s8-mirror-live-20261019` | `[0.29,-0.035,0.19]` | 24/24 | 38/150 | 0/64 | 2/4 | 模型原生 STOP |

Study ID 按 10 月 19 日创建后保持冻结，交付日期为 10 月 20 日。原任务仍为 0.35 s、控制周期 0.01 s、物理步 0.0005 s、保持窗口 0.30–0.35 s；位置上限 0.01 m、保持速度上限 0.02 m/s。任务 canonical identities 分别 `596fd628…`、`d24aeac7…`，与对应 S7 原任务相同。

第二目标 21 次新评价完整有效，均为同一个历史材料化结构的新控制。最佳终点/保持误差 **0.01026257076459409 m**，保持最大速度 **0.022357234539154065 m/s**，G=**0.11786172695770314**，位置和速度均超限。历史 G=0.1363182145，当前有限搜索改善但仍失败。所有逐次结果、完整验收和候选在 [summary](../../evidence/s8_variant/summary.json)，独立重算及实际张力核对在 [independent_audit](../../evidence/s8_variant/independent_audit.json)。

镜像没有本轮有效物理候选，不能把历史 G=3.6020739579 称为本轮结果。原 S7 完整失败方案保留为 [明确历史引用](../../evidence/s8_mirror/historical_best_reference.json)，本轮数学结果和无物理验证事实见 [summary](../../evidence/s8_mirror/summary.json)。

两项均无待恢复操作、未结算收据或资源占用。数值累计分别约 35.4373 s、22.8224 s，工程联调约 28.8139 s；这些是现有数值账本测量，不是完整 CPU 时间或端到端研发墙钟，也不作为节时证明。余额均不转移、不重置、不继续消费。

## I. 可恢复设计与证据交付

第二目标的 [design_package.json](../../evidence/s8_variant/study/design_package.json) 包含完整机器人参数/配置、35×4 实际控制、任务、原接受组件、raw/evaluator/source 引用，accepted=false、status=best_valid_candidate；另有 [best_control.json](../../evidence/s8_variant/best_control.json)。恢复依赖同目录 immutable_artifacts.tar.gz 和逐成员 archive_manifest.json，hash/输入绑定/独立指标已验证。

镜像 [design_package.json](../../evidence/s8_mirror/study/design_package.json) 明确为 no_valid_candidate、accepted=false。当前 Study 的候选、未测种子、数学结果、Provider 证据都在 archive；已知最佳完整物理失败包来自 [原 S7 mirror](../../evidence/s7_mirror/best_control.json)，归属保持历史，不冒充新结果。

工程包、两项正式包均逐成员 SHA256 校验；实际请求工具 ID 配对检查通过；所有本轮新物理采样重算 G 并核对实际张力与序列。configured API key 在本轮变更文件和 archive 成员扫描为 0 匹配，见 [secret_scan](../../evidence/s8_verification/secret_scan.json)。未持久化认证 header 或提交私有环境文件。

## J. 测试、结论边界与剩余问题

分阶段 S8.0 20 项、S8.1 30 项、S8.2 50 项通过，集合有重复，不能累计。最终相关回归 **130 项：129 通过、1 跳过**；跳过仅为原显式 opt-in 真实 RL 测试。最后仅改变数学摘要字段顺序后，17 项相关检查再次通过。日志为 [final_regression](../../evidence/s8_verification/final_regression.txt) 和 [final_display_tests](../../evidence/s8_verification/final_display_tests.txt)。普通 unittest 未启动新 Provider、真实 MATLAB、MuJoCo、NMPC 或训练；真实联调均由显式 CLI/工程驱动运行。

测试覆盖启动/网关、Unicode 异常保留、缺依赖/超时、工程与科学收费分离、工具准入、条件 Schema、精确错误、不同目标/通道/网格、界限和退化响应、稀疏系数、兼容起点、收据复用、共享预算、首次通过停止及既有 Strands 恢复。真实物理覆盖仍为两段四腱；纯数值 1/3/6 通道夹具不是任意拓扑物理通过证据。

结论分别为：工程工具可用、注册数学诊断可计算、公共新接口可执行、真实 Agent 确已运行、第二目标有限控制搜索有所改善；**新任务可行解、跨任务自主闭环及整体成本优势均未证明。** 镜像甚至没有推进到物理评价，未满足该项 S8.3 新能力使用要求。

主要剩余问题是模型把大量请求花在字段/视图探索和重复读取上，收尾保留也被错误读取消耗；可用数学静态输入没有进入实际动态验证，新增引导初始化/多起点未被正式模型采用，许多物理预算闲置。最后的精确数学 pointer/静态输入摘要已离线修正，但需要未来独立授权和冻结研究验证其实际收益。未通过扩大预算、放宽任务或额外重开 Study 掩盖这些问题。
