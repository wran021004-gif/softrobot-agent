"""Publication figures from archived metrics only; no model loading or integration."""
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent
FIG = OUT / "FIGURES_PAPER"
DATA = OUT / "FIGURE_DATA"
FIG.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)
BUNDLE = json.loads((OUT / "evidence_bundle.json").read_text(encoding="utf-8"))
COL = dict(navy="#26384B", teal="#527F7B", slate="#70849A", ochre="#B08A59",
           green="#557663", brick="#A35D55", gray="#929BA4")
plt.rcParams.update({
    "font.family": "Arial", "font.size": 8.5, "axes.titlesize": 8.5,
    "axes.labelsize": 8.5, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "legend.fontsize": 8, "axes.linewidth": .6, "lines.linewidth": .8,
    "xtick.major.width": .5, "ytick.major.width": .5,
    "xtick.major.size": 3, "ytick.major.size": 3,
    "svg.fonttype": "none", "savefig.facecolor": "white", "figure.facecolor": "white",
})


def write_csv(name, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (DATA / name).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                        for k, v in r.items()})


def tidy(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(direction="out", pad=2)
    ax.set_axisbelow(True)


def save(fig, name):
    # Physical paper dimensions are retained; no bbox tightening/rescaling.
    fig.savefig(FIG / (name + ".png"), dpi=600)
    fig.savefig(FIG / (name + ".svg"))
    plt.close(fig)


finals = {p["condition"]: p for p in BUNDLE["independent_physical"] if p["node_id"] == "S5"}
conditions = ["M1_A", "M1_B", "M1_C", "M5"]
labels = ["M1 A", "M1 B", "M1 C", "M5"]
final_data = []


def recorded(condition, constraint, multiplier=1):
    p = finals[condition]
    cm = p["constraints"][constraint]
    final_data.append(dict(task_id="T07", run_id=p["run_id"], node_id="S5", condition=condition,
                           candidate_id=p["candidate_id"], metric=constraint,
                           original_value=cm["observed"], original_unit=cm["units"],
                           original_limit=cm["limit"], original_margin=cm["margin"],
                           display_multiplier=multiplier, display_value=cm["observed"] * multiplier,
                           display_limit=cm["limit"] * multiplier,
                           accepted=p["accepted"], evaluation_scope="independent_frozen_physical_replay",
                           source=p["result_source"],
                           source_pointer=f"/acceptance/constraint_margins/{constraint}"))
    return cm["observed"] * multiplier, cm["limit"] * multiplier


# Figure 1: three dimensions remain separate; each limit is from the original replay.
fig, axs = plt.subplots(1, 3, figsize=(7.16, 2.35),
                        gridspec_kw={"width_ratios": [1.15, 1.45, .57]})
fig.subplots_adjust(left=.071, right=.99, bottom=.235, top=.86, wspace=.47)
for ax in axs:
    tidy(ax)
x = np.arange(4)
positions = [recorded(c, "tool_position" if c == "M5" else "holding_position", 1000) for c in conditions]
axs[0].bar(x, [v for v, _ in positions], width=.55, color=COL["navy"], linewidth=0)
for i, (v, lim) in enumerate(positions):
    axs[0].plot([i-.36, i+.36], [lim, lim], color=COL["brick"], lw=.8, ls=(0, (3, 2)))
    axs[0].text(i, v+.36, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
axs[0].set(xticks=x, xticklabels=labels, ylabel="Position error (mm)", ylim=(0, 11.5),
           yticks=[0, 5, 10], title="(a) Position")

hold = [recorded(c, "holding_speed", 1000) for c in conditions[:3]]
tendon = [recorded(c, "geometric_tendon_speed", 1000) for c in conditions]
axs[1].bar(x[:3]-.17, [v for v, _ in hold], width=.3, color=COL["slate"], label="Hold speed")
axs[1].bar(x+.17, [v for v, _ in tendon], width=.3, color=COL["teal"], label="Tendon speed")
for i, (_, lim) in enumerate(hold):
    axs[1].plot([i-.34, i], [lim, lim], lw=.8, color=COL["brick"], ls=(0, (3, 2)))
for i, (_, lim) in enumerate(tendon):
    axs[1].plot([i, i+.34], [lim, lim], lw=.8, color=COL["brick"], ls=(0, (3, 2)))
axs[1].set(xticks=x, xticklabels=labels, ylabel=r"Speed (mm s$^{-1}$)", ylim=(0, 35),
           yticks=[0, 10, 20, 30], title="(b) Motion limits")
axs[1].legend(loc="upper center", bbox_to_anchor=(.5, -.225), ncol=2, frameon=False,
              handlelength=1.2, handletextpad=.4, columnspacing=.9, borderaxespad=0)
axs[1].text(3-.17, 3, "n/a", ha="center", fontsize=7.5, color=COL["gray"], rotation=90)

angle, angle_limit = recorded("M5", "tool_axis_direction", 180/math.pi)
axs[2].bar([0], [angle], width=.5, color=COL["navy"], linewidth=0)
axs[2].plot([-.38, .38], [angle_limit, angle_limit], color=COL["brick"], lw=.8, ls=(0, (3, 2)))
axs[2].text(0, angle+.13, f"{angle:.3f}", ha="center", va="bottom", fontsize=8)
axs[2].set(xticks=[0], xticklabels=["M5"], ylabel="Axis error (deg)", ylim=(0, 3.65),
           yticks=[0, 1, 2, 3], xlim=(-.65, .65), title="(c) Tool axis")
save(fig, "T07_final_physical_constraints")
write_csv("T07_final_physical_constraints_plotdata.csv", final_data)

# Figure 2: only A is compared across morphology trials. All points stay unconnected.
diag_by_name = {Path(d["original_json"]).name: d for d in BUNDLE["mathematical_diagnostics"]}
design_defs = [
    ("M1_A_SHARED_NATIVE_REFINED.json", "Ellipse\n14.1 mm", "S1"),
    ("ISOTROPIC_ROOT_A_NATIVE.json", "Circle\n14.1 mm", "S2"),
    ("ROOT_FULL_GRID_A_NATIVE.json", "Root\n+1 mm", "S3"),
    ("DISTRIBUTED_REACH_A_NATIVE.json", "Both\nlonger", "S4"),
    ("MINIMUM_RADIUS_ROOT_A_NATIVE.json", "Circle\n14.0 mm", "S5"),
]
control_defs = [
    ("MINIMUM_RADIUS_ROOT_M1_C_NATIVE.json", "Historical\ninitialization", "S5"),
    ("CURRENT_C_FROM_A_NATIVE.json", "A-seeded\nreoptimization", "S5"),
]
diagnostic_data = []


def diagvalue(name, node, group):
    d = diag_by_name[name]
    q = next(v for v in d["quantities"] if v["name"] == "best_signed_maximum_excess")
    diagnostic_data.append(dict(task_id="T07", run_id=BUNDLE["selected_run_id"],
                                panel_group=group, node_id=node, condition=d["condition"],
                                candidate_id=d["candidate_id"], metric=q["name"],
                                original_value=q["value"], original_unit=q["unit"],
                                display_value_percent=100*q["value"], limit_percent=0,
                                source=d["store_source"], source_json=d["original_json"],
                                source_pointer=q["source_pointer"],
                                evaluation_scope="finite_native_diagnostic_NOT_independent_acceptance",
                                task_acceptance=d["task_acceptance"], solver=d["solver"],
                                control_schedule_settings=d.get("control_schedule_settings", {}),
                                comparison_note="Same original condition within each panel; control initialization, resolution and budget vary. Discrete trials, not a convergence curve or isolated causal ablation."))
    return 100*q["value"]


fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.5), gridspec_kw={"width_ratios": [1.9, 1]})
fig.subplots_adjust(left=.085, right=.985, bottom=.3, top=.865, wspace=.34)
for ax in axs:
    tidy(ax)
    ax.axhline(0, lw=.7, color=COL["gray"], ls=(0, (3, 2)))
    ax.set_ylabel("Native maximum excess (%)")

y = [diagvalue(name, node, "morphology_trials_A") for name, label, node in design_defs]
for i, val in enumerate(y):
    axs[0].scatter(i, val, s=25, marker="o", zorder=3,
                   color=COL["green"] if val < 0 else COL["brick"])
    axs[0].annotate(f"{val:.2f}", (i, val), xytext=(0, 5) if val >= 0 else (-7, 0),
                    textcoords="offset points", ha="center" if val >= 0 else "right",
                    va="bottom" if val >= 0 else "center", fontsize=8)
axs[0].set(xticks=np.arange(len(design_defs)), xticklabels=[d[1] for d in design_defs],
           ylim=(-2.3, 12.8), yticks=[0, 5, 10], xlim=(-.45, 4.45),
           title="(a) Shared-morphology trials: condition A")

y = [diagvalue(name, node, "control_initialization_C") for name, label, node in control_defs]
for i, val in enumerate(y):
    axs[1].scatter(i, val, s=28, marker="D", zorder=3,
                   color=COL["green"] if val < 0 else COL["brick"])
    axs[1].annotate(f"{val:.2f}", (i, val), xytext=(0, 5) if val >= 0 else (-7, 0),
                    textcoords="offset points", ha="center" if val >= 0 else "right",
                    va="bottom" if val >= 0 else "center", fontsize=8)
axs[1].set(xticks=[0, 1], xticklabels=[d[1] for d in control_defs],
           ylim=(-2.3, 6.3), yticks=[0, 2, 4, 6], xlim=(-.45, 1.45),
           title="(b) Final hardware: condition C")
save(fig, "T07_evidence_driven_research")
write_csv("T07_evidence_driven_research_plotdata.csv", diagnostic_data)

# Structural parameters are exact descriptive data, not new derived mechanics.
structure_rows = []
for node in ["S0", "S1", "S2", "S3", "S4", "S5"]:
    st = BUNDLE["structures"][node]
    p = st["parameters"]
    structure_rows.append(dict(task_id="T07", run_id=BUNDLE["selected_run_id"], node_id=node,
                               candidate_id=st["candidate_id"], segment_lengths_m=p["segment_lengths_m"],
                               young_pa=p["young_pa"], root_sections=p["segment_sections"][0],
                               tail_sections=p["segment_sections"][1], routing_radii_m=p["routing_radii_m"],
                               tendon_count=p["tendon_count"], actuator_count=p["actuator_count"],
                               original_candidate_source=st["candidate_store_source"],
                               original_candidate_json=st["candidate_json"], original_xml=st["original_xml"]))
write_csv("T07_structural_parameters.csv", structure_rows)

provenance = {
    "task_id": "T07", "run_id": BUNDLE["selected_run_id"],
    "actor": BUNDLE["actor"], "actor_note": BUNDLE["actual_executor_note"],
    "generator": str(Path(__file__)),
    "command": r'C:\Users\gugugaga\miniconda3\envs\softagent\python.exe D:\softrobot-agent\runs\multitask-paper-data-20261118\T07\plot_t07_paper.py',
    "input": str(OUT / "evidence_bundle.json"),
    "physical_sources": {c: finals[c]["result_source"] for c in conditions},
    "diagnostic_sources": [r["source"] for r in diagnostic_data],
    "style": {"figure_width_in": 7.16, "font": "Arial", "normal_label_pt": 8.5,
              "colors": COL, "png_dpi": 600, "svg_text_as_paths": False},
    "transformations": ["m to mm: multiply 1000", "m/s to mm/s: multiply 1000",
                        "rad to degree: multiply 180/pi", "dimensionless excess to percent: multiply 100"],
    "plot_scope": ["No new physics, mathematical search or numerical integration.",
                   "Figure 1 uses independent full replay constraints; Figure 2 uses local diagnostic proxies only.",
                   "No line connects design trials; different conditions are kept in separate panels.",
                   "Different budgets/resolutions are preserved in the diagnostic plot-data CSV.",
                   "Recorded public hypothesis and editorial interpretation remain separate in agent_decision_timeline.csv."],
    "figures": ["T07_final_physical_constraints", "T07_evidence_driven_research"],
}
(DATA / "SOURCE_PROVENANCE.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")

table = r"""% Generated exclusively from archived independent physical constraints.
% Run: codex-expert-T07-20261113. Requires booktabs.
\begin{tabular}{lrrrrl}
\toprule
Condition & Position (mm) & Hold speed (mm/s) & Tendon speed (mm/s) & Axis (deg) & Status \\
\midrule
"""
for c, label in zip(conditions, labels):
    p = finals[c]
    pos = p["constraints"]["tool_position" if c == "M5" else "holding_position"]["observed"] * 1000
    hold = "--" if c == "M5" else f'{p["constraints"]["holding_speed"]["observed"]*1000:.3f}'
    tendon = p["constraints"]["geometric_tendon_speed"]["observed"]*1000
    axis = f"{angle:.3f}" if c == "M5" else "--"
    table += f"{label} & {pos:.3f} & {hold} & {tendon:.3f} & {axis} & PASS \\\\\n"
table += r"""\bottomrule
\end{tabular}
% Position: maximum holding error for M1 A/B/C; maximum tool-position error for M5.
% Original limits: reach position 10 mm; hold speed 30 mm/s;
% geometric tendon speed 25 mm/s; M5 position 8 mm; M5 axis 3 deg.
% Missing measurements are shown as --, not zero.
"""
(FIG / "TABLE_T07_FINAL.tex").write_text(table, encoding="utf-8")
print(json.dumps({"figures": provenance["figures"], "physical_plot_rows": len(final_data),
                  "diagnostic_plot_rows": len(diagnostic_data), "output": str(FIG)}))
