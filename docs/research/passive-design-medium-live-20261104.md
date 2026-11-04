# 被动自主科研与接口监督进展（2026-11-04，Main 44 快照）

用户已正式批准科研、持续监督、及时接口修复和按需追加 Provider；数学、分析及其共享物理计算均无累计上限。本记录是结算边界的进展快照，不是科研完成、Main STOP 或任务成功声明。原始 Store、完整 wire、凭据、批准全文和候选当前数值不公开。

## 身份、范围与预算

当前 Study 为 `passive-design-autonomy-medium-20261104`，独立 Store，Main/Reporter 均为 medium。初始 resolved identity 为 `76051370f38e2d08b61b07ffcdeb0d34a149149816b376086b5676805ec31772`；资源增补后的当前 identity 为 `aa36218578bf9dee6d1d6c5680fc888afc1a8f2518ee9b44025dd8bababe96e2`。

当前数值及接口绑定提交为 `1a97f44bd0c1d0a3194a24b2b94b1762c45ae35d`。科学 profile 仍为 `9f95b160c2aa80a89ca40d324d75fc33e660fd51a86f3fe6a65235cdc376dcd3`。物理任务、初态规则、时序、评价器、积分、原型和生成能力沿用准备方案；没有导入旧候选、赢家或 H2 路线。

精确求导授权继续使用 [24 条版本化选择器](../../configs/research/family_sensitivity_passive_design_20261104.json)。只有实际存在、有效连续、授权且方法适用的路径可选；具体问题及工作点还须原准入和真实数值资格检查。旧冻结表未修改。原窄表的来源、18 条连续路径中仅授权 2 条的证据、物理域及离线回归见 [准备审计](math-admission-passive-study-20261104.md)。

| 当前资源 | 设置及消耗 |
|---|---|
| Provider | 初始 24，依次以原授权/账本机制 +8 至 32、40、48、56；当前 47/56，内含 4 次收尾 |
| 数学与共享物理累计上限 | `null`；真实成本及原扣账历史继续保留 |
| 单 Worker / 单问题 | 原 180 s 保护、原至多 64 次评价合同；Main 明确的更低上限仍有效 |
| 独立 Replay | 原有限子限额 16；已执行 0 |
| 公共操作 | 65/256，内含原收尾保护 8 |
| 实际 Provider wire | 全部发往 `http://127.0.0.1:8787/v1/chat/completions`，模型仅 `gpt-5.6-sol`，reasoning 全部 medium |

每次资源增补均保存旧 identity、旧账本、授权增补与新 identity，再按原机制绑定；未重置费用或改写旧失败。每至多 4 次 Main 只读监督，在 Main 8 做阶段检查；当时已有真实数值信息，未机械终止。

## 各 Study 的历史成本

| Study | Provider | Main / Reporter | Tokens | 数学账本扣记 / 实际评价尝试 | 实际积分步 | 新生成候选 / 独立 Replay |
|---|---:|---:|---:|---:|---:|---:|
| 原 `passive-mechanism-autonomy-20261104` | 55/64 | 50 / 5 | 729032 | 1 / 1 | 500 | 0 / 0 |
| 独立 `passive-design-autonomy-unmetered-20261104`（none） | 28/40 | 28 / 0 | 283131 | 0 / 0 | 0 | 1 / 0 |
| 当前 medium | 47/56 | 44 / 3 | 716981 | 22 / 21 | 9500 | 2 / 0 |

原 Study 和 none Study 均为监督暂停，不是 Main STOP。当前 medium 在本快照处也为已结算监督检查边界，state=ready；继续执行沿用同一 Store。未启动的零成本准备草案另行保留，不用于抵消任何历史费用。

medium 的真实 Worker 记录共 23 次 model build、23 个 episode 启动、18 个完成。数学账本扣记 22、backend 账本扣记 24，与 Worker 实际 21 次评价尝试、23 次 build 分列；例如 Main 申请优化上限 8，实际尝试 7。没有把申请上限冒充实际计算，也没有回写历史扣账。

## Main 已自主完成的科研动作

1. Main 生成独立基线、完成候选绑定 diagnose，并执行两次相同的有限时域基线/腱禁用消融检查。重复计算保留为真实消耗；没有宣称重复本身带来新信息。
2. Main 19 自选自然曲率 y 与截面方向的双参数问题；Main 20 纠正根层字段后，因此前 diagnose 的明确上限 1 而收到最低 10 次的非执行反馈。依赖为 `1+4+4+1`，最坏合法成本为 10 model / 10 episode / 5000 steps，累计数学剩余额为 null。程序未静默上调。
3. Main 24 自行以合法上限执行该问题。截面方向得到两尺度局部一致估计；曲率及联合探针出现卸载动态资格失败，不能作为有效耦合梯度或下降证书。实际尝试 10 次，积分 3000 步，低于全完成的最坏成本。
4. Main 27 根据已有数值证据生成第二个候选。核对实际物理结构后，唯一变化是截面方向；请求补写的其他默认字段没有造成额外物理变化。
5. Main 36 完成同协议的完整有限时域匹配比较，第二候选的任务违反量下降约 2.45%。两条观测有效、完整，但均未满足冻结阈值；独立接受状态仍未测量。
6. Main 42 自选截面方向局部优化，将单请求上限 8 正确放入 `structure.requested_budget`。Worker 实际尝试 7 次、完成 3500 步，记录进一步改进建议。Main 尚未把该建议生成第三候选，也没有独立 Replay 或 SELECT。

这些是真实 Worker 数值记录，不是只读内存反事实、目录投影或编译成功的替代证据。局部一致性、完整研究观测和独立任务接受继续严格区分。

## 监督发现与最小修复

### 生成缺省值与冻结拓扑不一致

none Study Main 3 省略 segment_count 后，旧合同缺省 2 与冻结可执行集合 `[1]` 冲突；错误文本还固定称只能生成两段。`2f41e6c` 使聚焦 Schema 在缺省值不属于当前 enum 时要求显式填写，错误反馈展示实际冻结段/腱范围。未改原生成合同缺省或物理 family 源码。两项定向回归通过。

### 非法根层字段反复出现

实际 V4 Schema 根层只含 `version/domain/structure`（本被动分支），`additionalProperties=false`；diagnose 候选的唯一位置为 `decision.selected_candidate`。模型曾重复填写顶层候选，或把 hypothesis、physical_problem、load_condition、requested_budget 放到外层。Schema 本身及拒绝正确，未通过删除字段伪造合法请求。

核查真实 wire 后发现：每次请求/反馈边界交接不复制完整旧对话，当前包保留科学结果和精确查询，但近期工具摘要仅保留四条；V4 校验拒绝的工具外层状态仍是 success，因此摘要没有保留内部输入错误。模型收到直接报错能纠正，经过若干读取后仍可能复发。这支持修复反馈保留，不证明单一因果或模型能力上限。

`5d2f4eb` 从原 Store 的校验反馈保留最近三项拒绝事实、错误字段、原因及来源，跨普通读取和 SDK 交接继续提供；当前 Schema 始终具有权威性。根层字段说明直接由现有 question_schema 的 properties 产生，不建立第二份规则表。真实 wire 已确认保留生效；错误仍偶有复发，不能宣称根治。

随后 Main 在成本拒绝后把上限放错根层，收到泛化的“多余字段”后删除它，仍沿用旧 diagnose 上限。`b2911a3` 改为从实际 payload Schema 推导 `expected_field`，例如 `structure.requested_budget`；最低成本反馈也指明合法上限字段。原输入、上限、授权和执行门禁不变，Main 必须重新提交。`7e816be` / `1a97f44` 同时使非法 domain 类型进入原验证反馈，避免字段展开先抛类型错误；此边界问题由离线回归发现，不冒充真实 Main 故障。

没有添加字段别名、自动过滤、自动移动、自动提高上限或重试科研脚本。完整错误请求和真实失败均保留。research_intent 继续由 action 确定性绑定，候选冲突仍拒绝。

## 验证与后续验收

准备阶段的 M1、被动 v2、M5、Reporter、证书、SELECT/STOP 回归及已确认的基线旧失败见准备审计。实时修复另外完成：

- 生成 Schema 与实际 SDK 聚焦 diagnose：2 项通过。
- 连续四次读取及真实 SDK Mock 交接后的拒绝保留、坏字段拒绝、最低成本保护：3 项通过。
- 合法字段位置、错放上限不丢弃、继承低上限仍拒绝、Main 显式更正后才准入：2 项通过；追加非法 domain 边界后最终定向复核通过。

以上新增离线测试不发送真实 Provider；正式 Study 的 47 次 Provider 消耗单独按上表记录。当前 1022 个 artifact 哈希全部有效，无 pending、未封口调用、未知 Worker、占用额度或未消费响应。原 Study 的 Store、SDK 文件和授权库逐文件哈希仍与最初清单一致。

后续继续由 Main 解释优化结果，选择是否生成、改变问题、继续数学或独立 Replay。科研参数、努力与路线不由监督者指定。任务通过必须来自原独立 Replay、正式证书及 SELECT 门禁；停止须保留原完整结果索引和 STOP 合同。若接口确有阻断，最小修复、离线验证、提交后绑定，所有旧成本和证据保留；模型未遵循正确 Schema 或物理资格失败不能伪装为接口成功。

## Main 48 增补：最新数值卡跨交接丢失

Main 43–48 交替重复同一结果和相同参数页，无新计算、生成或证据增益。结算时为 Main 48 / Reporter 3、Provider 51、792927 tokens；数学扣记 22 / 实际尝试 21、实际积分 9500、候选 2 / Replay 0 均未增加。这些读取费用完整保留。

只读核查实际 wire 发现，`object_choices.main_packet` 在某数值结果曾获 HTTP200 交付后，会在未来包中删去其 `structure_research`，但 `verified_facts` 仍把最新结果指向 `mathematical_research.latest_result`。交接又不复制完整旧对话，故“曾送达”不等于“当前上下文仍有”。本次看到 result_5 只剩身份、状态和方向标签；科学原始数据在 Store 中完整保留。此前部分旧结果仍可见，不能据此断言所有最新数值卡都持续可见。

`2577277` 删除这段跨请求压缩逻辑，保留同一当前包内的唯一事实来源与去重，不添加新缓存、指令路线或计算。更新原多条件合成数值/真实 SDK Mock 回归，验证经过后续请求和普通任务读取后，基线、改进状态、生成建议、接受状态及数学/候选数均不变；回归通过，无真实 Provider 或积分。

绑定后以原机制追加 Provider 8 次至 64，当前 51/64，含 4 次收尾；resolved identity 为 `c7df059d61ff909f566335fbb8f7d0c5d12a78b028ec2b4f954a157cfa830685`。科学 profile、授权、数学/共享物理 null 和所有旧成本不变。随后在同一 Store 继续有限观察窗口；该修复效果仍需真实 Main 验证，不宣称已消除所有模型错误或决策循环。

## Main 64 增补：独立 Replay 已执行

最新数值卡修复后，Main 49 离开重复读取，Main 50 生成第三个独立候选，实际物理变化仍仅为截面方向；Main 51 自主选择独立 Replay。随后仍多次把 selected_candidate 错放 Plan 根层。原 Schema 拒绝正确，但通用反馈的 field 为 null、缺少位置说明。`91239ce` 从原 validator 的实例、Schema 和路径返回错误字段、所在层及该层合法字段，不移除、搬动或改写请求。`2053bc4` 的最终两个定向测试通过，覆盖根层与嵌套字段定位及原 diagnose 候选提示；无真实 Provider。

Main 57、60 自行纠正格式后，原 Replay 门禁发现冻结任务所引用的协议来源 artifact `86fd14382396bdafd2d421ae2bcca73c06cc693d1699cc4278d217f13e56e9a8` 缺失，尚未启动 Worker。这是监督者准备独立 Study 时漏存冻结依赖：原任务引用已保留，其对应的两字段协议适用范围定义未进入新 Store。只读打开原 Store，核对原字节、SHA256、媒体类型和定义角色，再按同一哈希写入当前 Store，并保存修复来源事件。该定义不是候选、优化结果或成功证据；未改任务、协议引用、参数授权、identity、profile 或成本，也未导入历史结构。原 Store 与授权库逐文件保全检查再次通过。没有放宽来源门禁或新建 Harness。

Main 61 读取已有数值结果、62–63 仍发生格式拒绝，Main 64 最终合法提交并实际完成首次独立 Replay：新增 1 model / 1 episode / 500 steps。原评价器给出 `valid_failure`；执行、初态资格、阶段协议、全部载荷和无接触检查通过，冻结位移指标约 `8.7520e-5 m`，超过 `1e-9 m` 上限。该失败保留为独立证据，不是接口错误，也不证明问题全局不可行。未 SELECT，未宣称任务成功。

Main 64 结算快照：Main 64 / Reporter 3，Provider 67，1080724 tokens；候选 3 / 独立 Replay 1；数学扣记 22 / 实际数学尝试 21；全部实际 model build 24 / episode 启动 24 / 完成 19 / 积分 10000 步。backend 原扣记 25 与真实 build 分列。无 pending、未封口调用、未知 Worker 或占用资源。

Provider 先于 Main 57 按原机制从 64 增至 72，identity 为 `8218929f8a0bb31a58fda5729e7f885bdc917872ff6ba8ff8db9f8073e6b7097`。独立 Replay 形成新有效信息后，再按用户持续授权增加至 80，identity 为 `fdf1c0ec42c1d5a5bc7ca6b675ccaee7e8b50b079470d1b420125ceb5967f4d3`，仍保护其中 4 次收尾；所有历史费用保留。数学、分析及共享物理累计上限继续为 null，单 Worker 和单请求的明确资源合同不变。Main 仍自主选择后续科研问题；每至多四次 Main 检查实际信息增益，不为无变化的读取或错误循环自动续费。
