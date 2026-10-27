# BF4 S1：有限可行性搜索

## 授权与事先固定

2026-10-27，用户在当前对话明确授权：“授权 S1，预算可以充足”。
执行的是上一轮提议并冻结的 S1：至多 3 个结构、每个 1 个 `.2 N` 控制起点、每组至多 76 次 native 完整序列回调、共至多 3 次独立回放，最多 138,600 个积分步。
首次完整独立验收通过后立即停止可行性搜索；不追分，不自动开展 S2。

- 原 [v1 冻结计划](../../configs/research/bf4_tracking_freeze_v1.json)保持不变。
- 新 [S1 配置](../../configs/research/study_bf4_tracking_s1.json)记录本次授权、独立 Study 与额度。
- [固定驱动](../../tests/research/bf4_tracking_s1.py)仅编排原 Store、candidate generator、控制初始化、native direct control 和独立 physical_replay；无新优化器。
- 私有原始记录保存在 `runs/bf4-s1/private-store`，不上传成功结构、控制或原始 Store。
- 不继承 S0、BF1、BF2 预算；S0 的 1,200 步继续单列。
- 科研任务、12 mm 容差、0.6 s 时域、物理张力界、三结构顺序、四个控制结点、3 次 response 迭代与 5% 局部裕量均不调整。
- Provider、NMPC、RL、额外 GVS/T1/T2 评价和结构比较阶段的额度均为零。

准备检查：原 loader 可解析新配置，任务与 FamilySpace 身份与冻结计划一致，原编译器确认 development 接口就绪；驱动导入检查通过，未因此进行积分。

## 执行状态

待绑定本次提交后执行，完整结果和实际成本将在阶段结束后补齐。
