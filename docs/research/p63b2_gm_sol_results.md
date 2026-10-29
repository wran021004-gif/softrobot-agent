# P6.3-B2 G / M：sol 实际小测试

用户明确要求开始 G、M，先使用 sol。两项沿用 B2 已审查的预算与起点定义，独立分支 `codex/p6-3b2-sol-gm-tests`，不修改历史 Study。正式配置为 `study_p63b2_g_sol_live.json`、`study_p63b2_m_sol_live.json`；基线 `11d5f28a8fdb9962f4f7fe502084ac41c7cbdad0`。[零起点预检](p63b2_gm_sol_preflight.json) 记录两份准确 identity、预算与知识权限。模型目录非推理 GET 返回 200，准确 sol 可用；没有额外 smoke 推理。

首次启动前 guard(expensive=True) 复现 `PROTECTED_CLOSEOUT_REQUIRES_EXISTING_WORK_OR_STOP`：G 的零计算额度使 science_fits=False，故未发送任何模型请求。B2 的 resolver 检查未覆盖这个准入阻断。本轮仅在原 budget.science_fits 增加纯生成情形：FamilySpace、capabilities 为空、动作仅 generate/stop、尚无候选时允许进入原流程；取得合法候选后仍进入收尾，Provider/Public 保护额度不变，不增加任何数学/物理权限。新增一项离线准入测试通过（1.030s），覆盖零计算可生成、Provider 保护仍生效、取得候选即收尾、普通科学 Study 不受该分支影响。保留失败预检记录，并在干净提交后通过原 bind/migrate 更新实现绑定，不重置预算或删除原记录。

M 起点只按既定请求（2 段、4 腱、其余继承）调用一次原 generate_candidate，来源标记 Operator、未经任务评价，不自动搜索或修复。G 不提供候选。两项都使用原 formal_study_authorization 和相同 sol 的 request-feedback Handoff 准入；Knowledge-enabled、九项 success_case 可读、P3 原始中文。独立物理、NMPC、RL、Offline NLP/BDF 均为 0。所有失败请求仍计入各自总额，没有新的豁免。
