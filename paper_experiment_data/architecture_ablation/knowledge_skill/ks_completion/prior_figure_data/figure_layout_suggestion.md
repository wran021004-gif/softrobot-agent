# Knowledge / Skill 2×2 绘图建议

- 每任务各一个 2×2 网格：列为 Knowledge OFF/ON，行为 Skill OFF/ON。主色编码 Decision Quality，次级网格编码 Historical Experience Utilization；四项分数保持独立，不用文字长度替代质量。
- 六个新回放的 Decision Quality 均为 4。经验利用分：T04 的 K+S− / K−S+ / K−S− 为 3 / 3 / 0；T07 为 4 / 3 / 0。单次回放、单模型盲评，不画统计显著性星号。
- K+S+ 用斜线填充或虚线边框，标“历史工程 Core Plan，非 LLM 回放”。其 Decision Quality 为两任务各 3；不能由分差推论联合开关损害性能，也不能证明联合增益。
- factorial_effects.csv 分开给出纯新回放的 K@Soff、S@Koff 差值与涉及历史参照的描述性差值。交互项不可严格识别。Knowledge 原文也包含部分流程建议，本实验不是事实与流程语义完全正交的干预。
- Token 使用 initial_context_tokens_estimate 比较初始上下文，另列 total_sent_input_text_tokens_estimate 和请求数展示修正开销。Main 实测用量缺失；历史 K+S+ 的上下文数只是未执行的重建估算，不能画成实测输入。六次新回放共 11 次请求、5 次 Schema 修正；最终 Plan 未被评审判定存在明确非法动作，不等于验证了执行准入。
- 盲评保留人工入口。首轮误将评审参考库视为每个 Main 已收内容而被替代，原请求、响应和评分保存在 review_round_1；最终图表只使用澄清后的评分。

## T04 流程图素材：K−S+ 新回放中明确写出的后续计划

~~~mermaid
flowchart LR
 A["生成当前合法候选"] --> B["原生初态构造"]
 B --> C["检查残差与误差"]
 C --> D["独立 qualify t=0"]
 D --> E["初始化绝对张力节点"]
 E --> F["完整独立回放"]
~~~

节点来自 K−S+ 原文，均为拟议步骤；未补入未明确提出的点组采样或资格绑定细节。K+S− 的并列注释可选“interior tension search”。历史执行另标：点组构造失败→局部重试→独立资格验证→完整验收，不能拼接成新 LLM 已执行的流程。

## T07 流程图素材：两个单开条件分轨展示

~~~mermaid
flowchart LR
 K1["K+S−：历史两根段腱＋两全长腱"] --> K2["生成当前候选"]
 K2 --> K3["后续优先诊断 M1_B"]
 S1["K−S+：共同结构假设"] --> S2["生成当前 owned 候选"]
 S2 --> S3["最难任务诊断"]
 S3 --> S4["同一结构标识上验证全任务"]
~~~

两轨来自不同条件，不合并成一次联合 LLM 决策。控制初始化迁移只用历史动作原文作侧注：“No physical acceptance or state is inherited; all controls are freshly reintegrated.” 本检查点没有实际子任务结果，不声称已避免错误拼接或错误迁移。

素材：[原文 Clip](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/figure_data/knowledge_skill_clips.md) · [Clip JSON](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/figure_data/knowledge_skill_clip_data.json) · [四条件评分表](D:/softrobot-agent/paper_experiment_data/architecture_ablation/knowledge_skill/figure_data/factorial_results.csv)
