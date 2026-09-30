function out = analyze_linear_model(A,B,C,D,drift,dt,windows,omega,margin)
% Trusted structured numeric entry point. Never changes A for stability.
sys = ss(A,B,C,D);
p = pole(sys); [wn,zeta] = damp(sys);
ds = c2d(sys,dt,'zoh');
n = size(A,1); m = size(B,2);
aug = zeros(n+m+1); aug(1:n,1:n)=A;
aug(1:n,n+1:n+m)=B; aug(1:n,end)=drift(:);
E=expm(dt*aug);
out.A_d=ds.A; out.B_d=ds.B; out.drift_d=E(1:n,end)';
out.poles=[real(p),imag(p)]; out.natural_frequency_rad_s=wn;
out.damping_ratio=zeta;
H=freqresp(sys,omega); sv=sigma(sys,omega);
out.frequency_real=real(H); out.frequency_imag=imag(H);
out.singular_values=sv';
out.continuous_gramians=cell(1,numel(windows));
out.held_gramians=cell(1,numel(windows));
out.gramian_algorithms=cell(1,numel(windows));
for k=1:numel(windows)
    T=windows(k);
    if all(real(p)<-margin)
        W=gram(sys,'c',gramOptions('TimeIntervals',[0 T]));
        out.gramian_algorithms{k}='Control System Toolbox gram with gramOptions TimeIntervals';
    else
        halves=max(0,ceil(log2(max(1,norm(A,1)*T/.5)))); h=T/2^halves;
        V=expm(h*[A B*B';zeros(n) -A']); F=V(1:n,1:n);
        W=V(1:n,n+1:end)*F';
        for j=1:halves
            W=W+F*W*F'; F=F*F;
        end
        out.gramian_algorithms{k}='scaled Van Loan expm and doubling; unstable or marginal model';
    end
    out.continuous_gramians{k}=(W+W')/2;
    Wh=zeros(n);
    for j=1:round(T/dt)
        Wh=ds.A*Wh*ds.A'+ds.B*ds.B'/dt;
    end
    out.held_gramians{k}=(Wh+Wh')/2;
end
end
