# 公共接口验收记录 · 2026-09-14

基线 `e1051c43345aad634b5185758de21019ed4f0daf`，开发分支 `feat/round9-matlab-dynamics-design-loop`。Python 3.11.16（现有 softagent 环境）。最终聚焦检查 **37 项通过，0 failure / 0 error**；未执行全库 discovery 或新实验。

复现：

```powershell
python examples/check_public_tools.py
```

脚本输出在 `runs/public_interface_review/`；供 review 的静态副本为 [validation.json](evidence/public_tools/validation.json)、[完整测试日志](evidence/public_tools/tests.log)、[本轮实现文件 SHA-256](evidence/public_tools/source_hashes.json)。完整机器目录可通过 `python examples/public_tools.py catalog` 重新生成；阅读版是[统一清单](public_tools_catalog.md)。

## 验收覆盖与证据等级

| 等级 | 实际检查 | 能证明的范围 |
| --- | --- | --- |
| 代码/契约 | 29 个公共入口；52 项库声明；IMPLEMENTED 入口 AST 核对无缺失；目录发现未加载 mujoco、matlab.engine 或 reach_dynamics | 目录与源码入口、schema 一致；不证明后端当前有许可证/可运行 |
| 实际宿主链路，注入响应 | Dynamics `apply_model_response → submit → dispatch → attempt/public receipt → latest_preview`；旧 DeepSeek 的创建/检查/评价/拒绝/复用/停止 | 运行器、来源、费用与反馈连接真实执行；provider 响应和评价 worker 是测试注入，不是在线 LLM 实验 |
| 数学计算 | 独立 PCC 输入 L=1.25 m、bend=[0.4,-0.2]；雅可比对独立位置公式的中心差分一致至 7 位小数；随后原生调用 read_json | 已有几何内核端到端可调用、可组合，不依赖候选或冻结任务 |
| 独立数据夹具 | specimen_alpha、2.99–3.5 s、目标 [0.7,0.1,0.2] m；诊断时间阶段与 HTML 保存参数匹配；Node `--check` 通过 | 读取/诊断/时间轴不硬编码 cNNN、原目标或两秒；该夹具不作物理结果 |
| 真实后端静态检查 | 现有 MuJoCo 模型编译、质量/刚度映射、单向腱力、mj_forward 有限状态检查 | 真实引擎静态行为；验收禁止 mj_step，不代表新的动力学验证 |
| 真实历史结果复用 | c071 已保存 MATLAB 与 MuJoCo 原生视频，0.2–0.6 s、10 fps、各 5 帧；复制已登记证据至独立服务后走公共入口、重复调用缓存；视频字节、源数据和 manifest 哈希匹配 | 双后端历史视频缓存与公共接口接通；未重新渲染，也未启动 MATLAB 新求解 |
| 失败/恢复 | 无效版本/类型/非有限数、错 namespace、权限、预算、证据篡改、执行异常、封存恢复、未知工具名路径保护；V1 非数值 continuation 允许、数学变化拒绝 | 失败反馈、费用保留和恢复边界；不提供任意外部代码的 OS 隔离 |

验收脚本对 `mujoco.mj_step` 和 `DynamicsBackends.simulate`设置失败哨兵。新增动力学步、后端 rollout、真实模型 API 调用均为 **0**。原始 Round 9 状态、两个账本、冻结设置以及视频依赖/媒体文件的前后哈希全部相同，逐文件值见 validation.json。

真实人类 CLI 也完成了独立配置的 `init → call`：[调用回执](evidence/public_tools/cli_result.json)、[PCC 数据](evidence/public_tools/cli_data.json)。返回末端 `[1.2087480213744717, 0.2458610121248868, -0.1229305060624434]` m；caller 为 human_cli，收取一次服务 tool_call，模型/动力学调用均为零。副本内的 details_ref 保留原服务会话路径，原文件位于 `runs/public_interface_review/cli_geometry`。

本轮没有新 MATLAB/MuJoCo 动力学求解、在线 LLM 闭环、重新原生视频渲染或模型视觉理解验收。文本模型仍只获得媒体引用。这些未验证项不会标成 PASS。

## 回归期间发现的问题与处理

- 修复未知工具名直接进入 DynamicCampaign 结果路径的问题；公开错误现在可安全封存。
- 原 Round 6 测试夹具隐式读取当前开发配置，却断言 thinking=disabled、18 次模型预算；改为夹具显式配置，生产配置未改。原 DynamicContext 测试继承已终止历史实验，提前退出；改为测试自己所需的上下文约束，不改历史状态。修复后相关旧协议测试通过。
- 探索性运行 `tests.test_round7_context` 的四项旧测试仍因 Round 6 历史计算定义与后来代码不兼容而拒绝，未纳入最终聚焦验收，也未放宽数值检查。[只读兼容诊断](evidence/public_tools/legacy_compatibility.json)记录原因；其中 controller、DesignSpec、design_compiler 和 mujoco_tools 的差异在 e1051c4 已存在，本次对这四个文件没有改动。该结果不是声称全库回归通过。

原生视频内核、PCC 数学内核、DynamicsBackends、控制器、任务、物理契约、指标和原授权 grant 的 git diff 为空。未修改用户原有两个无关未跟踪文件。交付保留为工作区改动，供 review。
