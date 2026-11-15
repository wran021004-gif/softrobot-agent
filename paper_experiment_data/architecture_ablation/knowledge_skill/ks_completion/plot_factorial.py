"""Standalone scientific figures from the completed blind-score table only."""
import csv
import json
import os
import sys
from pathlib import Path

RUN=Path(__file__).resolve().parent;DATA=RUN.parent/'figure_data'
sys.path.insert(0,str(RUN/'plot_runtime'))
os.environ['MPLCONFIGDIR']=str(RUN/'mpl_cache')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

METRICS=[('historical_experience_utilization','Historical experience utilization'),
         ('decision_quality','Research decision quality'),
         ('evidence_consistency','Evidence consistency'),
         ('research_actionability','Research actionability')]


def plot():
    with (DATA/'factorial_results.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==8 and all(r['origin']=='Main_LLM_decision_replay' for r in rows)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','pdf.fonttype':42})
    files=[]
    for task in ['T04','T07']:
        by={r['condition']:r for r in rows if r['task_id']==task}
        fig,axes=plt.subplots(2,2,figsize=(8.8,7.7),layout='constrained')
        for i,((metric,title),ax) in enumerate(zip(METRICS,axes.flat)):
            values=np.array([[float(by['K-S-'][metric]),float(by['K-S+'][metric])],
                             [float(by['K+S-'][metric]),float(by['K+S+'][metric])]])
            im=ax.imshow(values,vmin=0,vmax=4,cmap='Blues',origin='lower',aspect='equal')
            ax.set_xticks([0,1],['OFF','ON']);ax.set_yticks([0,1],['OFF','ON'])
            ax.set_xlabel('Skill');ax.set_ylabel('Knowledge')
            ax.set_title(f'({chr(97+i)}) {title}',fontsize=11,pad=9)
            ax.set_xticks(np.arange(-.5,2,1),minor=True);ax.set_yticks(np.arange(-.5,2,1),minor=True)
            ax.grid(which='minor',color='white',linewidth=2);ax.tick_params(which='minor',bottom=False,left=False)
            for ki in range(2):
                for si in range(2):ax.text(si,ki,f'{values[ki,si]:g}',ha='center',va='center',fontsize=25,fontweight='semibold',color='white' if values[ki,si]>=2.6 else '#12334b')
            for spine in ax.spines.values():spine.set_visible(False)
        colorbar=fig.colorbar(im,ax=axes.ravel().tolist(),ticks=[0,1,2,3,4],shrink=.72,pad=.035)
        colorbar.set_label('Blind score (0–4)')
        fig.suptitle(f'{task} | Knowledge × Skill: four Main LLM decisions',fontsize=15,fontweight='semibold')
        fig.supxlabel('One decision per cell; independent model blind review. No significance claim.\nInvalid proposed actions: 0 in every cell. Human verification pending.',fontsize=9)
        for suffix in ['svg','png','pdf']:
            path=DATA/f'{task}_knowledge_skill_2x2.{suffix}'
            fig.savefig(path,dpi=220,facecolor='white',metadata={'Creator':'Softrobot-Agent E1 completed four-cell blind-score material'} if suffix=='pdf' else None)
            files.append(path.as_posix())
        plt.close(fig)
    result=json.loads((DATA/'ks_four_condition_comparison.json').read_text('utf-8'))
    result['figure_files']=files
    (DATA/'ks_four_condition_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DATA/'factorial_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    layout='''# Complete Knowledge / Skill 2×2 figures

Generated T04_knowledge_skill_2x2 and T07_knowledge_skill_2x2 as SVG, PNG and PDF. Each task has four metric panels; each panel is the full 2×2 design (horizontal Skill OFF/ON, vertical Knowledge OFF/ON). All panels share the same 0–4 scale and show raw blind scores. Engineering Core Plans are excluded.

Both tasks: historical utilization is K−S−=0, K+S−=3, K−S+=3, K+S+=3. Decision quality, evidence consistency and actionability are 4 in every cell; no invalid proposed actions were identified. Therefore the plots show a measured experience-utilization contrast, not a decision-quality increase or demonstrated incremental joint gain. Do not add significance stars, confidence intervals or robot-success labels.

For each metric, factorial_effects.csv gives conditional and averaged main effects; interaction_effects.csv gives I=y11−y10−y01+y00 and the distinct +/-1 coefficient I/4. Utilization: K main=+1.5, S main=+1.5, I=−3, joint minus best single=0 for both tasks. Other score/count effects are zero. The negative contrast is compatible with overlapping benefits and score bounds; it does not establish harmful interaction. One sample/cell is insufficient for statistical synergy claims.

Optional case inset: quote the K+S+ original decisions from knowledge_skill_clips.md. T04 links a historical out-of-domain 0.27 m root to legal fresh two-segment generation, then bank inspection, separate time-zero qualification and complete replay; owned binding and returned-knot transfer remain unspecified. T07 links split-span historical routing to owned common-structure generation and hardest-case diagnosis, but does not explicitly use the known historical geometry failure or control-seed extraction. These are proposed future procedures, not executed new actions. Their qualitative connection did not earn a score above either single factor.

Use token_costs.csv only with estimated labels: Gateway actual usage is unavailable. Complete wire estimates include every request and repeated history; legacy visible-text estimates are separate. Old six requests were reconstructed from saved objects using the same HTTPX serialization; new K+S+ wire bytes were captured directly.

Current scores come from fresh anonymous four-LLM comparisons at blind_review/complete_four_llm/. Previous mixed-origin tables/reviews are archived under ks_completion/prior_figure_data. K+S+ was acquired later with the same frozen inputs/settings, but backend/default reasoning identity is unverified. Human scoring templates remain available.
'''
    (DATA/'figure_layout_suggestion.md').write_text(layout,encoding='utf-8')
    print(json.dumps({'figure_files':files,'matplotlib_version':matplotlib.__version__,'data_rows':len(rows)}),flush=True)


if __name__=='__main__':plot()
