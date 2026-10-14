研究由真实 Strands/DeepSeek 模型选择动作并终止，原始请求、工具结果、证据读取和决定完整保留。

科学结果：新方案确认通过=True；任务表现=passed and confirmed。原确认基线保持 2/2，不计为本次新成果。
NMPC 实际执行=3；RL 训练=1；新数学求解=0；独立验证=0。
模型 STOP 决定：The confirmed joint-design result is limited: one deterministic fixed-initial-state acceptance per execution (seed 17, zero initialization), limited-repeat-supported, with no robustness, generalization, superiority or causal claim, and parameter_improvement_attribution_permitted false. Confirming the reference baseline is not a new achievement. The failed direct and residual RL routes and the failed independent mathematical verification are preserved as-is and establish neither design infeasibility nor a causal diagnosis of the reduced-model-versus-execution holding discrepancy. Unfinished requirements: study delivery/closeout of the frozen selection and its two confirmations, and any deeper diagnosis of the pre-holding node-velocity inconsistency and of the holding-speed gap, which are not required deliverables. Next step: stop.。

工程验证见 engineering_checks.json：真实 Windows 子进程树终止；超时失败回执与原有回执保留；无阶段时记录执行级超时；不确定终止保留待定及预留；恢复不启动；缺失检查点无需不可能评估；原始候选和参考可公开读取且可使用。
资源分配、实际消耗、预留和剩余见 scientific_summary.json；历史成本单独列出，无额度转移。
原始不可变证据见 immutable_artifacts.tar.gz；运行文件精确哈希见 runtime_manifest.json。
