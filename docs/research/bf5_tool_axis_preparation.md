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

接口与协议已冻结，动力学预检将在绑定提交后执行。后续只将真实结果、独立评价引用、费用与未决原因追加到此报告；不修改上述阈值和预算。完整私有结构、成功控制、轨迹、执行映射及 Store 不上传。

## 交给 A 的最小集成范围

集成注册的新 task/evaluator/contracts、任务专属 adapter、条件/协议分支、Native/playback 轴信号和双约束 response 衔接，以及本任务定义与有限配置即可。无需集成私有 Store、成功控制或结构答案，也无需本轮增加 GVS 姿态求导、RL/NMPC、完整姿态、外力、避障或新 STL 求解器。面向普通 Agent 的下一步仍限于显式序列路线；其他控制/数学路线需另行实现真实方向约束后再声明支持。
