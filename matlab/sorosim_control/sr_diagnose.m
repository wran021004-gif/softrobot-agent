function out=sr_diagnose(model,r)
% Bounded S3.5 probes, using the production model and callbacks unchanged.
assert(model.S.ndof==12,'S35_PROBE_REQUIRES_ARCHIVED_12_COORDINATE_CANDIDATE');
q=r.x(1:12);v=r.x(13:24);u=r.u;a=r.a;
switch r.kind
    case 'geometry_mechanics'
        out.routing=sr_routing(model,q,u,false,[],r.samples);
        out.dynamics=sr_dynamics(model,q,v,u,zeros(12,1));
        % Additive kinetic-energy restriction, using existing upstream samples.
        J=model.S.Jacobian(model.T*q)*model.T; terms=cell(model.S.N,1);
        for k=1:model.S.N
            c=model.spec.links{k}; M=zeros(12); G=zeros(12,1);
            g=model.S.FwdKinematics(model.T*q);
            for j=1:numel(model.node_indices{k})
                ix=model.node_indices{k}(j); B=J((ix-1)*6+(1:6),:);
                R=g((ix-1)*4+(1:3),1:3);
                if strcmp(c.kind,'flexible_segment')
                    W=squeeze(c.mass(j,:,:))*c.weights(j);
                else
                    W=blkdiag(c.inertia,c.mass_kg*eye(3));
                end
                M=M+B'*W*B;
                G=G+B(4:6,:)'*W(4:6,4:6)*R'*model.spec.gravity(:);
            end
            terms{k}=struct('link',c.id,'kind',c.kind,'mass',M,'gravity',G);
        end
        out.link_terms=terms;
    case 'kernels'
        t=tic;first=sr_derivatives(model,q,v,u,a);out.first_s=toc(t);
        times=zeros(3,4);
        for j=1:3
            t=tic;d=sr_derivatives(model,q,v,u,a);times(j,:)=[toc(t),d.routing_s,d.dynamics_s,0];
            t=tic;sr_routing(model,q,u,false);times(j,4)=toc(t);
        end
        out.warmed_s=times;out.base=first;
        profile clear;profile on;
        t=tic;sr_derivatives(model,q,v,u,a);out.profiled_s=toc(t);
        profile off;p=profile('info');
        table=p.FunctionTable;rows=struct('name',{},'calls',{},'total_s',{},'children',{},'lines',{});
        for j=1:numel(table)
            rows(j)=struct('name',table(j).FunctionName,'calls',table(j).NumCalls, ...
                'total_s',table(j).TotalTime,'children',table(j).Children,'lines',table(j).ExecutedLines);
        end
        out.profiler=rows;
    case 'callbacks'
        c=r.context;c.profile=false;z=r.z(:);
        [obj,con,inspect]=sr_nmpc_callbacks(model,c);
        inspect(z);t=tic;baseline=inspect(z+1e-8);out.uninstrumented_s=toc(t);
        c.profile=true;[obj,con,inspect,~,stats]=sr_nmpc_callbacks(model,c);
        t=tic;obj(z);con(z);inspect(z);obj(z+1e-8);con(z+1e-8);obj(z);out.profiled_s=toc(t);
        out.stats=stats();e=inspect(z+1e-8);
        out.equivalence=max(abs([e.objective-baseline.objective;e.gradient-baseline.gradient; ...
            e.constraints-baseline.constraints;full(e.jacobian(:)-baseline.jacobian(:))]));
        s=svd(full(e.jacobian));out.jacobian_singular_extrema=[s(1),s(end)];
        out.jacobian_condition=s(1)/s(end);
        out.objective=e.objective;out.violation=norm(e.constraints,inf);
        direction=sin((1:numel(z))');direction=direction/norm(direction);h=1e-6;
        ep=inspect(z+1e-8+h*direction);em=inspect(z+1e-8-h*direction);
        out.directional_absolute=[abs((ep.objective-em.objective)/(2*h)-e.gradient'*direction), ...
            norm((ep.constraints-em.constraints)/(2*h)-e.jacobian*direction,inf)];
        out.directional_relative=out.directional_absolute./max(1e-12, ...
            [abs((ep.objective-em.objective)/(2*h)),norm((ep.constraints-em.constraints)/(2*h),inf)]);
    case 'integrate'
        opts=optimoptions('fsolve','Display','off','SpecifyObjectiveGradient',true, ...
            'FunctionTolerance',1e-20,'StepTolerance',1e-12,'OptimalityTolerance',1e-12, ...
            'MaxIterations',60,'MaxFunctionEvaluations',200);
        rows=cell(numel(r.refinements),1);
        for j=1:numel(rows)
            count=r.refinements(j);h=r.period_s/count;x=r.x(:);trace=zeros(count,4);t=tic;
            for k=1:count
                previous=x;
                [x,res,flag,info]=fsolve(@equation,previous,opts);
                trace(k,:)=[norm(res,inf),flag,info.iterations,info.funcCount];
                assert(norm(res,inf)<1e-9 && all(isfinite(x)),'DIAGNOSTIC_ROOT_FAILED');
            end
            wall=toc(t);d=sr_dynamics(model,x(1:12),x(13:24),u,zeros(12,1),[],false);
            rows{j}=struct('substeps',count,'x',x,'position', ...
                model.spec.mount_rotation*d.tip_position+model.spec.mount_position(:), ...
                'velocity',model.spec.mount_rotation*d.tip_velocity,'wall_s',wall,'roots',trace, ...
                'final_force_residual_nm2',norm(res(13:24),inf)*.001);
        end
        out.refinements=rows;
    case 'serialization'
        timings=zeros(3,2);
        for j=1:3
            t=tic;encoded=jsonencode(r.sample);timings(j,1)=toc(t);
            t=tic;jsondecode(encoded);timings(j,2)=toc(t);
        end
        out.encode_decode_s=timings;out.characters=numel(encoded);
    otherwise
        error('UNKNOWN_DIAGNOSTIC');
end

    function [res,J]=equation(next)
        d=sr_derivatives(model,next(1:12),next(13:24),u,(next(13:24)-previous(13:24))/h);
        res=[(next(1:12)-previous(1:12)-h*next(13:24))/10;d.residual/.001];
        J=[eye(12)/10,-h*eye(12)/10;d.Rq/.001,(d.Rqd+d.Rqdd/h)/.001];
    end
end
