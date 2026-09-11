# reach_window：待 Human 确认的正式 benchmark 字段

全部为 **PROPOSED_NOT_APPROVED**。以下数值来自开发 fixture，只是候选；确认后才可
按 proposals/benchmark/reach_window_v1/README.md 升格。

| 待确认字段 | 候选值 / 待决语义 |
| --- | --- |
| 1. Window plane / x position | y-z 平面、法向 +x；x=0.18 m。当前只实现该方向。 |
| 2. Window centre | [0.18, 0, 0.06] m。 |
| 3. Aperture width | 0.12 m。 |
| 4. Aperture height | 0.18 m。 |
| 5. Wall/frame thickness | 沿 x 为 0.02 m。 |
| 6. Outer extent | frame_width=0.15 m；总外宽 0.42 m、外高 0.48 m。 |
| 7. Target position | [0.25, 0, 0.15] m。 |
| 8. Final target tolerance | 最终 tip 欧氏误差 ≤ 0.01 m。 |
| 9. Coordinate/environment convention | SI；固定 world-origin base；直臂 +x，截面 y-z；是否复用 -9.81 m/s² 重力和 z=-0.02 m 地板。 |
| 10. Initial robot configuration | 需要明确获批的状态表示和数值。当前 zero-qpos 直臂已穿窗；本轮不实现新的初态生成器。 |
| 11. Entire initial body before wall? | 建议 before_window：包含半径的所有 capsule 严格位于近墙面之前；或由 Human 选择 unrestricted。 |
| 12. Whole robot path through aperture? | 建议检查最终连通中心线在整个 wall slab 内都通过按半径收缩的孔洞；需确认是否还要求时间轨迹上的插入事件。当前不是连续 swept-path 证明。 |
| 13. Any window-frame contact allowed? | 建议禁止任意采样时刻（含初态）的非正距离窗口接触；地板接触不计入窗口门控。 |
| 14. If contact allowed, threshold/semantics? | 未指定；需 Human 定义距离/力/持续时间等判据及单位，允许接触模式尚未实现。 |
| 15. Final entire body region | 建议 unrestricted（保留最终 aperture 条件）；是否另有限制由 Human 决定。固定基座本身不能移动到墙后。 |
| 16. Benchmark randomization | 建议 none；V1 固定场景。 |
