function tf_view(folder,index)
% Native Figure over saved states only. Never calls tf_run or an ODE solver.
p=jsondecode(fileread(fullfile(folder,'resolved_physics.json')));
scene=jsondecode(fileread(fullfile(folder,'experiment_scene.json')));
rows=jsondecode(fileread(fullfile(folder,'replay_trajectory.json')));
if nargin<2, index=numel(rows); end
r=rows(index); figure('Name','Saved tendon family — geometry, not exact contact'); hold on; axis equal; grid on; view(3);
for i=1:numel(p.parts)
    part=p.parts(i); R=squeeze(r.body_rotations(i,:,:)); origin=r.body_positions_m(i,:);
    if ~isempty(part.section_properties)
        prop=part.section_properties; rings={prop.outer_yz_m};
        holes=prop.holes_yz_m;
        if iscell(holes), rings=[rings;holes(:)]; elseif ~isempty(holes)
            if ndims(holes)==2, rings{end+1}=holes; else
                for j=1:size(holes,1), rings{end+1}=squeeze(holes(j,:,:)); end
            end
        end
        a=-part.section_axis_rad; Q=[cos(a) -sin(a);sin(a) cos(a)];
        for j=1:numel(rings)
            yz=rings{j}*Q'; yz=[yz;yz(1,:)];
            verts=[zeros(size(yz,1),1) yz;part.length_m*ones(size(yz,1),1) yz]*R'+origin;
            m=size(yz,1);
            for k=1:m-1
                face=verts([k k+1 k+1+m k+m],:);
                patch(face(:,1),face(:,2),face(:,3),[.3 .6 .8],'FaceAlpha',.6,'EdgeColor','none');
            end
            plot3(verts(1:m,1),verts(1:m,2),verts(1:m,3),'k-');
        end
    else
        verts=part.collision_vertices_m*R'+origin;
        faces=convhull(verts); trisurf(faces,verts(:,1),verts(:,2),verts(:,3),'FaceColor',[.7 .5 .2],'FaceAlpha',.7);
    end
end
routes=r.tendon_routes_m;
for k=1:numel(p.tendons)
    if iscell(routes), xyz=routes{k}; else, xyz=squeeze(routes(k,:,:)); end
    plot3(xyz(:,1),xyz(:,2),xyz(:,3),'-o','LineWidth',1.5,'MarkerSize',3);
end
target=scene.target_world_m; plot3(target(1),target(2),target(3),'rp','MarkerSize',14);
tip=r.tip_m; plot3(tip(1),tip(2),tip(3),'go','MarkerSize',8);
xlabel('world x / m'); ylabel('world y / m'); zlabel('world z / m');
title(sprintf('Saved t = %.3f s; section walls, holes and routed tendons',r.time_s));
end
