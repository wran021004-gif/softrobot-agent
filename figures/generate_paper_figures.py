#!/usr/bin/env python3
"""Generate quantitative publication figures from the normalized paper_handoff CSVs.

Run from the repository root:
    python figures/generate_paper_figures.py

Requires pandas, numpy, and matplotlib. Figure 3 is deliberately excluded: it
requires MuJoCo-native rendering of the actual PHS-2D-9S candidate XML models.
"""
from pathlib import Path
import math
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm, LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "paper_handoff"
DATA = HANDOFF / "figure_data"
SUPP = HANDOFF / "supplementary_data" / "architecture_metrics"
OUT = ROOT / "figures"

NAVY = "#26384B"
TEAL = "#527F7B"
SLATE = "#70849A"
OCHRE = "#B08A59"
GREEN = "#557663"
BRICK = "#A35D55"
GRAY = "#929BA4"
LIGHT = "#D9DEE2"
WHITE = "#FFFFFF"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.titlesize": 9.0,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.edgecolor": NAVY,
    "axes.linewidth": 0.7,
    "xtick.color": NAVY,
    "ytick.color": NAVY,
    "text.color": NAVY,
    "axes.labelcolor": NAVY,
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "savefig.facecolor": WHITE,
    "savefig.bbox": "tight",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

def read_csv(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Required handoff data not found: {p}")
    return pd.read_csv(p, encoding="utf-8-sig", keep_default_na=False)

def numeric(series):
    return pd.to_numeric(series.replace({"UNKNOWN": np.nan, "": np.nan, "None": np.nan}), errors="coerce")

def save(fig, stem):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.svg")
    plt.close(fig)
    print(f"wrote figures/{stem}.pdf and .svg")

def clean_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=LIGHT, linewidth=0.45, alpha=0.8)
    ax.set_axisbelow(True)

def fig02_task_portfolio():
    df = read_csv(DATA / "fig02_task_portfolio.csv")
    order = ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09", "T10", "PHS-2D-7S"]
    df["task_id"] = pd.Categorical(df["task_id"], order, ordered=True)
    df = df.sort_values("task_id")
    fig, ax = plt.subplots(figsize=(7.25, 4.35))
    ax.axis("off")
    rows = []
    for _, r in df.iterrows():
        morphology = f'{int(float(r["segment_count"]))}S / {int(float(r["tendon_count"]))}T / {int(float(r["actuator_count"]))}A'
        metric_id = str(r.get("metric_1_id", ""))
        val = numeric(pd.Series([r.get("metric_1_value", "UNKNOWN")])).iloc[0]
        unit = str(r.get("metric_1_unit", ""))
        if pd.notna(val):
            metric = f"{metric_id.replace('_', ' ')}: {val:.3g} {unit}"
        else:
            metric = metric_id.replace("_", " ")
        required = str(r["required_condition_count"])
        rows.append([str(r["task_id"]), str(r["canonical_name"]), str(r["task_family"]).replace("_", " "), morphology, required, metric])
    table = ax.table(
        cellText=rows,
        colLabels=["Task", "Canonical task", "Regime", "Morphology", "Req.", "Representative metric"],
        cellLoc="left", colLoc="left", loc="center",
        colWidths=[0.08, 0.27, 0.14, 0.15, 0.07, 0.29],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7.1)
    table.scale(1, 1.38)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(LIGHT)
        cell.set_linewidth(0.45)
        cell.set_facecolor(WHITE)
        if row == 0:
            cell.set_text_props(weight="bold", color=NAVY)
            cell.set_linewidth(0.8)
            cell.set_edgecolor(NAVY)
        elif col == 0:
            cell.set_text_props(weight="bold", color=NAVY)
        elif col == 2:
            cell.set_text_props(color=SLATE if "passive" in rows[row-1][2].lower() else TEAL)
    ax.set_title("Eleven FULL task cases and task-specific physical outcomes", loc="left", pad=10, fontweight="bold")
    fig.text(0.01, 0.015, "30 required conditions pass; two T10 frozen controls are separate. PHS-2D-9S is an independent study.", fontsize=7.2, color=GRAY)
    save(fig, "fig02_task_portfolio")

def fig04_gradient_validation():
    df = read_csv(DATA / "fig04_gradient_validation.csv")
    df["implicit"] = numeric(df["implicit_gradient"])
    df["fd"] = numeric(df["finite_difference_gradient"])
    df["err"] = numeric(df["relative_error_percent"])
    metrics = list(df["metric"].drop_duplicates())
    colors = {"point_dx_m": NAVY, "tip_xy_m": TEAL, "tip_ratio": OCHRE}
    labels = {"point_dx_m": "Loaded-point displacement", "tip_xy_m": "Horizontal tip displacement", "tip_ratio": "Tip-to-point ratio"}
    fig = plt.figure(figsize=(7.1, 5.0))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.75], hspace=0.38, wspace=0.34)
    for i, metric in enumerate(metrics[:3]):
        ax = fig.add_subplot(gs[0, i])
        sub = df[df["metric"] == metric]
        x = sub["implicit"].to_numpy(float)
        y = sub["fd"].to_numpy(float)
        ax.scatter(x, y, s=25, color=colors.get(metric, NAVY), edgecolor=WHITE, linewidth=0.45, zorder=3)
        lo = min(np.nanmin(x), np.nanmin(y))
        hi = max(np.nanmax(x), np.nanmax(y))
        pad = max((hi-lo)*0.08, 1e-6)
        ax.plot([lo-pad, hi+pad], [lo-pad, hi+pad], color=GRAY, linestyle="--", linewidth=0.9)
        ax.set_xlim(lo-pad, hi+pad)
        ax.set_ylim(lo-pad, hi+pad)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(labels.get(metric, metric.replace("_", " ")), fontsize=8)
        ax.set_xlabel("Implicit derivative")
        ax.set_ylabel("Finite-difference derivative")
        ax.grid(color=LIGHT, linewidth=0.4)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    ax = fig.add_subplot(gs[1, :])
    df = df.sort_values(["material_s", "force_n", "metric"])
    x = np.arange(len(df))
    for metric in metrics[:3]:
        sub = df[df["metric"] == metric]
        idx = [df.index.get_loc(i) for i in sub.index]
        ax.scatter(idx, sub["err"], s=23, color=colors.get(metric, NAVY), label=labels.get(metric, metric), edgecolor=WHITE, linewidth=0.4)
    ax.axhline(0.1191, color=BRICK, linestyle=":", linewidth=0.9, label="Maximum observed: 0.1191%")
    ax.set_ylabel("Relative discrepancy (%)")
    ax.set_xlabel("Six signed-loading branches × three metrics")
    ax.set_xticks([])
    ax.grid(axis="y", color=LIGHT, linewidth=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    fig.suptitle("Local passive-equilibrium sensitivity consistency", x=0.02, ha="left", fontweight="bold")
    save(fig, "fig04_gradient_validation")

def fig05_research_trajectories():
    df = read_csv(DATA / "fig05_research_trajectories.csv")
    df["seq"] = numeric(df["sequence"])
    specs = [
        ("PHS-2D-9S", df[df["study_id"].astype(str).str.contains("PHS-2D-9S", na=False)].sort_values("seq").head(3)),
        ("T04", df[df["task_id"] == "T04"].sort_values("seq").loc[lambda x: x["node_id"].isin(["T04-010", "T04-216", "T04-220"])].sort_values("seq")),
        ("T07", df[df["task_id"] == "T07"].sort_values("seq").loc[lambda x: x["node_id"].isin(["T07-060", "T07-074", "T07-106"])].sort_values("seq")),
        ("T10", df[df["task_id"] == "T10"].sort_values("seq").loc[lambda x: x["node_id"].isin(["T10-017", "T10-210", "T10-222"])].sort_values("seq")),
    ]
    fig, axes = plt.subplots(4, 1, figsize=(7.2, 5.8), sharex=False)
    for ax, (task, sub) in zip(axes, specs):
        if sub.empty:
            ax.text(0.02, 0.5, f"{task}: selected research nodes not found in handoff", transform=ax.transAxes, va="center")
            ax.set_axis_off()
            continue
        xs = np.arange(len(sub))
        ax.plot(xs, np.zeros(len(xs)), color=LIGHT, linewidth=1.2, zorder=1)
        for x, (_, row) in zip(xs, sub.iterrows()):
            status = str(row.get("execution_status", ""))
            color = GREEN if status == "completed" else (BRICK if "fail" in status.lower() else OCHRE)
            ax.scatter([x], [0], s=45, color=color, edgecolor=WHITE, linewidth=0.6, zorder=3)
            node = str(row["node_id"])
            action = str(row.get("research_action", "")).replace("\n", " ")
            action = action[:78] + ("…" if len(action) > 78 else "")
            ax.annotate(f"{node}\n{action}", (x, 0), xytext=(0, 12 if x % 2 == 0 else -34),
                        textcoords="offset points", ha="center", va="bottom" if x % 2 == 0 else "top",
                        fontsize=6.5, color=NAVY,
                        arrowprops=dict(arrowstyle="-", color=GRAY, lw=0.45))
        ax.set_title(task, loc="left", fontsize=8, fontweight="bold")
        ax.set_ylim(-0.85, 0.85)
        ax.set_xlim(-0.5, len(sub)-0.5)
        ax.set_yticks([])
        ax.set_xticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    fig.suptitle("Evidence-guided research trajectories", x=0.02, ha="left", fontweight="bold")
    fig.text(0.02, 0.01, "Green: action completed; ochre: unresolved/diagnostic; red: failed. Intermediate diagnostics are not physical acceptance.", fontsize=6.8, color=GRAY)
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    save(fig, "fig05_research_trajectories")

def fig06_abc_comparison():
    df = read_csv(DATA / "fig06_abc_comparison.csv")
    tasks = ["T01","T02","T03","T04","T05","T06","T07","T08","T09","T10","PHS-2D-7S"]
    methods = ["A","B","C"]
    status_codes = {"PASS": 0, "VALID_FAILURE": 1, "INCOMPLETE": 2, "QUALIFICATION_FAILED": 3}
    status_colors = [GREEN, BRICK, GRAY, OCHRE]
    cmap = ListedColormap(status_colors)
    norm = BoundaryNorm([-0.5,0.5,1.5,2.5,3.5], cmap.N)
    mat = np.full((len(tasks), len(methods)), np.nan)
    labels = [["" for _ in methods] for _ in tasks]
    viol = np.full_like(mat, np.nan, dtype=float)
    for _, r in df.iterrows():
        ti = tasks.index(str(r["task_id"])) if str(r["task_id"]) in tasks else None
        mi = methods.index(str(r["method"])) if str(r["method"]) in methods else None
        if ti is None or mi is None:
            continue
        st = str(r["status"])
        if st in status_codes:
            mat[ti,mi] = status_codes[st]
        dev = str(r.get("protocol_deviation","")).lower() in ("true","1","yes")
        labels[ti][mi] = ("PASS" if st=="PASS" else st.replace("_","\n")) + ("†" if dev else "")
        vv = numeric(pd.Series([r.get("violation_fraction","UNKNOWN")])).iloc[0]
        if pd.notna(vv) and int(float(r.get("evaluated_conditions",0) or 0))>0:
            viol[ti,mi] = vv
    fig, (ax1, ax2) = plt.subplots(1,2,figsize=(7.2,4.6),gridspec_kw={"width_ratios":[1.0,1.0]})
    ax1.imshow(np.ma.masked_invalid(mat), cmap=cmap, norm=norm, aspect="auto")
    ax1.set_xticks(range(3), ["A\nLLM-only","B\nDirect tools","C\nFULL"])
    ax1.set_yticks(range(len(tasks)), tasks)
    ax1.set_title("(a) Evaluation status", loc="left", fontweight="bold")
    for i in range(len(tasks)):
        for j in range(3):
            if labels[i][j]:
                ax1.text(j,i,labels[i][j],ha="center",va="center",fontsize=6.2,color=WHITE if mat[i,j] in (0,1,3) else NAVY)
    ax1.set_xticks(np.arange(-.5,3,1), minor=True)
    ax1.set_yticks(np.arange(-.5,len(tasks),1), minor=True)
    ax1.grid(which="minor",color=WHITE,linewidth=1.2)
    ax1.tick_params(which="minor",bottom=False,left=False)
    cmap2 = LinearSegmentedColormap.from_list("muted_violation",[WHITE,"#D9C7A8",OCHRE,BRICK])
    im=ax2.imshow(np.ma.masked_invalid(viol), cmap=cmap2, vmin=0, vmax=max(0.5,np.nanmax(viol) if np.isfinite(viol).any() else 0.5), aspect="auto")
    ax2.set_xticks(range(3), ["A","B","C"])
    ax2.set_yticks(range(len(tasks)), tasks)
    ax2.set_title("(b) Fraction of evaluated constraints violated", loc="left", fontweight="bold")
    for i in range(len(tasks)):
        for j in range(3):
            if np.isfinite(viol[i,j]):
                ax2.text(j,i,f"{viol[i,j]:.2f}",ha="center",va="center",fontsize=7,color=NAVY)
            else:
                ax2.text(j,i,"—",ha="center",va="center",fontsize=8,color=GRAY)
    ax2.set_xticks(np.arange(-.5,3,1), minor=True)
    ax2.set_yticks(np.arange(-.5,len(tasks),1), minor=True)
    ax2.grid(which="minor",color=WHITE,linewidth=1.2)
    ax2.tick_params(which="minor",bottom=False,left=False)
    cb=fig.colorbar(im,ax=ax2,fraction=0.046,pad=0.04)
    cb.set_label("Violation fraction",fontsize=7)
    fig.suptitle("Eleven-task research-mode comparison",x=0.02,ha="left",fontweight="bold")
    fig.text(0.02,0.01,"† Protocol-deviant B variant. Dashes denote unavailable physical evaluation, not zero violation.",fontsize=6.8,color=GRAY)
    fig.tight_layout(rect=[0,0.04,1,0.95])
    save(fig,"fig06_abc_comparison")

def fig07_architecture_ablation():
    reporter=read_csv(DATA/"fig07_reporter_knowledge_skill.csv")
    pairs=reporter[reporter["panel"]=="A"].copy()
    pairs["off"]=numeric(pairs["score_off"])
    pairs["on"]=numeric(pairs["score_on"])
    ks5=read_csv(SUPP/"knowledge_skill_five_dimension.csv")
    ks5["score_num"]=numeric(ks5["score"])
    ks5["mean5"]=ks5["score_num"]
    grouped=ks5.groupby(["protocol_id","task_id","checkpoint_id","condition"],dropna=False)["mean5"].mean().reset_index()
    ks_supp=read_csv(SUPP/"knowledge_skill_supplement.csv")
    status_cols=[c for c in ks_supp.columns if c in ("task_id","checkpoint_id","condition","session_status")]
    if len(status_cols)==4:
        status=ks_supp[status_cols].drop_duplicates()
        grouped=grouped.merge(status,on=["task_id","checkpoint_id","condition"],how="left")
    else:
        grouped["session_status"]="completed"
    fig=plt.figure(figsize=(7.2,5.0))
    gs=fig.add_gridspec(2,2,height_ratios=[1.0,1.15],hspace=0.45,wspace=0.35)
    ax=fig.add_subplot(gs[0,:])
    for i,(_,r) in enumerate(pairs.iterrows()):
        ax.plot([i-0.10,i+0.10],[r["off"],r["on"]],color=GRAY,linewidth=0.8,zorder=1)
        ax.scatter(i-0.10,r["off"],color=GRAY,s=23,zorder=2)
        ax.scatter(i+0.10,r["on"],color=TEAL,s=23,zorder=2)
        ax.text(i,4.18,str(r["checkpoint_id"]),ha="center",fontsize=6.5)
    ax.set_xticks(range(len(pairs)),pairs["checkpoint_id"],rotation=0)
    ax.set_ylim(2.5,4.35)
    ax.set_ylabel("Five-dimensional mean score (0–4)")
    ax.set_title("(a) Reporter OFF/ON matched decisions",loc="left",fontweight="bold")
    ax.grid(axis="y",color=LIGHT,linewidth=0.4)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    orig=reporter[reporter["panel"]=="B"].copy()
    conditions=["K-S-","K+S-","K-S+","K+S+"]
    for ax,task in [(fig.add_subplot(gs[1,0]),"T04"),(fig.add_subplot(gs[1,1]),"T07")]:
        sub=orig[orig["task_id"]==task].set_index("condition").reindex(conditions)
        vals=[numeric(pd.Series([sub.loc[c,"experience_utilization"]])).iloc[0] if c in sub.index else np.nan for c in conditions]
        mat=np.array(vals,dtype=float).reshape(1,4)
        im=ax.imshow(np.ma.masked_invalid(mat),cmap=LinearSegmentedColormap.from_list("ks",[WHITE,"#B8C8C5",TEAL]),vmin=0,vmax=3,aspect="auto")
        ax.set_xticks(range(4),conditions)
        ax.set_yticks([])
        ax.set_title(f"(b) Original E1 utilization — {task}",loc="left",fontweight="bold")
        for j,v in enumerate(vals):
            ax.text(j,0,"—" if pd.isna(v) else f"{v:.0f}",ha="center",va="center",color=NAVY,fontsize=8)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.suptitle("Research architecture decision studies",x=0.02,ha="left",fontweight="bold")
    fig.text(0.02,0.01,"Original E1 utilization is 0/3/3/3 per task; the supplemental five-dimensional K/S profiles are reported by checkpoint in the supplement.",fontsize=6.8,color=GRAY)
    fig.tight_layout(rect=[0,0.04,1,0.95])
    save(fig,"fig07_architecture_ablation")

def fig08_context_comparison():
    df=read_csv(DATA/"fig08_context_comparison.csv")
    actual=df[df["actual_cumulative_input_tokens"].astype(str).str.upper()!="UNKNOWN"].copy()
    actual["tokens"]=numeric(actual["actual_cumulative_input_tokens"])
    cross=read_csv(SUPP/"context_cross_task.csv")
    cross["score"]=numeric(cross["blind_decision_quality"])
    cross["recall"]=numeric(cross["key_evidence_recall"])
    checkpoints=list(dict.fromkeys(cross["checkpoint_id"].tolist()))
    fig=plt.figure(figsize=(7.2,5.0))
    gs=fig.add_gridspec(2,2,height_ratios=[1.0,1.1],hspace=0.42,wspace=0.35)
    ax1=fig.add_subplot(gs[0,:])
    protocols=list(dict.fromkeys(actual["protocol_id"].tolist()))
    xbase=np.arange(len(protocols))
    for offset,cond,color in [(-0.13,"Flat",GRAY),(0.13,"Hierarchical",TEAL)]:
        vals=[]
        for p in protocols:
            row=actual[(actual["protocol_id"]==p)&(actual["condition"]==cond)]
            vals.append(float(row["tokens"].iloc[0]) if not row.empty and pd.notna(row["tokens"].iloc[0]) else np.nan)
        ax1.bar(xbase+offset,vals,width=0.24,color=color,label=cond)
        for x,v in zip(xbase+offset,vals):
            if np.isfinite(v): ax1.text(x,v*1.03,f"{v/1000:.0f}k",ha="center",fontsize=7)
    ax1.set_yscale("log")
    ax1.set_xticks(xbase,protocols)
    ax1.set_ylabel("Provider-reported cumulative input tokens (log)")
    ax1.set_title("(a) Historical actual-usage pairs (different accounting scopes)",loc="left",fontweight="bold")
    ax1.legend(frameon=False,ncol=2)
    ax1.grid(axis="y",color=LIGHT,linewidth=0.4)
    ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False)
    for ax,metric,title in [
        (fig.add_subplot(gs[1,0]),"score","(b) Blind decision quality"),
        (fig.add_subplot(gs[1,1]),"recall","(c) Key-evidence recall")
    ]:
        for cond,color,marker in [("Flat",GRAY,"o"),("Hierarchical",TEAL,"s")]:
            sub=cross[cross["condition"]==cond].set_index("checkpoint_id").reindex(checkpoints)
            vals=sub[metric].to_numpy(float)
            ax.plot(range(len(checkpoints)),vals,color=color,marker=marker,linewidth=0.8,markersize=4,label=cond)
        ax.set_xticks(range(len(checkpoints)),[x.replace("-","\\n",1) for x in checkpoints],fontsize=6.5)
        ax.set_ylim(-0.08,4.25 if metric=="score" else 1.08)
        ax.set_ylabel("Score (0–4)" if metric=="score" else "Recall (0–1)")
        ax.set_title(title,loc="left",fontweight="bold")
        ax.grid(axis="y",color=LIGHT,linewidth=0.4)
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.legend(frameon=False,fontsize=6.5)
    fig.suptitle("Hierarchical context: measured usage and cross-task evidence",x=0.02,ha="left",fontweight="bold")
    fig.text(0.02,0.01,"Six new cross-task pairs have UNKNOWN Provider usage; T08 Flat is a budget-exhausted session and remains missing.",fontsize=6.8,color=GRAY)
    fig.tight_layout(rect=[0,0.04,1,0.95])
    save(fig,"fig08_context_comparison")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig02_task_portfolio()
    fig04_gradient_validation()
    fig05_research_trajectories()
    fig06_abc_comparison()
    fig07_architecture_ablation()
    fig08_context_comparison()
    print("Figure 3 requires separate MuJoCo-native candidate rendering; do not replace it with a schematic.")

if __name__ == "__main__":
    main()
