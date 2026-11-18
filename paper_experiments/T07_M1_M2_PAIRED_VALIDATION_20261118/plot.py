"""Render the T07 audit figure from the condition-level CSV."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
M1 = "#167876"
M2 = "#9F492D"
INK = "#263444"
GRAY = "#687583"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=HERE)
    args = parser.parse_args()
    with (args.directory / "paired_results.csv").open(encoding="utf-8", newline="") as stream:
        pairs = list(csv.DictReader(stream))
    plt.rcParams.update({"font.size": 8, "axes.labelcolor": INK, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "svg.hashsalt": "t07-pairs"})
    fig, (paired, conditions) = plt.subplots(1, 2, figsize=(7.1, 3.1), width_ratios=[1, 1.25],
                                             gridspec_kw={"wspace": 0.40})
    fig.subplots_adjust(bottom=.28, top=.84, left=.11, right=.97)
    paired.set_title("a   Matched structure contrast", loc="left", fontweight="bold")
    conditions.set_title("b   Original required conditions", loc="left", fontweight="bold")
    for mode, color, marker in (("m1", M1, "o"), ("m2", M2, "D")):
        for row in pairs:
            left, right = row[f"{mode}_d0_gmax"], row[f"{mode}_d1_gmax"]
            if left and right:
                paired.plot([0, 1], [float(left), float(right)], marker=marker, color=color, lw=1.6)
                paired.annotate(f'{row["condition"].replace("_", " ")} · Δ {float(row["delta_" + mode]):+.3f}',
                    (1, float(right)), xytext=(0, 10), textcoords="offset points", ha="center", color=color)
    for axis in (paired, conditions):
        axis.grid(alpha=.18)
        axis.set_axisbelow(True)
    paired.axhline(0, color=GRAY, ls="--", lw=.8)
    paired.set(xlim=(-.28, 1.32), ylim=(-.26, 2.72), ylabel="Signed maximum violation, $g_{max}$",
               xticks=[0, 1], xticklabels=["Baseline $d_0$", "Modified $d_1$"])
    if not any(row["delta_m2"] for row in pairs):
        paired.text(.5, .48, "No reliable M2 pair", ha="center", color=GRAY, transform=paired.transAxes)
    for pos, row in enumerate(pairs):
        for mode, color, marker, offset in (("m1", M1, "o", -.12), ("m2", M2, "D", .12)):
            values = [row[f"{mode}_{arm}_gmax"] for arm in ("d0", "d1")]
            if all(values):
                conditions.plot([float(value) for value in values], [pos + offset] * 2, color=color, lw=1.2)
            for arm, value in enumerate(values):
                if value:
                    conditions.scatter(float(value), pos + offset, color=color if arm else "white",
                                       edgecolors=color, marker=marker, zorder=4, s=26, linewidths=1)
    conditions.axvline(0, color=GRAY, ls="--", lw=.8)
    conditions.set(xlim=(-.18, 2.32), xlabel="Signed maximum violation, $g_{max}$", yticks=range(len(pairs)),
                   yticklabels=[row["condition"].replace("_", " ") for row in pairs])
    conditions.invert_yaxis()
    handles = [Line2D([], [], marker=marker, color=color, linestyle="", label=label)
               for marker, color, label in [("o", M1, "M1 · fixed"), ("D", M2, "M2 · reoptimized")]]
    handles += [Line2D([], [], marker="o", color=GRAY, markerfacecolor=face, linestyle="", label=label)
                for face, label in [("white", "Baseline"), (GRAY, "Modified")]]
    fig.legend(handles=handles, ncol=4, loc="lower center", bbox_to_anchor=(.5, .064), frameon=False)
    fig.text(.5, .035, "Missing or nonconverged cells are not plotted. Dashed line: feasibility threshold.",
             ha="center", color=GRAY, fontsize=7)
    for suffix in ("svg", "pdf"):
        metadata = {"Date": None} if suffix == "svg" else {"CreationDate": None}
        path = args.directory / f"t07_m1_m2.{suffix}"
        fig.savefig(path, metadata=metadata)
        if suffix == "svg":
            path.write_bytes(b"\n".join(line.rstrip() for line in path.read_bytes().splitlines()) + b"\n")
    plt.close(fig)


if __name__ == "__main__":
    main()
