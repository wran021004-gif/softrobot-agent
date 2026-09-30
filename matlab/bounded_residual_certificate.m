function out = bounded_residual_certificate(P,base,target,lower,upper,limit,atol)
% Bounded least-squares candidate plus an independently checkable box dual bound.
b=target(:)-base(:); lower=lower(:); upper=upper(:);
scale=max([norm(b,inf),max(abs(P),[],'all')*max(max(abs(lower),abs(upper))),limit,atol,realmin]);
options=optimoptions('lsqlin','Display','off','OptimalityTolerance',1e-12,'StepTolerance',1e-14);
[z,~,~,exitflag,output]=lsqlin(P/scale,b/scale,[],[],[],[],lower,upper,[],options);
r=P*z-b; candidate=norm(r);
if candidate>0 && all(isfinite(r))
    v=r/candidate; coefficients=P'*v;
    terms=min(coefficients.*lower,coefficients.*upper);
    raw=-v'*b+sum(terms);
else
    v=zeros(size(b)); coefficients=zeros(size(lower)); terms=zeros(size(lower)); raw=0;
end
bound=max(0,raw);
allowance=atol+16*eps*(1+abs(v'*b)+sum(abs(terms)));
out.z=z; out.candidate_residual=candidate; out.residual_vector=r;
out.solver_success=exitflag>0; out.exitflag=exitflag; out.iterations=output.iterations;
out.residual_scale=scale; out.direction=v; out.direction_norm=norm(v);
out.matrix_transpose_direction=coefficients; out.box_min_terms=terms;
out.lower_bound=bound; out.raw_bound=raw; out.numerical_allowance=allowance;
out.margin_over_limit=bound-limit-allowance; out.certified_infeasible=out.margin_over_limit>0;
end
