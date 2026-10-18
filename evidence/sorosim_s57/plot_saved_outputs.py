"""MATLAB figure from saved S5.7 outputs; no model, integrator or optimizer calls."""
from pathlib import Path
import json,time
import matlab.engine
from tools.state_io import read,atomic_json
root=Path('evidence/sorosim_s57');started=time.perf_counter()
previous=read(root/'plot_metadata.json') if (root/'plot_metadata.json').exists() else {}
engine=matlab.engine.start_matlab('-nodesktop -nosplash')
try:
    engine.workspace['saved_json']=json.dumps(read(root/'summary.json'))
    engine.workspace['figure_path']=str((root/'prediction_refinement.png').resolve())
    engine.eval(r"""
S=jsondecode(saved_json);f=figure('Visible','off','Position',[50,50,1250,700]);
tiledlayout(2,3,'TileSpacing','compact');counts=[1,4,8,16,32];
for j=1:3
    c=S.cases(j);
    for row=1:2
        if row==1,field='position';scale=.01;unit='m';else,field='velocity';scale=.02;unit='m/s';end
        a=nexttile((row-1)*3+j);full=zeros(1,5);inc=full;
        for k=1:5
            r=c.resolutions.(sprintf('x%d',counts(k))).comparison.(field);
            full(k)=r.one_step_norm;inc(k)=r.increment_norm;initial=r.projection_norm;
        end
        loglog(counts,full,'o-','DisplayName','Full next-step mismatch');hold on;
        loglog(counts,inc,'s-','DisplayName','Increment mismatch');
        if initial>1e-10,yline(initial,'--','DisplayName','Initial mismatch');end
        yline(scale,':','DisplayName','Task scale');grid on;xticks(counts);
        limits=[full,inc,scale];if initial>1e-10,limits=[limits,initial];end
        ylim([min(limits)*.8,max(limits)*1.3]);
        ylabel([field,' error norm (',unit,')']);
        if row==1,title(sprintf('k=%d, t=%.2f s',c.update_index,c.time_s));else,xlabel('Internal substeps per 0.01 s');end
        if j==2 && row==1,legend('Location','southwest','FontSize',8);end
    end
end
sgtitle({'S5.7: archived NMPC state and actual tension','Signed vectors: full = initial + increment; their norms do not add.'});
exportgraphics(f,figure_path,'Resolution',180);close(f);
""",nargout=0)
finally:
    engine.quit()
atomic_json(root/'plot_metadata.json',dict(elapsed_s=time.perf_counter()-started,prior_render_s=previous.get('elapsed_s',0.),source='saved summary only',
    new_integrations=0,new_physics_steps=0,new_optimizer_calls=0))
