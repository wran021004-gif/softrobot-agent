"""Append the independent delivery review after all real slots have settled."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.state_io import read

OUT=Path(__file__).resolve().parent
review=read(OUT/'independent_results_review.json')
selection=read(OUT/'final_frozen_selection.json')
verification=read(OUT/'verification.json')
accounting=read(OUT/'publication_inflight_accounting.json')
assert review['independent_checks_passed'] and verification['complete']
doc=ROOT/'docs/research_v3_structural_continuation.md'
marker='## 完整冻结验证与最后交付'
old=doc.read_text(encoding='utf-8')
if marker in old:raise ValueError('FINAL_REVIEW_ALREADY_APPENDED')
groups=verification['groups']
lines=['',marker,'',
 '同一活动完成六次研究尝试：两次既有 terminal 权重实验，以及本次恢复的近段两点和反馈后实际执行的远段两点。近段与远段批次均为 nominal、seed17；除各自 section scale 外，近/远长度 0.16/0.11 m、两种 compliant 材料、terminal/holding 权重 0.05/0.05 均固定。全部为有限枚举，独立数值诊断为零；嵌入 NMPC 数值计算计入后端。',
 '', '近段反馈后 model-6 真实提出并执行远段批次。之后 model-7 的长度提案因每点缺少全部变量而拒绝；model-8 的远段长度提案因完整计划预算少 590 s 而拒绝。两者没有执行长度候选。model-9 随后自愿 STOP，但把“实际可用容量的短缺为零”误读成“实际可用时间为零”。原回答和错误回执保留；这不是资源耗尽或最优停止点的证据。近段控制混淆、历史任务身份不匹配及 F437 范围错误的独立纠正见 review JSON。',
 '', '冻结资格规则选择旧 terminal 权重 0.10 候选 batch-396bdbbae02626d3-0；holding 权重仍为 0.05，物理结构不变。历史 trade-off 不取消新鲜 nominal 联合通过的资格。完整预算 gate 通过后，依五案例、seed17 再 seed18、每槽 incumbent 再 candidate 的顺序完成二十次新执行，未调参、替换候选、重试或用历史缓存替代。',
 '', '下表单位为：终端误差/保持最大误差 mm，保持最大速度 mm/s；联合判据仍为位置 10 mm、保持速度 20 mm/s。完整精度及执行 ID 见 verification.json。',
 '', '| 案例 | seed | incumbent 联合 | candidate 联合 | incumbent 三指标 | candidate 三指标 |',
 '|---|---:|---|---|---|---|']
def metrics(r):
 m=r['acceptance']['metrics']
 return '/'.join(f'{1000*m[k]:.6f}' for k in ('terminal_error_m','holding_max_error_m','holding_max_speed_m_s'))
for slot in verification['plan']['schedule']:
 pair=[next(r for r in g['records'] if (r['case_id'],r['seed'],r['repetition'])==(slot['case_id'],slot['seed'],slot['repetition'])) for g in groups]
 status=['通过' if r['acceptance']['accepted'] else '失败' for r in pair]
 lines.append(f'| {slot["case_id"]} | {slot["seed"]} | {status[0]} | {status[1]} | {metrics(pair[0])} | {metrics(pair[1])} |')
lines+=['','| 角色 | 联合通过/固定分母 | 最差终端 mm | 最差保持误差 mm | 最差保持速度 mm/s |','|---|---:|---:|---:|---:|']
for group,aggregate in zip(groups,review['matched_verification']['groups']):
 m=aggregate['metrics']
 lines.append(f'| {group["role"]} | {aggregate["accepted"]}/{aggregate["scheduled"]} | {1000*m["terminal_error_m"]:.6f} | {1000*m["holding_max_error_m"]:.6f} | {1000*m["holding_max_speed_m_s"]:.6f} |')
outcome='按冻结改善规则支持晋升该候选' if selection['improvement_supported'] else '按冻结规则保留原 incumbent'
lines+=['',f'完整比较为 `{selection["comparison"]["relation"]}`，basis 为 `{selection["comparison"]["basis"]}`；{outcome}。此结论与“整个套件联合通过”分别报告。权威的验证后选择见 final_frozen_selection.json；原科研 STOP 的 selected 身份仍封存保留，不通过重开科研改写它。',
 '', '独立审查从官方评价与 motion 原始记录重算末段六点、三个指标及联合通过，核对二十个唯一新执行 ID、顺序、冻结参数/初态/控制器/后端/模型、资格选择、聚合、原限额/时钟、旧封存文件及实现 hash，十四项全部通过。结果见 independent_results_review.json。',
 '', '最终模型报告没有送出：组装触发 CONTEXT_VERIFICATION_METRIC_JOIN_CONFLICT。两次 incumbent nominal 的 terminal_error_m 在官方评价/验证表示为 0.002697828858325615 m，而历史 bound ledger 为 0.0026978288583256148 m，相差 4.336808689942018e-19 m；严格相等保护拒绝合并。二十槽位合成 gate 没有覆盖此真实的浮点表示差异，故通过工程 gate 不等于最终实跑报告一定可组装。原始请求快照、两份数值与事实 ID 见 final_report_blocker_review.json。未绕过保护、舍弃原值或调大 token 限额。final_model_interpretation.json 是此前 index3 的工程报告，不能当作最新科学 STOP；当前独立审查明确标记 final_model_report_is_current=false。修复已满七次，因此止于完整物理验证和独立交付，沒有第八次修复、重发提供方或重跑物理验证。',
 '', '初始全链 gate 有 34 项受影响检查；第七次修复另通过两项真实反馈/最大八研究点加二十合成验证槽位的请求压力检查，以及十项相关回归。合成回执不是物理证据。旧 Stage359/Stage356 整类回归及两项旧 settlement 假设失败日志均保留，没有声称全仓测试全绿，也未放宽安全或复用规则。',
 '', '修复累计 7/7，本次新增 3/3。原截止时间仍为 1791377029.4261196（2026-10-07 12:43:49.426 UTC），原总预算不变，没有新角色/worker 或额外独立数值操作。最终验证后的封存交付结束本次续行；未使用的研究槽位不是必须耗尽的目标。',
 '', '发布快照包含独立审查/发布的在途预留，见 publication_inflight_accounting.json，不能当作最终实际费用。最终正常 push 与远端 SHA 核验后，原本地账本一次性结算收尾费用，权威收据在 runs/research_native_development_v3_20261007/structural_final_settled_costs.json。提供方失败请求未提供的 token 用量、货币账单仍未知；没有复制报告数字回填账本或重复退款。',
 '', '这些是固定开发案例中的观测比例，不是总体成功概率、连续时间保持保证、实时可行性、全局最优、结构因果解释或 LLM 优势证明。下一任务应另行授权：先解决官方终端指标与历史指标的精确来源/浮点表示合并，并以实际二十次回执覆盖 gate；再调查远段扰动保持失败、明确计划预算短缺提示。本次不增添第八次工程修复或新实验。']
doc.write_text(old+'\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(document=str(doc),outcome=selection['outcome'],comparison=selection['comparison']),ensure_ascii=False))
