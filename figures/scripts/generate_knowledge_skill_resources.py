"""Eleven task panels: compare four configurations separately for each resource."""
from pathlib import Path
import csv
import html
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'figures' / 'fig06_knowledge_skill_resources'
CONFIGS = ['K0S0', 'K1S0', 'K0S1', 'K1S1']
LABELS = ['K−S−', 'K+S−', 'K−S+', 'K+S+']
COLORS = ['#a3acb5', '#c4a578', '#8eaaa0', '#2877b5']
TASKS = [f'T{i:02}' for i in range(1, 11)] + ['PHS-2D']
NAMES = ['Multi-target Reach', 'Loaded Hold', 'Fast Reach',
         'Figure-eight Tracking', 'Tool Alignment', 'Pose Scanning',
         'Shared Morphology', 'Progressive Stiffness', 'Button Press',
         'Impact Recovery', 'Passive Tip Suppression']
METRICS = [('math_charged_evaluations', 'Math'),
           ('physical_launches', 'Physical'),
           ('core_request_records', 'Requests'),
           ('total_tokens', 'Tokens')]
rows = list(csv.DictReader((ROOT / 'paper_handoff/figure_data/fig05_resource_ablation.csv').open(encoding='utf-8-sig')))
data = {(r['task'], r['configuration']): r for r in rows if r['configuration'] in CONFIGS}
assert len(data) == 44
totals = {}
for k in CONFIGS:
    totals[k] = {key: sum(int(data[t,k][key]) for t in TASKS if data[t,k][key]!='') for key,_ in METRICS}
    data['ALL',k] = {key: str(totals[k][key]) for key,_ in METRICS}
    data['ALL',k]['formal_select'] = ''
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="1800" viewBox="0 0 2400 1800">',
       '<title>Knowledge and Skill: task-wise grouped resource bars</title>',
       '<style>text{font-family:"Comic Sans MS","Microsoft YaHei",cursive}</style>',
       '<defs><pattern id="missing" width="12" height="12" patternUnits="userSpaceOnUse"><rect width="12" height="12" fill="#69666e"/><path d="M0 0 L12 12 M0 12 L12 0" stroke="#aaa6af" stroke-width="1.5"/></pattern></defs>',
       '<rect width="2400" height="1800" fill="white"/>']
def text(x, y, s, size=30, anchor='start', weight=400, color='#283c44'):
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{html.escape(s)}</text>')
def rect(x, y, w, h, fill, stroke='none', sw=1, rx=0):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')
def line(x1,y1,x2,y2,color='#d8dfe3',width=1.5):
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
def checkmark(x, y):
    svg.append(f'<path d="M{x-8} {y} L{x-2} {y+6} L{x+10} {y-8}" fill="none" stroke="#263c45" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
def frame(x,y,w,h):
    rect(x,y,w,h,'white','#9da7ae',2.8,17)
    rect(x+3,y+3,w-6,h-6,'none','#9da7ae',1,15)

text(35,46,'Knowledge / Skill: within-task resource comparison',42,weight=700)
text(35,91,'Compare bars only within each resource group',31)
for i,label in enumerate(LABELS):
    x=1280+i*275
    rect(x,25,32,27,COLORS[i],rx=3)
    text(x+46,51,label,32,weight=700 if i==3 else 400)
checkmark(1300,84)
text(1322,95,'Task completed',28)
text(1730,95,'Lower bar = less recorded work',28)

normalized=[]
for t,(task,name) in enumerate(list(zip(TASKS,NAMES))+[('ALL','Total workload')]):
    px=25+(t%3)*795
    py=132+(t//3)*414
    frame(px,py,760,394)
    text(px+23,py+43,'All 11 tasks — total workload' if task=='ALL' else f'{task}  {name}',33,weight=700)
    if task=='ALL':
        for c,k in enumerate(CONFIGS):
            completed=sum(data[a,k]['formal_select']=='selected' for a in TASKS)
            text(px+23+c*180,py+83,f'{LABELS[c]}: {completed}/11',25,weight=700 if c==3 else 400,color='#2877b5' if c==3 else '#44545d')
        text(px+23,py+111,'K+S− Tokens: ≥ subtotal (10/11 tasks)',23,color='#56535b')
    else:
        text(px+23,py+86,'Completed:',27)
        completed_slot=0
        for c,label in enumerate(LABELS):
            if data[task,CONFIGS[c]]['formal_select']=='selected':
                tx=px+184+completed_slot*135
                text(tx,py+86,label,27,weight=700 if c==3 else 400,color='#2877b5' if c==3 else '#44545d')
                checkmark(tx+96,py+76)
                completed_slot+=1
    for m,(key,label) in enumerate(METRICS):
        gx=px+27+m*180
        top=py+125
        base=py+327
        height=202
        rect(gx,top-9,164,height+18,'#f7f9fa',rx=6)
        for fraction in (0,.5,1):
            yy=base-height*fraction
            line(gx+7,yy,gx+157,yy,'#c3cdd4' if fraction==0 else '#e0e6e9',1.4)
        vals=[float(data[task,k][key]) for k in CONFIGS if data[task,k][key]!='']
        lo,hi=min(vals),max(vals)
        equal=lo==hi
        if equal:
            text(gx+82,top+24,'Equal',23,'middle',color='#687681')
        for c,k in enumerate(CONFIGS):
            raw=data[task,k][key]
            z=None if raw=='' else ((float(raw)-lo)/(hi-lo) if not equal else .5)
            bx=gx+12+c*36
            if z is None:
                rect(bx,top,28,height,'url(#missing)','#56535b',1,3)
                rect(bx-5,top+83,38,35,'#56535b',rx=3)
                text(bx+14,top+108,'NA',22,'middle',700,'white')
            else:
                bar_height=z*height
                if z==0:
                    # A colored baseline cap shows the minimum, not a positive value.
                    line(bx,base,bx+28,base,COLORS[c],5)
                else:
                    rect(bx,base-bar_height,28,bar_height,COLORS[c],rx=2)
                if task=='ALL' and k=='K1S0' and key=='total_tokens':
                    text(bx+14,top+29,'≥',28,'middle',700,'#283c44')
            normalized.append(dict(task=task,configuration=k,metric=key,raw=raw,normalized=z,equal_column=equal,completed=data[task,k]['formal_select']=='selected'))
        text(gx+82,py+367,label,30,'middle',700)

svg.append('</svg>')
OUT.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
OUT.with_suffix('.json').write_text(json.dumps(normalized,indent=2),encoding='utf-8')
assert len(normalized)==192
assert sum(v['normalized'] is None for v in normalized)==1
assert all(v['normalized'] is None or 0<=v['normalized']<=1 for v in normalized)
print('Generated 11 task panels plus aggregate panel; 1 NA and 1 incomplete aggregate.')
print(json.dumps(totals,indent=2))
