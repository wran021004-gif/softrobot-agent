# 框架扩展验证记录

基线：`1a0081b6822ccf802cfd08ce8d1ecb9c5049a69b`。使用仓库文档指定的 `softagent` Python 环境。默认系统 Python 缺少 PyYAML，未用于有效验收。未运行全量测试或历史实验重放。

## 最终真实验收

命令：`python examples/framework_acceptance.py --real`。

最终独立目录：`runs/framework_acceptance/8f8d2b7043dc4b569618ba24db8cbe2c`。

| 场景 | 实际执行 | 任务目标与时长 | 结果 |
| --- | --- | --- | --- |
| C1 + 现有坐标搜索 | 2 次真实 MuJoCo 评价；再读同一评价命中缓存，求解增量 0 | `[0.30,0,0.08]`，40 步/0.08 s | 基线误差 0.05010972492756694 m；原 0.01 m 容差下 FAIL。两个 trial 均有独立评价、hash 和费用记录。 |
| C2 生命周期 | 1 次真实 MuJoCo 评价 | `[0.28,0.02,0.12]`，60 步/0.12 s | 误差 0.07349628850587914 m；FAIL。生命周期 finished，执行 60 步，保存 controller contract 与反馈更新。 |
| 数学扩展 | 原生 function 声明发现 → provider response 适配 → 真实独立进程 → 公共反馈 → JSON 证据读取 | 直态 PCC，L=1 m | 奇异值 `[0.5,0.5]` m/rad，rank=2，condition=1；第二次命中缓存。无任务评估。 |
| 保存信号规则 | 导入登记且 hash 相符的历史 MATLAB 轨迹，调用 `diagnostics.signal_rule` | 原始采样与原模型身份 | 保存独立规则版本/源码 hash、输入 hash、采样索引和结论；零新增 MATLAB 动力学求解。 |
| 诊断与展示 | 从新 MuJoCo 输出导入证据，调用诊断，再复用该输出生成 HTML | 两个目标、两个时长 | 目标/时长与 TaskContext、shared input、评价和 HTML payload 一致；末尾剩余时长 0。展示不再求解或重复运行诊断。 |

这批验收合计 3 次短评价、140 个 MuJoCo 积分步，模型 API 调用 0，MATLAB 动力学求解 0。两个开发任务未通过原容差，未将“工具运行完成”表述为“机器人任务成功”。本轮目标是接口和扩展机制，不是通过调参提高这两个短任务的分数。

开发过程中因控制/注册/搜索接口继续修改，保留了两批早期短验收目录 `a7bb096f8119477d8fef79eb70bbb87b` 和 `672593eebd8c4c848389c44e1e1d7a11`，每批同样 3 次短评价。本轮这类开发验收累计 9 次/420 步；交付以最后一批为准。三项旧控制回归另包含两条 1000 步的真实控制/被动执行轨迹，未运行整套历史实验。

## 代码、注入、保存数据和真实后端分别计数

共 **36 个不同用例分批通过**，不称为一次全量测试通过：

- `tests.test_framework`：13 项，直接覆盖三个原问题、目录绑定/未实现声明、数学 native 链、缓存、进程超时注入、模型量缺失、独立诊断规则、控制 reset/周期/观测、搜索与评价身份、预算恢复、无效评分、旧 campaign evaluator/MATLAB 提案适配。
- `tests.test_public_tools`：11 项，既有 schema/native/gateway、错误语义、账本恢复、证据篡改、保存视频/诊断等回归；视频复用保存缓存，不生成新视频或求解。
- `tests.test_dynamic_runtime`：3 项，旧动态 agent 通道、证据分页、权限/恢复等；模型和数值 worker 均为明确夹具。
- `tests.test_round9`：6 项，IR/编译映射、参数身份、预算、实体时间、保存回放等；不做新动力学搜索。
- `tests.test_architecture.MuJoCoTests` 中 3 项控制相关回归：原测试的临时目录被 Windows 沙箱拒绝，最初 3 个 setup/cleanup 各报一次错误；改用普通工作区目录夹具后，原断言与真实 MuJoCo 均不变，3 项通过。没有改写原测试文件或放宽业务检查。

证据日志：

- [最终聚焦测试，29 项](evidence/framework/final_focused.log)：framework 12 + public 11 + round9 6。
- [新增 campaign/search 适配用例，1 项](evidence/framework/campaign_adapter.log)。
- [目录与扩展补充检查](evidence/framework/extension_checks.log)：其中两项是注册/反馈修改后的定向复验，不能重复计为不同用例。
- [旧控制测试目录夹具适配后的 3 项](evidence/framework/legacy_controller_checks.log)。
- [最初聚焦运行日志](evidence/framework/initial_test_run.log)：保留动态 runtime 的 3 项通过记录和临时目录失败原始记录。PowerShell 把 unittest 的 stderr 标为 NativeCommandError；实际失败原因是日志中的目录 PermissionError。

另通过 `compileall`、`git diff --check`。与 `1a0081b` 比较，`tasks/`、`physics_contracts/`、`metrics/`、`configs/run.yaml`、`configs/simulator.yaml`、`configs/experiments/`、`tools/design_continuation.py` 均无修改。原物理、评分、授权与历史兼容规则未放宽。

## 可搬运证据

- [结构化验收结果](evidence/framework/acceptance.json)。
- [证据压缩包](evidence/framework/acceptance_bundle.zip)，约 2 MB，96 个文件：原调用回执、两套评价配置/账本、shared input、IR/XML、轨迹、控制器更新、规则输出、HTML 等。
- [逐文件及压缩包 hash](evidence/framework/bundle_manifest.json)。压缩包内采用验收根目录下的相对路径；回执内保留原始运行目录身份，不改写历史证据字节。
- [源码身份清单](evidence/framework/source_manifest.json)。打包时已验证它与最终工作区 `source_hashes()` 和运行环境完全匹配。
- [31 项公共工具目录](framework_tool_catalog.json)、[可读目录](public_tools_catalog.md)、[领域契约与注册投影](framework_contracts.json)。这些文档都是代码契约的导出，不构成额外授权源。

## 没有声称完成的验证

没有外部 LLM API 决策闭环；使用的是实际原生工具 schema 与调用适配上的 provider-response 夹具。没有重新运行 MATLAB ODE 求解；现有 MATLAB 提案调用通过注入验证其记账/复用，真实搜索验收使用相同坐标提案公式的 Python 适配加 MuJoCo。没有真实机器人标定、通用动力学量验证、非长度执行器、新任务族或多 agent 验收。超时/中断异常路径为注入测试，正常数学 worker 与 MuJoCo 路径为真实执行，两者未混称。

后续能力接入与剩余后端限制见 [扩展说明](framework_extensions.md)。当前无待决定的授权或科学定义问题；超出已声明模型/执行通道的能力保持明确不支持。
