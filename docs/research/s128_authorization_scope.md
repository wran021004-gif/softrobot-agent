# S12.8 独立正式授权范围

2026-10-21 用户对完整冻结范围回复“批准”。独立批准已绑定下列范围身份和源码身份，
记录见 `evidence/s128_preflight/authorization.json`；正式研究已完成，自主 STOP、无 SELECT。
此范围不能用 S12.7.6 A/B 的批准或剩余额度代替。

- Study：`s128-cold-live-20261021`。
- 冻结源码、本地和冻结时远端 SHA：`988acfe3339dc4a55b6a46df7349ed98783ae4ee`。
- 配置身份：`ba4b62cc3e1efe04c0742bdbb6d64ba3e1546502b9a22e7ef9635251432b3833`。
- 范围身份：`416dc421be8453ea40b583fa23a69f28b344343d4e4d8cc85c961c53da19db28`。
- 机器范围：`evidence/s128_preflight/provider_scope.json`。

批准后允许真实 DeepSeek Agent 自主开展此新 Cold-start 研究：生成结构，选择数学、控制、
Direct/Residual PPO 等合法方法，读取真实反馈，修订研究或 SELECT/STOP。不规定动作顺序。
原任务、输入范围、时域、采样、评价器及验收阈值全部不变，不导入旧实验证据。

| 项目 | 冻结上限 |
|---|---:|
| Provider | `https://api.deepseek.com`，`deepseek-flash`，thinking enabled / high |
| Provider 请求 | 128，内含 12 protected |
| 单次输出 | 131072 tokens |
| 公共操作 | 400，内含 24 protected |
| 共享物理启动 | 80 |
| 数学分析 | 8 |
| 离线 NLP / BDF / NMPC | 各 4 |
| PPO 阶段 | 8，start 与 continuation 共用 |
| PPO 总训练动作 | 4,194,304 |
| 单阶段训练动作 | 1,048,576 |
| RL 独立评价 | 12 episodes，包含阶段评价预留 |

全部是上限，不是要求用满；共享物理、阶段和评价预留的原保护保留，不在运行中追加。
科学过程使用原 count-mode，没有科学时间提前停止。Provider 关闭自动重试。

允许传输：本 Study 的冻结任务、FamilySpace、生成结构、控制、工具 Schema、合法科学证据，
以及后续真实工具调用/ID/结果和完整 assistant reasoning。原始 HTTP、使用量和 receipt 完整留存。
不传输凭据、无关私人文件、旧 Study 聊天或已测实验答案。
Provider 文档参数已核对；批准后的 59 次正式请求均 HTTP 200，账户可用性已由实际请求确认。

原始 HTTP、完整 reasoning、SDK、Store、checkpoint、科学数组和完整 export
只保存在本地忽略目录 `runs/research/s128-cold-live-20261021`。
GitHub 只公开项目代码、配置、派生统计、必要证据引用和允许公开的报告。
**不授权上传原始 Provider 对话或完整私人 Store/SDK。**

从全新 Strands session 开始。P0 最小恢复一致性检查通过；完整生产轮换尚未单独准入，
使用已验证的连续路径和逐请求容量保护，不扩展新一轮 Harness 实验。
实际通过原始独立 MuJoCo 验收后才可 SELECT；有限预算未找到解时如实报告。
本范围不包含新 Study、额外额度、S12.9 或 S13。
