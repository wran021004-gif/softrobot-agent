function [reachable, distance, max_reach, margin] = analyze_workspace(L, tx, ty, tz)
    % M0 geometric screening; M1 planning is separate in plan_pcc_reach.m.
    target = [tx; ty; tz];
    distance = norm(target);
    max_reach = L;
    margin = max_reach - distance;
    reachable = distance <= max_reach;
end
