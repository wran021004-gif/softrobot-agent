function [routes,lengths,Jlength]=tf_routes(g,tendons)
% Each tendon consumes only its explicitly ordered points. Tension virtual
% work is -Jlength' * T, including reactions on all intermediate guides.
nt=numel(tendons); n=size(g.base.J,2);
routes=cell(nt,1); lengths=zeros(nt,1); Jlength=zeros(nt,n);
for k=1:nt
    points=tendons(k).points; xyz=zeros(numel(points),3);
    [prev,Jprev]=tf_point(g,points(1)); xyz(1,:)=prev';
    for j=2:numel(points)
        [current,J]=tf_point(g,points(j)); xyz(j,:)=current';
        delta=current-prev; len=norm(delta);
        lengths(k)=lengths(k)+len;
        Jlength(k,:)=Jlength(k,:)+(delta'/len)*(J-Jprev);
        prev=current; Jprev=J;
    end
    routes{k}=xyz;
end
end
