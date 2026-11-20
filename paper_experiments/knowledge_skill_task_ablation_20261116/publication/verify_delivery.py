"""Read-only source consistency checks and checksums of publication products."""
import csv,json,gzip,lzma,hashlib,re,sys,subprocess,os,zipfile
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def csvout(p,rs):
 with Path(p).open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rs for k in r)));w.writeheader();w.writerows(rs)
def rel(p):return Path(p).relative_to(R).as_posix()
T=list(csv.DictReader((R/'summary/TASK_RESULTS.csv').open(encoding='utf8',newline='')))
expected={'K0S0':3,'K1S0':6,'K0S1':6,'K1S1':11};counts={c:sum(r['condition']==c and r['accepted']=='True' for r in T) for c in expected}
manifests=[load(p) for p in sorted((R/'episode_manifests').glob('*/*.json'))]
stores=[]
for m in manifests:
 p=R/m['store'];before=m['source_store_stat_before'];st=p.stat();stores.append(dict(task_id=m['task_id'],condition=m['condition'],unchanged_size_mtime=st.st_size==before['size'] and st.st_mtime_ns==before['mtime_ns'],native_stopped=m['final_native_state']['research_status']=='stopped',pending=bool(m['final_native_state'].get('pending'))))
critical=[]
for r in csv.DictReader((R/'raw_archive/CRITICAL_SOURCE_HASHES.csv').open(encoding='utf8')):
 p=R/r['path'];critical.append(dict(path=r['path'],sha256=r['sha256'],matches=sha(p)==r['sha256']))
historical=[]
for r in load(R/'ORIGINAL_FULL_STORE_BASELINE.json'):
 p=Path(r['path']);print('Checking historical',p.parent.name,flush=True)
 historical.append(dict(path=str(p),bytes=r['size'],baseline_sha256=r['sha256'],current_sha256=sha(p) if p.exists() else None))
for r in historical:r['unchanged']=r['baseline_sha256']==r['current_sha256']
dump(R/'publication/HISTORICAL_FULL_INTEGRITY.json',historical)
source_manifest=R/'SOURCE_MANIFEST.csv';saved=R/'publication/ORIGINAL_INPUT_SOURCE_MANIFEST.csv'
if not saved.exists():saved.write_bytes(source_manifest.read_bytes())
inputchecks=[];source_rows=list(csv.DictReader(saved.open(encoding='utf8')));last_mapping={r['archived']:r for r in source_rows}
for r in source_rows:
 p=R/r['archived'];source=Path(r['source']);actual=sha(p) if p.exists() else None;sourceok=source.exists() and sha(source)==r['sha256'];same=actual==r['sha256'];explained=same;basis='byte-identical'
 if not same and sourceok and p.exists() and (p.name=='RUNTIME.json' or p.name=='source-runtime-engineering.json'):
  src=json.loads(source.read_text(encoding='utf-8-sig'));arch=json.loads(p.read_text(encoding='utf-8-sig'))
  src.update(credentials_reference=str(p.parent/'UNUSED_NO_PROVIDER.json'),research_python='D:\\softrobot-agent\\.pilot-env\\Scripts\\python.exe',rl_python='D:\\softrobot-agent\\.pilot-env\\Scripts\\python.exe')
  explained=src==arch;basis='freeze.py declared credentials_reference/research_python/rl_python rewrite; parsed equality'
 if not same and r!=last_mapping[r['archived']]:
  explained=sha(p)==last_mapping[r['archived']]['sha256'];basis='earlier source mapping superseded by later copied T09 guide-hardware source; freeze.py lines 44-47'
 inputchecks.append(dict(source=r['source'],archived=r['archived'],exists=p.exists(),sha256=r['sha256'],archived_sha256=actual,source_hash_unchanged=sourceok,matches=same,explained_and_verified=explained,verification_basis=basis))
# Check original current checkout remains the committed reader runtime.
core=load(R/'PREFERRED_CORE_RUNTIME.json');core_current=subprocess.check_output(['git','-C',core['core_directory'],'rev-parse','HEAD'],text=True).strip()
selected=load(R/'selected_cases/SELECTED_TRACE_MANIFEST.json');tracechecks=[]
for case in selected['cases']:
 for cell in case['conditions']:
  m=load(R/cell['path']);folder=R/'selected_cases'/case['category']/case['task_id']/cell['condition'];valid=True
  for name in ['CORE_CALLS.jsonl','DECISION_EVENTS.jsonl']:
   dest=folder/(name+'.xz');src=R/m['source_episode']/name;h=hashlib.sha256()
   with lzma.open(dest,'rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
   valid=valid and h.hexdigest()==sha(src)
  tracechecks.append(dict(task_id=case['task_id'],condition=cell['condition'],compressed_logs_byte_identical=valid))
figures=load(R/'figures/FIGURE_MANIFEST.json');figurechecks=[]
for figure in figures:figurechecks.append(dict(name=figure['name'],files_exist=all((R/figure[k]).is_file() for k in ['png','pdf','data'])))
fact=list(csv.DictReader((R/'summary/FACTORIAL_EFFECTS.csv').open(encoding='utf8')));fx=next(r for r in fact if r['task_id']=='mean_of_matched_tasks' and r['metric']=='accepted')
factorial_ok=all(abs(float(fx[k])-v)<1e-12 for k,v in [('knowledge_marginal',4/11),('skill_marginal',4/11),('interaction',2/11)])
rootnames=['README.md','EXPERIMENT_PROTOCOL.md','FINAL_RESULTS_REPORT.md','AUDIT_REPORT.md','LIMITATIONS.md','FORMAL_COHORT_MANIFEST.json','PREFERRED_CORE_RUNTIME.json','ENVIRONMENT_LOCK.json','BUDGET_MANIFEST.json','CONDITION_MANIFEST.json','RESOURCE_MANIFEST.json','SCIENTIFIC_CONFIG_PARITY_AUDIT.json','SOURCE_MANIFEST.csv','.gitignore','.gitattributes']
dirs=['summary','episode_manifests','selected_cases','figures','raw_archive','source_snapshot','inputs','inputs_full_corrected']
files=[R/n for n in rootnames if (R/n).is_file()]
figure_paths={'figures/FIGURE_MANIFEST.json'}|{f[k] for f in figures for k in ['png','pdf','data']}
for name in dirs:files.extend(p for p in (R/name).rglob('*') if p.is_file() and (name!='figures' or rel(p) in figure_paths))
for name in ['build_dataset.py','analyze_and_plot.py','verify_delivery.py','audit_contexts.py','CONTEXT_AUDIT.json','REPRODUCTION_CHECK.json','DATASET_AUDIT.json','ANALYSIS_ENVIRONMENT.json','HISTORICAL_FULL_INTEGRITY.json','ORIGINAL_INPUT_SOURCE_MANIFEST.csv']:
 if (R/'publication'/name).exists():files.append(R/'publication'/name)
# Scan text and the content of compressed trace logs. Never print a matching
# payload: report only the file and pattern category.
patterns=[('openai_key',re.compile(rb'(?<![A-Za-z0-9_-])sk-(?:proj-)?[A-Za-z0-9_-]{24,}')),('github_key',re.compile(rb'(?<![A-Za-z0-9_-])(?:ghp_|github_pat_)[A-Za-z0-9_]{24,}')),('bearer',re.compile(rb'Bearer\s+[A-Za-z0-9._~-]{24,}')),('token_value',re.compile(rb'"(?:access_token|refresh_token)"\s*:\s*"[^"\s]{20,}"'))]
hits=[]
for p in files:
 if p.name=='DELIVERY_FILES.csv':continue
 if p.suffix not in ['.md','.json','.csv','.py','.txt','.toml','.gz','.xz']:continue
 stream=lzma.open(p,'rb') if p.suffix=='.xz' else gzip.open(p,'rb') if p.suffix=='.gz' else p.open('rb')
 with stream as f:
  tail=b''
  for b in iter(lambda:f.read(1024*1024),b''):
   blob=tail+b
   for label,pat in patterns:
    if pat.search(blob):hits.append(dict(path=rel(p),pattern=label))
   tail=blob[-256:]
for p in [p for p in files if p.suffix=='.zip']:
 with zipfile.ZipFile(p) as z:
  for info in z.infolist():
   if info.file_size>20*1024*1024 or Path(info.filename).suffix not in ['.py','.json','.toml','.txt','.md']:continue
   blob=z.read(info)
   for label,pat in patterns:
    if pat.search(blob):hits.append(dict(path=rel(p)+'!'+info.filename,pattern=label))
checks=dict(formal_cells=len(T),distinct_cells=len({(r['task_id'],r['condition']) for r in T}),counts=counts,matrix_matches=counts==expected,
 native_closed=all(r['native_stopped'] and not r['pending'] for r in stores),current_store_stats_unchanged=all(r['unchanged_size_mtime'] for r in stores),
 critical_source_hashes_unchanged=all(r['matches'] for r in critical),critical_source_files=len(critical),historical_full_stores_unchanged=all(r['unchanged'] for r in historical),
 historical_full_stores=len(historical),original_frozen_input_copies_unchanged=all(r['matches'] for r in inputchecks),original_input_files=len(inputchecks),
 original_input_sources_unchanged=all(r['source_hash_unchanged'] for r in inputchecks),declared_input_transformations_verified=all(r['explained_and_verified'] for r in inputchecks),input_copy_hash_differences=sum(not r['matches'] for r in inputchecks),
 preferred_core_commit_unchanged=core_current==core['core_commit'],core_commit=core_current,selected_cases=len(selected['cases']),selected_matched_cells=len(tracechecks),
 selected_logs_lossless=all(r['compressed_logs_byte_identical'] for r in tracechecks),figures=len(figures),figure_files_complete=all(r['files_exist'] for r in figurechecks),
 factorial_acceptance_exact=factorial_ok,credential_pattern_hits=hits,blind_ratings_completed=0,new_scientific_executions=0,source_modifications=0)
checks['ready_for_commit']=len(T)==44 and all(checks[k] for k in ['matrix_matches','native_closed','current_store_stats_unchanged','critical_source_hashes_unchanged','historical_full_stores_unchanged','original_input_sources_unchanged','declared_input_transformations_verified','preferred_core_commit_unchanged','selected_logs_lossless','figure_files_complete','factorial_acceptance_exact']) and not hits
reproduction=load(R/'publication/REPRODUCTION_CHECK.json')
checks['figures_reproducible_without_raw_stores']=reproduction['matrix_identical'] and reproduction['all_figure_data_identical'] and reproduction['figures_regenerated']==12
checks['ready_for_commit']=checks['ready_for_commit'] and checks['figures_reproducible_without_raw_stores']
dump(R/'publication/DELIVERY_AUDIT.json',dict(timestamp=datetime.now(timezone.utc).isoformat(),checks=checks,stores=stores,input_checks=inputchecks,trace_checks=tracechecks,figure_checks=figurechecks))
text=f'''# 最终归档审计

正式 44 单元全部原生封闭：{checks['native_closed']}。重建通过数 {counts}，与给定矩阵一致：{checks['matrix_matches']}。严格区分未选择与科研失败。

44 个当前 Store 只读提取期间的大小与 mtime 一致：{checks['current_store_stats_unchanged']}；{len(critical)} 个关键原始文件 SHA256 复核一致：{checks['critical_source_hashes_unchanged']}。完整原始文件目录索引使用路径、大小和 mtime；巨大 Store 和逐步文件没有逐一重算 SHA256，未声称全量内容哈希验证。

18 个历史 FULL Store 与实验启动前基线 SHA256 一致：{checks['historical_full_stores_unchanged']}。104 条输入来源记录的原始源文件均与原 SHA256 一致：{checks['original_input_sources_unchanged']}。12 条副本记录的字节哈希不同：11 个运行时副本按 freeze.py 预定改写三个宿主/凭据路径字段，另有一条 T09 早期映射被后写入的原任务 guide 硬件来源覆盖。上述改写/覆盖已逐条验证：{checks['declared_input_transformations_verified']}，没有静默把不等哈希当作相同。本次没有改写这些输入副本。现用 Core 提交仍为 {core_current}，本次没有改写 Core 或 manuscript。

六项案例的 24 条四条件 Trace，其解压字节与源日志完全一致：{checks['selected_logs_lossless']}。全部 12 张图均有 PNG、PDF、独立源 CSV：{checks['figure_files_complete']}。接受率配对边际与差中差精确复算：{factorial_ok}。

在不提供原始 episode/Store 目录的独立目录中，仅凭交付的紧凑表成功重绘 12 张图，接受矩阵与全部图数据逐字节一致：{checks['figures_reproducible_without_raw_stores']}。验证记录见 publication/REPRODUCTION_CHECK.json。

凭据模式命中：{len(hits)}。检查包含拟交付文本及压缩 Trace 内容；没有把此模式扫描解释为所有潜在秘密的形式证明。盲评有效评分 0/44，未制造独立评分。

完整原始文件保留本地，Git 包含紧凑数据及精选日志。目录完整索引不等于把所有原始数组上传，也不等于对全部本地文件做了内容哈希。

已知解释差异：T08 的 K+S− 和 K−S+ 均通过；不能列为 Skill 独有通过。优先案例多数没有正文检索链。最终上下文与记录的资源上限存在差异，所有实际值均保留，因此效应仅作描述统计。T04/K1S0 时间终止单列，不虚报其物理费用耗尽。

原生重建和给定通过矩阵没有未解决差异。可以提交：{checks['ready_for_commit']}。
'''
(R/'AUDIT_REPORT.md').write_text(text,encoding='utf8')
# Top-level source manifest retains original source mappings and adds all
# authoritative indexed source locations; it never relabels local-only as pushed.
sources=[dict(source=r['source'],archived=r['archived'],sha256=r['archived_sha256'],source_sha256=r['sha256'],role='frozen_input_with_declared_path_rewrite' if not r['matches'] else 'original_frozen_input',storage='included_input_copy') for r in inputchecks]
sources.extend(dict(source=m['source_episode'],archived=f'episode_manifests/{m["task_id"]}/{m["condition"]}.json',sha256='',role='formal_episode',storage='compact_manifest_in_git; original_store_local') for m in manifests)
csvout(source_manifest,sources)
files=list(dict.fromkeys(files+[R/'AUDIT_REPORT.md']));files=[p for p in files if p.name!='DELIVERY_FILES.csv']
delivery=[dict(path=rel(p),bytes=p.stat().st_size,sha256=sha(p),storage='intended_git_delivery') for p in sorted(files)]
delivery.append(dict(path='publication/DELIVERY_AUDIT.json',bytes=(R/'publication/DELIVERY_AUDIT.json').stat().st_size,sha256=sha(R/'publication/DELIVERY_AUDIT.json'),storage='intended_git_delivery'))
csvout(R/'raw_archive/DELIVERY_FILES.csv',delivery)
dump(R/'publication/GIT_DELIVERY_PATHS.json',dict(paths=[r['path'] for r in delivery]+['raw_archive/DELIVERY_FILES.csv'],total_bytes=sum(r['bytes'] for r in delivery),largest_file_bytes=max(r['bytes'] for r in delivery),ready_for_commit=checks['ready_for_commit']))
print(json.dumps(checks,ensure_ascii=True),flush=True)
if not checks['ready_for_commit']:sys.exit(2)
