"""Build the main-text, within-task Knowledge/Skill workload comparison."""
from pathlib import Path
import csv
import html
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'figures' / 'fig06_knowledge_skill_resources'
CONFIGS = ['K0S0', 'K1S0', 'K0S1', 'K1S1']
LABELS = ['K− S−', 'K+ S−', 'K− S+', 'K+ S+']
TASKS = [f'T{i:02}' for i in range(1, 11)] + ['PHS-2D']
METRICS = [('math_charged_evaluations', 'A  Mathematical evaluations'),
           ('physical_launches', 'B  Physical launches'),
           ('core_request_records', 'C  Core requests'),
           ('total_tokens', 'D  Token consumption')]
rows = list(csv.DictReader((ROOT / 'paper_handoff/figure_data/fig05_resource_ablation.csv').open(encoding='utf-8-sig')))
data = {(r['task'], r['configuration']): r for r in rows if r['configuration'] in CONFIGS}
assert len(data) == 44
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="1350" viewBox="0 0 2400 1350">',
       '<title>Knowledge and Skill: within-task resource comparison</title>',
       '<style>text{font-family:"Comic Sans MS","Microsoft YaHei",cursive}</style>',
       '<defs><pattern id="missing" width="12" height="12" patternUnits="userSpaceOnUse"><rect width="12" height="12" fill="#f0f0f0"/><path d="M-3 3 L3 -3 M0 12 L12 0 M9 15 L15 9" stroke="#b7bdc2" stroke-width="2"/></pattern><linearGradient id="scale"><stop stop-color="#eef4f6"/><stop offset="1" stop-color="#527f91"/></linearGradient></defs>',
       '<rect width="2400" height="1350" fill="white"/>']
def text(x, y, s, size=32, anchor='start', weight=400, color='#283c44'):
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{html.escape(s)}</text>')
def rect(x, y, w, h, fill, stroke='none', sw=1, rx=0):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')
def color(value):
    a, b = (238,244,246), (82,127,145)
    return '#'+''.join(f'{round(x+(y-x)*value):02x}' for x,y in zip(a,b))

text(42, 44, 'Compare configurations within each task', 36, weight=700)
rect(1040, 20, 280, 28, 'url(#scale)')
text(1020, 45, 'Less', 29, anchor='end')
text(1340, 45, 'More recorded work', 29)
svg.append('<circle cx="1740" cy="33" r="9" fill="#233b46" stroke="white" stroke-width="2"/>')
text(1760,45,'Task completed',29)
rect(2100,20,35,28,'url(#missing)')
text(2150,45,'Unavailable',29)
X, CW = 275, 187
for c, task in enumerate(TASKS):
    text(X+c*CW+CW/2, 103, task, 32, 'middle', 700)

normalized = []
for panel, (key, title) in enumerate(METRICS):
    top = 132 + panel*300
    rect(25,top,2350,280,'white','#9da7ae',2.8,17)
    rect(28,top+3,2344,274,'none','#9da7ae',1,15)
    rect(47,top-17,650,45,'white')
    text(58,top+16,title,36,weight=700)
    for r,label in enumerate(LABELS):
        text(241,top+71+r*51,label,33,'end',700 if r==3 else 400)
    for c,task in enumerate(TASKS):
        available = [float(data[task,k][key]) for k in CONFIGS if data[task,k][key] != '']
        maximum = max(available)
        for r,k in enumerate(CONFIGS):
            raw = data[task,k][key]
            value = None if raw=='' else (float(raw)/maximum if maximum else 0.0)
            x,y = X+c*CW, top+37+r*51
            rect(x,y,CW-6,46,'url(#missing)' if value is None else color(value), '#d6dfe2', 0.8, 3)
            passed = data[task,k]['formal_select']=='selected'
            if passed:
                svg.append(f'<circle cx="{x+(CW-6)/2}" cy="{y+23}" r="8" fill="#233b46" stroke="white" stroke-width="2"/>')
            normalized.append(dict(task=task,configuration=k,metric=key,raw=raw,normalized=value,completed=passed))
    rect(X-4,top+37+3*51-3,CW*11-2,52,'none','#527f91',3,5)
svg.append('</svg>')
OUT.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
OUT.with_suffix('.json').write_text(json.dumps(normalized,indent=2),encoding='utf-8')
assert sum(v['normalized'] is None for v in normalized)==1
assert all(v['normalized'] is None or 0<=v['normalized']<=1 for v in normalized)
tokens = lambda t,k: float(data[t,k]['total_tokens'])
print('Complete tasks:', {k:sum(data[t,k]['formal_select']=='selected' for t in TASKS) for k in CONFIGS})
print('K+S+ uses fewer recorded tokens than K-S-:', sum(tokens(t,'K1S1')<tokens(t,'K0S0') for t in TASKS), 'of 11')
print('Generated',OUT.with_suffix('.svg'))
