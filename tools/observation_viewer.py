"""One local Matplotlib workbench for saved trajectories and derived GIF/PNG."""
from pathlib import Path
import numpy as np
from tools.observation_tools import load_observation


class ObservationViewer:
    def __init__(self, sources):
        import matplotlib.pyplot as plt
        from matplotlib.widgets import Slider, Button
        self.records = [load_observation(p) for p in sources]
        self.playing = False; self.index = 0; self.speed = .5
        self.times = []
        for t in sorted(set(s['time_s'] for r in self.records for s in r['samples'])):
            # Coalesce floating-point representations of the same accepted output
            # timestamp, never interpolate states or collapse the 0.002 s phases.
            if not self.times or t-self.times[-1]>1e-10:self.times.append(t)
        self.times = self.times or [0.]
        self.figure = plt.figure(figsize=(14,8))
        self.figure.subplots_adjust(left=.05,right=.97,bottom=.22,top=.85,wspace=.30,hspace=.50)
        grid=self.figure.add_gridspec(3,4)
        self.axes3 = [self.figure.add_subplot(grid[:2,2*i:2*i+2],projection='3d') for i in range(min(2,len(self.records)))]
        self.curves = [self.figure.add_subplot(grid[2,i]) for i in range(4)]
        self.lines=[]; self.cursors=[]
        for i,r in enumerate(self.records[:2]):
            ax=self.axes3[i]; points=np.array([s['centerline_m'] for s in r['samples']])
            if len(points):
                minimum=points.min(axis=(0,1)); maximum=points.max(axis=(0,1))
                center=(minimum+maximum)/2; radius=max(.08,float((maximum-minimum).max())*.6)
                for setter,c in zip((ax.set_xlim,ax.set_ylim,ax.set_zlim),center): setter(c-radius,c+radius)
            ax.set(xlabel='X (m)',ylabel='Y (m)',zlabel='Z (m)'); ax.set_box_aspect((1,1,1))
            line,=ax.plot([],[],[], '-o',lw=5,markersize=3,color=('tab:blue','tab:orange')[i]);self.lines.append(line)
            if r['target_m'] is not None: ax.scatter(*r['target_m'],marker='*',s=130,color='red')
            ax.set_title(f"{r['backend']} | {r['control']} | {r['status']}\nL={r['design'].get('total_length_m')} m, r={r['design'].get('tendon_routing_radius_m','N/A')}, tendons={r['design'].get('tendon_count','N/A')}\n{r['model']}",fontsize=8)
            if not r['samples']:
                import textwrap
                detail=str(r.get('reason','No saved dynamic samples'))+'\nSource: '+r['source']
                if r.get('diagnostics'):
                    d=r['diagnostics'];trigger=d.get('trigger',{})
                    detail+=f"\n{trigger.get('state_kind')}: t={trigger.get('time_s')}, q={trigger.get('state_rad')}; last valid output t={d.get('last_valid_time_s')}"
                ax.text2D(.02,.5,'\n'.join(textwrap.fill(line,70) for line in detail.splitlines()),transform=ax.transAxes,fontsize=8)
            ts=[s['time_s'] for s in r['samples']]
            its=[s['input_time_s'] if s['input_time_s'] is not None else np.nan for s in r['samples']]
            for j,key in enumerate(('error_m','tip_m','tendon_actual_m','force_n')):
                values=[s[key] for s in r['samples']]
                if values and all(v is not None for v in values):
                    plotted=self.curves[j].plot(ts if j<2 else its,values,alpha=.75,lw=.7,linestyle='-' if i==0 else ':')
                    if j==0:plotted[0].set_label(r['control'])
                    if j==1:
                        for axis_name,curve in zip('XYZ',plotted):curve.set_label(f'{i+1} {axis_name}')
                else: self.curves[j].text(.02,.85-i*.16,f'{i+1}: unavailable',transform=self.curves[j].transAxes,fontsize=7)
            targets=[s['tendon_target_m'] for s in r['samples']]
            if targets and all(t is not None for t in targets):self.curves[2].plot(its,targets,'--',lw=.6,alpha=.5)
        for ax,title in zip(self.curves,('Tip error (m), derived','Tip XYZ (m)','Tendons (m), dashed=target','Signed actuator force (N)')):
            ax.set_title(title,fontsize=8);ax.set_xlabel('time (s)',fontsize=8);ax.tick_params(labelsize=7);ax.grid(alpha=.2)
            self.cursors.append(ax.axvline(self.times[0],color='black',lw=.8))
            ax.set_xlim(self.times[0],max(self.times[-1],self.times[0]+.001))
        for ax in self.curves[:2]:
            if ax.get_legend_handles_labels()[0]:ax.legend(fontsize=6,ncol=2)
        self.label=self.figure.text(.05,.145,'',fontsize=8,family='monospace')
        self.figure.text(.05,.97,'Saved motion workbench | world: X forward, Y/Z cross section | drag 3D view to rotate',fontsize=12)
        self.figure.text(.05,.925,'Shape reconstructed from saved state. Position: post integration; force/length: dynamics stage. Missing fields are unavailable.',fontsize=8)
        self.slider=Slider(self.figure.add_axes([.10,.09,.68,.025]),'Time (s)',0,max(self.times[-1],.001),valinit=0)
        self.slider.on_changed(self.seek)
        self.buttons=[]
        for x,label,callback in [( .05,'Play / pause',self.toggle),(.20,'Step',self.step),(.32,'0.25x / 1x',self.slow),(.46,'PNG',self.snapshot),(.56,'GIF',self.export)]:
            button=Button(self.figure.add_axes([x,.025,.12,.04]),label);button.on_clicked(callback);self.buttons.append(button)
        self.timer=self.figure.canvas.new_timer(interval=40);self.timer.add_callback(self.tick);self.timer.start()
        self.seek(0)

    def seek(self,value):
        self.index=min(len(self.times)-1,max(0,int(np.searchsorted(self.times,value+1e-10,side='right')-1)))
        t=self.times[self.index];text=[]
        if abs(self.slider.val-t)>1e-10:
            self.slider.eventson=False;self.slider.set_val(t);self.slider.eventson=True
        for line,r in zip(self.lines,self.records):
            if not r['samples']: continue
            times=[s['time_s'] for s in r['samples']]
            idx=int(np.searchsorted(times,t+1e-10,side='right')-1)
            if idx<0 or t>times[-1]+1e-9:
                line.set_data_3d([],[],[]);text.append(f"{r['backend']}: outside saved interval");continue
            s=r['samples'][idx];p=np.array(s['centerline_m']);line.set_data_3d(*p.T)
            input_time='unavailable' if s['input_time_s'] is None else f"{s['input_time_s']:.4f}"
            error='unavailable' if s['error_m'] is None else f"{s['error_m']:.6f} m"
            text.append(f"{r['backend']} {r['control']}: state t={s['time_s']:.4f}, input t={input_time}, tip={np.round(s['tip_m'],4)}; error={error}")
        self.label.set_text('\n'.join(text))
        for cursor in self.cursors: cursor.set_xdata([t,t])
        self.figure.canvas.draw_idle()

    def toggle(self,event=None): self.playing=not self.playing
    def step(self,event=None): self.playing=False;self.slider.set_val(self.times[(self.index+1)%len(self.times)])
    def slow(self,event=None): self.speed=.25 if self.speed!=.25 else 1.
    def tick(self):
        if self.playing:
            t=self.times[self.index]+.04*self.speed
            self.slider.set_val(0 if t>self.times[-1] else t)

    def snapshot(self,event=None,path=None):
        path=Path(path or 'runs/round4/derived/observation.png');path.parent.mkdir(parents=True,exist_ok=True)
        self.figure.savefig(path,dpi=110);return path

    def export(self,event=None,path=None):
        from PIL import Image
        path=Path(path or 'runs/round4/derived/observation.gif');path.parent.mkdir(parents=True,exist_ok=True)
        saved=self.times[self.index];self.playing=False;frames=[]
        # Downsample saved frames only; no interpolation of physical states.
        for t in np.linspace(self.times[0],self.times[-1],min(51,len(self.times))):
            self.seek(t);self.figure.canvas.draw()
            frames.append(Image.fromarray(np.asarray(self.figure.canvas.buffer_rgba()).copy()).convert('RGB').resize((1008,576)))
        frames[0].save(path,save_all=True,append_images=frames[1:],duration=80,loop=0)
        self.seek(saved);return path


def main():
    import argparse
    parser=argparse.ArgumentParser(description='只读动态观察；鼠标拖动三维视角。PNG/GIF 存入 runs/round4/derived。')
    parser.add_argument('sources',nargs='+');parser.add_argument('--export');parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if len(args.sources)>2: parser.error('At most two sources')
    import matplotlib.pyplot as plt
    viewer=ObservationViewer(args.sources)
    if args.export: viewer.export(path=args.export)
    if args.smoke:
        def check():
            from matplotlib.backend_bases import MouseEvent
            def click(index):
                ax=viewer.buttons[index].ax;x,y=ax.transAxes.transform((.5,.5))
                for name in ('button_press_event','button_release_event'):
                    MouseEvent(name,viewer.figure.canvas,x,y,button=1)._process()
            click(0);viewer.tick();click(0);click(1);click(2)
            viewer.slider.set_val(viewer.times[-1]*.6)
            viewer.axes3[0].view_init(elev=24,azim=48)
            viewer.figure.canvas.draw();viewer.snapshot(path='runs/round4/derived/window_interaction.png')
            from tools.closeout_state import atomic_json
            atomic_json('runs/round4/derived/window_check.json',dict(backend=plt.get_backend(),
                interactive_window=viewer.figure.canvas.manager.window.winfo_exists()==1,
                controls=['play','pause','step','slow','seek','view'],index=viewer.index,backend_solves=0))
            plt.close(viewer.figure)
        timer=viewer.figure.canvas.new_timer(interval=1800);timer.single_shot=True;timer.add_callback(check);timer.start()
    plt.show()
