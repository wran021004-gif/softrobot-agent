"""Portable saved-coordinate animation and scalar plots; no dynamics imports."""
import html
import json
from pathlib import Path
from tools.state_io import read,atomic_json
from tools.trajectory_diagnosis import load_rows

def render_candidate(root,c,backend):
    r=c['results'][backend];folder=(root/r['result_ref']).parent;rows=load_rows(folder/'trajectory.json.gz')
    if not rows:raise ValueError('No saved coordinates')
    # Animation downsamples coordinates only; curve data retain all output samples.
    data=dict(candidate_id=c['candidate_id'],backend=backend,result=r,design=c['design'],control=c['control'],rows=rows,
              model_status=c['results'].get('matlab',{}).get('model_task_success','未运行'),
              canonical_status=c['results'].get('mujoco',{}).get('canonical_task_success','未运行'),
              diagnostics=read(folder/'diagnosis.json') if (folder/'diagnosis.json').exists() else {})
    path=root/f'observations/{c["candidate_id"]}_{backend}.html';path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(data,ensure_ascii=False).replace('</','<\/')
    page='''<!doctype html><meta charset="utf-8"><title>Reach trajectory</title>
<style>body{font:15px system-ui;background:#101a29;color:#e4edf8;margin:24px}button,select,input{margin:6px;padding:6px}canvas{background:#172438;border:1px solid #456;width:min(100%,900px)}pre{white-space:pre-wrap}a{color:#9df} .note{color:#aabbd0}table{border-collapse:collapse}td,th{padding:6px;border:1px solid #456}</style>
<h1 id="title"></h1><p id="status"></p><p class="note">保存轨迹回放；零动力学调用。世界 x-z 投影；MuJoCo 的平面外 y 运动保留在原始数据。红点为固定目标。等效设计参数未标定。</p>
<canvas id="scene" width="900" height="430"></canvas><br><button id="play">播放 / 暂停</button><input id="time" type="range" min="0" max="2" step="0.002" value="0" style="width:60%"><span id="stamp"></span>
<p>曲线 <select id="field"><option value="error">末端误差 m</option><option value="tipx">末端 x m</option><option value="tipz">末端 z m</option><option value="length">腱指令 / 路径长 m</option><option value="force">正张力 N</option><option value="q">关节角 rad</option><option value="v">关节角速度 rad/s</option></select><select id="entity"></select></p>
<canvas id="plot" width="900" height="260"></canvas><p class="note">极值来自保存数值采样，不是连续时间严格极值。MuJoCo 绳力/路径采用 solver_time_s，状态采用 time_s。MATLAB 输出是 ode15s 解的固定采样插值；内部时间另存。</p>
<h2>诊断事件（点击定位时间）</h2><div id="events"></div><details><summary>模型、控制、物理配置和指标</summary><pre id="details"></pre></details>
<script>const D=PAYLOAD;const rows=D.rows;const $=x=>document.getElementById(x);let playing=false,last=performance.now();
$('title').textContent=D.candidate_id+' / '+D.backend+' / '+D.result.model_id;
$('status').textContent=D.backend+' 数值计算完成：'+D.result.complete+'；MATLAB模型预测通过：'+D.model_status+'；MuJoCo任务通过：'+D.canonical_status+'；本后端误差 '+D.result.position_error_m+' m；计算 '+D.result.elapsed_s+' s';
$('details').textContent=JSON.stringify({result:D.result,design:D.design,control:D.control},null,2);
function entities(){let f=$('field').value,tendon=['length','force'].includes(f),joint=['q','v'].includes(f);$('entity').innerHTML='';let n=tendon?rows[0].command_m.length:joint?rows[0].qpos_rad.length:1;for(let j=0;j<n;j++){let label=tendon?'tendon_'+j:joint?('joint_'+(D.backend==='matlab'?j:Math.floor(j/2))+'_'+(D.backend==='matlab'||j%2===0?'y':'z')):'末端';$('entity').add(new Option(label,j))}}
function nearest(t,key='time_s'){let lo=0,hi=rows.length-1;while(lo<hi){let mid=Math.floor((lo+hi)/2);if(rows[mid][key]<t)lo=mid+1;else hi=mid;}return rows[lo];}
function draw(){const t=+$('time').value,r=nearest(t),c=$('scene').getContext('2d');c.clearRect(0,0,900,430);const L=D.design.total_length_m,s=640/Math.max(.6,L*1.4),X=x=>100+x*s,Z=z=>330-z*s;
c.strokeStyle='#697';c.beginPath();c.moveTo(0,Z(-.02));c.lineTo(900,Z(-.02));c.stroke();
c.fillStyle='#ff6575';c.beginPath();c.arc(X(.25),Z(.15),6,0,7);c.fill();c.fillStyle='#fff';c.fillText('目标 (0.25,0,0.15)m',X(.25)+10,Z(.15));
function line(points,color,width){c.strokeStyle=color;c.lineWidth=width;c.beginPath();points.forEach((p,i)=>i?c.lineTo(X(p[0]),Z(p[2])):c.moveTo(X(p[0]),Z(p[2])));c.stroke();}
if(r.tendon_routes_m)r.tendon_routes_m.forEach((rt,j)=>line(rt,['#fba','#7df','#fb5','#b8f','#afa'][j%5],1));
if(r.centerline_m)line(r.centerline_m,'#e8f2ff',5);c.fillStyle='#ffd';c.fillRect(X(0)-5,Z(0)-5,10,10);c.fillText('固定基座',X(0)-40,Z(0)+30);
$('stamp').textContent=r.time_s.toFixed(3)+' s';plot();}
function plot(){const c=$('plot').getContext('2d');c.clearRect(0,0,900,260);let f=$('field').value,j=+$('entity').value;const force=['length','force'].includes(f);let series=[rows.map(r=>({t:r[force?'solver_time_s':'time_s'],v:f==='error'?Math.hypot(r.tip_m[0]-.25,r.tip_m[1],r.tip_m[2]-.15):f==='tipx'?r.tip_m[0]:f==='tipz'?r.tip_m[2]:f==='length'?r.solver_tendon_length_m[j%r.command_m.length]:f==='force'?-r.solver_actuator_force_n[j%r.command_m.length]:f==='q'?r.qpos_rad[j]:r.qvel_rad_s[j]}))];
if(f==='length')series.push(rows.map(r=>({t:r.solver_time_s,v:r.command_m[j%r.command_m.length]})));
let vals=series.flat().map(p=>p.v),lo=Math.min(...vals),hi=Math.max(...vals),span=Math.max(hi-lo,1e-6);lo-=span*.1;hi+=span*.1;
const X=t=>70+t*390,Y=v=>220-(v-lo)/(hi-lo)*190;c.strokeStyle='#456';c.strokeRect(70,30,780,190);c.fillStyle='#dde';c.fillText(hi.toPrecision(4),5,35);c.fillText(lo.toPrecision(4),5,220);c.fillText('0 s',65,245);c.fillText('2 s',835,245);
series.forEach((s,k)=>{c.strokeStyle=['#8df','#ffb75b'][k];c.lineWidth=2;c.beginPath();s.forEach((p,i)=>i?c.lineTo(X(p.t),Y(p.v)):c.moveTo(X(p.t),Y(p.v)));c.stroke();});c.strokeStyle='#f66';c.beginPath();c.moveTo(X(+$('time').value),30);c.lineTo(X(+$('time').value),220);c.stroke();}
for(const e of (D.diagnostics.events||[])){let b=document.createElement('button');b.textContent=e.entity_name+' '+e.event_type+' '+e.t_start_s.toFixed(3)+'–'+e.t_end_s.toFixed(3)+' s';b.title=e.detection_rule+' '+JSON.stringify(e.values);b.onclick=()=>{$('time').value=e.t_start_s;draw()};$('events').append(b);}
$('time').oninput=draw;$('field').onchange=()=>{entities();draw()};$('entity').onchange=draw;$('play').onclick=()=>playing=!playing;
entities();$('time').value=Math.max(0,Math.min(2,+(new URLSearchParams(location.search).get('t')||0)));
function tick(now){if(playing){$('time').value=(+$('time').value+(now-last)/1000)%2;draw()}last=now;requestAnimationFrame(tick)}draw();requestAnimationFrame(tick);
</script>'''.replace('PAYLOAD',payload)
    path.write_text(page,encoding='utf8');return path

def render_workbench(book):
    root=book.root;state=book.state;esc=lambda x:html.escape(str(x)); rows=[]
    for c in state['candidates']:
        results=c['results'];links=[]
        for backend in ('matlab','mujoco'):
            p=root/f'observations/{c["candidate_id"]}_{backend}.html'
            if p.exists():links.append(f'<a href="{p.relative_to(root).as_posix()}">{backend} 动画/曲线/事件</a>')
        cells=[c['candidate_id'],c['parent_id'],c['physics_version'],c['control']['mode'],json.dumps(c['changes'],ensure_ascii=False)]
        for backend in ('matlab','mujoco'):
            r=results.get(backend,{});cells.extend([r.get('complete','NOT_RUN'),r.get('position_error_m','NOT_RUN'),r.get('elapsed_s','NOT_RUN'),
                r.get('model_task_success' if backend=='matlab' else 'canonical_task_success','NOT_RUN')])
        rows.append('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in cells)+'<td>'+'<br>'.join(links)+'</td></tr>')
    headers=['候选','父候选','物理版本（等效参数未标定）','控制','变更','MATLAB 数值完成','MATLAB 误差 m','MATLAB 用时 s','模型预测通过','MuJoCo 数值完成','MuJoCo 误差 m','MuJoCo 用时 s','MuJoCo 任务通过','观察']
    page='<!doctype html><meta charset="utf-8"><title>Round 9 reach workbench</title><style>body{font:14px system-ui;background:#101a29;color:#e4edf8;padding:24px}table{border-collapse:collapse}td,th{border:1px solid #456;padding:8px}a{color:#9df}pre{white-space:pre-wrap}</style>'
    page+=f'<h1>Round 9 · reach_free</h1><p>流程完成：{state["status"]=="STOPPED"}；会话状态：{esc(state["status"])}</p>'
    selection=book.selected_design()
    if selection:
        page+='<section style="border:2px solid #9df;padding:16px"><h2>Final design selection</h2>'
        page+=f'<p><strong>Selected candidate: {esc(selection["selected_candidate_id"] or "None")}</strong></p>'
        page+=f'<p>Design file: {esc(selection["design_file"] or "None")}</p><p>Reason: {esc(selection["reason"])}</p>'
        page+=f'<p>Source: {esc(selection["source"])}</p></section>'
    if state.get('stop_reason'):page+='<details><summary>Full stop reason</summary><pre>'+esc(state['stop_reason'])+'</pre></details>'
    page+='<p>固定任务：目标 [0.25,0,0.15]m，t=2s，容差 0.01m。MATLAB 为未标定平面动态筛选；任务真值使用原 MuJoCo 评价器。</p>'
    page+='<p><a href="history/audit.json">历史核对</a> · <a href="inputs/grant.json">冻结授权与范围</a> · <a href="budget.json">预算账本</a> · <a href="candidate_table.json">完整候选表</a> · <a href="working_memory.json">工作记忆</a></p>'
    if state.get('tool_call_corrections'):
        page+='<h2>工具调用数量纠正（每个被拒绝决策最多一次）</h2>'
        for r in state['tool_call_corrections'].values():
            index=r['correction_request_index']
            link=(f'<a href="model_calls/{index:03d}/request.json">{index:03d} request</a>' if index is not None else 'pending / 尚未发送')
            response=(f'<a href="{esc(r["correction_response_ref"])}">correction response</a>' if r.get('correction_response_ref') else '')
            page+=f'<p>Rejected {r["rejected_request_index"]:03d}: count={r["observed_count"]}; <a href="{esc(r["original_response_ref"])}">original response</a>; correction={link} {response}; outcome={esc(r["outcome"])}</p>'
            page+='<pre>'+esc(r.get('original_error',r.get('error')))+'\n'+esc(r.get('error') or '')+'</pre>'
            if r.get('correction_observed_count') is not None:page+=f'<p>Correction rejected count: {r["correction_observed_count"]}</p>'
    if state.get('experiment'):
        summary=book.experiment_summary();eid=summary['experiment_id'];baseline=summary['baseline_id']
        page+=f'<h2>实验 {esc(eid)} · {esc(summary["status"])}</h2><p>基线 {baseline}；只计新实验后代与新数值回执。历史 c057/c065/c066 成功不属于本实验。</p>'
        page+='<p>Historical best: c066 (before llm_reach_v1; separate from the final design selection above).</p>'
        page+=f'<p><a href="experiments/{eid}/experiment.json">实验额度与起点</a> · <a href="experiments/{eid}/summary.json">实验结论</a>'
        for cid,label in ((baseline,'baseline'),(summary['best_id'],'best new verified')):
            if cid:
                for backend in ('matlab','mujoco'):
                    ref=f'observations/{cid}_{backend}.html'
                    if (root/ref).exists():page+=f' · <a href="{ref}">{label} {cid} {backend} playback</a>'
        page+='</p><pre>'+esc(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre>'
    errors=[{k:r[k] for k in ('index','status','error','correction_for','observed_tool_call_count') if k in r}
            for r in state['model_calls'][-3:] if r.get('error')]
    if errors:page+='<h2>最近模型错误</h2><pre>'+esc(json.dumps(errors,ensure_ascii=False,indent=2))+'</pre>'
    page+='<table><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr>'+''.join(rows)+'</table>'
    page+='<h2>实际预算消耗</h2><pre>'+esc(json.dumps(book.ledger['used'],indent=2))+'</pre><h2>已核对的 LLM 诊断</h2><pre>'+esc(json.dumps(state['verified_diagnoses'],ensure_ascii=False,indent=2))+'</pre>'
    atomic_json(root/'candidate_table.json',state['candidates']);(root/'index.html').write_text(page,encoding='utf8')
