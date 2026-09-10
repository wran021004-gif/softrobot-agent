function [reachable, distance, max_reach, margin] = analyze_workspace(L, tx, ty, tz)
    % MVP geometric reachability check.
    % TODO: replace with PCC/PCS workspace analysis.
    target = [tx; ty; tz];
    distance = norm(target);
    max_reach = L;
    margin = max_reach - distance;
    reachable = distance <= max_reach;
end
