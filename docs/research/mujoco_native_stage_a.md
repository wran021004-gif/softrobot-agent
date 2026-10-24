# 阶段 A：MuJoCo 原生数学接入

本工作从已推送的 `research/s148-mass-intervention@34a3b22ca` 建立独立工作树
`.worktrees/mujoco-native-math-stage-a` 和分支 `codex/mujoco-native-math-stage-a`。
已读取 AGENTS、S142–S148 报告和相关实现；S142 报告从其原工作树读取。
主工作树的环境、未跟踪文件以及旧研究 Store 均不修改。

## 审计与实现边界

原项目已有结构生成/编译、MuJoCo 执行、局部受限响应优化、冻结任务约束、
Store/worker 恢复、F0–F2 ResultCard/Reporter/L0–L3。S144 的原生 checkpoint
已验证可复现 S142 增刚结构的 0.34–0.35 s；S145–S148 的 GVS 投影/质量诊断
不需要重跑。

实际缺口是 `analysis.calculate/dispatch` 绑定控制器准备的低维模型与 GVS 保存状态，
没有公共原生动力学、实际张力短时响应或固定输入结构功能响应。
因此只扩展原 `AnalysisRequest` 和 `research_analysis`，不另建 Agent、Store 或解释系统。

新增 `extensions/tendon_family/mujoco_analysis.py` 负责原生求值/积分，
`tools/research/native_analysis.py` 负责请求适用性、结构配对与原任务约束的局部解释。
结构仍通过原 `construct → resolved_configuration → generated_serial → compiler → compile_xml`。
原数值内核使用原编译器的内存 XML 输出，避免 Windows 临时目录 ACL 问题。

MuJoCo 使用 [原生 API](https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html)
提取质量矩阵、求解质量系统和 Jacobian；力分量遵循
[官方计算语义](https://mujoco.readthedocs.io/en/stable/computation/index.html)。
重力 **bias** 由相同构型零速度求值分离，重力驱动力为其负号；
速度 bias 为两次原生 bias 之差。被动力保留 spring/damper 等原生分量。
`J M⁻¹ passive` 明确是被动力对末端加速度的贡献，不是机器人的总恢复响应。
总末端加速度包含 `J qacc + Jdot qvel`。

## 公共调用

继续调用原 `research_analysis`，保持 `candidate`、冻结 `protocol` 与原预算准入。
新方法明确使用 `model_source="mujoco"`、`operating_point="saved_state"`：

```json
{
  "candidate": {"artifact_id": "<原候选证据 ID>"},
  "model_source": "mujoco",
  "operation": "short_input_response_v1",
  "operating_point": "saved_state",
  "saved_state": {"artifact_id": "<完整原生 checkpoint 的证据 ID>"},
  "protocol": "<原冻结 TaskAnalysisProtocol 对象>",
  "native": {
    "horizon_s": 0.01,
    "difference_step_n": 0.1,
    "correction_radius_n": 0.25
  }
}
```

`native_dynamics_v1` 只作零步进力学；`short_input_response_v1` 对每通道使用两档
实际合法张力差分，必要时单侧；`fixed_input_structure_v1` 增加
`structure_response={variable,candidates}`，比较已通过原结构授权的 1–2 个单参数候选。
差分不是重新优化后的能力，Conic/KKT/包络接口原义不变。

也可用 `execution + update_id` 读取当前 Study 拥有的完整理想张力执行：
在原数学 worker 内只重放所需实际输入前缀，逐点验证已保存 native 状态/末端量，
之后才克隆原生 checkpoint；前缀成本计入该结果。不要求旧优化器完整输入记录。
只保存 GVS `x` 的状态会返回不适用，不能冒充完整原生状态。

不指定 `model_source` 时旧 GVS/SoRoSim 调用与序列化保持原义。
显式 `gvs`/`sorosim` 选择低维 provider；SoRoSim 仍需候选冻结的原 solver 设置，
不会从其他控制器臆造。MuJoCo 不需要 GVS Basis、投影、动力学图或 MATLAB。

原生 v1 范围限定为无接触/约束、无外部施力、无 activation 状态的具名 hinge 模型及理想张力，
支持最长 0.05 s 的短时分析。本阶段不开发完整 MuJoCo-NMPC、全局结构搜索或自主 Study。

## 必要验证

用原 `.mainline5-env` 单线程环境，运行定向契约回归及
`tests/research/mujoco_native_stage_a.py`。后者通过真实 `analysis.dispatch`、原 contained worker、
Store receipt、ResultCard、Reporter 和 evidence_read 完成四个分析请求：原生力学、
六路输入响应、远段 Young 模量两档单侧扰动、远段截面高度 ±1% 配对。
主 Agent/Reporter 不调用 Provider；完整矩阵只保存在原分析结果中。

实际数值、成本与最终核验结果在实验完成后补入本报告。
