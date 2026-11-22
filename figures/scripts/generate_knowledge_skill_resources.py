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
METRICS=[('mathematical_analyses','A  Mathematical analyses',1,900,[0,300,600,900]),
         ('physical_evaluations','B  Physical evaluations',1,300,[0,100,200,300]),
         ('agent_requests','C  Agent requests',1,600,[0,200,400,600]),
         ('total_tokens','D  Token consumption (M)',1e6,6,[0,2,4,6])]
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="1220" viewBox="0 0 2400 1220">',
     '<title>Knowledge and Skill: total resource consumption across eleven tasks</title>',
     '<style>text{font-family:"Comic Sans MS","Microsoft YaHei",cursive}</style>',
     '<rect width="2400" height="1220" fill="white"/>']
def text(x,y,s,size=32,anchor='start',weight=400,color='#283c44'):
    svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{color}">{html.escape(s)}</text>')
def rect(x,y,w,h,fill,stroke='none',sw=1,rx=0):
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')
def line(x1,y1,x2,y2,color='#d8dfe3',width=1.5):
    svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
for i,(key,title,scale,maximum,ticks) in enumerate(METRICS):
    x=30+(i%2)*1200
    y=45+(i//2)*600
    rect(x,y,1140,550,'white','#9da7ae',2.8,19)
    rect(x+3,y+3,1134,544,'none','#9da7ae',1.1,17)
    rect(x+20,y-18,650,48,'white')
    text(x+30,y+18,title,40,weight=700)
    left=x+120;right=x+1080;base=y+440;height=345
    for tick in ticks:
        yy=base-tick/maximum*height
        line(left,yy,right,yy,'#a8b5bd' if tick==0 else '#e2e7ea',1.8)
        text(left-20,yy+10,f'{tick:,}',29,'end',color='#62717a')
    for c,k in enumerate(CONFIGS):
        value=float(data[k][key])/scale
        bx=left+55+c*235
        bh=value/maximum*height
        rect(bx,base-bh,140,bh,COLORS[c],rx=3)
        shown=f'{value:,.2f}' if scale!=1 else f'{int(value):,}'
        text(bx+70,base-bh-18,shown,36,'middle',700 if c==3 else 400,'#2877b5' if c==3 else '#44545d')
        text(bx+70,base+57,LABELS[c],36,'middle',700 if c==3 else 400,'#2877b5' if c==3 else '#283c44')
svg.append('</svg>')
OUT.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
OUT.with_suffix('.json').write_text(json.dumps({'source':str(SOURCE.relative_to(ROOT)),'aggregation':'author-updated configuration totals across 11 tasks','normalization':'zero-baseline axes; workbook request totals; workbook token totals in millions','configurations':[data[k] for k in CONFIGS]},indent=2),encoding='utf-8')
print('Generated four total-consumption panels from verified workbook totals.')
