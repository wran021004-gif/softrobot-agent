# M5 Handoff R1：修复与六次真实错误审计

R1 离线验收通过；没有启动新科研 Study、Provider 或科学 Worker。
基线为 M5 实际执行提交 `2bbd532ec72a428ff84b0ab16e218fe8a66e9592`，
修复位于独立分支 `codex/m5-handoff-r1`。

## 只读证据与根因

原 Study `m5-main-off-experience-20261028-s1` 的 SQLite 均以 mode=ro / query_only
打开，保留996个事件、112条调用及0条未结算调用。未恢复或迁移已停止的 Study。
含原始请求的详细复盘保留在忽略目录 `runs/m5-handoff-r1/source_review.json`，不提交。

首次 M5 读取的原始反馈事件51含完整正文；其序列化工具结果3406 bytes，
超过原紧凑反馈2000 bytes门槛。Handoff提交事件62投影成 summary_only，
下一份Provider请求事件66原样携带该摘要，仅有引用，正文已经丢失。
已逐项核对原始反馈、保存的Handoff投影和实际wire，三者未被事后改写。

## 修复范围

- feedback_delivery：成功读取单项、含文本正文且完整序列化工具结果不超过8192 bytes
  的经验，按原始结果精确交付。仅响应实际read；搜索、不可用来源和超长正文不获此例外。
  不预注入六卡；原科学全文读取与硬上下文门禁保留。
- 从现有Main读取回执派生entry_id/revision去重进度，排除预检及Reporter读取。
  tool_read_completed与body_delivered分开；后者复用已有已确认Provider wire解析，
  只有原经验工具反馈完整出现才记为true。元数据跨Handoff保留，不重复携带正文。
  不新增持久化记忆、缓存或SHA机制；不把交付解释为理解、采纳或科学证据。
- 缺action错误增加具体字段和当前合法action列表；不替Main选择action。
  未改任务、评价器、优化器、预算、授权、路由或会话旋转逻辑。

原Store在新代码下只读重新投影，事件51可完整保留；原48份历史wire不会因此改变。
由27次M5读取和4次公共经验读取派生的历史进度只剩两项，body_delivered仍为false，
没有将修复后的投影冒充历史交付。

## 六次工具错误

表内编号均为原Store真实事件，wire列为下一份实际Provider请求。

| Main请求 | 错误 | 原反馈 → Handoff → wire | 交付及后续 |
|---:|---|---|---|
| 5 | TOOL_ROUTE_ACTION_REQUIRED_OR_UNAVAILABLE | 113 → 119 → 123 | 精确交付；6补generate，原expected仅重复错误码，R1补具体提示 |
| 34 | 同上 | 704 → 710 → 714 | 精确交付；35补generate，未提交实际生成Plan |
| 40 | 同上 | 833 → 839 → 843 | 精确交付；41补select，随后切到evidence_read，未SELECT |
| 45 | TOOL_SCHEMA_REQUIRED / fields | 932 → 940 → 944 | 精确交付；47补fields，随后出现视图混用 |
| 47 | EVIDENCE_VIEW_MISMATCH / candidate_index | 971 → 982 → 986 | 摘要保留准确working_set修正查询；48按该查询成功 |
| 47 | EVIDENCE_VIEW_MISMATCH / control_result_links | 976 → 982 → 986 | 摘要保留准确修正查询；剩余额度内未重读该项 |

六项Handoff投影与下一wire对应项完全相同；不是六次错误反馈丢失。
fields遗漏和派生视图混用属于F1已知类别，原校验/纠错有效；Main只部分修复，
未产生科学进展。缺action属于真实输入错误，原提示具体性不足。
没有数值求解或结构可行性证据，也不将这些错误全归为Main科研能力问题。

## 路由审计与离线验证

18次成功路由选择分布于16轮，下一份wire都加载了该轮最后合法选择。
请求1同时选择generate和经验工具，请求41同时选择select和证据工具，
后者覆盖前者符合现有单工具契约，不是Handoff遗失路由。
generate Schema确实曾进入请求3/7/14/20/24/30/36；Main随后自行切回经验。

仅运行四项定向unittest，37.708 s，全部通过；均检查实际序列化MockTransport请求：

1. 短卡超过旧2000 bytes门槛仍完整进入下一wire；切到generate后不重复正文，
   最小进度保留；零发送恢复后实际下一wire仍加载generate并保留精确交付状态。
2. 超长卡继续摘要，不授予正文交付状态。
3. 缺action、fields缺失、派生视图混用的纠错进入下一wire，修正工作集读取成功。
4. 复用原Handoff科学全文读取凭证测试，确认没有降低SELECT读取要求。

脚本化响应只证明交付和路由边界，不证明真实Main将生成候选或改善科学决策。
真实外部Provider0、科学Worker0、积分0；未跑全仓或全部F1回归。
下一步仅准备独立待授权的R2小预算配置，不复用旧授权、Store或余额。
