from pathlib import Path
import json,csv,struct
O=Path(__file__).resolve().parent
def rd(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sv(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
cases=rd(O/'SOURCE_DATA/FULL_CASES.json');bindings=rd(O/'SOURCE_DATA/MODEL_BINDINGS.json');out=[]
for c in cases:
    tid=c['task_id'];name=c['condition_name'];bb=bindings.get(tid,[]);b=next((b for b in bb if b['condition_name']==name),bb[0] if bb else {})
    stem=f'{tid}_{b.get("condition_name",name)}'
    existing=lambda p:str(p) if p.exists() else 'unavailable'
    out.append(dict(task_id=tid,condition=name,condition_role=c['condition_role'],run_id=c['run_id'],candidate_id=c['candidate_id'],result_source=json.dumps(c['source_reference'],ensure_ascii=False),
        store=b.get('store','unavailable'),result_reference=json.dumps(b.get('result_ref','unavailable')),candidate_reference=json.dumps(b.get('candidate_ref','unavailable')),
        raw_reference=json.dumps(b.get('raw_ref','unavailable')),original_xml_files=json.dumps(b.get('xml_files',[])),
        archived_samples=existing(O/'FIGURE_DATA'/f'{stem}_SAMPLES.json'),archived_signals=existing(O/'FIGURE_DATA'/f'{stem}_SIGNALS.json'),
        full_arrays=existing(O/'SOURCE_DATA/TASK_TIME_SERIES'/f'{stem}_FULL_ARRAYS.json'),
        passive_original_trace_manifest=str(O.parents[1]/'runs/phs2d-paper-data-20261112/SOURCE_EXTRACTS/EXECUTION_MANIFEST.json') if tid=='PHS-2D' else 'unavailable'))
with (O/'RAW_RESULT_INDEX.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,list(out[0]));w.writeheader();w.writerows(out)
animations=rd(O/'ANIMATIONS_MUJOCO/ANIMATION_MANIFEST.json');rows=['# MuJoCo任务动画','', '以下动画均由已有姿态驱动同一可视化XML，通过MuJoCo原生Renderer录制。机器人、原负载、导向件、底座/护套、原任务物体及任务提示均在MuJoCo场景中渲染；文字使用原生mjr_overlay。GIF编码只保存原始帧，不绘制或拼接机器人；全部原始RGB PNG帧及帧时间索引均保留。','', '每项目前选择一个代表性required工况展示，不代表已经为全部工况录制视频。全部32条逐工况验收及轨迹入口仍在原结果表中。慢放、抽样及完整覆盖范围见下表与manifest，不能按播放时长读取物理速度。','', '| 任务 / 工况 | 已保存物理时间/s | 帧数 | 动画 |','|---|---|---|---|']
for a in sorted(animations,key=lambda a:a['task_id']):
    p=Path(a['animation']);rows.append(f"| {a['task_id']} / {a['condition']} | {a['simulated_time_range_s'][0]:.5g}–{a['simulated_time_range_s'][1]:.5g} | {a['frames']} | [{p.name}](<{p.as_posix()}>) |")
rows+=['','PHS s7_positive源文件是共用无载基线之后的已保存加载分支，动画按实际源时间显示该分支；共用基线及其余工况仍在原执行manifest中。PHS与P3的受力点标记为材料坐标s=.7，不是Tip。箭头长度仅为固定显示尺度；屏幕数字来自原任务载荷定义或原记录，不从箭头长度读力。','', 'T04：原存89个目标节点显示为参考路径；T05/T06：原有向工具轴以原生箭头标记；T09：真实按钮与探头连接保留，button_slide按原始环境状态逐帧更新，展示深度和原接触力；T10：原+Y脉冲只作视觉提示，不向控制器增加信息。','', '底座、端部锚点板和连接护套是零质量示意外观；负载和星形导向孔/支杆来自原模型。实际几何与质量信息以original_physical_xml为准，视觉提示不参加动力学。','', '命令：','', '```powershell', "$env:PYTHONDONTWRITEBYTECODE='1'", "$env:PYTHONUTF8='1'", '& C:/Users/gugugaga/miniconda3/envs/softagent/python.exe D:/softrobot-agent/paper_experiments/paper_results_master_20261113/animate_native.py', '```','', '仅重录一项可加`--only T09`等参数。动画脚本中没有mj_step，渲染不产生新的物理解。']
(O/'ANIMATIONS_MUJOCO/README.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
cmd='''# 原生渲染命令

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
& C:/Users/gugugaga/miniconda3/envs/softagent/python.exe D:/softrobot-agent/paper_experiments/paper_results_master_20261113/render_full.py
& C:/Users/gugugaga/miniconda3/envs/softagent/python.exe D:/softrobot-agent/paper_experiments/paper_results_master_20261113/animate_native.py
```

结构截图为2400×1800原生PNG；动画1280×960，原始帧保存于ANIMATIONS_MUJOCO/FRAMES，每项有FRAME_INDEX.json。原XML、独立视觉XML、相机、姿态、编码、时间及选择范围见相应manifest。Pillow只用于GIF容器编码，不用于绘制、合成、裁切或补结构。没有新积分、结构求解或任务验收。

数据图当前不继续生成；FIGURES和plot_master.py仅为暂存草稿。
'''
(O/'RENDER_COMMANDS.md').write_text(cmd,encoding='utf-8')
# Useful checks: references, counts, PNG headers and declared physics equivalence. No redundant source hashing.
required=['PAPER_SUMMARY.md','ALL_TASK_RESULTS.csv','TASK_CASE_RESULTS.csv','KEY_RESEARCH_NODES.csv','CANDIDATE_EVOLUTION.csv','HARNESS_COMPONENT_EVIDENCE.csv','RESOURCE_COSTS.csv','ABLATION_DESIGN.md','FIGURE_PLAN.md','TABLE_DRAFTS.md','FIGURE_CAPTIONS.md','EVIDENCE_INDEX.md','DATA_DICTIONARY.md','RESEARCH_PROCESS.md','RAW_RESULT_INDEX.csv']
assert all((O/n).exists() for n in required)
assert len(cases)==32 and sum(c['condition_role']=='required' for c in cases)==30
assert all(c['passed'] for c in cases if c['condition_role']=='required')
assert sum(c['condition_role']=='control' for c in cases)==2
assert all(not c['passed'] for c in cases if c['condition_role']=='control')
assert len(animations)==11
screen=rd(O/'FIGURES_MUJOCO/SCREENSHOT_SOURCES.json');physics=rd(O/'VISUAL_XML/PHYSICS_EQUIVALENCE.json')
for s in screen:
    p=Path(s['png']);data=p.read_bytes()[:24];assert data[:8]==b'\x89PNG\r\n\x1a\n';assert list(struct.unpack('>II',data[16:24]))==[2400,1800]
    assert Path(s['visual_xml']).exists() and Path(s['source_xml']).exists()
for r in physics:assert r['passed'] and all(r['checks'].values())
for a in animations:
    assert Path(a['animation']).exists() and Path(a['frame_index']).exists()
    frames=rd(a['frame_index']);assert len(frames)==a['frames'];assert all(Path(f['png']).exists() for f in frames)
    assert a['physical_integration_performed'] is False
    gif=Path(a['animation']).read_bytes()[:6];assert gif in [b'GIF89a',b'GIF87a']
sv(O/'PACKAGE_STATUS.json',dict(task_count=11,required_cases=30,required_passed=30,control_cases=2,control_passed=0,key_research_nodes=32,phs_nodes=11,
    physical_structure_rows_within_runs=28,phs_candidate_models=9,harness_components=11,resource_run_rows=23,structure_screenshots=len(screen),visual_models=len(physics),native_animations=len(animations),
    animation_frames=sum(a['frames'] for a in animations),data_charts='existing drafts retained; further plotting deferred',new_research_or_physics_integration=False,necessary_checks_passed=True))
print('PACKAGE',len(screen),'screenshots,',len(physics),'visual models,',len(animations),'native animations,',sum(a['frames'] for a in animations),'frames')
