# BF5：末端位置与工具轴方向最小预检

## 真实任务与冻结范围

任务 B 授权在完成并推送 S2 后增加一个真正不同的最小任务类别。S2 已在 `4a5ddea86` 封存并推送；本阶段只用一个事先选定的合法 P1 构型，不做三结构比较或大型结构搜索。

[任务定义](../../tasks/bf5_position_tool_axis_v1.json)、[冻结协议](../../configs/research/bf5_tool_axis_freeze.json)及[独立 Study](../../configs/research/study_bf5_tool_axis_preparation.json)在任何 BF5 动力学搜索之前固定。应用语义是将轻型探测工具定位到工作点，并使工具中心轴朝向指定观察/接近方向。

- 世界系采用原模型的 `world_base_x_forward_yz_cross_section`；目标位置 `(0.290, -0.025, 0.120) m`。
- 工具轴是 `tip_site` 局部单位 `+x`，世界目标方向是单位化的 `(1, -0.18, -0.20)`，即 `(0.9656541191, -0.1738177414, -0.1931308238)`。
- 每个真实 post-step 时刻从 `data.site_xmat[tip_site]` 取得旋转矩阵；`axis_world = R_tip_site @ axis_local`，不是欧拉角、位置切向量或完整姿态误差。
- 方向误差为 `acos(clamp(axis_world dot target_axis_world, -1, 1))`，方向有正负，反向的轴误差为 π；统一 rad。
- 0.6 s 时域、1 ms 积分、20 ms 控制/记录；全部 30 个 post-step 样本必须完整，分别在 0.58 和 0.60 s 评分。两时刻都要求位置误差 ≤8 mm、轴方向误差 ≤π/60 rad（3°）。没有速度或轴向 roll 条件。
- 初始命名 qpos/qvel 全零，常量 0.2 N 六通道控制起点，物理界 `0..8 N`。沿用四结点 response 搜索，最多 51 次完整 600 步 Native 回调、2 次迭代、一次独立完整回放，共最多 31,200 步。代理同时达标即回放；不追分，不增加起点或放宽阈值。

## 物理可执行域审计

MuJoCo 原本已有 `tip_site` 世界旋转矩阵，原信号链只保存末端位置/速度，未导出工具轴。模型由每个柔性 cell 的两主弯曲铰链构成，允许空间弯曲产生末端轴变化；不包含独立材料扭转、剪切或轴向伸长。工具轴只有两个方向自由度，不能据此声称任意 6D 位姿控制。

在同一 P1 的三个合法小角度状态做了 3 次 MuJoCo forward、1 次模型构建，0 积分步；均无接触或约束激活，旋转正交误差不超过 `3.56e-15`，行列式接近 1。原始状态、轴、位置和费用本地保存在 `runs/bf5-tool-axis/domain_audit.json`。这是运动学域审计，不是这些状态在有界张力下可达或静力平衡的证明。其小弯曲状态接近目标的位置/轴组合，因此选择该有限目标开展一次有界动力学预检，而不扫描任务参数。

## 最小接口与边界

新增 `reference.tool_axis_goal` / `reference.tool_axis_evaluation`、`task.position_tool_axis`、`evaluate.position_tool_axis`。沿用 TaskDefinition、Registry、ResearchTaskAdapter 工厂、原 Store、candidate generator、Native 序列搜索、physical_replay 与 SELECT。任务专属 adapter 仅翻译目标、真实信号、条件与适用性。

新增 `tip_tool_axis`：tip 实体、3 维、无量纲、世界系、post-step。Native 与独立 playback 各自从自己的 MuJoCo 数据投影，不继承预测的方向。独立 evaluator 要求完整且对齐的位置和单位轴记录，分别保留 `tool_position` 与 `tool_axis_direction` 的实际误差、容限和通过状态。缺失轴、非单位轴或错误时间网格不能降级为位置通过。

Native response 对单位轴采用等价几何约束 `||axis-target|| <= 2*sin(angle_tolerance/2)`；实际排序和独立评价仍计算真实 arccos 弧度误差，两项归一化违反量分别保留。沿用原局部优化器，未开发通用姿态优化器。已有 affine/GVS 分析对整个新任务返回 `not_applicable`，方向要求作为原 unsupported contract 完整保留，没有只认证位置。

`backend.family_mujoco@1.3.0` 仅声明本轮已接通的显式序列路线，物理模型/积分器与原版本相同。配置中的既有 GVS controller 数据仅供原候选构造/序列绑定元数据使用；不执行 NMPC。该 backend 的普通 controller solve 明确拒绝新任务，防止默默调用只优化位置的控制器。旧 Tracking 定义、评价函数、信号与 backend 1.2 路线语义保持原样。

定向检查涵盖局部轴到世界轴投影、正向/垂直/反向夹角、roll 不变性、单位轴校验、位置与轴任一失败、缺失方向/错网格、弧度与等价锥、Native 两项覆盖和数学不适用；加上原 BF4 回归共 14 项通过，无科学积分。

## 有限预检状态

预检在提交 `ba68617d8` 绑定后已完成。基线最大位置误差 55.383296 mm、最大工具轴误差 0.271304541 rad。51 次 Native 回调、2 次 response 迭代后，最佳完整控制的独立回放为 **valid_failure**：

| 独立指标 | 实际值 | 冻结上限 | 结果 |
|---|---:|---:|---|
| 最大位置误差 | 7.969945402 mm | 8 mm | 通过 |
| 最大工具轴误差 | 0.0523898560571 rad（3.001717641°） | 0.0523598775598 rad（3°） | 失败 |
| 最大归一化违反量 | 0.000572547123 | 0 | 失败 |
| 完整积分与评分 | 600 步，30 个完整 post-step 样本，2 个评分时刻 | 完整双信号 | 通过 |
| 求解错误 / 张力违反 | 0 / 0 N | 0 / 原界 | 通过 |

Native 和独立回放分别计算的位置/轴误差一致；独立评价缺失项与来源问题均为空。没有把位置通过当成整个任务通过，也没有因只差 0.001718° 而放宽阈值。没有独立可行见证；这只是有限搜索失败，不能推出结构不可行或目标在动力学上不可达。

实际费用为 Native 51 次完整序列、30,600 步，一次独立回放、600 步，合计 **31,200 步**。Native / 回放模型构建各 1 次；前置运动学审计另计 1 次构建和 3 次 forward、0 积分步。Store 数值累计 5.672948 s，驱动 9.403430 s（包含前者，不能再相加）。代理未同时达标，搜索在固定 2 次迭代结束后进行最佳序列的唯一独立回放；没有通过后追分。

原始数据、结构、完整控制、独立执行与评价映射、账本在本地 `runs/bf5-tool-axis/summary.json` 及 `private-store/` 封存。[公开收据](../../evidence/bf5_tool_axis_preparation/summary.json)只列指标、真实独立评价引用、身份、费用与适用范围。不得上传完整私有 Store 或控制。

现阶段最小科学缺口是：已有一条位置达标、方向略超限的完整失败序列，尚缺一条同时满足两项条件的独立动态见证。后续如继续寻找可行解，必须保留本次预算与结果，在单独声明的续算额度内调用研究链路现有工具；不得倒改这个预检、重新定义目标或把失败记作通过。

## 面向可行解的有限续算（计算前声明）

用户随后明确：“我们以找到可行解为目的，只能使用研究链路中提供的工具”。据此优先继续当前工具轴任务，以完整独立通过为停止目标；原 BF4 已有 S1b 见证，S2 的公平失败对照不变。

新的[续算冻结协议](../../configs/research/bf5_tool_axis_continuation_freeze.json)与[独立 Study](../../configs/research/study_bf5_tool_axis_continuation.json)在续算之前声明：同一个 P1、同一真实任务和零物理初态，使用原研究链路 `initialize_control` 从该候选自身已失败的完整最佳控制重新绑定；不手改控制数组，不继承验收。至多额外 51 次 Native 完整回调、2 次原 response 迭代、一次独立回放、31,200 步。两个 BF5 阶段累计上限为 102 回调、2 次独立回放、62,400 步，不清空原 Store 或费用。

续算仅调用既有生成、控制初始化、`research_analysis` Native response、`physical_replay`、证据读取与 SELECT。使用原优化器已提供的 `safety_margin_fraction=0.005`，使局部规划目标略在边界内，针对先前观察到的正残差；独立物理验收仍为原 8 mm 和 3°，并非放宽标准。未新增求解器、控制方法、结构扫描或外部数值试算。完整独立通过后立即 SELECT 封存，不进行额外追分。

## 交给 A 的最小集成范围

集成注册的新 task/evaluator/contracts、任务专属 adapter、条件/协议分支、Native/playback 轴信号和双约束 response 衔接，以及本任务定义与有限配置即可。无需集成私有 Store、成功控制或结构答案，也无需本轮增加 GVS 姿态求导、RL/NMPC、完整姿态、外力、避障或新 STL 求解器。面向普通 Agent 的下一步仍限于显式序列路线；其他控制/数学路线需另行实现真实方向约束后再声明支持。
