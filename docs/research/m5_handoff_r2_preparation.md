# R2：较小预算的 M5 Main-Off 经验辅助配置（未授权运行）

R1 已冻结为 `53b9bbdb99a92780b6130ccf5ddc4708098eddbc`。
新叶配置：`configs/research/study_m5_main_off_experience_r2.json`。
拟用独立ID：`m5-main-off-experience-r2-20261028`。
此交付只有配置解析和依赖检查，没有prepare/bind/run，没有创建Store或授权事件。

保留原M5任务、物理、评价器、两段六腱/每段12 cells、时间网格、agent_choice，
以及全部Main-Off/角色/按需工具/Handoff策略。六张短卡仍按需读取，
本地索引与卡片复制到新ID的experience资源目录，私有内容不提交。
不移植旧Store、候选、控制、accepted身份或预算余额；不增加初始规划要求。

| 项目 | R2上限 |
|---|---:|
| Provider总请求，含Main/路由/Reporter | 24（收尾6包含在内） |
| Public Operations，含原有子操作计费 | 80（收尾12包含在内） |
| 数学/Native共享分析 | 2 |
| 单次Native回调 / 迭代 / knots | 100 / 16 / 4 |
| 独立物理回放，共享物理启动额度 | 2 |
| NMPC/PPO/RL、自动重试、成功后额外确认 | 均0 |

按两次100回调、每次最多600积分步、保守前缀重建及两次独立回放，
现有额度覆盖约122,400次积分尝试；没有新增全局积分账本或硬门禁。
预算是上限，不保证完整科研链路或成功；首次完整独立通过仍立即原门禁收尾。

配置已解析，原任务/FamilySpace/控制/后端/角色比对不变，实际F3解释器依赖ready。
配置身份为 `8aeb40c6c0afaff8502c7741bd3e503c6a9175c2a34f171da2ec93873f2c643c`。
预检结果保存在本地新资源目录configuration_preflight.json，目录内没有platform.sqlite。

**仍需独立运行授权。** 拟授权目的地为
`https://api.deepseek.com/chat/completions`，模型deepseek-flash，Main Thinking关闭；
Reporter沿用现有策略且共享24次总额度。拟发送范围：冻结M5任务/设计空间、
本次候选结构和控制信息、Main计划/假设/工具请求及反馈、必要测量与Trace/Recall/
证据摘要，以及Main实际选择读取的六张私有短卡相应内容。
拟执行范围仅为上表预算内的一次正式Study及既有Handoff/精确恢复。
排除完整私有或历史Store、历史赢家结构参数、成功张力数组和原始成功控制轨迹、
完整Codex搜索日志及私有数据发布。原M5/C3授权不复用。

授权后仍须从此新配置正常prepare、冻结绑定和登记独立授权，再发送真实请求。
R1的离线交付验收不等于R2真实Main的行为或科学结果已被验证。
