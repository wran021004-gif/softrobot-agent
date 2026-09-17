# 平台验收与完成边界

## 本次：领域接入（基线 a716f32）

一次定向组 `conda run -n softagent python -m unittest tests.test_platform_domain -v`，3/3 通过（1.239 s）。一个非基线候选分别通过公共宿主完成 **MuJoCo 1 次、MATLAB 1 次** 0.08 s 求解及保存结果评价／信号／诊断／规则／回放数据准备，合计 14 次工具调用、2 次 backend_solves、0 次模型请求；无全仓库测试、历史实验重跑、视频编码或 GUI。两份评价有效且任务未达标。实际编译量与有效候选一致，后处理未增加求解。范围、可复制命令和未验证部分见 [领域指南](platform_domain.md)，数据摘要见 [platform_domain.json](evidence/platform_domain.json)。以下各轮记录保持原意。

## 本次：公共接口两项修复（基线 6751639）

实现完成后只运行一次组合命令：

```powershell
conda run -n softagent python -m unittest tests.test_platform_public_fixes -v
```

**3 组通过，0 失败、0 错误、0 跳过，用时 4.082 s。** 无补测、全仓库测试或历史验收重跑。实际输出及三个 SQLite 项目路径见 [platform_public_fixes.log](evidence/platform_public_fixes.log)。随后仅只读核对账本和最终差异，`git diff --check` 通过。

| 组别 | 实际断言及结果 | 替身执行 |
| --- | --- | ---: |
| 结果契约 | 普通数学返回 validity/solver_status 且没有 task_success，正常／缓存均成功，3.0.0 结果版本保持；真实 EvaluationResult 的成功与失败均正确投递，缓存仍为 1.2.0；旧 1.1 回执／评价读取默认来源为空 | 2 次离散后端、1 次数学函数替身 |
| 仿真复用链路 | 同计算三请求、独立身份、同一轨迹、直接原始来源，三份结果均为 valid/task_success=false；新 Host 重开后来源保持，三份再评价成功；原始预留占 reference_device，两个命中预留资源为空，各工具计费 1、求解计费 0、实际耗时大于零 | 1 次离散后端 |
| 重算与幂等 | 初次执行、cache=new、command_m 改为 0.31 共执行三次；重试封存的 new 和 changed 请求，返回原回执，账本、事件和执行计数不变 | 3 次离散后端 |

三组共 **20 条封存工具调用、6 次合成后端执行**。测试复用现有 `ReferenceBackend`，仅在测试注册表中将其计为求解、声明 `reference_device`，以验证共同预算和资源槽；生产参考后端的零物理求解声明保持。6 个 backend_solves 是替身记账，**真实模型请求、MATLAB、MuJoCo 均为 0**；没有模型离线对话或工作者进程。第二组保存一份轨迹文件；缓存读取没有产生新的后端目录。第一组临时开启评价缓存仅验证通用契约路径，生产 `evaluation.run` 仍默认关闭缓存。

修改文件和关键入口见 [本次交付](platform_delivery.md#本次公共接口两项修复基线-6751639)。范围为同一会话和现有缓存键；精确版本、种子、源码／资产与运行环境检查原样保留。旧证据不改写，历史依赖变化继续要求只读或显式迁移。本次没有发现阻碍既定范围内扩展开发的剩余具体问题，不启动下一轮泛化准备任务。

## 上一轮：公共核心修复与接口定版（基线 c677c22）

一次受影响组合验收 **12 项全部通过**。没有运行全仓库或历史实验。原始日志见 [acceptance.log](evidence/platform_convergence/acceptance.log)，会话目录见 [acceptance.json](evidence/platform_convergence/acceptance.json)，按各 SQLite 事件及回执统计的运行量见 [usage.json](evidence/platform_convergence/usage.json)。

| 行为组 | 已证明的外部行为 |
| --- | --- |
| 结果投递 | 实算 5 和 10 进入后续请求，触发不同候选；证据页正文可读；原始响应与解析失败可追查 |
| 候选一致性 | 0.31 在示例上限 0.305 前被拒绝、运行零次；合法预检与执行输入一致；响应系数贯通评价 |
| 搜索恢复 | 提案改变状态/RNG，最后 pending 不因 stopped 被跳过；已封存工具不重做，反馈与连续运行一致 |
| 版本绑定 | 同名 1.0/2.0 分别绑定并返回预期结果；未绑定版本拒绝；旧唯一配置规范化，歧义定位字段 |
| 插拔与依赖 | 新控制器名称共享通道即可兼容；单位/坐标不匹配拒绝；未用扩展和文档不失效，已用源码变化检测 |
| 工作者 | 两类实际进程重叠；共同入口读取/数学共计三次工具费用、两个工作者槽；子额度耗尽拒绝；取消/失败/冲突/迟到输出复用原机制 |
| 证据与经验 | 相同内容的两次执行分别保留候选关联，评价必须消除歧义；不适用模型记忆不混入上下文 |
| 完整运行与调试 | 两份开发任务均完成发现、读结果、提案、执行、评价、停止；只读查询不改变数据库，旧配置可解析 |

| 实际运行类别 | 最后组合验收 | 本次累计（含先前分组、失败与补测） |
| --- | ---: | ---: |
| 离线适配器请求／回复 | 22 / 22 | 54 / 54 |
| 合成执行 | 15 | 30 |
| 数学工具完成（含版本测试替身） | 8 | 17 |
| 本地工作者进程（含取消和失败） | 8 | 13 |
| 真实模型请求 | 0 | 0 |
| MATLAB、MuJoCo、Genesis 真实求解 | 0 | 0 |

失败与修复：首次纯编译检查发现 Pydantic 冻结对象不能赋值，改用副本更新；首批工作者因子会话锁目录未创建而失败，补齐目录后定向验收通过；最后组合无失败。文档终检还发现 PowerShell 管道将新中文替换成问号，已改用保留 Unicode 的文件补丁重写，只涉及文档。

组合验收后的源码检查发现：模型服务的调用理由会覆盖 session.control 自身的 reason。已将工具参数封装到 arguments，保留外层调用元数据；本地构造 DeepSeek 响应验证两个 reason 和精确版本均保留，没有网络请求。仅补跑受影响结果投递组，通过记录见 [transport_followup.log](evidence/platform_convergence/transport_followup.log) 和 [transport_followup.json](evidence/platform_convergence/transport_followup.json)。没有再次运行组合验收。

执行命令：`conda run -n softagent python examples/platform_convergence_acceptance.py`。另外只读核对旧 reach_shifted 配置及注册目录，51 项发现未加载 NumPy、MuJoCo、MATLAB 或 Genesis。结果证明公共接口可接入，不证明真实模型推理质量、机器人成功率或物理标定。

---

## 以下为历史平台建立验收（不计入本次成绩）

## 结论

**在声明的本地接口范围内具备并行扩展条件。** 公共宿主、任务／后端／评价注册、请求与结果身份、共享资源和恢复、确定性本地协作、记忆／原技能生命周期、可执行示例及中文模板均有验收证据。

这不表示全部物理任务、硬件、真实模型或外部仿真器已经验证。正式科研审批仍需真实策略与审批来源；本次所有新配置都是独立开发用途。

## 验证入口与结果

- `python examples/platform_acceptance.py`：28 项最终组合检查通过（当时的 23 项平台检查与 5 项旧技能／公共工具回归），0 失败、0 错误、0 跳过。
- 随后新增“迟到的已封存工作者输出核对 unknown，且不重新启动”的定向检查通过。合计 **29 个不同用例**。现在同一入口会收集新增用例，共 29 项；没有为这一单点补充再次重复整组。
- `python examples/platform_acceptance.py --real --matlab`：两次 MuJoCo 短计算完成；MATLAB 启动被当前进程访问控制拒绝，保留失败和费用。
- `python examples/platform_acceptance.py --skip-checks --matlab`：经正常本机权限启动已有 MATLAB，完成一次独立短计算。没有增加案例规模或使用历史科研预算。
- 两个完整配置通过实际解析／能力检查；空白模板报告缺少 environment_file；数学包模板实际输出 4 m²。`compileall`、生成契约和 `git diff --check` 通过。
- 旧工作台的平台转发入口实际完成 create → 离线五轮 run → export；[保存页面](../runs/platform_cli_verification/project/overview.html) 来自已保存参考结果。
- status、resources、events、inputs、context、compatibility、memory、skills 八条 CLI 查询均成功，查询前后数据库字节完全一致，见 [只读命令记录](evidence/platform/cli_readonly.json)。

## 分类计数

以下累计包含发现具体失败后的定向复验和最终 CLI 冒烟，不将它们伪装为一次测试。精确、可重新查询的统计见 [validation.json](evidence/platform/validation.json)。

| 类别 | 本次累计 | 含义 |
| --- | --- | --- |
| 真实模型 API | **0** | 没有模型密钥调用或模型训练 |
| 离线模型回复 | **41** | 实际传输载荷及反馈循环夹具，不证明自主决策质量 |
| 正常数学工具执行 | **20** | 含 1 次可复制模板计算；缓存命中不算新数学执行 |
| 合成参考后端执行 | **51** | 明确的一阶离散长度信号模型，不是真实机器人物理 |
| 真实 MuJoCo | **2 次，共 100 步** | 分别 40 步和 60 步，无重复科研实验 |
| 真实 MATLAB 动力学 | **1 次** | 0.08 s；40 个输出区间／41 个采样时刻，ode15s 473 个成功内部步、788 次 RHS 评价 |
| MATLAB 启动失败 | **1 次，未进入求解** | 故障记录保留；随后独立请求在正常权限下通过 |
| 本地工作者进程 | **33 个** | 23 个已完成、5 个故障注入失败、5 个取消；这是多批契约／恢复测试的总数 |
| 未知预留故障注入 | **8 条保留记录** | 不自动退款或重演；不代表还有真实求解器运行 |

正常实验证明的是接口，不是得分提升。三次真实短计算均输出有效评价、task_success=false，原阈值未降低。MATLAB 的引擎启动约 12.55 s，完整调用约 15.09 s，说明声明的求解超时不能被误称为覆盖引擎启动的硬超时。

## 代表性验收证据

| 边界 | 已证明 |
| --- | --- |
| 新数学工具 | manifest 发现 → 同一离线循环调用 → 不可变输出读取 → 后续决定；未改核心工具名分支 |
| 两类任务 | 两个到达目标／时长真实短执行；长度保持任务无末端目标点，输出最大／RMS 偏差 |
| 任务遗漏／后端不兼容 | 字段、单位、评价实现、执行器、信号相位和参数空间在求解前拒绝 |
| 后端与控制 | 原两后端和参考后端统一外层；参考分步、控制 reset／restore／周期检查；实际 close |
| 搜索与排名 | 算法拥有状态，恢复不重复求解；有效任务失败可作为样本，无效未完成不能排名；不同来源身份拒绝混排 |
| 回执与恢复 | 请求原文、稳定请求／执行身份、缓存与显式新计算分离；异常中断保留额度，封存结果可核对 |
| 并发资源 | SQLite 同事务预留；同一排他资源并发只能一方获得；复制项目不产生新授权 |
| 双工作者 | 绳索／接触工作区间实际重叠 **0.7831 s**，独立输出并校验原采样；重复接收不重复合并 |
| 协作异常 | 取消、失败、冲突、过期候选、迟到输出核对 unknown 均有注入覆盖 |
| 记忆／技能 | 有来源的开发记录及验证技能进入后续模型实际输入；模型不能自报已验证事实／审批身份 |
| 历史与只读 | 原数值证据摘要保持；可变状态单列；只读查询不改变数据库或预算 |

## 可搬运交付

- [最终组合测试日志](evidence/platform/final_checks.log)、[新增迟到输出检查](evidence/platform/late_worker_check.log)。后者保留 PowerShell 将 unittest stderr 包装为 NativeCommandError 的外层记录；测试正文为 1 项 OK，无断言失败。
- [短后端结果](evidence/platform/short_backends.json)、[MATLAB 短结果](evidence/platform/matlab_short.json)。原始计数字段保留当时含义；分类汇总以 validation.json 的账本重查为准。
- [验收证据包](evidence/platform/acceptance_bundle.zip)、[文件与包摘要](evidence/platform/bundle_manifest.json)。含模型实际输入、数据库、数值导出和故障夹具。解包是只读副本，不重新领取授权。
- [最终源码快照](evidence/platform/source_snapshot.zip)、[源码身份表](evidence/platform/source_manifest.json)。真实短求解保留当时依赖摘要；之后的请求留存、记忆身份、导出、依赖声明及迟到输出核对改动经定向检查，未为记录好看重跑物理求解。
- 早期 failure_ready 夹具留下的失败输出已显式核对结算，未重新启动进程，见 [对账记录](evidence/platform/reconciled_worker_fixture.json)。

## 明确未实现／未验证范围

- Genesis 未实现；接球的球体环境、碰撞信号、接住和冲击评价未实现，人工清单准确标记待定义。
- 真实 DeepSeek 传输适配保留，但本次 API 请求为零；没有真实多语言模型决策质量结论。
- 当前传输适配没有实际图像／视频输入；文件引用不能被记为已获得视觉理解。
- 压力、力矩等新执行通道、任意新环境物理、完整质量矩阵、多目标搜索及分布式调度未实现。
- 旧后端仍是未标定模型；V1 编译质量惯量保留原仿真器导出来源，未用新公式替换。MATLAB 启动／关闭和外部服务取消没有硬终止保证。
- 本地身份绑定、grant 锚点和内容摘要不构成远程认证、恶意代码沙箱或对有权限篡改者的防护。

这些是声明的扩展边界，不是用“后续工作”替代已经要求接通的核心入口。
