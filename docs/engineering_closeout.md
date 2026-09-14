# f2df1b0 工程收尾与一次局部扩展

起点为 `f2df1b0ee50ce633b39df6b187798f6f87d73605`，工作区开始时干净。本轮只处理版本、源码身份、视频超时，并新增一个数学工具。没有动力学求解、付费模型调用、历史任务重放或新视频生成。

## 三项收尾

**版本一致性。** `ToolCall/PublicResult.contract_version=1.0` 只表示公共信封协议。`tool_version` 是每项注册独立维护的三段数字版本，不再由公共 schema 枚举 `1.0.0/1.1.0`。请求省略/null 时选择绑定注册版本；显式版本必须属于该工具的 `version + compatible_versions` 精确兼容集合。不暗示任意较低版本兼容。原生函数描述使用注册版本，宿主原生调用适配明确传入该版本；回执返回实际解析的绑定版本，并记录请求版本。未知工具无法解析绑定时版本为 null。旧工具仍保留原来的显式兼容集合。

定向检查把现有 PCC 工具临时注册成 `7.3.2`、兼容 `7.2.0`，验证声明、原生调用、请求校验、回执一致，未改公共版本列表。旧 `1.1.0` 请求被该测试注册拒绝且不收费。历史回执字节不回写。现有旧 runtime 的版本预设保持 1.1.0；独立服务可按自己的注册升级。本轮视频服务为 1.2.0，新数学工具为 1.0.0。

**旧验收源码身份。** 原 `docs/evidence/framework/source_manifest.json` 的 226 项全部可回溯：187 项与 f2df1b0 的 Git blob 字节完全一致，39 项仅换行表示不同。39 项中有混合 LF/CRLF 文件，不能只尝试“全 LF”和“全 CRLF”来判断内容是否变化。对这 39 项，工作区原始字节精确匹配旧 SHA256；仅将 CRLF 转为 LF 后，与 Git blob 做字节比较也完全一致。未做去空格、重排或语义宽松比较。当前 `core.autocrlf=true`。

已保留原始清单、原始验收包及哈希；另保存 39 份原始源码表示（约 89 KB 压缩包）与逐文件 Git/SHA256 对应表。没有内容差异或无法回溯项，因此未为该问题补做动力学验证，也没有修改任何历史兼容检查。

**视频超时。** 原 180 秒只存在于声明，inline 路径的 renderer、FFmpeg、MATLAB 启动/调用/退出都可能阻塞。现在服务直接使用既有 process 执行机制；CLI/campaign 的公共兼容函数也委托同一注册及 worker。期限从 worker 启动计，包含保存数据加载、缓存检查、渲染、编码、解码校验和引擎退出。宿主前置校验与最终证据文件系统持久化不属于这段 worker 期限，不承诺对异常文件系统/OS 调度给出绝对端到端上限。

为了避免只杀掉 Python 而留下 FFmpeg/MATLAB 子进程，在现有执行器增加了 `process_tree` 选项。Windows worker 在启动后端前加入 kill-on-close Job；无法建立 Job 时先报 `PROCESS_CONTAINMENT_UNAVAILABLE`，不启动后端。POSIX 用独立进程组。超时终止 worker 及所属后代，并最多等待 5 秒确认 worker 退出，原调用预留不退还。正常退出仍使用既有 Renderer/临时目录上下文和 `engine.quit()`；硬中断留下的未封存输出保留为故障证据，不伪装成可复用视频。

清理保证仅覆盖所属 Job/进程组。独立 broker 或主动脱离该组的外部服务不能保证被终止；系统拒绝终止/异常 I/O 也不提供绝对清理保证。本轮用真实子进程加阻塞绑定注入验证了 Windows Job 清理，没有启动真实 MATLAB 或 renderer。因此没有声称验证 MATLAB 的所有平台行为。旧有效视频按原 adapter/source/parameter 契约复用，原文件 hash 未变。

## 新扩展：PCC 参数公差传播

新增 `analysis.pcc_tolerance@1.0.0`，原生名 `analysis__pcc_tolerance`。已有能力返回 Jacobian 或单参数采样趋势，本工具产生此前没有的三维末端协方差、主误差方向、轴向标准差、RMS 位置偏差和参数方差贡献排名，帮助决定应优先收紧哪项参数公差。

输入为基准 `length_m/bend_rad` 和独立参数标准差 `length_std_m/bend_std_rad`，沿用 PCC 坐标、单位和模型边界。从 `PCCModel` 读取 tip/Jacobian，固定 bend 下长度导数为 tip/L。令 `A=[tip/L,J]`，计算 `A diag(sigma²) Aᵀ`；贡献排名按各参数对协方差迹的贡献排序。它不假定高斯分布、不提供概率置信区间，也不是有限扰动范围的严格上界。大公差或靠近 PCC 分支边缘时，一阶近似可能不可靠；重复特征值下的主方向不唯一。

此次扩展自身修改仅为：

- `schemas/pcc_tolerance.py`：输入和输出契约。
- `tools/pcc_tolerance.py`：协方差传播与贡献分析。
- `tools/tool_registry.py`：一条 ServiceTool 注册，含自身版本、分析语义、缓存和依赖。
- 定向测试及本文档。

没有为新工具修改公共 dispatch、反馈分支、预算、缓存、worker 或证据读取。那些公共层修改分别对应本轮已存在的版本和视频超时缺口。未来同类数学能力仍只需要自身实现、契约、注册与必要验证；有新模型假设或新增执行资源时才需要对应适配，不能借注册隐式获得授权。

一次实际原生调用的输入为 L=0.4 m、bend=[0.3,-0.2] rad、长度标准差 0.001 m、bend 标准差 [0.01,0.02] rad。结果与完整输入、来源及解释在 [调用记录](evidence/engineering_closeout/calls.json) 中。随后通过 `evidence.read_json` 读取 `/parameter_contributions`，与已封存结果一致。整个流程计费两次工具调用、零后端求解、零模型 API 调用。provider response 是离线构造，计算和公共调用链是真实执行，不称为外部 LLM 闭环。

## 最小验证与证据

[7 项定向检查日志](evidence/engineering_closeout/focused_tests.log)：版本传播、真实扩展调用/读取、保存视频缓存、阻塞 worker 与实际子进程清理、直态公差公式/零公差，以及两项原公共接口回归。全部通过后没有追加测试或重复验收。未为覆盖率运行全量套件。

- [旧验收与 Git 源码对应表](evidence/engineering_closeout/source_correspondence.json)
- [39 份原始换行表示](evidence/engineering_closeout/original_source_representations.zip)
- [可重跑的源码审计脚本](evidence/engineering_closeout/audit_sources.py)：固定参考 f2df1b0；当前文件已改动时从 Git/原始表示包恢复比对依据，不篡改旧清单。
- [本轮回执及输出](evidence/engineering_closeout/calls.json)
- [本轮调用依赖源码及测试后文案变动对应关系](evidence/engineering_closeout/validation_sources.json)
- [本轮调用时的依赖源码字节](evidence/engineering_closeout/validation_sources.zip)
- [当前可读工具目录](public_tools_catalog.md)，实时 JSON 可用 `python examples/public_tools.py catalog` 导出。原 `framework_tool_catalog.json` 保留为上轮快照。

测试后只调整了超时错误文案（不再笼统声称已终止）和目录展示文本/版本列，未改变执行行为；调用中的原始源码 hash 保持原样，另外保存了可按 hash 核查的调用时源码字节和变动对应关系。冻结任务、物理、评分、实验授权、历史证据及兼容规则未改动。三项收尾和一次扩展均完成，本轮至此结束。
