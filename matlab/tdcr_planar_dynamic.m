function out = tdcr_planar_dynamic(input_json, output_path)
% Independent planar multi-joint dynamics; no graphics or shared workspace.
p=jsondecode(input_json); clock=tic; n=numel(p.mass); ne=0; cmd=p.command(:);
y0=zeros(2*n,1); tout=[]; yout=[]; commands=[]; internal=[]; successful_steps=0; status='completed'; reason='';
accepted_t=[];accepted_y=[];last_rhs_time=0;
opts=odeset('RelTol',p.solver.rtol,'AbsTol',p.solver.atol,'MaxStep',p.solver.max_step_s,'Refine',1,'OutputFcn',@progress);
bend=p.bend(:); dt=p.dt; h=p.control.update_every_steps*dt;
try
  if strcmp(p.control.mode,'C1'), h=p.duration; end
  for start=0:h:p.duration-dt/2
    if strcmp(p.control.mode,'C2')
      [pts,~,~,~]=geometry(y0(1:n)); tip=[pts(end,1);0;pts(end,2)];
      [~,J]=pcc(p.length,bend); delta=p.control.gain_rad2_per_m2*J'*(p.target(:)-tip);
      delta=delta*min(1,p.control.max_bend_update_rad/max(norm(delta),eps));
      bend=bend+delta; bend=bend*min(1,pi/max(norm(bend),eps));
      active=-p.radius*(bend(1)*cos(p.angles(:))+bend(2)*sin(p.angles(:)));
      active=min(.25*p.length,max(-.25*p.length,active));
      raw=p.length+active+p.control.bias_fraction*p.length;
      raw=min(1.30*p.length,max(.73*p.length,raw));
      cap=p.control.rate_limit_ref_per_s*p.length*h;
      cmd=min(cmd+cap,max(cmd-cap,raw));
    end
    finish=min(p.duration,start+h);
    sol=ode15s(@rhs,[start finish],y0,opts);
    internal=[internal; sol.x(:)]; %#ok<AGROW>
    successful_steps=successful_steps+max(0,numel(sol.x)-1);
    ts=(start:dt:finish)'; if abs(ts(end)-finish)>1e-10, ts=[ts;finish]; end
    ys=deval(sol,ts)';
    if ~isempty(tout), ts=ts(2:end); ys=ys(2:end,:); end
    tout=[tout;ts]; yout=[yout;ys]; commands=[commands;repmat(cmd',numel(ts),1)]; %#ok<AGROW>
    y0=sol.y(:,end);
    if sol.x(end)<finish-1e-9, error('TDCR:EarlyStop','Solver stopped before requested endpoint'); end
  end
catch ex
  status='failed'; reason=[ex.identifier ': ' ex.message];
  if isempty(tout) && ~isempty(accepted_t)
    tout=accepted_t;yout=accepted_y;commands=repmat(cmd',numel(tout),1);internal=accepted_t;
    successful_steps=max(0,numel(accepted_t)-1);
  end
end
rows=cell(numel(tout),1); maxpenetration=0;
for a=1:numel(tout)
  q=yout(a,1:n)'; v=yout(a,n+1:end)'; cmd=commands(a,:)';
  [~,aux]=forces(q,v); maxpenetration=max(maxpenetration,max(0,-min(aux.gap)));
  rows{a}=struct('time_s',tout(a),'solver_time_s',tout(a),'tip_m',[aux.points(end,1),0,aux.points(end,2)], ...
    'qpos_rad',q','qvel_rad_s',v','command_m',cmd','solver_tendon_length_m',aux.lengths', ...
    'solver_actuator_force_n',-aux.tension','solver_contact_count',sum(aux.normal>0), ...
    'centerline_m',[aux.points(:,1),zeros(n+1,1),aux.points(:,2)],'tendon_routes_m',aux.routes, ...
    'tendon_demand_n',aux.demand','tendon_velocity_m_s',(aux.Jlength*v)', ...
    'qfrc_actuator',aux.drive','qfrc_spring',aux.spring','qfrc_damper',aux.damping', ...
    'qfrc_contact_approx',aux.contact','floor_gap_m',aux.gap','normal_contact_approx_n',aux.normal');
end
complete=strcmp(status,'completed') && ~isempty(tout) && abs(tout(end)-p.duration)<1e-9 && all(isfinite(yout(:)));
err=[]; tip=[]; if complete, tip=rows{end}.tip_m; err=norm(tip-p.target(:)'); end
out=struct('computation_status',status,'complete',complete,'reason',reason,'position_error_m',err, ...
 'tip_m',tip,'model_task_success',complete && err<=p.tolerance,'elapsed_s',toc(clock), ...
 'rhs_evaluations',ne,'solver','ode15s','successful_internal_steps',successful_steps, ...
 'internal_time_convention','concatenated interval meshes; duplicate control boundaries excluded from successful step count', ...
 'internal_time_s',internal','output_sampling_s',dt,'max_sampled_penetration_m',maxpenetration, ...
 'last_valid_time_s',0,'last_rhs_time_s',last_rhs_time,'trajectory',{rows},'model_id','matlab_tdcr_planar_dynamic_v1');
if ~isempty(tout), out.last_valid_time_s=tout(end); end
fid=fopen(output_path,'w'); cleaner=onCleanup(@()fclose(fid)); fwrite(fid,jsonencode(out),'char');

 function stop=progress(t,y,flag)
   stop=false;
   if isempty(flag),accepted_t=[accepted_t;t(:)];accepted_y=[accepted_y;y'];end
 end
 function dy=rhs(t,y)
   last_rhs_time=t;
   ne=ne+1; if toc(clock)>p.timeout_s, error('TDCR:Timeout','Wall clock cap exceeded'); end
   [acc,~]=forces(y(1:n),y(n+1:end)); dy=[y(n+1:end);acc];
   if any(~isfinite(dy)), error('TDCR:Nonfinite','Nonfinite derivative'); end
 end
 function [points,Jpoints,routes,Jroutes]=geometry(q)
   ang=cumsum(q); u=[cos(ang),-sin(ang)]; du=[-sin(ang),-cos(ang)];
   points=[0,0;cumsum(p.ds*u,1)]; Jpoints=zeros(2,n,n+1);
   for k=1:n
     Jpoints(:,:,k+1)=Jpoints(:,:,k); Jpoints(:,1:k,k+1)=Jpoints(:,1:k,k+1)+repmat(p.ds*du(k,:)',1,k);
   end
   nt=numel(p.angles); routes=zeros(nt,n+1,3); Jroutes=zeros(2,n,n+1,nt);
   for t=1:nt
     off=p.offsets(t,:); routes(t,1,:)=[0,off(1),off(2)];
     for k=1:n
       ro=[off(2)*sin(ang(k)),off(2)*cos(ang(k))]; dro=[off(2)*cos(ang(k)),-off(2)*sin(ang(k))];
       routes(t,k+1,:)=[points(k+1,1)+ro(1),off(1),points(k+1,2)+ro(2)];
       Jroutes(:,:,k+1,t)=Jpoints(:,:,k+1); Jroutes(:,1:k,k+1,t)=Jroutes(:,1:k,k+1,t)+repmat(dro',1,k);
     end
   end
 end
 function [acc,a]=forces(q,v)
   [points,Jpoints,routes,Jroutes]=geometry(q); ang=cumsum(q); omega=cumsum(v);
   u=[cos(ang),-sin(ang)]; du=[-sin(ang),-cos(ang)]; M=zeros(n); bias=zeros(n,1); gravity=zeros(n,1);
   for k=1:n
     J=Jpoints(:,:,k); J(:,1:k)=J(:,1:k)+repmat(p.ds/2*du(k,:)',1,k);
     ab=sum(-p.ds*u(1:k-1,:).*omega(1:k-1).^2,1)'-p.ds/2*u(k,:)'*omega(k)^2;
     A=zeros(1,n); A(1:k)=1;
     M=M+p.mass(k)*(J'*J)+p.inertia_y(k)*(A'*A);
     bias=bias+p.mass(k)*J'*ab; gravity=gravity+p.mass(k)*J'*[p.gravity(1);p.gravity(3)];
   end
   nt=numel(p.angles); lengths=zeros(nt,1); Jlength=zeros(nt,n);
   for t=1:nt
     for k=1:n
       dr=squeeze(routes(t,k+1,:)-routes(t,k,:)); len=norm(dr); lengths(t)=lengths(t)+len;
       Jlength(t,:)=Jlength(t,:)+dr([1,3])'/max(len,eps)*(Jroutes(:,:,k+1,t)-Jroutes(:,:,k,t));
     end
   end
   demand=p.kp*(lengths-cmd); tension=min(p.fmax,max(0,demand)); drive=-Jlength'*tension;
   spring=-p.stiffness(:).*(q-p.natural(:)); damping=-p.damping(:).*v;
   gap=zeros(n,1); normal=zeros(n,1); contact=zeros(n,1);
   for k=1:n
     gap(k)=min(points(k:k+1,2))-p.body_radius-p.floor_z;
     % Two endpoint quadrature avoids discontinuous switching of the entire
     % segment force between endpoints when an almost horizontal link rocks.
     for j=k:k+1
       penetration=p.floor_z+p.body_radius-points(j,2);
       if penetration>0
         J=Jpoints(:,:,j);weight=min(1,penetration/1e-4);
         f=.5*max(0,5000*penetration-5*weight*J(2,:)*v);
         normal(k)=normal(k)+f;contact=contact+J(2,:)'*f;
       end
     end
   end
   acc=M\(drive+spring+damping+gravity+contact-bias);
   a=struct('points',points,'routes',routes,'lengths',lengths,'Jlength',Jlength,'demand',demand,'tension',tension, ...
     'drive',drive,'spring',spring,'damping',damping,'contact',contact,'normal',normal,'gap',gap);
 end
end

function [tip,J]=pcc(L,b)
u=b(1);v=b(2);t=norm(b);
if t<1e-4
 a=1-t^2/6+t^4/120-t^6/5040;c=.5-t^2/24+t^4/720-t^6/40320;
 da=-1/3+t^2/30-t^4/840;dc=-1/12+t^2/180-t^4/6720;
else
 a=sin(t)/t;c=2*sin(t/2)^2/t^2;da=(t*cos(t)-sin(t))/t^3;dc=(t*sin(t)-4*sin(t/2)^2)/t^4;
end
tip=L*[a;c*u;c*v];J=L*[da*u,da*v;c+dc*u*u,dc*u*v;dc*u*v,c+dc*v*v];
end
