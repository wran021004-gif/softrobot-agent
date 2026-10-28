# P2：修正数学授权后的第三轮 Thinking 配对

用户批准 P2 全局 Provider 上限 17、本阶段 9，仍保护原研究和本阶段各两次收尾额度；数学和回放预算不变，P3 不启动。原账本 addendum 为 `77173a2fd9c2b9fb9e81ae49dd30c820c1db2b4ec915fc254b19df0d3f2b1afa`。此次原子授权同时将此前已批准的数学范围绑定到新的配置身份，记录 `b0ad066ac558e83cb403eb61740bd95e06c72ac6a33e78d61fd3831c81aabda6`；没有增加数学条目、回放或方法权限。研究配置显式绑定 `0f26095c84232025b3c2d3121440395d9ccb76de`，原科学 profile 和历史保留。

两组获得同一决策包 `e26de61250fdbc332017abc7eb1b3f2202dd0ec5c9b69364e08b21412fcf63d7`：同一任务和工具 Schema、同一 T1 真实反馈、历史回放摘要、此前证据读取反馈、上轮两次完全相同的结果索引以及修正后的数学授权。历史回放以带原始引用的摘要提供；上轮实际工具调用没有被伪装成当前对话中的模型行为。两个请求只改变 `thinking` 和 `reasoning_effort`，没有复制旧 assistant reasoning；无自动重试。

| 指标 | Thinking-On，高 | Thinking-Off |
| --- | ---: | ---: |
| 请求 | `r3-request-f020584b4f744e18bdb4c2cae700a7fd` | `r3-request-7d849f4811b042938acc3660d923fa77` |
| HTTP / finish reason | 200 / tool_calls | 200 / tool_calls |
| 输入 / 输出 / 总 tokens | 41,860 / 7,759 / 49,619 | 41,835 / 335 / 42,170 |
| reasoning tokens | 5,862 | Provider 未报告 |
| Provider 墙钟 | 50.687 s | 2.328 s |
| 请求体 | 147,968 bytes | 147,943 bytes |
| 动作 | `research_plan.diagnose` | 两项 `evidence_read` |

两次响应完整，Off 的 reasoning tokens 未报告，保持未知。这个样本 Off 成本较低；上一样本 Off 反而略高，不能从少量样本宣称模式整体更优。

On 选择对两条保存的失败记录做只读诊断，实际工具返回 success，且没有进行数学或物理计算。然而其返回的 `numerical_evidence`、`incomplete_executions` 均为空，未能兑现模型希望对失败进行比较的意图；原反馈 `65d290a18f50b984a2ab7a1b6bbe47021f61037cc686d6119f4368a697ac2f45` 保留。模型假设两条失败不只是同一控制序列的问题，但两次记录使用同一候选及同一控制序列；仅凭这些记录不能分离模型或结构原因与该控制序列的影响，不能把假设当作结论。

Off 的两项读取均实际成功，分别读取当前 eligible methods 和 `tendon_force_capability_v1` 的方法详情，反馈 artifacts `d5570d5cc52fc49070a2b9e2ae631748574346ecffca11a0045c106305e62434` 与 `91c37a1e80e51c9c5a4271eb8456f2f9d62fa65089d0ee246095fc0d86def418`。第二项真实返回正式范围已授权，但仍缺少 72 维非零广义方向；该方法只是瞬时几何诊断，不证明动态任务通过。没有自动构造方向或执行数学计算。

## 诊断反馈修复

`diagnose` 原来只处理普通 `results` 中的不完整记录，忽略单独保存的 Native 分析和固定控制回放；普通 results 的不完整分支也缺少 `compact_result` 导入。修复使两类不完整结果作为只读事实返回，保留来源、状态、错误、完成步数、失败时间和控制值，并明确不作原因或任务通过结论。真实旧结果不变。

修复已提交并显式绑定到原 Study 的实现 `08da019101cb44f75b90c013c2bc56aea69fa3ab`，科学 profile 和计费不变。对现存两个 artifacts 做只读投影核验后，得到 Native 和物理回放各一条不完整记录，均为 152 步、0.152 s、FatalError；原因仍未解决。核验记录 `fe3d9046b4433f6d68832de59fcf39e7fa9058371bb7137a1e82f9cf9e3d36bd` 是实施后的离线审计，不冒充模型当时收到的工具结果，也不计为新的科学运行。没有自动重新执行诊断调用。

## 账本和限制

P2-B 共 12/17 Provider，剩余 5，其中原研究和本阶段各 2 次受保护，非保护 1 次；14/28 public、1/2 数学条目、1/1 独立回放，累计 2.8108355 数值秒。整个 P2 累计 12 Provider、18 public、3 数学条目、2 次 T1 尝试、1 次独立回放、7.0716047 数值秒，以及 **585,362 Provider tokens**（483,985 input、101,377 output）。阶段新增 tokens 为 **311,614**，超过之前建议的 300,000 监控阈值 11,614；该阈值先前明确是建议而非已执行硬上限，实际 Provider 用量和超出情况在此公开。无未结算 worker。

两组都尚未提出或执行结构/控制修订，真实反馈驱动修订仍未验证。只剩一次非保护 Provider，不能继续发送两次配对请求并同时保留四次收尾额度；上面新工具反馈和诊断修复尚未交给任何模型。监督暂停记录 `a71692452c1376cc1181a1bc4f1fad7d1fb7a108c16e694b6ad5c1507bf6e95e`，Study 保持 ready，不伪装模型 STOP。数学条目仍只剩 1，回放为 0，即使未来加 Provider 预算，也不能保证两组都能完成独立的数学修订验证；增加调用次数也不能保证模型不再选择读取。P3 仍为 `PENDING_EXPLICIT_P3_APPROVAL`。
