# PHS-2D Knowledge 正式研究准入（2026-11-05）

后续进展：用户明确授权一次 Gateway 实测并在 HTTP200 后选择继续原 Gateway；Study 已真实启动。以下为此前准入与阻断记录，当前进展见 [真实研究报告](phs2d-knowledge-live-20261105.md) 和 [状态 JSON](phs2d-knowledge-status-20261105.json)。

新的 Knowledge-enabled Study 已准备并隔离冻结；**真实自主研究尚未启动**。用户回复“批准”后，原 Store 已登记精确身份和注册数学的正式授权，原授权门禁通过。此前不可重试共享额度 429 的独立恢复依据仍未取得。没有真实推理探测、换模型、后台重试或自主科学 STOP。

## 身份与保全

- 研究分支：`codex/phs2d-knowledge-autonomy-20261105`，基线 `89f00e3dee57b6b9f23b428488ff6c8b4f2ea371`；远端指定分支核对相同。远端默认 HEAD 为 `2a854280db69425dc50af9012b8da52194a679ee`，没有将其混入本次科学基线。
- 新 Study：`phs2d-knowledge-autonomy-20261105`。
- resolved identity：`31c22b6af32975d2d30c87e1c56943faf0fb47d6273d74d5496a790237b5dab7`。
- 科学 profile：`69db05e7b850caed1dc2a8727a496d115dee6fc1891401f67ae866f09cb380ea`。与原 prepared profile 的唯一差异为新 Study 从 version=1 开始及其身份；科学内容、源文件哈希、TaskAdapter 验收与执行环境合同相同。不继承工程执行证书。
- 实现源提交：`f3845ef00fb4593f5f47cc0dc79641409718a681`，最终文档提交后的绑定见私有 `runs/knowledge_prepared_receipt.json`。
- 模型仍为原 Gateway 的 `gpt-5.6-sol`，Main reasoning=medium、Reporter=none。
- 原 prepared Study `phs2d-autonomous-original-prepared-20261105` / `fdeb8249a7db41b71a550d412728477ff168488a2b8c8b96ed76419f1accf758` 保持原样；4 个实际 Store 文件前后字节哈希相同，原配置 knowledge=off，候选、数学、Replay、Provider 消耗均为零。

新 Study 空候选池，无 supplied evidence、历史候选、历史数学结果或 control seeds。原完整十工况、加载/无载初始化协议、FamilySpace v2、合法参数域、实体几何条件、评价器和 SELECT/STOP 合同均未改变。

## Knowledge 审核与交接

仅启用以下六条原始 revision=1：`skill-finite-search`、`skill-parameter-model`、`skill-matched-comparison`、`skill-local-to-experiment`、`skill-continue-or-stop`、`skill-witness-replay`。正文未修改。逐项身份、真实原始字节 SHA256、元数据身份、来源及引用隔离结论见 [source audit](phs2d-knowledge-audit-20261105.json)。

Manifest identity 为 `9cbaac4f2a5c419c5480bdc007b69c44392caca2c970bf2c7b3c1c8e6a848e75`，纳入 resolved identity。六条均为条件性科研方法，无成功孔位、腱路、payout、几何/材料组合或优化方向。六条正文只引用两个未授权历史程序条目和代码合同名称；后续条目不因被引用而获得访问权。特别是 `research-witness-and-cost@2` 下游关联 PHS/P3 历史案例，本 Study 无法读取该条目。未启用 `passive-force-response-research`，未启用任何 case、success_case、私有研究轨迹或整个索引。

复用原 experience 系统，没有第二套 Knowledge/Memory。真实 SDK + Mock HTTP 验证：初始 wire 提供 `experience_retrieve` 与简洁程序提示；正文按需检索后才进入反馈；准确条目/版本/适用性保留；Agent 和 Reporter 直接读取所有非白名单条目、追随程序引用均被拒绝；检索收据不进入科学引用目录，不能支持 SELECT/STOP。内容偏离已冻结正文哈希时拒绝交付。

交付只证明 SDK 接口和隔离可用，不能证明真实 Main 理解、采用或因 Knowledge 改变研究路线。

## 有限资源与授权请求

| 资源 | 新 Study 初始硬限额 |
|---|---:|
| Main/Reporter 共享 Provider | 24，其中 4 保护收尾 |
| 数学评价 | 20 |
| 共享 backend episode | 80 |
| 公共操作 | 160，其中 8 保护收尾 |
| 独立 Replay limit | 80，仍受共享 backend 限额 |
| 物理 / 数学 Worker watchdog | 1,800 / 7,200 s |

扩展策略拟冻结累计新增 Provider≤104，总额≤128，每次≤8。**策略上限不是已批准增补，当前未应用任何真实增补**。每个增补仍须使用原 `extend_provider_requests` 事务、精确旧身份/旧上限授权、结算边界、提交重绑定和当前身份科研授权；历史费用/失败/证据保留。没有新增数学或物理扩展机制，没有将限额设为 null。现有 engineering-only 计数扩展不能用于这个 formal Study。

[精确授权请求](phs2d-knowledge-authorization-request-20261105.json) 已由用户明确回复“批准”。对应的一个 `formal_study_authorization` 事件已保存在原私有 Store，scope identity 为 `9b7b09ce994c99472647691a556bed7d89ae923c63ea64bd79bd61feaf7fea65`；当前身份和注册数学门禁实际通过。授权范围包括原注册数学、独立十工况 Replay、上述初始预算及 Provider 扩展策略；科学预算扩展未获授权。后续具体增补仍遵循请求中逐次精确绑定的要求。预算增加不增加科学证据资格。

授权后，约每 4 次 Main 请求在已结算反馈边界做只读监督；区分新假设、真实新数学、不同合法结构、独立 Replay 与重复读取/等价实验/反复非法字段。有效进展才允许提出下一有限增补。外部额度或资源耗尽为监督暂停，不能代写 Main STOP。监督者不提供具体结构、参数方向或机制答案。

## Gateway 与计算准入

本轮仅作非推理 GET：`/health` HTTP200，`account_status=connected`、`plan_usage=true`；`/v1/models` HTTP200，含精确 `gpt-5.6-sol`。这些返回没有共享额度余额或恢复证明，不能据此推翻此前 `subscription_sharing_usage_limit_exceeded`、`retryable=false`。本地 SDK getSession 只读保存会话状态，没有可证明恢复的额度字段；官方 usage 页读取超时。没有发送 POST 推理请求。

原研究解释器、已安装科学/SDK 库与线程环境已检查；设置冻结的三个线程变量为 1 后 `execution_environment.status=ready`。缺少 cvxpy，但本 Study 仅冻结 `mechanism_structure_v1`，未授权 conic 方法，原准入正确判为 ready。未安装新依赖、切换 Provider 或增加单次计算上限。

## 既有证据与本轮修复

只读核对原公开 summary/certificates/integrity：完整十工况 v1.2 accepted、证书完整、仅在其工程 Study 内具备资格，不能导入新正式 Study。此前 71 个不同定向测试的记录保留，不宣称本轮全部重跑。

既有完整十工况实际为 352,000 积分步、10 加载 episode、1 个共享无载准备、1 模型、Worker 887.847 s。此前全部具名工程实验累计 640,000 步、4 动态模型、16 加载 episode；数学探针另有 5 模型、10 平衡、0 积分。历史失败、费用与证书没有重写；未测量货币账单。

本轮最小公共修复：

1. compact Skill 对通用 `soft_robot_research` 的适用性检查支持被动任务；此前 passive_response 不在旧任务枚举，导致提示缺失。方法仍标记跨任务未经验证，不指定科研动作。
2. 按冻结 compact 正文哈希检查按需读入，拒绝文件漂移；不覆盖历史非 compact Study 的旧语义。
3. 在原扩展策略上增加可选 `maximum_requests_per_extension`，并在原事务拒绝超批次增补；旧双字段策略兼容，累计门槛不变。
4. 修正一个旧 Reporter 测试夹具：先注册其合成调查对象，使程序性知识断言实际到达；没有改变生产 Reporter 的对象门禁。

本轮 15 个不同定向测试在干净工作树下全部通过，耗时 56.666 s，限定于 Knowledge/SDK、来源隔离、SELECT/STOP 科学信用、授权前拒绝、Reporter、有限增补事务及成本保全。完整测试结果见 [状态 JSON](phs2d-knowledge-status-20261105.json)；初次测试暴露夹具注册前置条件缺失，以及一次文档写入期间触发干净工作树绑定门禁，均保留在本地日志。没有运行大型科学验证或把合成 SDK 回复当作真实研究进展。

## 当前研究结果与交接

| 要求 | 当前事实 |
|---|---|
| Knowledge 方法采用及影响 | 未测量；只有离线交接证据 |
| Main 自主假设及削弱条件 | 无真实 Main 发送，尚无假设 |
| 数学结果、有效性、成本 | 新 Study 均为零 |
| 候选物理变化 | 空候选池 |
| 独立十工况及失败原因 | 新 Study 未执行；原工程 accepted 不计入 |
| 数学指导结构设计 | 尚未测量 |
| L1 / L2 / L3 / L4 | 均未由真实自主运行建立 |
| Provider / Reporter / tokens | 新 Study 全部为零 |
| episode / 积分 / Native 模型构建 | 新 Study 科学执行全部为零 |
| 科学 Worker 耗时 | 零；准备/离线测试时间不充当科学计算 |
| 当前阻断 | 共享额度恢复未证实；精确身份和注册数学授权已通过 |

精确身份批准已登记。取得可靠的非推理恢复依据后，应从此 Store 经原 SDK 实际启动，按有限窗口继续监督。当前可用浏览器的官方用量页已重定向到登录页，无法读取 Gateway 对应账号的共享额度；批准操作本身不能证明额度恢复。不得新建空 Store 重算费用，不得通过模型请求探测恢复，不得将本轮准入工作宣称为自主发现。下一阶段的问题由 Main 自主提出；这里不推荐具体设计路线。

私有 Store、原始 wire、凭据和历史获胜结构不纳入 Git。源码、测试、审计与本报告只在独立研究分支交付，不合并 main。
