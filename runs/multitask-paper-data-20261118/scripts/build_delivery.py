"""Assemble the evidence library, figure layouts and text-free video gallery."""
from pathlib import Path
import csv,json,html,os
from extract_render_inputs import O,ROOT,read,save,csvout

NAMES=['Multi-target Reach-and-Hold','Load-Conditioned Hold','Fast Target Reaching','Figure-Eight Trajectory Tracking','End-Effector Position and Tool-Axis Alignment','Loaded Time-Indexed Pose Scanning','Shared-Morphology Multi-Task Design','Passive Progressive-Stiffness Response','Guided Spring-Button Contact Manipulation','Impact-Recovery Control']
STORY={
 'T01':('结构与控制协同','14.1→14 mm 腱路，再将两段各加长2.5 mm；同硬件三目标分别重优化','补充；可作结构修改备用'),
 'T02':('材料修改','14→12 MPa，三个外载工况独立复核；外观几何没有显著变化','补充'),
 'T03':('快速执行','固定结构的0.5 s到达与保持','补充'),
 'T04':('研究路线改变','早期GVS路线未完整交付；改为原生静力bank及前馈，完整22 s八字轨迹通过','正文决策与执行'),
 'T05':('位姿任务','真实10 g负载下同时满足位置与有向工具轴约束','正文执行备用；补充完整结果'),
 'T06':('时序位姿','20 g负载下扫描位置及工具轴','补充；执行备用'),
 'T07':('共享形态设计','椭圆根段→圆根段、14.1→14 mm腱路；保留加长反例；四工况分别重优化控制','正文结构与决策重点'),
 'T08':('被动机制','固定放绳偏置1.5→1.8 mm；相同几何、双向渐进刚度与卸载回归','补充；被动机制备用'),
 'T09':('接触执行','保留20个真实导向组件；修复环境接口后实际按钮接触、保持与释放通过','正文物理执行重点'),
 'T10':('控制路线改变','固定结构，GVS/NMPC→原生离散反馈；三工况共同配方通过，冻结输入对照失败','正文决策重点及量化执行')}

def txt(path,s):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def csvread(p):return list(csv.DictReader(Path(p).open(encoding='utf-8-sig')))
def link(p,label=None):return f'[{label or Path(p).name}]({str(Path(p).resolve()).replace(chr(92),"/")})'
def rel(p,base):return Path(os.path.relpath(p,base)).as_posix()
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(v).replace('|','/') for v in row)+' |\n' for row in rows)

def main():
    cases=read(O/'FINAL_CASES.json');screens=read(O/'SCREENSHOT_MANIFEST.json');videos=read(O/'VIDEO_MANIFEST.json');metrics=csvread(O/'CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv')
    # Replace the readable F0 shorthand with its exact archived Store/run identity.
    for r in screens:
        if r['task_id']=='PHS-2D' and r['condition_id']=='F0':
            r['candidate_id']='69b12ba54f8c5cfb497772a85512daf4c18ac13b7a6584240340e65cd56dd42d';r['run_id']='psd2d-core-fresh-20261112';r['candidate_source']=str(ROOT/'runs/phs2d-paper-data-20261112/SOURCE_EXTRACTS/F0_CANDIDATE.json')
    save(O/'SCREENSHOT_MANIFEST.json',screens);csvout(O/'PHS-2D/render_manifest.csv',[r for r in screens if r['task_id']=='PHS-2D'])
    def values(tid,key):
        return [float(r['value']) for r in metrics if r['task_id']==tid and r['metric']=='evaluator:'+key and r['condition_role']!='control']
    def worst(tid,key,scale=1):return max(values(tid,key))*scale
    short={
      'T01':f"最大保持误差 {worst('T01','holding_position',1000):.6f} mm；三目标",
      'T02':f"最大保持误差 {worst('T02','holding_position',1000):.6f} mm；三载荷",
      'T03':f"终点 {worst('T03','terminal_position',1000):.6f} mm；保持 {worst('T03','holding_position',1000):.6f} mm",
      'T04':f"RMSE {worst('T04','tracking_rmse',1000):.6f} mm；最大 {worst('T04','tracking_max',1000):.6f} mm",
      'T05':f"位置 {worst('T05','tool_position',1000):.6f} mm；轴角 {worst('T05','tool_axis_direction'):.9f} rad",
      'T06':f"最大位置误差 {worst('T06','tracking_max_error',1000):.6f} mm；轴角 {worst('T06','tool_axis_direction'):.9f} rad",
      'T07':'四工况35项原始硬约束通过；M5位置7.920000 mm、轴角0.051836161 rad',
      'T08':f"刚度比 {worst('T08','plus_x_stiffness_ratio'):.9f}；高载位移 {worst('T08','plus_x_high_maximum',1000):.6f} mm",
      'T09':f"深度/力联合保持 {worst('T09','depth_and_force_hold_0p4s'):.3f} s；意外碰撞0",
      'T10':f"正式三工况通过；最大最终保持误差 {worst('T10','final_hold_position',1000):.6f} mm；两个冻结输入对照失败"}
    comparison=[];selected=[]
    for i,name in enumerate(NAMES,1):
        tid=f'T{i:02d}';cc=[r for r in cases if r['task_id']==tid and r['condition_role']=='required'];c=read(cc[0]['candidate_file']);st=c['configuration']['robot']['structure']['data'];flex=[x for x in st['components'] if x['kind']=='flexible_segment'];ss=[r for r in screens if r['task_id']==tid];vv=[r for r in videos if r['task_id']==tid]
        comparison.append(dict(task_id=tid,task_name=name,run_id=cc[0]['run_id'],actor='Codex expert/surrogate; no formal Main SDK/Provider run in this archive',required_motion_conditions=len(cc),accepted_motion_conditions=sum(bool(r['accepted']) for r in cc),acceptance_scope='original acceptance; T08 both directions share one result',segments=len(flex),tendons=len(st['tendons']),actuators=len(st['actuators']),lengths_m=json.dumps([s['length_m'] for s in flex]),key_metrics=short[tid],research_story=STORY[tid][1],placement=STORY[tid][2],screenshots=len(ss),videos=len(vv),candidate_source=cc[0]['candidate_file'],result_source=cc[0]['result_file'],metric_source=str(O/'CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv')))
        timeline=csvread(O/tid/'candidate_timeline.csv')
        for r in timeline:
            selected.append(dict(task_id=tid,node_id=r.get('node_id','unavailable'),candidate_id=r.get('candidate_id','unavailable'),stage=r.get('stage','unavailable'),main_story=STORY[tid][0],editorial_priority=STORY[tid][2],reason=STORY[tid][1],original_timeline=str(O/tid/'candidate_timeline.csv'),original_row_json=json.dumps(r,ensure_ascii=False)))
        figures=sorted((O/tid/'FIGURES_PAPER').glob('*.png'))
        txt(O/tid/'ASSET_INDEX.md',f'# {tid} — {name}\n\n'+STORY[tid][1]+'。\n\n'+short[tid]+'。\n\n'+f'原始独立结果：{link(cc[0]["result_file"])}。候选和决策见本目录CSV。完整逐约束数据见根 `CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv`。\n\n'+f'本任务有{len(ss)}张原生截图和{len(vv)}段无字视频；所有截图、视频及状态来源分别见 `render_manifest.csv` 和 `video_manifest.csv`。视觉组件复用先前完成的版本，新增的是原生光照、可见地面和阴影。\n\n'+''.join('- '+link(p)+'\n' for p in figures)+'\n'+f'视频统一入口：{link(O/"VIDEO_GALLERY.html")}。\n')
    csvout(O/'CROSS_TASK/task_comparison.csv',comparison);csvout(O/'CROSS_TASK/candidate_selection_matrix.csv',selected)
    txt(O/'MULTITASK_SUMMARY.md','# 多任务科研素材整理结果\n\n'+f'十项历史FULL任务均已建立候选、决策、逐约束指标、原始模型和状态索引；共{len(screens)}张新原生截图、{len(videos)}段无字MP4。PHS-2D只作独立参考，不混入十任务的成本或验收。\n\n'+table(['任务','通过的场景条件','最有价值的指标','正文建议'],[(r['task_id'],f"{r['accepted_motion_conditions']}/{r['required_motion_conditions']}",r['key_metrics'],r['placement']) for r in comparison])+'\n实际执行者为 Codex expert/surrogate，原记录明确未运行正式Main/Provider。本文素材可以支持真实工具研究过程，不能据此声称十项Main SDK自主复现。T08双向场景共用一份原始验收；T10冻结输入为对照，不属于正式必需工况。\n\n'+'''T07：有六个本轮形态候选，独立物理XML只留存S1椭圆根段和S5最终圆根段。四个最终candidate artifacts绑定不同工况，但结构参数和模型身份相同。控制初始化反例与长度反例单独保留，不能称其独立通过。

T10：十个精选节点的结构不变。研究路线从GVS/NMPC转为原生静力、全阶切线、离散LQR及有界状态反馈，最终三工况采用共同配方。±0.04 N、50 ms半正弦冲击很小，不夸大成大幅击退恢复。早期一轮虽然评价超限，profile仍为execution_incomplete。

T04：早期GVS路线没有完整交付，不画成有完整误差结果的失败基线。最终22 s八字任务的RMSE和最大误差取原始独立验收；89点静力bank不是最终任务结果。

T09：完整49维状态包含button_slide，截图没有把按钮位移补成零。首次接口回合的9次意外碰撞和最终0次分别保留，不把修复误写成删除硬件。

缺失项：部分数学候选无原始XML/独立物理状态；T07 S0/S2/S3/S4不伪造结构截图。十任务Codex宿主Token不可得，标为unavailable。独立Main复现只保留PHS原研究的来源与Token，不能移用。
''')
    txt(O/'TASK_SELECTION.md','# 正文案例选择\n\n'+table(['展示位置','选定内容','要支持的贡献','素材'],[
      ('结构演化主图','PHS-2D + T07','发现物理约束并改变真实结构','Figure_A_structure_evolution.html'),
      ('决策过程主图','T04 + T10；T07作共享形态补充','根据原始证据切换研究路线','Figure_B_research_trajectories.html'),
      ('物理执行主图','T09接触 + T04跟踪；T10量化对照','最终方案满足原任务，包含接触、轨迹与扰动','Figure_C_physical_outcomes.html'),
      ('补充材料','T01/T02/T03/T05/T06/T08，以及正文任务其余工况','覆盖范围和完整证据','各任务ASSET_INDEX.md、SUPPLEMENTARY索引')])+'\nT07重点：共享形态下单工况可行不等于全任务可行，结构修改后仍需分别优化控制和独立验收。T10重点：固定结构上的控制路线改变与共同配方验证，与PHS-2D被动结构设计形成互补。\n\nT05作为主文执行替补：工具轴与位置联合约束清楚；T10的动作幅度较小，优先用量化主动/冻结输入对照说明作用，不依赖夸张动画。\n\n索引保留真实actor；图中使用Agent或Codex expert/surrogate，不写未经证实的Main SDK。\n')
    folder=O/'CROSS_TASK/figure_assets';folder.mkdir(exist_ok=True)
    def im(tid,name,label):return (O/tid/'FIGURES_MJ'/name,label)
    A=[('PHS-2D',[
      im('PHS-2D','PHS-2D_F0_reference_oblique.png','F0 · initial diagnostic'),im('PHS-2D','PHS-2D_F3_s7_positive_reference_oblique.png','F3 · intermediate'),im('PHS-2D','PHS-2D_F8_s7_positive_reference_oblique.png','F8 · accepted design')]),
      ('T07', [im('T07','T07_S1_ellipse_B_reference_oblique.png','S1 · ellipse, 14.1 mm route'),im('T07','T07_M1_A_reference_oblique.png','S5 · round, 14 mm route')])]
    B=[('T04 · evidence changes the route',[
      im('T04','T04_earlier_native_route_tracking_oblique.png','Earlier archived native execution'),im('T04','T04_default_final_oblique.png','Final native execution')]),
      ('T04 · complete original tracking evidence',[(O/'T04/FIGURES_PAPER/T04_figure_eight_path_and_error.png','Final 22 s tracking')]),
      ('T07 · shared morphology constrains every condition',[im('T07','T07_S1_ellipse_B_reference_oblique.png','S1 · ellipse root'),im('T07','T07_M1_A_reference_oblique.png','S5 · common round root')]),
      ('T07 · morphology and control decisions',[(O/'T07/FIGURES_PAPER/T07_evidence_driven_research.png','Original discrete diagnostics; not independent acceptance')]),
      ('T10 · fixed structure, controller iteration',[im('T10','T10_positive_y_pre_impact_oblique.png','Before pulse'),im('T10','T10_positive_y_impact_oblique.png','Pulse'),im('T10','T10_positive_y_final_hold_oblique.png','Final hold')]),
      ('T10 · original route-specific evidence',[(O/'T10/FIGURES_PAPER/T10_control_route_constraint_comparison.png','Original route-specific diagnostics')])]
    C=[('T09 · recorded contact sequence',[
      im('T09','T09_default_approach_oblique.png','Approach'),im('T09','T09_default_maximum_depth_oblique.png','Maximum button travel'),im('T09','T09_default_hold_oblique.png','Joint depth/force hold')]),
      ('Original physical outcomes',[(O/'T09/FIGURES_PAPER/T09_contact_depth_and_force.png','Contact and hold')])]
    captions={
      'Figure_A_structure_evolution':'Native MuJoCo views of PHS-2D and T07. Each task uses a fixed camera and scale across its selected structures. PHS F0 is an initial diagnostic, not a registered accepted design. Only the two T07 morphologies with original physical XML are shown; its other math-only candidates remain in the evidence table. Previously completed visual mounting, anchor and junction envelopes are retained as visual-only elements.',
      'Figure_B_research_trajectories':'Archived evidence supports route changes in T04 and T10. T04 switches from an incomplete GVS route to native bank/feedforward execution. T10 retains the same morphology while changing controller construction. Diagnostic values with different protocol scopes are discrete comparisons, not a convergence curve. Final T10 common-recipe cases and frozen-input controls remain separate.',
      'Figure_C_physical_outcomes':'Recorded native states of T09 show approach, maximum travel and holding; plots use actual button displacement and contact force in the specified hold window. T04 tracking and T10 feedback controls are available as separate execution alternatives. Videos are rendered directly from archived states; camera, source time, force cues and playback rates are documented outside the image.'}
    style='body{font-family:Arial,Helvetica,sans-serif;color:#26384B;max-width:1200px;margin:32px auto;padding:0 20px;background:white}h1{font-size:20px;font-weight:500}h2{font-size:16px;font-weight:500;margin:28px 0 8px}.row{display:flex;gap:14px;align-items:start}figure{margin:0;flex:1;min-width:0}img,video{width:100%;height:auto;display:block}figcaption{font-size:13px;margin:6px 0 0}p{font-size:14px;line-height:1.55}a{color:#527F7B}.caption{border-top:1px solid #ddd;margin-top:24px;padding-top:12px}'
    assets=[]
    for stem,rows in [('Figure_A_structure_evolution',A),('Figure_B_research_trajectories',B),('Figure_C_physical_outcomes',C)]:
        body='<h1>'+stem.replace('_',' ')+'</h1>'
        tex=['% Layout draft. Include original native PNG panels without cropping/retouching.','\\begin{figure*}[t]','\\centering']
        for row_i,(heading,items) in enumerate(rows):
            if stem=='Figure_B_research_trajectories' and row_i in [2,4]:
                # Three case drafts, each a separate float. Do not shrink 7.16-in
                # quantitative panels to half width and make their labels unreadable.
                tex+=['\\caption{'+captions[stem]+'}','\\end{figure*}','','\\begin{figure*}[t]','\\centering']
            if stem=='Figure_B_research_trajectories' and row_i in [0,2,4]:
                stages={0:['Incomplete GVS delivery','Native reference bank','Feedforward','Complete 22 s acceptance'],2:['B-only pass','Shared A/C conflict','Round root and minimum route','Four independent case passes'],4:['Startup constraint conflict','Native full-order feedback','Common-recipe correction','Three required cases pass']}[row_i]
                body+='<p>'+' &rarr; '.join(stages)+'</p>'
                tex.append('\\small '+r' $\rightarrow$ '.join(stages)+'\\par\\medskip')
            body+='<h2>'+html.escape(heading)+'</h2><div class="row">';tex.append('% '+heading)
            for path,label in items:
                assert path.exists(),path;body+='<figure><img src="'+rel(path,folder)+'"><figcaption>'+html.escape(label)+'</figcaption></figure>'
                tex.append('\\begin{minipage}[t]{'+format(.96/len(items),'.3f')+'\\textwidth}\\centering\\includegraphics[width=\\linewidth]{\\detokenize{'+rel(path,folder)+'}}\\par\\small '+label.replace('·','--')+'\\end{minipage}\\hfill')
                assets.append(dict(figure=stem,task=heading,panel_label=label,asset=str(path),source_manifest=str(O/'SCREENSHOT_MANIFEST.json') if path.parent.name=='FIGURES_MJ' else str(path.parent.parent/'FIGURE_DATA')))
            body+='</div>';tex.append('\\par\\medskip')
        body+='<p class="caption">'+captions[stem]+'</p>';txt(folder/(stem+'.html'),'<!doctype html><meta charset="utf-8"><style>'+style+'</style>'+body)
        tex+=['\\caption{'+captions[stem]+'}','\\end{figure*}'];txt(folder/(stem+'.tex'),'\n'.join(tex)+'\n')
    csvout(folder/'FIGURE_ASSET_SOURCES.csv',assets)
    txt(O/'FIGURE_PLAN.md','# 三组跨任务图草稿\n\n'+''.join(f'- {link(folder/(s+".html"),s)}；同名 `.tex` 可用于LaTeX排版。\n' for s in captions)+'\n这些是直接引用原始PNG/SVG的排版草稿，不裁切、不重画机器人。图片标签在版面外，视频帧内无文字。原生截图保持单独文件。B组按T04/T07/T10三个独立case float组织，二维图保持双栏宽度，避免把8–9pt标签缩成半宽。正文可选其中两例，其余置补充材料。\n\n'+''.join('**'+s+'**\n\n'+c+'\n\n' for s,c in captions.items())+'正式二维图已覆盖T01–T10，并有分Study资源图。T07/T10各保留一张研究诊断图和一张最终执行/验收图。不同范围的候选指标不直接连线。\n')
    txt(O/'FIGURE_CAPTIONS.md','# Figure captions\n\n'+''.join('## '+s+'\n\n'+c+'\n\n' for s,c in captions.items())+'各任务定量图详细来源与评价窗口见任务FIGURES_PAPER中的图注，T10图注位于T10/FIGURE_CAPTIONS.md。资源图图注见CROSS_TASK/figure_assets/selected_final_run_resources_CAPTION.md。\n')
    # Booktabs drafts, with no averaged metrics across unlike tasks.
    tex=['% Requires booktabs. Native units and each task remain separate.','\\begin{tabular}{lrrrrl}','\\toprule','Task & Segments & Tendons & Inputs & Cases & Flexible lengths (mm) \\\\','\\midrule']
    for r in comparison:tex.append(f"{r['task_id']} & {r['segments']} & {r['tendons']} & {r['actuators']} & {r['accepted_motion_conditions']}/{r['required_motion_conditions']} & "+', '.join(f'{1000*v:g}' for v in json.loads(r['lengths_m']))+' \\\\')
    tex+=['\\bottomrule','\\end{tabular}'];txt(O/'CROSS_TASK/TABLE_STRUCTURE_AND_COVERAGE.tex','\n'.join(tex)+'\n')
    txt(O/'TABLE_PLAN.md','# 论文表格\n\n'+table(['表','内容','建议列数','数据来源'],[('结构与任务覆盖','段/腱/输入、真实长度、必需条件','6','CROSS_TASK/TABLE_STRUCTURE_AND_COVERAGE.tex'),('共享形态四工况','T07各工况位置/速度/工具轴与约束','5','T07/FIGURES_PAPER/TABLE_T07_FINAL.tex'),('控制路线与最终验收','T10原路线、共同配方及控制对照','4–6','T10/TABLES.tex'),('补充逐约束指标','T01–T10所有约束，原值/限值/单位/结果','6','CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv'),('分Study计算成本','数学、物理episodes、步数、工具、Token可得性','6','CROSS_TASK/resource_usage_per_run.csv')])+'\n采用booktabs，无竖线与彩色底纹；不平均位置、力、角度误差，不将不同Study成本直接相加。\n')
    txt(O/'TABLE_DRAFTS.md','# 表格数据草稿\n\n'+table(['任务','段数','腱/输入','长度(mm)','通过场景条件'],[(r['task_id'],r['segments'],str(r['tendons'])+'/'+str(r['actuators']),', '.join(f'{1000*v:g}' for v in json.loads(r['lengths_m'])),str(r['accepted_motion_conditions'])+'/'+str(r['required_motion_conditions'])) for r in comparison])+'\n'+table(['任务','结果指标','原始验收范围'],[(r['task_id'],r['key_metrics'],r['run_id']) for r in comparison])+'\n最终booktabs数据及更多表格来源见TABLE_PLAN.md。T08双向场景共用一个原始验收结果；其他行也不能据此解释为不同结构数。\n')
    # All video labels, times and playback rates are outside the native frames.
    gallery='<h1>MuJoCo native task videos</h1><p>原生光照与阴影；画面无文字。沿用既有导向盘、锚固板和连接包覆。轨迹/目标/力为原任务的可视提示。短任务适度慢放；见各项倍率。</p>'
    vr=[]
    for tid in [f'T{i:02d}' for i in range(1,11)]+['PHS-2D']:
        gallery+='<h2>'+tid+'</h2>'
        for v in [x for x in videos if x['task_id']==tid]:
            p=Path(v['video']);poster=next(p.parent.glob(p.stem.replace('_native_shadows','')+'_frame_0000.png'),None)
            gallery+='<figure style="max-width:800px;margin:18px 0"><video controls preload="none"'+(' poster="'+rel(poster,O)+'"' if poster else '')+' src="'+rel(p,O)+'"></video><figcaption>'+html.escape(v['condition_id'])+' · '+str(v['simulation_duration_s'])+' s source · '+format(v['playback_speed'],'.3g')+'× playback · '+html.escape(str(v.get('condition_role','reference')))+' · <a href="'+rel(p,O)+'" download>MP4</a></figcaption></figure>'
            vr.append((tid,v['condition_id'],v.get('condition_role','reference'),f"{v['simulation_duration_s']:g} s",f"{v['playback_speed']:.3g}×",link(p,'MP4')))
    txt(O/'VIDEO_GALLERY.html','<!doctype html><meta charset="utf-8"><style>'+style+'</style>'+gallery)
    txt(O/'VIDEO_INDEX.md','# 原生视频清单\n\n25 fps，1600×1200，H.264 MP4，无音轨、无文字叠加。直接渲染历史qpos，不插值姿态，不重新积分；RGB帧仅进行视频编码。短任务慢放，长任务按原时间播放。\n\n'+table(['任务','工况','角色','原时间','播放倍率','文件'],vr)+'\n画面提示：绿点/轴为冻结目标及方向；灰蓝线为原保存参考路径，深色轨迹为已执行Tip；砖红箭头为原任务指定外载或实际按钮接触力。箭头显示长度只用固定视觉比例（T02 0.6 m/N、T10 1.3 m/N、T08 0.25 m/N、PHS-2D 0.45 m/N、T09 0.2 m/N），不是新物理几何。各视频frame_sources.csv保存每帧原状态索引和时间。\n')
    txt(O/'README.md','# 多任务科研证据与原生MuJoCo素材库\n\n'+f'已整理T01–T10及独立PHS-2D参考：{len(screens)}张原生PNG、{len(videos)}段带地面阴影的无字MP4。\n\n'+f'先打开 {link(O/"VIDEO_GALLERY.html","视频预览")} 或 {link(O/"TASK_SELECTION.md","正文案例选择")}。研究数据总览见 {link(O/"MULTITASK_SUMMARY.md")}；三组排版草稿见 {link(O/"FIGURE_PLAN.md")}。\n\n'+'''每个任务的候选、决策与指标分别在candidate_timeline.csv、agent_decision_timeline.csv、metric_history.csv。evidence_bundle.json保留原Store artifact、run_id、原XML、模型与保存状态。render_manifest.csv和video_manifest.csv逐项链接对应视觉XML、相机和状态来源。全部原生PNG未裁切/修饰，MP4只编码Renderer RGB帧。

视觉组件复用前次paper_results_master_20261113/VISUAL_XML的导向盘、末端锚固板、段间包覆连接件和基座。当前修改是恢复可见地面、原生灯光与阴影、统一任务内相机并读取已有状态。不同几何的中间候选采用原先同一视觉规则，坐标来自它自身模型。组件为既有示意外观，不新增物理硬件。逐XML.check.json记录原物理模型、模板及编译后属性对比。

本次没有结构搜索、数学优化、控制执行、mj_step或新的物理结果；mj_fwdPosition只用于已有状态的空间位置更新。未修改core、原始XML、冻结条件、Figure 1、Phase 2或Overleaf。

注意数据身份：十任务原执行者是Codex expert/surrogate，不是已验证的正式Main SDK/Provider运行。部分数学节点无物理XML或独立验收，明确标unavailable。资源按31个task/run保留，不作跨Study总和；候选artifact数量不等于结构形态数量。

重现命令与环境见RENDER_COMMANDS.md；完整来源与缺项见EVIDENCE_INDEX.md。
''')
    txt(O/'EVIDENCE_INDEX.md','# 证据入口\n\n'+table(['对象','入口','说明'],[('最终模型/状态','FINAL_CASES.json','22条十任务场景（含2个控制对照）及3条PHS参考'),('逐约束原值','CROSS_TASK/FINAL_CONSTRAINT_METRICS.csv','原Store验收分量与精确pointer'),('全部候选相关记录','SUPPLEMENTARY/complete_candidate_index.csv','142条；11条为执行记账记录，不计结构候选'),('完整原决策','SUPPLEMENTARY/complete_decision_index.csv','434条，保留run与原行'),('精选研究链','CROSS_TASK/research_decision_summary.csv','72条，不罗列全部调用'),('来源','SUPPLEMENTARY/source_index.csv','916条来源引用；原始文件/Store定位'),('已读扩展','SUPPLEMENTARY/extension_index.csv','19条指定前驱/反例/数值复核，不声称全仓库覆盖'),('截图','SCREENSHOT_MANIFEST.json','每图原XML、视觉模板、qpos状态/参考姿态、相机'),('视频','VIDEO_MANIFEST.json','原状态索引、逐帧来源、播放倍率与ffprobe'),('分Study成本','RESOURCE_USAGE.json','31条，数学与物理管线口径分开')])+'\n关键缺项：T07 S0/S2/S3/S4无原始物理XML，不制作伪造演化；十任务Codex宿主Tokens不可得；T04早期GVS未完整执行，T10部分旧profile不完整。其余缺少独立观察/假设字段时，只保留原决策rationale，不杜撰内部推理。\n\nPHS原研究详见 '+link(ROOT/'runs/phs2d-paper-data-20261112/EVIDENCE_INDEX.md')+'。本包新增其F8正负distal加载与F3失败过程参考动画，不改变旧研究表格。PHS原指标最小受力点14.798132 mm、最大评分Tip4.346997 mm、最大传递比0.153750600，均只属于该独立Study。\n')
    txt(O/'RENDER_COMMANDS.md','''# 重现渲染

PowerShell，工作目录D:\\softrobot-agent：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$py='C:/Users/gugugaga/miniconda3/envs/softagent/python.exe'
& $py -u runs/multitask-paper-data-20261118/scripts/extract_render_inputs.py
& $py -u runs/multitask-paper-data-20261118/scripts/add_phs_reference_motion.py
& $py -u runs/multitask-paper-data-20261118/scripts/render_native_assets.py --mode all
& $py -u runs/multitask-paper-data-20261118/scripts/render_intermediate_stills.py
& $py -u runs/multitask-paper-data-20261118/scripts/build_delivery.py
```

MuJoCo3.13.0，1600×1200，25fps，原生Renderer、4samples、4096阴影；8MiB编译线程栈用于Windows模型编译。既有视觉模板、原模型、相机参数见每任务VISUAL_XML/*.check.json和CAMERA_SETTINGS.json。所有新视觉geom为mass=0、contype=0、conaffinity=0，编译后质量/惯量、骨架、关节、腱路、原碰撞geom和积分设置与对应原模型比较通过。

视频使用本机已有FFmpeg：D:/Program Files (x86)/英雄联盟(26)/Cross/icreate/recorder-release/ffmpeg.exe，h264_nvenc、QP18、yuv420p、faststart。仅编码原生帧，不叠字、不裁切、不重画。没有重新积分或构造新轨迹。每帧选择最近的原保存状态，不插值姿态；精确播放倍率与来源见VIDEO_MANIFEST及frame_sources.csv。

定量图复现脚本分别为T01/make_quantitative_figures.py（八任务）、T07/plot_t07_paper.py、T10/make_paper_figures.py。分Study资源与补充索引的复现脚本为scripts/consolidate_resources.py、scripts/consolidate_supplement.py。
''')
    print('DELIVERY',len(screens),'native PNG;',len(videos),'MP4;',len(comparison),'tasks',flush=True)

if __name__=='__main__':main()
