function info = tdcr_replay_saved(folder, output_folder, fps)
% Native Figure only: saved planar eight-joint poses, no solver or force model.
if nargin<2, output_folder=''; end
if nargin<3, fps=25; end
p=jsondecode(fileread(fullfile(folder,'shared_input.json')));
ir=jsondecode(fileread(fullfile(folder,'robot_ir.json')));
result=jsondecode(fileread(fullfile(folder,'result.json')));
assert(strcmp(result.backend,'matlab'),'Use the MATLAB backend saved trajectory.');
assert(abs(ir.section.body_radius_m-p.body_radius)<1e-12);
if ~isempty(output_folder)
    assert(~isfile(fullfile(output_folder,'native_scene.gif')),'Export already exists.');
    if ~isfolder(output_folder), mkdir(output_folder); end
end
scratch=tempname; mkdir(scratch);
cleanup=onCleanup(@()clean_scratch(scratch));
files=gunzip(fullfile(folder,'trajectory.json.gz'),scratch);
rows=jsondecode(fileread(files{1})); clear cleanup;
times=[rows.time_s]; n=ir.section.segments; nt=size(p.offsets,1);
assert(numel(rows(1).qpos_rad)==n && n==8,'Expected saved planar eight-joint poses.');
assert(all(diff(times)>0),'Saved timestamps must increase.');
L=p.length; r=p.body_radius;
fig=figure('Name',[result.candidate_id ' MATLAB | saved trajectory replay'], ...
    'Tag','Round9SavedReplay','Visible','on','Color',[.95 .96 .98], ...
    'Position',[80 80 960 700],'MenuBar','none','ToolBar','figure');
ax=axes(fig,'Position',[.08 .22 .88 .72]); hold(ax,'on'); grid(ax,'on');
axis(ax,'equal'); xlim(ax,[-.15*L 1.2*L]); ylim(ax,[-.4*L .4*L]); zlim(ax,[p.floor_z-.03 .9*L]);
xlabel(ax,'world x (m)'); ylabel(ax,'world y (m)'); zlabel(ax,'world z (m)'); view(ax,[-35 24]);
patch(ax,[-.15*L 1.2*L 1.2*L -.15*L],[-.4*L -.4*L .4*L .4*L], ...
    p.floor_z*ones(1,4),[.65 .67 .70],'FaceAlpha',.65,'EdgeColor','none');
% A fixed-base marker, sized from the saved body radius; it is not a new body.
base=[-r -r -r;0 -r -r;0 r -r;-r r -r;-r -r r;0 -r r;0 r r;-r r r];
patch(ax,'Vertices',base,'Faces',[1 2 3 4;5 6 7 8;1 2 6 5;2 3 7 6;3 4 8 7;4 1 5 8], ...
    'FaceColor',[.25 .28 .32],'EdgeColor','none');
text(ax,-r,0,1.6*r,'fixed base');
[sx,sy,sz]=sphere(16);
xml=fileread(fullfile(folder,'robot.xml'));
target_size=regexp(xml,'<site name="target_site"[^>]*size="([^"]+)"','tokens','once');
target_radius=str2double(target_size{1});
surf(ax,p.target(1)+target_radius*sx,p.target(2)+target_radius*sy,p.target(3)+target_radius*sz, ...
    'FaceColor',[.9 .1 .15],'EdgeColor','none');
text(ax,p.target(1),p.target(2),p.target(3)+.02,'saved target');
tip=plot3(ax,0,0,0,'o','MarkerFaceColor',[.1 .6 .1],'MarkerEdgeColor','none');
bodies=gobjects(n,1); tendons=gobjects(nt,1); colors=lines(nt);
for j=1:n
    bodies(j)=surf(ax,zeros(12,21),zeros(12,21),zeros(12,21), ...
        'FaceColor',[.3 .6 .85],'FaceAlpha',.3,'EdgeColor','none');
end
for j=1:nt
    tendons(j)=plot3(ax,0,0,0,'Color',colors(j,:),'LineWidth',2,'DisplayName',sprintf('tendon_%d',j-1));
end
legend(ax,tendons,'Location','northeastoutside'); camlight(ax,'headlight'); lighting(ax,'gouraud');
button=uicontrol(fig,'Style','togglebutton','String','Pause','Value',1,'Units','normalized', ...
    'Position',[.07 .12 .12 .05],'Callback',@toggle);
slider=uicontrol(fig,'Style','slider','Min',times(1),'Max',times(end),'Value',times(1), ...
    'Units','normalized','Position',[.23 .13 .68 .03],'Callback',@scrub);
forces=uicontrol(fig,'Style','text','Units','normalized','Position',[.05 .015 .9 .085], ...
    'BackgroundColor',fig.Color,'HorizontalAlignment','left');
cursor=times(1); clock=tic; last=0; timer_handle=[];
fig.CloseRequestFcn=@close_figure;
draw_frame(1); drawnow;
indices=[]; scheduled=[times(1):1/fps:times(end),times(end)]; scheduled=unique(scheduled,'stable');
if ~isempty(output_folder)
    set(button,'Enable','off'); set(slider,'Enable','off');
    for k=1:numel(scheduled)
        idx=find(times<=scheduled(k)+1e-12,1,'last'); indices(end+1)=idx; %#ok<AGROW>
        draw_frame(idx); drawnow;
        frame=getframe(fig); % Real MATLAB Figure framebuffer, not Python drawing.
        [indexed,map]=rgb2ind(frame.cdata,256);
        delay=1/fps;
        if k<numel(scheduled), delay=scheduled(k+1)-scheduled(k); end
        if k==1
            imwrite(indexed,map,fullfile(output_folder,'native_scene.gif'),'gif','LoopCount',inf,'DelayTime',delay);
        else
            imwrite(indexed,map,fullfile(output_folder,'native_scene.gif'),'gif','WriteMode','append','DelayTime',delay);
        end
    end
    imwrite(frame.cdata,fullfile(output_folder,'native_scene.png'));
    set(button,'Enable','on','Value',0,'String','Play'); set(slider,'Enable','on'); cursor=times(end);
end
points=rows(end).centerline_m;
assert(norm(points(end,:)-rows(end).tip_m(:)')<1e-10,'Saved centerline/tip mismatch.');
assert(abs(sum(vecnorm(diff(points),2,2))-L)<1e-10,'Saved robot length mismatch.');
info=struct('backend','matlab','candidate_id',result.candidate_id,'renderer','MATLAB Figure / getframe', ...
    'source',folder,'sample_indices_zero_based',indices-1,'saved_times_s',times(indices), ...
    'length_m',L,'body_radius_m',r,'segment_length_m',p.ds,'target_m',p.target, ...
    'final_saved_tip_m',rows(end).tip_m,'final_rendered_tip_m',points(end,:), ...
    'backend_solves',0,'rescoring',false,'interpolation',false,'figure_visible',strcmp(fig.Visible,'on'), ...
    'geometry','Separate actual-radius capsules on saved segment endpoints; no smoothed backbone', ...
    'force_semantics','Only original solver_actuator_force_n at saved solver_time_s');
if ~isempty(output_folder)
    fid=fopen(fullfile(output_folder,'native_replay.json'),'w'); fwrite(fid,jsonencode(info),'char'); fclose(fid);
end
timer_handle=timer('ExecutionMode','fixedSpacing','Period',.03,'BusyMode','drop','TimerFcn',@tick);
last=toc(clock); start(timer_handle);

    function draw_frame(idx)
        row=rows(idx); pts=row.centerline_m;
        theta=linspace(0,2*pi,21); phi=[linspace(-pi/2,0,6),linspace(0,pi/2,6)];
        xx=r*sin(phi)'; xx(7:end)=xx(7:end)+p.ds; rr=r*cos(phi)';
        for j=1:n
            u=(pts(j+1,:)-pts(j,:))/p.ds; v=[0 1 0]; w=cross(u,v);
            X=pts(j,1)+xx*u(1)+rr*cos(theta)*v(1)+rr*sin(theta)*w(1);
            Y=pts(j,2)+xx*u(2)+rr*cos(theta)*v(2)+rr*sin(theta)*w(2);
            Z=pts(j,3)+xx*u(3)+rr*cos(theta)*v(3)+rr*sin(theta)*w(3);
            set(bodies(j),'XData',X,'YData',Y,'ZData',Z);
        end
        for j=1:nt
            route=squeeze(row.tendon_routes_m(j,:,:));
            set(tendons(j),'XData',route(:,1),'YData',route(:,2),'ZData',route(:,3));
        end
        set(tip,'XData',pts(end,1),'YData',pts(end,2),'ZData',pts(end,3));
        set(slider,'Value',row.time_s);
        title(ax,sprintf('%s | MATLAB saved trajectory | t=%.3f s | length %.5f m',result.candidate_id,row.time_s,L));
        set(forces,'String',sprintf('Saved actuator force (N), solver t=%.3f s: %s\nPlanar 8-joint model. Saved poses only; no integration or rescoring.', ...
            row.solver_time_s,mat2str(row.solver_actuator_force_n(:)',5)));
    end
    function tick(~,~)
        now=toc(clock); elapsed=now-last; last=now;
        if get(button,'Value')==0, return; end
        cursor=min(times(end),cursor+elapsed);
        draw_frame(find(times<=cursor,1,'last')); drawnow limitrate;
        if cursor>=times(end), set(button,'Value',0,'String','Play'); end
    end
    function toggle(~,~)
        if get(button,'Value'), set(button,'String','Pause'); if cursor>=times(end), cursor=times(1); end
        else, set(button,'String','Play'); end
    end
    function scrub(~,~)
        cursor=get(slider,'Value'); set(button,'Value',0,'String','Play');
        draw_frame(find(times<=cursor,1,'last')); drawnow;
    end
    function close_figure(~,~)
        if ~isempty(timer_handle) && isvalid(timer_handle), stop(timer_handle); delete(timer_handle); end
        delete(fig);
    end
end

function clean_scratch(folder)
file=fullfile(folder,'trajectory.json'); if isfile(file), delete(file); end
rmdir(folder); % This function created this single-file temporary directory.
end
