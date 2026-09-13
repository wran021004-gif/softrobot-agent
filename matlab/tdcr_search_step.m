function out=tdcr_search_step(state_json)
% Base MATLAB bounded coordinate pattern search. Python persists every trial.
s=jsondecode(state_json); x=s.best(:)'; d=numel(x); k=s.iteration;
axis=mod(floor(k/2),d)+1; direction=1-2*mod(k,2);
scale=s.step; x(axis)=min(1,max(0,x(axis)+direction*scale));
out=jsonencode(struct('x',x,'axis',axis,'direction',direction,'algorithm','bounded_coordinate_pattern_local_v1'));
end
