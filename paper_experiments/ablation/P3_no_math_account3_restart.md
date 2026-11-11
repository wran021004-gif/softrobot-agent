# P3 No-Math 第三账号重启

用户在账号诊断后明确要求“直接修复，然后我们重新开始这个消融实验的study”。此次重新开始由用户单独授权，不是自动预算扩展或自动新建重试。

旧Study `p3-ablation-no-math-20261112` 保持封存：默认8787网关的首个请求返回429，只有1次请求，无候选、科研决策、数学或物理执行；旧请求及错误证据完整保留、单独报告。不能将其当作有效No-Math科学结果，也不能认定第三账号额度耗尽。

新Study：`p3-ablation-no-math-20261112-account3-restart1`。配置为 `configs/research/study_p3_ablation_no_math_account3_restart_v1.json`，直接引用 `runtime_p3_gateway_account3_20261112.json`：8789端口与 `~/.softrobot-agent/chatgpt-api-account3.json`。模型仍为gpt-5.6-sol，Main/Reporter推理、解释器、线程及其他Runtime语义保持原值。

Core绑定 `16d72fe82263a44a83ca8dc6f8111b4b0e6c1858`。只修复原授权传输迁移与首个429后的精确SDK恢复兼容，不改P3任务、模型、设计空间、数值算法或No-Math门禁。5项新增Mock测试、原11项P3与9项M1回归全部通过；没有完整套件或新增科学预实验。

新Store为空、agent_choice；不导入旧Store、历史候选、控制参数或成功结构。Knowledge ON沿用原45记录／17ID及准确版本。原任务协议、双方向五阶段、阈值、物理模型、最终每段2cells及结果证据边界完全保留。

新Study硬预算：Provider总额200（Main/Reporter共享，含4保护）、数学0、物理150、公共操作800；FamilySearch每请求24/16。第200次允许完成、第201次禁止。预算不得自动增加；原定成功/budget_exhausted/incomplete_at_budget规则和缺测UNKNOWN规则沿用。旧错误请求1次另列，所以整个操作历史成本不能只报告新Study账本。

只启动这一个新No-Math Study。再次外部失败时保留原始失败并停止，不自动创建restart2、不换到其他账号、不启动其他消融。
