function [objective,constraint,inspect,step] = sr_nmpc_callbacks(model,c)
% One evaluation cache shared by SQP objective/constraints; all math is local.
last=[]; cached=[];
objective=@obj;constraint=@con;inspect=@evaluate;step=@defect;

    function [f,g]=obj(z)
        e=evaluate(z);f=e.objective;g=e.gradient;
    end
    function [ci,ce,gi,ge]=con(z)
        e=evaluate(z);ci=[];ce=e.constraints;gi=[];ge=e.jacobian';
    end
    function e=evaluate(z)
        if isequal(z,last), e=cached;return;end
        n=c.n;nx=2*n;N=c.steps;H=c.horizon;m=c.m;nv=numel(z);
        X=reshape(z(1:nx*(N+1)),nx,N+1).*c.state_scale;
        U=reshape(z(nx*(N+1)+1:end),m,H).*c.input_scale;
        f=0;gx=zeros(size(X));gu=zeros(size(U));
        ce=zeros(nx*(N+1),1);A=sparse(nx*(N+1),nv);
        ce(1:nx)=(X(:,1)-c.measured)./c.state_scale;A(1:nx,1:nx)=eye(nx);
        motion=zeros(3,N);velocity=zeros(3,N);
        for k=1:N
            control=ceil(k/c.recipe.substeps);x=X(:,k);y=X(:,k+1);u=U(:,control);
            d=sr_derivatives(model,y(1:n),y(n+1:end),u,(y(n+1:end)-x(n+1:end))/c.h);
            rows=k*nx+(1:nx);previous=(k-1)*nx+(1:nx);following=k*nx+(1:nx);
            inputs=nx*(N+1)+(control-1)*m+(1:m);
            ce(rows)=[(y(1:n)-x(1:n)-c.h*y(n+1:end))/10;d.residual/.001];
            Ap=[-eye(n)/10,zeros(n);zeros(n),-d.Rqdd/(c.h*.001)];
            An=[eye(n)/10,-c.h*eye(n)/10;d.Rq/.001,(d.Rqd+d.Rqdd/c.h)/.001];
            A(rows,previous)=Ap.*c.state_scale'; A(rows,following)=An.*c.state_scale';
            A(rows,inputs)=[zeros(n,m);d.Ru/.001].*c.input_scale';
            p=model.spec.mount_rotation*d.tip_position+model.spec.mount_position(:);
            v=model.spec.mount_rotation*d.tip_velocity;
            jp=model.spec.mount_rotation*d.tip_position_q;
            jv=model.spec.mount_rotation*[d.tip_velocity_q,d.tip_velocity_qd];
            position_error=(p-c.target)/c.position_scale;
            f=f+c.h*(c.recipe.tracking_weight*(position_error'*position_error)+c.recipe.velocity_weight*sum(y(n+1:end).^2));
            gx(1:n,k+1)=gx(1:n,k+1)+2*c.h*c.recipe.tracking_weight*jp'*position_error/c.position_scale;
            gx(n+1:end,k+1)=gx(n+1:end,k+1)+2*c.h*c.recipe.velocity_weight*y(n+1:end);
            holding=c.elapsed+k*c.h>=c.holding_start-1e-12;
            weight=c.h*c.recipe.holding_tip_speed_weight*holding/c.holding_normalization;
            if k==N
                f=f+c.recipe.terminal_weight*sum(position_error.^2)+c.recipe.terminal_velocity_weight*sum(y(n+1:end).^2);
                gx(1:n,k+1)=gx(1:n,k+1)+2*c.recipe.terminal_weight*jp'*position_error/c.position_scale;
                gx(n+1:end,k+1)=gx(n+1:end,k+1)+2*c.recipe.terminal_velocity_weight*y(n+1:end);
                weight=weight+c.recipe.terminal_tip_speed_weight;
            end
            f=f+weight*sum((v/c.recipe.tip_speed_scale_m_s).^2);
            gx(:,k+1)=gx(:,k+1)+2*weight*jv'*v/c.recipe.tip_speed_scale_m_s^2;
            motion(:,k)=p;velocity(:,k)=v;
        end
        for k=1:H
            if k==1, previous=c.previous;else,previous=U(:,k-1);end
            change=U(:,k)-previous;
            f=f+c.period*(c.recipe.tension_weight*sum(U(:,k).^2)+c.recipe.variation_weight*sum(change.^2));
            gu(:,k)=gu(:,k)+2*c.period*(c.recipe.tension_weight*U(:,k)+c.recipe.variation_weight*change);
            if k>1, gu(:,k-1)=gu(:,k-1)-2*c.period*c.recipe.variation_weight*change;end
        end
        gradient=[reshape(gx.*c.state_scale,[],1);reshape(gu.*c.input_scale,[],1)];
        e=struct('objective',f,'gradient',gradient,'constraints',ce,'jacobian',A, ...
            'states',X,'tensions',U,'tip_positions',motion,'tip_velocities',velocity);
        last=z;cached=e;
    end
    function [r,J]=defect(previous,following,tension)
        n=c.n;
        d=sr_derivatives(model,following(1:n),following(n+1:end),tension, ...
            (following(n+1:end)-previous(n+1:end))/c.h);
        r=[(following(1:n)-previous(1:n)-c.h*following(n+1:end))/10;d.residual/.001];
        J=[eye(n)/10,-c.h*eye(n)/10;d.Rq/.001,(d.Rqd+d.Rqdd/c.h)/.001];
    end
end
