# S7：任务驱动结构—控制研究与有界失败交付

S7.0–S7.3 的接口开发、回归、真实 DeepSeek/Strands 研究、独立 MuJoCo 评价及归档已执行。**两个新任务均未找到满足原验收的可行解，不能交付通过标签的 `(d*, U*)`。** 本轮交付公共研究能力、两项真实有界失败、各自最优有效结构与控制，以及完整原始证据。原 S6 可行解和全部封存证据保持不变。

## A. 仓库、冻结和提交

工作树为 `D:/softrobot-agent/.worktrees/sorosim-matlab-nmpc`，分支为 `feat/sorosim-matlab-nmpc`。起始 SHA 为 `6629b37f976ad7fc63521171082f6a8f1cb7e4e5`，初始目标工作树干净；未修改 IDE 中另一个 `rl-control-pilot` 工作树，也未清理根目录用户文件。

| 提交 | 内容 |
|---|---|
| `09c23504338da3e1b58699b1cafc9f8116ec49f7` | 上下文、任务输入、设计与控制接口、冻结配置和协议 |
| `3b1b93aa3c7f3daf4ff4186f2c50390ee2d592b2` | 真实连接与独立工程联调证据；两项正式 Study 的首次实现冻结 |
| `d8ded1527eb8b2f1c812c78d92e7ae4c9c4c61d0` | 修复显式证据读取和不完整执行的上下文；原 Study 原预算迁移 |
| `68c27fe2` | 两项正式研究原始证据和失败交付包 |
| `84569f57b7573ab5452e8ddfc07fd50aee14fa25` | 公开条件参数目录、完整计费与交付核验 |
| `077fdf85a2c8209fea8f809b285dfeb360a1f525` | 修正目录中继承默认值的描述，保持生成器物理语义不变 |

最终代码/证据 SHA 为 `077fdf85a2c8209fea8f809b285dfeb360a1f525`。本报告作为最后的文档提交，其完整 SHA 由 `git log -1 --format=%H -- docs/research/s7_delivery.md` 确定；交付时的本地/远端完整 SHA、干净状态及 push 返回码另记在本机 [最终 Git 回执](../../runs/s7_final_receipt.json)，并在交付消息报告。这样避免把文档自己的提交 hash 写入自身造成循环。

普通 push 目标为用户明确授权的 `git@github.com:wran021004-gif/softrobot-agent.git` 的 `feat/sorosim-matlab-nmpc`。首次自动审批因目的地/载荷尚未核实而拒绝；核实附件授权、origin 和内容后，前两次提交已正常推送。最终报告提交后再次普通推送并核对 HEAD。未强推、未合并 main、未重置工作树。初次无提权 fetch/commit 曾被共享 `.git` 的只读沙箱阻止，随后使用已授权的 Git 元数据写入权限完成。

## B. 工程变更与复用

生产 Python 相对起点 **新增 363 行、删除 25 行，净增 338 行**；没有新增生产模块。配置、测试、文档和研究证据另计。完整逐文件清单及行数见 [change_inventory.json](../../evidence/s7_verification/change_inventory.json)，包括本文和生成清单自身。

| 生产文件 | 职责与复用 |
|---|---|
| `extensions/tendon_family/family_space.py` | 从既有域生成条件参数目录，补充物理参数域与旧序列化兼容；复用 `parse_space`、`validate_request`、`Domain` |
| `extensions/tendon_family/generated_serial.py` | 在既有 `generate_family` 内应用经域校验的密度、弯曲黏性、自然曲率、截面角；不另建生成器 |
| `tools/research/agent.py` | 有界 packet、动作 schema 裁剪、公共 Offload 配置、显式读取视图；保留原 Harness、DeepSeekModel 和 LiveBoundary |
| `tools/research/config.py` | 在现有 defaults/task extends 与 resolve 中校验小型 context 限额和控制种子声明 |
| `tools/research/contracts.py` | 在原 Plan 加入 `initialize_control`，在原 EvidenceQuery 加入视图、字段和区间；复用 Pydantic 边界 |
| `tools/research/core.py` | 原 dispatch/recover 路径接入控制初始化、证据视图和统一设计包导出；仍用原 Store、预算与任务接受机制 |
| `tools/research/design.py` | 原 candidate builder 中接入已有 recipe/solver 的稀疏 patch；不允许 patch 任务 settling |
| `tools/research/evidence_policy.py` | 新动作的意图、候选与来源准入；不完整 acceptance 保持诊断性质 |
| `tools/research/physical_replay.py` | 复用 `binding`、`model_context` 和 Store，生成合法候选专属初始序列并计时 |
| `tools/research/research_context.py` | 历史观察与跨任务控制种子分开；纯确定性有界投影和可取回预览 |
| `tools/research/state.py` | 原 closeout 可读引用集合包含已注册初始化控制 |

配置沿用 `family_study_defaults.json` 和已有控制/任务继承机制；新任务仅需 Study/task JSON。新增 `tests/research/s7_study.py` 是显式工程驱动及归档组合，`s7_audit.py` 是离线校验，均不是第二套研究循环。真实研究仍从 `python -m tools.research run` 进入。

新函数的实质 AST 函数体精确重复检查未发现重复；检查限定为至少四条语句的新函数体，不等同于一般语义克隆检测。没有新 Store、预算系统、任务注册器、优化器、会话系统、向量数据库或多 Agent 架构。完整检查范围见 [final_verification.json](../../evidence/s7_verification/final_verification.json)。

## C. 上下文、恢复与真实 token

保留安装的 `strands-agents==1.59.0`、`strands-harness==0.2.0`，未升级依赖。实际检查发现 `BeforeModelCallEvent` 只开放取消字段，未采用未证实的临时消息注入。保留稳定研究指令前缀和既有动态 system packet 机制；不改写 Strands 消息、推理或工具配对。

从封存的 S6.2/S6.3 读取 15 个真实决策包，对相同状态作确定性有界投影，并计入新增控制能力描述。合计序列化 UTF-8 大小从 **1,019,691 字节变为 371,670 字节，减少 63.5507%**。各状态减少约 4.79%–77.65%，没有把每个状态均称为减少 30%。任务身份、任务约束、最优有效候选身份与违反量、预算、方法额度、合法动作、完整新结果引用集合及保留失败样本均经过等值/成员检查。

该比较是决策包的字节规模，**不是完整会话 token 的受控性能比较，也不是实际 token 节省证明**。原 packet 和新投影引用、逐项覆盖检查保存在 [context_comparison.json](../../evidence/s7_verification/context_comparison.json)。其中 schema 大小是当前完整 schema 与受限动作 schema 的示例，不代表每次正式研究请求的固定减少比例。

启用 S7 紧凑配置时，公共 `Offload.truncate` 的阈值为 1500、预览为 500 token；旧 Study 仍使用原设置。原内容保存在 Store/Strands Offload 中，按精确引用取回；没有辅助 LLM 总结请求。EvidenceQuery 支持 `summary`、`full`、`fields`、`range`，以及交付阶段新增的 `capabilities`。默认模型读取是确定性摘要，显式 `view=full` 可取回完整值。轨迹区间查询需指定实际列表 pointer，例如 `/samples` 或 `/trajectory/tensions_n`。

| Study | 请求数 | Prompt token | Completion token | Reasoning token | Cache hit token | 最大 prompt |
|---|---:|---:|---:|---:|---:|---:|
| 连接检查 | 2 | 18,134 | 2,521 | 980 | 2,048 | 11,025 |
| 镜像任务 | 21 | 1,673,885 | 58,810 | 42,700 | 82,944 | 149,931 |
| 第二任务 | 20 | 1,212,596 | 34,362 | 18,454 | 68,224 | 112,683 |
| 合计 | **43** | **2,904,615** | **95,693** | **62,134** | **153,216** | **149,931** |

总 token 为 **3,000,308**，cache miss 为 **2,751,399**。这些均取自原始 provider usage，reasoning 已包含在 completion 内，不再加一次。真实累计 prompt 大于 S6 的累计值；请求数、任务和失败/读取行为不同，不能据此宣称实际 token 成本已下降。provider 未返回货币账单，未虚构金额。逐请求原 usage 及分项额度见 [accounting.json](../../evidence/s7_verification/accounting.json) 和每项 Study 的原始响应归档。

保留原始 wire 请求、响应字节、reasoning_content、工具 ID 配对及精确重放边界。离线 HTTP fixture 验证已接收响应只对完全相同的请求重放且不再次计费；恢复时同时恢复原 system 内容和工具定义。原始不确定结果会阻止继续发送。

真实运行确实暴露并影响了研究流程的两个工程缺陷：显式 view 默认合并错误，以及 NMPC 失败时 `acceptance=None` 导致上下文崩溃。修复后保留原会话、Study 身份、全部结果和费用，经显式实现迁移续跑；因此不声称新旧 Agent 决策等价。修复边界见 [repair_boundary.json](../../evidence/s7_verification/repair_boundary.json)。

## D. 任务、设计和控制空间

两项目标在任何 S7 物理执行之前固定，见 [s7_protocol.md](s7_protocol.md)。它们使用相同执行指令、family_space、工具、Store 生命周期和验收链路；第二目标没有根据实验结果事后改选。

| 项目 | 镜像 | 第二任务 |
|---|---|---|
| Study | `s7-mirror-live-20261019` | `s7-variant-live-20261019` |
| 目标 world m | `[0.29,-0.035,0.19]` | `[0.28,0.02,0.20]` |
| Canonical task identity | `d24aeac7041052ce1d2ae60e825a802e7367107784f6fec192b0a65c4a5e76e7` | `596fd628ade55dea581780cb3eebd3efebe83b7585554220ca83a7f2717e0ca0` |
| Study 配置 | [study_s7_mirror.json](../../configs/research/study_s7_mirror.json) | [study_s7_variant.json](../../configs/research/study_s7_variant.json) |
| 任务输入 | [既有镜像任务](../../tasks/reach_hold_mirror_v1.json) | [新目标稀疏任务](../../tasks/s7_reach_variant.json) |

原任务均为 0.35 s、控制/采样周期 0.01 s，保持窗口 0.30–0.35 s，终点/保持位置上限 0.01 m，保持速度上限 0.02 m/s。所有初始状态、环境、输入界及验收组件由冻结配置和注册器决定，没有修改阈值。

| 类别 | 开放范围与适用条件 |
|---|---|
| 拓扑 | 声明 1–9 段、1–12 腱；当前生成执行域为 1–9 段、1–7 腱，具体组合仍需候选校验 |
| 长度/材料 | 第 0 段 0.08–0.24 m，第 1 段 0.06–0.20 m，后续泛型 0.06–0.24 m；杨氏模量 2–15 MPa |
| 截面与离散 | circle/tube/ellipse/rectangle 的已授权尺寸、截面旋转、每段 1–32 cells；截面站数仍由原型约束 |
| 新物理入口 | 密度 500–2500 kg/m³，两个弯曲黏性分量 0–0.05 N·m²·s，两个自然曲率分量 ±10 rad/m，截面角 ±π |
| 腱系统 | 直径 0.5–1.2 mm、张力上限 1–8 N、初始化预张力 0–1 N；连续 spans、半径 14–23 mm、相位/偏角、导向站、锚点和显式路线 |
| 控制 | 候选专属张力数组、常张力/预张力、明确通道映射、ZOH 时间重采样、搜索节点/窗口/系数界/步长/信赖域/算法/迭代与评价上限 |
| NMPC/PPO | 原 recipe/solver 的可校验稀疏 patch；PPO 仍使用原 RLRequest 的训练、奖励、策略和预算契约 |

全部精确域和几何约束以 [family_space_s7.json](../../configs/research/family_space_s7.json) 为准。可对当前候选执行 `evidence_read(reference=候选, view=capabilities)`，得到 parameter_id、类别、类型、单位、边界/选择、默认值、拓扑依赖、执行有效性、方法和验证状态。该只读目录入口在两项 Study 封存后完成集成，仅作离线验证；正式研究使用的是已冻结的 family_summary、schema 和精确证据。

省略 `physical_parameters` 时继承 assembly 原型的实际物理值；域中的 default 是建议提议值。例如第 1 段继承密度 1050 kg/m³，第 0 段继承 y 黏性 0.0005 N·m²·s。目录已明确区分这些值，未把建议 default 静默施加到机器人。圆/管等轴对称截面的旋转不宣称产生材料方向变化。

`length_servo_gain_n_m` 和电机位移/速度界在 ideal_tension 下被绕过，不作为有效物理改变。预张力影响初始化；显式固定张力序列不因仅改变初始化预张力而自动变化。NMPC 权重不改变固定序列回放。既有实验有效身份检查继续拒绝无效模式参数制造的新实验。

8–12 腱、polygon 域、分支/闭链、剪切/扭转/轴向伸长、摩擦、扫掠自碰撞、新电机动力学均未获得执行支持。刚体负载质量/惯量、环境和连接原型保持冻结；没有把这些固定原型字段伪装为已开放的候选参数。高段数的生成/编译覆盖不等于高段数控制成功或所有拓扑组合可执行。

控制继承始终返回 `task_acceptance=unmeasured`。同通道可显式重新绑定；新通道数没有明确映射时使用新候选预张力，不直接复制旧数组。时间转移使用零阶保持，超过来源时长保持最后输入。输入界、有限值、维度、网格、任务/设计/模型身份均经原 binding 校验；任何新任务仍需独立评价。

## E. 真实 Agent 研究及失败恢复

最初移入的 S6 结构/控制是标记清楚的工程初始化，不是模型选择，不导入原任务 accepted。后续请求、研究假设、方法、变量、预算、反馈和 STOP 均保存在各 Study 的 [镜像决策](../../evidence/s7_mirror/decisions.json) / [第二任务决策](../../evidence/s7_variant/decisions.json) 及不可变 Store 归档中。

镜像任务的模型先选择四通道、四节点局部 response 搜索，实际完成 24 次独立回放，最佳 G 为 3.6020739579。随后自主生成了黏性和自然曲率变体，但两次直接套用旧候选控制被身份检查拒绝，这些变体不能称为已经物理验证。模型还选择 NMPC、平衡分析及离线 NLP，均留下 MATLAB Engine UnicodeDecodeError 的工程失败，没有形成可用数学或物理成功结论。之后模型生成了另一初始序列，但在 provider 探索额度进入保护区时没有继续回放，最后真实 STOP。

第二任务的模型先在移入结构上搜索控制，之后才选择新黏性结构与控制重新绑定。32 次首轮搜索将 G 降至约 0.1363；后续节点/窗口和 inward margin 调整未得到通过。模型自主生成两个黏性分量为 0.05 N·m²·s 的结构，并通过初始化与独立回放测试；该结构配本轮控制的结果更差。它只说明这些有限尝试失败，不能排除较小黏性或其他结构。实际后端达到 64 次上限后，模型真实 STOP。

镜像 21 次、第二任务 20 次 provider 请求均在各自 24 次上限内。两项分别有 12/9 条原始工具错误反馈，包括工程缺陷、错误 pointer、非法窗口及候选/控制不匹配。错误均保留，没有转移到新 Study ID。修复迁移前的累计模型/后端用量分别为 10/25 和 12/42；迁移前后 ledger 完全一致，任务阈值不变，material_behavior_change 为 false。

程序没有规定 mirror 的变量方向、必须使用哪根腱、必须先执行某种控制器或失败几次后必须改结构。收尾对所有新结果的引用由原 STOP 准入检查要求；未把失败优化或失败启动解释为结构不可行。

## F. 独立物理结果、预算与停止

| Study | 真实 provider | 公共操作 | 共享后端启动 | 完整固定张力回放 | 原任务通过 | 停止 |
|---|---:|---:|---:|---:|---|---|
| 连接检查 | 2/2 | 2/8 | 0/0 | 0 | 未开展 | 模型 STOP |
| 独立工程联调 | 0/0 | 7/16 | 2/2 | 2 | 否 | 两次工程额度完成 |
| 镜像任务 | 21/24 | 54/150 | 25/64 | 24 | **否** | provider 探索额度进入收尾保护，模型 STOP |
| 第二任务 | 20/24 | 87/150 | 64/64 | 64 | **否** | 共享物理后端耗尽，模型 STOP |

镜像的第 25 次后端启动是失败 NMPC，不计为完整有效物理回放。其数学分析计数 1、完整 NLP 计数 1，均保留失败；没有独立数学重积分或 PPO。第二任务没有数学、NMPC 或 PPO 执行。数学分析上限在冻结前从用户允许的 12 次收缩到 4 次；其他完整 NLP/重积分/NMPC/PPO 上限见配置，没有中途扩大。

| 最优有效物理指标（原始 SI） | 镜像任务 | 第二任务 | 冻结上限 |
|---|---:|---:|---:|
| terminal_error_m | 0.04219053752588926 | 0.010316951947567397 | 0.01 |
| holding_max_error_m | 0.04219053752588926 | 0.010316951947567397 | 0.01 |
| holding_max_speed_m_s | 0.09204147915843111 | 0.022726364290795355 | 0.02 |
| 最大归一化违反量 G | 3.6020739579215553 | 0.13631821453976767 | 0 |

两者最佳执行均完整、有效，holding coverage、solver error 检查及 force bounds 通过，但位置/速度组件失败，因此 accepted=false。第二任务的位置仍超限约 0.31695 mm，速度超限约 0.00272636 m/s；没有按舍入值制造通过。全部逐项原始验收和所有候选见 [镜像 summary](../../evidence/s7_mirror/summary.json) / [第二任务 summary](../../evidence/s7_variant/summary.json)。

测量到的 state 数值时间为连接 0 s、工程联调约 4.2830 s、镜像约 35.9719 s、第二任务约 74.4322 s；Store wall_s 另含按原边界记录的 provider/执行耗时。它们不是整机 CPU 时间或硬件运行时间。全部 43 次 provider、91 次共享后端启动和 150 次公共操作均归于原 Study；失败和拒绝未被删除，已占用资源为空。

独立工程联调实际验证了密度变化的四腱结构、三腱结构、合法初始化及两次完整 MuJoCo 执行，均为有效任务失败。它证明接口可以执行，不是自主 Agent 可行解，也没有与正式科学 Study 混用预算。

## G. 设计包、验证与复现

| 交付 | 内容 |
|---|---|
| [镜像设计包](../../evidence/s7_mirror/study/design_package.json) | 最优有效结构参数、完整 configuration、控制序列、原验收、原始证据引用、实现/任务身份、费用和 content hash |
| [第二任务设计包](../../evidence/s7_variant/study/design_package.json) | 同一契约，独立任务/候选/控制与证据 |
| [镜像原始归档](../../evidence/s7_mirror/study/archive_manifest.json) | 498 个成员；SHA256、原始请求/响应、数学/物理失败、轨迹、计划及 ledger |
| [第二任务原始归档](../../evidence/s7_variant/study/archive_manifest.json) | 769 个成员，保留全部 64 次物理结果及研究过程 |
| [连接与工程核验](../../evidence/s7_verification/final_verification.json) | 四份设计包共 1,339 个成员通过哈希检查，验证前后计费不变 |

两个正式包的 `status=best_valid_candidate`、`accepted=false`。没有生成 feasible witness 或通过标签。每个包携带完整张力数组、时间轴、通道顺序、物理/任务绑定和验收；原始内容由 archive_manifest 精确定位。不是只提供一张结果表。

最终相关回归为 **121 项：120 passed、1 skipped、0 failure、0 error**。跳过项是旧的 opt-in 三案例 M3-C2 物理控制试验，未重新消耗其封存/单次额度；不是本轮失败被跳过。测试包含实际模型编译、物理字段响应、条件参数、非法路线/域、动态通道/时间轴、证据查询、旧身份、预算/证据准入、合成成功即停、原始推理与工具配对、已接收响应精确恢复，以及 acceptance=None 后继续构建上下文。详见 [final_tests.json](../../evidence/s7_verification/final_tests.json)。

在目标工作树可执行以下只读核验，不会新增 provider 或物理启动：

```powershell
$env:PYTHONPATH='.;tests/research;C:/Program Files/MATLAB/R2024a/extern/engines/python/build/lib'
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m tests.research.s7_audit --package evidence/s7_mirror/study/design_package.json
& D:/softrobot-agent/.mainline5-env/Scripts/python.exe -m tests.research.s7_audit --package evidence/s7_variant/study/design_package.json
git diff --check
```

新任务仍使用 `python -m tools.research prepare --spec 新Study.json`，提交实现与配置后 `bind --run-id 新ID`，再 `run --run-id 新ID`。已封存 S7 ID 不再开展实验；未来重复物理研究应另行明确授权预算。当前任务没有通过，不把重新申请额度或换目标当作本轮成功。

## H. 结论的适用范围

任务无关的部分是统一配置解析、候选/控制身份、Store、预算、Strands 会话、证据读取、调度、原始归档和设计包契约。任务描述与原验收由注册适配器拥有；局部 norm-bound response 搜索、holding 样本和现有数学/NMPC 路线仍有 reach 任务适用范围，不把 obstacle、catching 等任务改写成 reach_hold。

本轮真实科学研究只覆盖两个新的 reach_hold 目标实例；它们都未通过。结构/控制接口、生成/编译和高段数离线检查通过，不等于这些结构的闭环性能或所有机器人任务可行。S7 的真实成功触发分支没有在新任务中发生；成功即停规则由既有契约和合成回归验证，S6 的历史成功仍只属于原任务。

没有额外要求鲁棒性、最优性、硬件、电机动力学或反馈控制。科学探索已在冻结预算边界停止。可保留的下一步问题是：在新的明确授权下，是否用不同控制参数化、较温和的黏性或其他结构选择缩小剩余违反量；本报告不对此给出未经验证的保证。
