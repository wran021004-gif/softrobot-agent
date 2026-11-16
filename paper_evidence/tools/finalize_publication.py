"""Finalize derived views, concise handoff and experiment accounting; no inference."""
import csv
import json
import shutil
import statistics
from collections import Counter,defaultdict
from pathlib import Path
from build_evidence import *


def rows(p):
    p=OUT/p
    return list(csv.DictReader(p.open(encoding='utf-8-sig'))) if p.exists() else []


def document(path,text):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.strip()+'\n','utf-8')


def finalize():
    # Restore the single authoritative annotation table from the independent saved reviews.
    annotations=[r for r in rows('research_nodes/decision_annotations.csv') if r['annotation_round']!='independent_blind_model_assisted']
    keypath=OUT/'annotation/private_node_key.json'
    if keypath.exists():
        key=json.loads(keypath.read_text('utf-8'))
        for p in sorted((OUT/'annotation').glob('blind_batch_*.json')):
            result=json.loads(p.read_text('utf-8'))
            for a in result['review']['annotations']:
                annotations.append(dict(node_id=key[a['anonymous_node_id']],dimension=a['dimension'],score=a['score'],
                    rationale=a['rationale'],supporting_evidence_reference=a['supporting_evidence_reference'],confidence=a['confidence'],
                    uncertain_fields=a['uncertain_fields'],annotation_round='independent_blind_model_assisted'))
    write_csv('research_nodes/decision_annotations.csv',annotations)
    write_csv('annotation/annotation_results.csv',[dict(node_id=r['node_id'],dimension=r['dimension'],annotation_round=r['annotation_round'],
        authoritative_record='research_nodes/decision_annotations.csv#node_id='+r['node_id']+'&dimension='+r['dimension']+'&annotation_round='+r['annotation_round']) for r in annotations])
    old=OUT/'annotation/blind_review_results.csv'
    if old.exists():old.unlink() # superseded generated view; raw reviews remain intact
    blind=[r for r in annotations if r['annotation_round']=='independent_blind_model_assisted']
    lines=['# Model-assisted research-node annotation','',f'Initial coverage: 32 nodes. Independent blinded coverage: {len(set(r["node_id"] for r in blind))} key nodes, {len(blind)} dimension ratings in five stateless sessions. Physical Outcome is quantitative and has no subjective score.','',
           'The initial and independent rounds remain distinct in the authoritative `decision_annotations.csv`. `annotation_results.csv` is a relational index and does not duplicate score values. The independent review withholds final success, experimental labels, prior ratings and editorial rank. Same-model dependence, incomplete original hypotheses, and incomplete causal pairing remain limitations.','',
           '| Dimension | Initial known ratings / mean | Blind known ratings / mean |','|---|---:|---:|']
    for dimension in ['Hypothesis Testability','Evidence Grounding','Method Appropriateness','Research Adaptation','Evidence-to-Action','Rejection Quality']:
        vals=[]
        for condition in [False,True]:
            v=[num(r['score']) for r in annotations if r['dimension']==dimension and (r['annotation_round']=='independent_blind_model_assisted')==condition and num(r['score']) is not None]
            vals.append(f'{len(v)} / {statistics.mean(v):.2f}' if v else '0 / UNKNOWN')
        lines.append('| '+dimension+' | '+' | '.join(vals)+' |')
    lines+=['','These means describe this selected set and rating round only. Missing/inapplicable ratings are excluded, not filled with zero. They are not task-success scores. Generic original expected/refuting observations are retained and limit testability scores.']
    document('annotation/annotation_summary.md','\n'.join(lines))

    # Every new figure row derives from its authoritative experiment summary.
    context=rows('figure_data/fig08_context_comparison.csv')
    context=[r for r in context if r['protocol_id'] in ['E2-C035','E2-R2-C037']]
    newcontext=rows('architecture_metrics/context_cross_task.csv')
    write_csv('figure_data/fig08_context_comparison.csv',context+newcontext)
    ks=rows('figure_data/fig07_reporter_knowledge_skill.csv')
    ks=[r for r in ks if r.get('panel')!='C']
    newks=rows('architecture_metrics/knowledge_skill_supplement.csv')
    ks += [dict(panel='C',protocol_id=r['protocol_id'],task_id=r['task_id'],checkpoint_id=r['checkpoint_id'],condition=r['condition'],
        experience_utilization=r['historical_experience_utilization'],decision_quality=r['decision_quality'],evidence_consistency=r['evidence_consistency'],
        research_actionability=r['research_actionability'],session_status=r['session_status'],source_reference=r['source_reference']) for r in newks]
    write_csv('figure_data/fig07_reporter_knowledge_skill.csv',ks)
    retrieved=[];requests=[];expstatus=[];failures=[]
    for experiment in ['context_gateway','knowledge_skill']:
        folder=OUT/'supplementary_experiments'/experiment
        for p in sorted((folder/'sessions').glob('*.json')):
            if 'failure' in p.name:
                d=json.loads(p.read_text('utf-8'));failures.append(dict(experiment=experiment,source_reference=p.relative_to(ROOT).as_posix(),failure=d.get('failure'),usage='UNKNOWN',attempt_scope='pre-success transport/initialization; excluded from completed decision population'));continue
            d=json.loads(p.read_text('utf-8'))
            expstatus.append(dict(experiment=experiment,session_id=d['session_id'],task_id=d['task_id'],checkpoint_id=d['checkpoint_id'],condition=d['condition'],
                status=d['status'],valid_decision=d['status']=='completed',provider_request_count=len(d['requests']),
                new_scientific_actions=0,source_reference=p.relative_to(ROOT).as_posix()))
            for i,r in enumerate(d.get('requests',[]),1):
                u=r.get('usage');u=u if isinstance(u,dict) else {}
                requests.append(dict(experiment=experiment,session_id=d['session_id'],request_index=i,input_tokens_actual=u.get('prompt_tokens'),
                    output_tokens_actual=u.get('completion_tokens'),usage_scope='Provider returned usage only; absent means UNKNOWN',
                    response_model=r.get('response_model'),response_id=r.get('response_id'),source_reference=p.relative_to(ROOT).as_posix()+'#/requests/'+str(i-1)))
            for i,r in enumerate(d.get('reads',[]),1):
                retrieved.append(dict(experiment=experiment,session_id=d['session_id'],read_index=i,**r))
    api=OUT/'supplementary_experiments/context/sessions'
    for p in sorted(api.glob('*.json')):
        d=json.loads(p.read_text('utf-8'));failures.append(dict(experiment='API-original-attempt',source_reference=p.relative_to(ROOT).as_posix(),failure=d.get('failure'),usage='UNKNOWN',attempt_scope='HTTP429 quota failure, no completed inference; separate protocol'))
    write_csv('architecture_metrics/supplement_session_status.csv',expstatus)
    write_csv('architecture_metrics/supplement_request_usage.csv',requests,fields=list(requests[0]) if requests else ['experiment','session_id','input_tokens_actual','output_tokens_actual'])
    write_csv('architecture_metrics/supplement_retrieval_path.csv',retrieved,fields=list(dict.fromkeys(k for r in retrieved for k in r)) if retrieved else ['experiment','session_id','read_index','turn','evidence_id','level','source_reference'])
    write_csv('architecture_metrics/supplement_transport_failures.csv',failures)
    protocol_studies=[('Reporter-six-pair','T01;T08','six anonymous ON/OFF checkpoint pairs'),('E1-original-four-cells','T04;T07','eight original decisions'),
        ('E2-C035','PHS-2D','accepted-inference usage'),('E2-R2-C037','PHS-2D','cumulative accepted-request usage'),
        ('E2-X6-Gateway-20261116','T01;T04;T07;T08;T09;T10','six frozen cross-task pairs; unreturned usage UNKNOWN'),
        ('KS16-decision-only-20261116','T04;T07','four checkpoints × four K/S cells'),('T07-M1M2-paired','T07','prepared protocol; no matched physical results')]
    protocol_studies.append(('E1-five-reassessment-20261116','T04;T07','common five-dimensional reassessment of original eight decisions; original four scores retained'))
    studies=[r for r in rows('registry/study_registry.csv') if r['study_id'] not in {x[0] for x in protocol_studies}]
    study_sources={'Reporter-six-pair':'architecture_metrics/reporter_pairs.csv','E1-original-four-cells':'architecture_metrics/knowledge_skill.csv',
        'E2-C035':'architecture_metrics/context_pairs.csv#protocol_id=E2-C035','E2-R2-C037':'architecture_metrics/context_pairs.csv#protocol_id=E2-R2-C037',
        'E2-X6-Gateway-20261116':'architecture_metrics/context_cross_task.csv','KS16-decision-only-20261116':'architecture_metrics/knowledge_skill_supplement.csv',
        'T07-M1M2-paired':'supplementary_experiments/m1_m2/executable_plan.json','E1-five-reassessment-20261116':'architecture_metrics/knowledge_skill_five_dimension.csv#protocol_id=E1-original-five-dimension-reassessment'}
    for sid,tid,scope in protocol_studies:
        studies.append(dict(study_id=sid,task_id=tid,original_run_id=sid,role='architecture_decision_only' if sid!='T07-M1M2-paired' else 'physical_protocol_not_executed',
            source_branch='paper/evidence-synthesis-20261116' if '20261116' in sid or sid=='T07-M1M2-paired' else BB,
            source_commit='UNKNOWN' if '20261116' in sid or sid=='T07-M1M2-paired' else B,source_reference=study_sources[sid],study_description=scope))
    write_csv('registry/study_registry.csv',studies)
    # New source records are listed without digests or environment information.
    manifest=[r for r in rows('source_manifest.csv') if r['source_branch']!='paper/evidence-synthesis-20261116']
    for r in expstatus:
        manifest.append(dict(study_id='E2-X6-Gateway-20261116' if r['experiment']=='context_gateway' else 'KS16-decision-only-20261116',task_id=r['task_id'],
            source_branch='paper/evidence-synthesis-20261116',source_path=r['source_reference'],run_id=r['session_id'],candidate_id='UNKNOWN',condition_id=r['condition'],
            source_locator=r['source_reference'],notes='new decision-only normalized execution record; zero scientific actions'))
    write_csv('source_manifest.csv',manifest)
    # Protocol identity columns are explicit in each figure view.
    for p in sorted((OUT/'figure_data').glob('fig*.csv')):
        data=rows(p.relative_to(OUT));fid=p.name.split('_')[0]
        decorated=[]
        for r in data:
            if fid=='fig04' and 'gradient' in p.name:r['task_id']='PHS-2D'
            if fid=='fig07':r['study_id']=r.get('protocol_id','UNKNOWN')
            decorated.append(dict(figure_id=fid,**{k:v for k,v in r.items() if k!='figure_id'}))
        write_csv(p.relative_to(OUT),decorated,fields=list(decorated[0]) if decorated else ['figure_id'])
    cvalid=sum(r['session_status']=='completed' for r in newcontext)
    kvalid=sum(r['session_status']=='completed' for r in newks)
    cblind=len(list((OUT/'supplementary_experiments/context_gateway/blind').glob('*.json')))
    kblind=len(list((OUT/'supplementary_experiments/knowledge_skill/blind_primary').glob('*.json')))
    five=rows('architecture_metrics/knowledge_skill_five_dimension.csv')
    fivenotes='Original E1 and supplemental decisions additionally share a separate five-dimensional review: physical interpretation, evidence consistency, limitation recognition, research actionability and evidence-reference accuracy. Historical utilization stays separate. Original four-dimensional scores remain preserved and are never averaged with the added five-dimensional scores.'
    if five:
        profiles=defaultdict(dict)
        for r in five:profiles[(r['protocol_id'],r['task_id'],r['checkpoint_id'],r['condition'])][r['dimension']]=r['score']
        metrics=['physical_interpretation','evidence_consistency','limitation_recognition','research_actionability','evidence_reference_accuracy']
        profiletext=['# Common five-dimensional K/S reassessment','',fivenotes,'',
            '| Protocol / task / checkpoint / condition | Physical | Evidence | Limits | Action | References | Five-score mean |',
            '|---|---:|---:|---:|---:|---:|---:|']
        for identity,scores in profiles.items():
            vals=[scores.get(m,'UNKNOWN') for m in metrics];numeric=[num(v) for v in vals]
            mean=f'{statistics.mean(numeric):.1f}' if all(v is not None for v in numeric) else 'UNKNOWN'
            profiletext.append('| '+' / '.join(identity)+' | '+' | '.join(vals)+' | '+mean+' |')
        profiletext+=['','These are one blinded model assessment per task/checkpoint, not statistical estimates. Preserve adverse cells and failed-submission status from the long table. Different original and later checkpoint states limit cross-checkpoint comparisons. Old four-score means and these five-score means measure different score sets and must not be compared as an improvement.']
        document('architecture_metrics/knowledge_skill_five_dimension_summary.md','\n'.join(profiletext))
    context_table=['| Checkpoint | Flat status / quality / recall | Hierarchical status / quality / recall |','|---|---|---|']
    for checkpoint in dict.fromkeys(r['checkpoint_id'] for r in newcontext):
        cells=[]
        for condition in ['Flat','Hierarchical']:
            r=next(x for x in newcontext if x['checkpoint_id']==checkpoint and x['condition']==condition)
            cells.append(f'{r["session_status"]} / {r["blind_decision_quality"]} / {r["key_evidence_recall"]}')
        context_table.append('| '+checkpoint+' | '+' | '.join(cells)+' |')
    document('supplementary_experiments/RESULTS.md',f'''# Decision supplement results

The six cross-task checkpoints and capacity gates were frozen before inference. There are {len(newcontext)}/12 recorded Main sessions, {cvalid} valid final decisions and {cblind}/6 independent anonymous paired reviews. Failed submissions remain failed and were not replaced. All new scientific actions = 0.

{chr(10).join(context_table)}

The existing API exhausted credits before any accepted inference. The existing historical Gateway was used under a separate protocol and its already-established text-serialized Core Plan transport. One unsupported native-tools request and one local initialization error are retained separately. Group selection, task contracts and score rubric were not tuned after results. Requested model and wire configuration match across conditions; the Gateway's effective default reasoning/backend identity is not exposed. Actual usage not returned by the Provider remains UNKNOWN. No measured cross-task input-token reduction can be claimed.

The K/S supplement records {len(newks)}/16 sessions, {kvalid} valid decisions and {kblind}/4 joint anonymous checkpoint reviews. The two frozen decision nodes per task use the same current evidence in all four K/S cells and the original immutable E1 resource bodies. Resource citations can partly reveal access, limiting semantic blinding. These scores do not establish synergy, significance or physical improvement. Preserve saturation and failures under the unchanged rubric.

The original E1 four-metric definitions are used for the supplemental four-score table; only the obsolete no-current-candidate fact was adapted to the actual frozen later state. The earlier generic five-dimensional review is retained separately and is not renamed as original decision_quality. {fivenotes} The common five-dimensional table has {len(five)} dimension records. At T07-106, the unchanged full evidence corpus exceeds the existing Gateway body ceiling; deterministic shared-subtree references retain every field and value, with recursive expansion checked equal to the original corpus before accepted inference. All four cells retain identical representation, raw-record read rights and request budget. This delivery difference is disclosed; comparisons remain checkpoint-specific.

New session JSONs are normalized execution records: source paths and missing-value representations are normalized. Schema validation was performed on the original in-memory response before serialization. Final decisions, validation errors, returned request IDs/usage and actual read receipts are retained. Intermediate invalid draft text is not retained in the early normalized records; its validation errors and request counts are retained. Anonymous review text is preserved. This limits reinspection of draft-level repairs but does not turn an invalid submission into a valid decision.

M1/M2 has a bounded preparation for T07, with actual same-order four-actuator/four-tendon contracts checked from the stored candidate configurations. The matched all-condition input/initial-state bindings and fixed-input replays remain pending. Its twelve rows are NOT_EXECUTED/UNKNOWN, not new physical observations.
''')
    document('README.md',f'''# Physics-Grounded Agentic Research for Soft-Robot Co-Design

本目录按论文科学论点组织现有证据：Main Agent 提出物理假设，PPRP 将研究意图转为可执行问题，互补的 M0–M3 支持不同物理问题，数学证据与物理证据分别进入 Research Decision。Reporter、Knowledge、Skill 与 Hierarchical Context 的结果作为决策过程证据单独报告。

**FULL：11 项任务，30 个 required 条件，另有 T10 的两个冻结对照。** 每项任务均有 2–4 个 Research Nodes。Task Registry 有 12 条物理 Study 记录，因为 PHS-2D 包含两个独立 Study；不得把独立九段结果计入原 11 项 FULL 分母。

| 证据 | 当前交付 |
|---|---|
| 任务能力 | 11 项 FULL 汇总；33 个 A/B/C 组合；3,160 条逐条件指标；保留失败、资格、偏离和缺失 |
| PHS-2D-7S | 四腱、无主动执行器，10/10；最小受力点 14.798 mm，最大 Tip 4.347 mm，最大比 0.15375；属于 FULL |
| PHS-2D-9S | 独立 Journal 的 46 个候选；四个代表机制节点；10/10；独立复核最小受力点 11.155 mm，最大 Tip 3.068 mm，最大比 0.1093；保留半步长与初态扰动检查 |
| 数学验证 | 6 载荷分支 × 3 指标，共 18 组隐式/有限差分梯度；一条共同模量扰动方向；最大相对差约 0.1191223% |
| 研究过程 | 32 个节点，1,927 条原始事件/证据—行动关系；原始假设、执行状态与事后结果范围分开；8 条数值变化记录 |
| 节点标注 | 全部节点初评；{len(set(r['node_id'] for r in blind))} 个关键节点独立匿名模型复核；保留理由、来源、置信度与不确定字段 |
| Reporter | 六组配对完整；平均 +0.300，2 胜/4 平/0 负；两个重点案例及原始决策对照 |
| Knowledge/Skill | 原八个四格决策完整；经验利用 0/3/3/3，其余评分饱和；补充 {len(newks)}/16 个会话，{kvalid} 个有效决策；另按用户要求增加统一五维盲评，保留原四维 |
| Context | E2 与 E2-R2 保留各自 usage 口径；新增 {len(newcontext)}/12 个跨任务会话，{cvalid} 个有效决策，{cblind}/6 组盲评；新 Gateway usage 缺失时为 UNKNOWN |
| M1/M2 | T07 两个真实结构、相同四通道契约已核对；逐条件三模式方案和原请求模板已准备；完整成对物理结果尚未执行 |

## 使用入口

- `registry/`：正式任务名、Study、符号及指标。选定参数集合使用 I_k，合法设计空间使用 D；M0–M3 不是顺序流程。
- `task_metrics/`：权威数值、候选结构、物理工况、数值复核和原始资源范围。`research_nodes/`：观察—假设—研究—证据—行动—结果及标注。
- `architecture_metrics/`：完整 Reporter/K/S/Context 配对、逐请求 usage、实际检索路径和失败记录。
- `figure_data/` 和 `figure_manifest.md`：Fig. 2–8 绘图 CSV、Panel 坐标/单位、颜色、Caption、正文/补充定位及缺失数据。Fig. 4C 的 UNKNOWN 不能绘成结果。
- 仓库根 `paper_handoff/`：供论文分支使用的自包含数据快照；不需要连接实验 Store 即可读取 CSV 和绘图数值。

## 关键解释边界

原论文草稿将 FULL 的 PHS 写为九段，与 Source A 原记录不一致。此交付按原始七段 FULL 与独立九段扩展分别注册，未修改论文正文或 Figure 1。无真机完整记录支持时不生成 Fig. 9 的测量结论。

局部数学诊断、结构生成、输入迁移、已执行重放和完整独立物理验收不相互替代。T08-C 的 development 分类和不利结果保留。不同任务的 m/rad/N 不求混合均值；不同资源范围不相加。实际 usage 不可用时保留 UNKNOWN，不用 tokenizer 估算替代。

原始数据只读，来源以 branch/path/run/candidate/condition/记录定位，不计算或校验文件哈希，不复制 Store 或完整 Trace。新输出只有归一化记录和由其生成的绘图视图；论文交付目录是生成快照，不应手工编辑第二份数据。

K/S 统一五维评价为 Physical Interpretation、Evidence Consistency、Limitation Recognition、Research Actionability、Evidence Reference Accuracy。历史经验利用单列；原四维和新增五维不混算。原 E1 和后续检查点的决策状态不同，只做分检查点的描述性比较，保留评分饱和。

## 复现与尚缺

标准库离线流程：`python paper_evidence/tools/build_evidence.py` → `research_details.py` → `prepare_m1_m2.py` → `finalize_publication.py` → `validate_evidence.py`。原来源通过固定 Git 提交只读加载；原始局部 Trace/Store 只在所需节点细节提取时读取。决策补充脚本是显式单独入口，不会由离线构建或验证触发。

数据交付已覆盖全部 Fig. 2–8 入口，但匹配 M1/M2 物理实验、结构演化统一相机渲染和新 Gateway 实际 usage 仍不能宣称完成。完整状态见 `supplementary_experiments/RESULTS.md` 与 `validation_report.md`。未访问到附加设计文本/DOCX 时，以任务说明和正式仓库记录为准。
''')
    document('notation_registry.md','''# Notation handoff

The authoritative symbols are in `registry/symbol_registry.csv`. Use τ for task; d for morphology; calligraphic D for admissible design space; θ for controller parameters; U for control input; q for generalized coordinates; gτ,i for task constraints; Vτ(d) for re-optimized task violation.

At research node k use s_k, H_k, E_k, a_k, P_k, **I_k**, O_k, σ_k, B_k for state, working hypothesis, evidence, action, PPRP, selected parameters, observables, analysis semantics and budget. Selected parameters must not be denoted D_k.

E_k = (E_k^math, E_k^phys). Mathematical Evidence and Physical Evidence are independent paths. M0: Mechanism Sensitivity m(d); M1: Fixed-input Physical Response yτ(d,U0); M2: Re-optimized Task Capability Vτ(d); M3: Closed-loop Performance Jτ,H(d,θ). These are complementary semantics, not stages that must execute in order.

Canonical task labels are T01–T10 and PHS-2D, without mathematical-semantic suffixes. PHS-2D-7S and PHS-2D-9S are separate Studies. Architecture scores are model-assisted decision ratings, not human expert assessment or robot capability.
''')
    # Explicit column inventory makes each view directly consumable without hidden scripts.
    inventory=['# Table dictionary','', '| Table | Rows | Columns / key |','|---|---:|---|']
    for folder in ['registry','task_metrics','research_nodes','architecture_metrics','figure_data']:
        for p in sorted((OUT/folder).glob('*.csv')):
            r=rows(p.relative_to(OUT));fields=list(r[0]) if r else next(csv.reader(p.open(encoding='utf-8-sig')))
            inventory.append('| '+p.relative_to(OUT).as_posix()+' | '+str(len(r))+' | '+', '.join(fields)+' |')
    document('table_dictionary.md','\n'.join(inventory))
    print(json.dumps(dict(context_sessions=len(newcontext),context_valid=cvalid,context_blind=cblind,ks_sessions=len(newks),ks_valid=kvalid,ks_blind=kblind,annotations=len(annotations))))


def handoff():
    target=ROOT/'paper_handoff';target.mkdir(exist_ok=True)
    # Copy only requested normalized publication data and new result records, never the original Store/trace.
    for folder in ['registry','figure_data']:
        shutil.copytree(OUT/folder,target/folder,dirs_exist_ok=True)
    for folder in ['task_metrics','research_nodes','architecture_metrics']:
        shutil.copytree(OUT/folder,target/'supplementary_data'/folder,dirs_exist_ok=True)
    selected=['annotation_rubric.md','annotation_summary.md','annotation_results.csv']
    for name in selected:
        p=target/'supplementary_data/annotation'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'annotation'/name,p)
    # Blind outcomes and new decision/session records are part of the publication evidence, not original traces.
    for p in (OUT/'supplementary_experiments').rglob('*.json'):
        rel=p.relative_to(OUT/'supplementary_experiments')
        dest=target/'supplementary_data/supplementary_experiments'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    for p in sorted((OUT/'annotation').glob('blind_batch_*.json')):
        dest=target/'supplementary_data/annotation'/p.name;shutil.copyfile(p,dest)
    for name in ['metric_dictionary.md','notation_registry.md','figure_manifest.md','table_dictionary.md','validation_report.md','source_manifest.csv']:
        if (OUT/name).exists():shutil.copyfile(OUT/name,target/name)
    shutil.copyfile(OUT/'supplementary_experiments/RESULTS.md',target/'supplementary_data/EXPERIMENT_RESULTS.md')
    # Rewrite internal normalized-data links for this standalone directory. Immutable original source locators remain provenance only.
    for p in target.rglob('*'):
        if p.suffix not in ['.csv','.json','.md']:continue
        text=p.read_text('utf-8-sig')
        text=text.replace('paper_evidence/supplementary_experiments/','supplementary_data/supplementary_experiments/')
        text=text.replace('paper_evidence/annotation/','supplementary_data/annotation/')
        for folder in ['task_metrics','research_nodes','architecture_metrics','annotation']:
            # Avoid repeatedly prefixing an already-normalized handoff path.
            import re
            text=re.sub(r'(?<![\w/])'+folder+r'/', 'supplementary_data/'+folder+'/',text)
        p.write_text(text,encoding='utf-8-sig' if p.suffix=='.csv' else 'utf-8')
    (target/'README.md').write_text('''# TRO publication data handoff

This directory is self-contained for reading publication tables and plotting their numbers. It contains the canonical Registry, Fig. 2–8 CSVs, captions/Panel specification, metric/notation dictionaries, and complete normalized supplementary tables. No temporary script, local absolute path or original Store is required to read these results.

Use `figure_manifest.md` first. Figure views are generated snapshots of `supplementary_data/`; do not edit either as a second authority. The evidence-synthesis branch owns the source-normalization scripts. Original source locators identify provenance and are not runtime dependencies. New normalized decision records, blind reviews, per-request usage and explicit failures are included.

FULL means T01–T10 plus seven-segment PHS-2D: eleven tasks and thirty required conditions. The independent nine-segment Study remains separate. Missing measurements stay UNKNOWN. Figure 4C is an unexecuted physical protocol, and common-camera robot renders remain pending. New Gateway actual usage is UNKNOWN unless returned; it cannot support measured token-savings claims. See `supplementary_data/EXPERIMENT_RESULTS.md` for valid/failed submissions and blind-review counts.

The manuscript .tex files and approved Figure 1 are unchanged. Draft PHS portfolio naming must be reconciled during later manuscript editing. This delivery commit adds data only.
''','utf-8')
    print('Standalone handoff files',sum(p.is_file() for p in target.rglob('*')))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--handoff',action='store_true');args=p.parse_args()
    handoff() if args.handoff else finalize()
