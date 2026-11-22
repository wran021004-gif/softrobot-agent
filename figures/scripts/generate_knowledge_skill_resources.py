"""Four aggregate resource bar charts from the author's verified workbook."""
from pathlib import Path
import csv
import html
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'figures/fig06_knowledge_skill_resources'
SOURCE=ROOT/'paper_handoff/figure_data/knowledge_skill_resource_totals.csv'
CONFIGS=['K0S0','K1S0','K0S1','K1S1']
LABELS=['K−S−','K+S−','K−S+','K+S+']
COLORS=['#a3acb5','#c4a578','#8eaaa0','#2877b5']
data={r['configuration']:r for r in csv.DictReader(SOURCE.open(encoding='utf-8'))}
assert set(data)==set(CONFIGS)
METRICS=[('mathematical_analyses','A','Mathematical','analyses',1,450,[0,150,300,450]),
         ('physical_evaluations','B','Physical','evaluations',1,150,[0,50,100,150]),
         ('agent_requests','C','Agent requests','',1,600,[0,200,400,600]),
         ('total_tokens','D','Token consumption','(M)',1e6,.6,[0,.2,.4,.6])]
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="590" viewBox="0 0 2400 590">',
     '<title>Knowledge and Skill: aggregate resource consumption across eleven tasks</title>',
     '<style>text{font-family:"Comic Sans MS","Microsoft YaHei",cursive}</style>',
     '<rect width="2400" height="590" fill="white"/>']
def rect(x,y,w,h,fill,stroke='none',sw=1,rx=0):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')
def text(x,y,value,size=36,anchor='start',weight=400,color='#283c44'):
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{html.escape(str(value))}</text>')
for i,(key,letter,title,second,scale,maximum,ticks) in enumerate(METRICS):
    x=24+i*600
    rect(x,28,552,476,'white','#9da7ae',2.8,19)
    rect(x+3,31,546,470,'none','#9da7ae',1.1,17)
    text(x+24,77,letter,38,weight=700)
    text(x+70,77,title,36,weight=700)
    if second: text(x+70,119,second,36,weight=700)
    left=x+88;right=x+524;base=459;height=282
    for tick in ticks:
        y=base-tick/maximum*height
        color='#a8b5bd' if tick==0 else '#e2e7ea'
        svg.append(f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="{color}" stroke-width="1.8"/>')
        text(left-14,y+11,f'{tick:g}',32,'end',color='#62717a')
    for j,k in enumerate(CONFIGS):
        value=float(data[k][key])/scale
        bx=left+24+j*105;bh=value/maximum*height
        rect(bx,base-bh,72,bh,COLORS[j],rx=3)
        text(bx+36,base-bh-16,f'{value:.2f}' if scale!=1 else str(int(value)),33,'middle',700 if j==3 else 400,'#2877b5' if j==3 else '#44545d')
for i,label in enumerate(LABELS):
    x=740+i*240
    rect(x,541,32,32,COLORS[i],rx=3)
    text(x+48,568,label,36,weight=700 if i==3 else 400)
svg.append('</svg>')
OUT.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8',newline='\n')
print('Generated compact Knowledge/Skill aggregate resource figure.')
