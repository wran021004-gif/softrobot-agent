# Reporter 到正式 Plan 与自主被动混合搜索

基线 `9c59b7d77`。保留此前全部提交和科学记录。

## 只读审查旧会话

旧 Study `passive-knowledge-loop-20261107` 只通过 query-only Store 连接和原审计文件读取，没有更新旧配置、事件、Evidence 或 Plan。单独的新审查位于 `evidence/passive_post_reporter_search_20261107/previous_failure_review.json`。

Reporter 的解释已在随后的三个 Main 请求中交付。第一个请求的 `research_plan` 本来已经允许 diagnose，Main 却又选择同一 diagnose route，所以这一步并非必要。无法从公开记录断言模型的内部动机；上下文同时说旧 diagnose 已完成、提供已加载数学接口、又建议 route/新 diagnose，存在表达冲突。

其他 Plan 动作仍被单一动作 Schema 挡在路由后，且 L0 的被动动作过滤器还遗漏了已授权的 search。route 的返回明确表示“仅选择，下一个请求加载”，没有提交 Plan。最后一次普通 Main 请求花在该选择上，随后两个 Closeout 请求只允许既有收尾，最终用于结果索引、大结果导航和过期分页请求。原 12/2 算术正确，但没有保留 Reporter 后的决策阶段。首次无效 metadata 搜索、刚保存 Plan 的重复读取和错误的顶层 selected_candidate 也消耗了请求；不能将全部失败归因于额度不足。

## 最小实现

- 已完成 Reporter 解释后，沿用原 `research_plan` 契约同时提供当前准入动作；Main 可直接提交，原 Host 准入、引用和费用检查继续执行。route 保留，用于确有需要的工具或动作消歧。
- L0 指出最新科学结果、当前候选、Reporter 假设解释索引、可用正式 Plan 和被动搜索范围。Reporter/Knowledge 仍是解释与上下文，不授予科学证据资格，不复制全部正文或矩阵。
- 被动 L0 动作过滤器接回已授权 passive search，不新增搜索实现。
- 修正可表示种子判断：原型固有的站点截面旋转可由既有生成器精确保留，不应被统一截面尺寸检查误拒。额外旋转和真正不均一截面仍拒绝，不做有损转换或自动修复。
- 新 Study 初始共享 Provider 16、额度内 Closeout 2、数学 4、搜索最多 8 个提案/3 次数学评价；其余物理、Replay、BDF、NMPC、RL 为 0。搜索子域为段数 [2,3]、腱数 [3,4]，完整 FamilySpace 未缩小，变量子集和连续区间由 Main 选择。
- 不新建阶段计数器。复用 `pause_exploration_remaining` 的已结算暂停：Reporter 前阈值 5，使第 9 次 Main 之后保留一次 Reporter + 四次普通 Main + 两次 Closeout。Reporter 后阈值 2，用于在进入 Closeout 前检查真实进度。用户本轮明确允许进度性追加；如确有需要，维护者显式调用原有限追加机制，保留全部成本与失败，不由 Agent 自动扩额。

## 冻结前离线验证

新增四项针对性检查：真实 SDK/Mock HTTP 的直接 Search Plan Schema 与原始编译、准入、保存；保留显式 route；L0 候选、数学来源与 Reporter 解释索引；16/2 的九次前期请求暂停和至少四次 Reporter 后普通容量；离散和连续坐标生成、固定原型旋转精确保留及额外旋转拒绝。没有把脚本选择算作自主能力。

已有主动种子/路由精确保留检查通过。两项旧 SoRoSim Mock 测试在 fixture 准备阶段因该 Python 缺少 `matlab.engine` 无法启动，没有进行安装或替代为物理成功。将使用现有原生主动小回归完成兼容检查后，再启动唯一新真实 Provider Study。

真实验收和最终十四项结果将在测试结束后补充；此时没有发送新真实 Provider 请求。
