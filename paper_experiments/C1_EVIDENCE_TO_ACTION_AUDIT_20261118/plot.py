"""Render the C1 evidence conversion figure directly from CSV."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

HERE = Path(__file__).resolve().parent
INK = "#263444"
GRAY = "#687583"
PALETTE = {"Main Agent": "#167876", "External Codex": "#9F492D", "Sub-agent": "#55689A",
           "Fixed program": "#A77E31", "Human/operator": "#8A5D88", "Reporter": "#9EA9B5"}


def read(directory, name):
    with (directory / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=HERE)
    args = parser.parse_args()
    funnel = read(args.directory, "funnel.csv")
    actors = read(args.directory, "by_actor.csv")
    per_task = read(args.directory, "by_task_actor.csv")
    tasks = ["PHS-2D", *(f"T{index:02d}" for index in range(1, 11))]
    plt.rcParams.update({"font.size": 8, "axes.labelcolor": INK, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "svg.hashsalt": "c1-funnel"})
    fig, (stages, execution) = plt.subplots(1, 2, figsize=(7.1, 3.65),
                                            gridspec_kw={"wspace": .43}, width_ratios=[1, 1.15])
    fig.subplots_adjust(bottom=.27, top=.88, left=.16, right=.97)
    stages.set_title("a   Evidence-to-action funnel", loc="left", fontweight="bold")
    execution.set_title("b   Executed actions by task", loc="left", fontweight="bold")
    active = [row for row in actors if int(row["proposed"]) > 0]
    positions = range(len(funnel))
    for pos, row in enumerate(funnel):
        total = int(row["count"])
        start = 0
        for actor in active:
            width = int(actor[row["stage"].lower()])
            if width:
                stages.barh(pos, width, left=start, height=.59,
                            color=PALETTE.get(actor["group"], GRAY))
            start += width
        assert start == total
        stages.annotate(str(total), (total, pos), xytext=(4, 0), textcoords="offset points", va="center")
    stages.set(yticks=positions, yticklabels=[row["stage"] for row in funnel], xlabel="Actions",
               xlim=(0, 1.19 * max(int(row["count"]) for row in funnel)))
    data = {(row["task_id"], row["actor"]): row for row in per_task}
    for pos, task in enumerate(tasks):
        start = 0
        validated = 0
        for actor in active:
            row = data.get((task, actor["group"]), {})
            width = int(row.get("executed", "0"))
            validated += int(row.get("validated", "0"))
            if width:
                execution.barh(pos, width, left=start, height=.62, color=PALETTE.get(actor["group"], GRAY))
            start += width
        if validated:
            execution.annotate(f"{validated} validated", (start, pos), xytext=(4, 0),
                               textcoords="offset points", va="center", fontsize=7)
    largest = max(sum(int(data.get((task, actor["group"]), {}).get("executed", "0")) for actor in active)
                  for task in tasks)
    execution.set(yticks=range(len(tasks)), yticklabels=tasks, xlabel="Actions", xlim=(0, max(1, largest) * 1.36))
    for axis in (stages, execution):
        axis.invert_yaxis()
        axis.grid(axis="x", alpha=.18)
        axis.set_axisbelow(True)
        axis.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
        axis.tick_params(axis="y", length=0)
    legend = [Line2D([], [], lw=5, color=PALETTE.get(actor["group"], GRAY), label=actor["group"]) for actor in active]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(.5, .068), frameon=False,
               ncol=max(1, len(legend)))
    fig.text(.5, .046, "Verified artifact links only; execution and independent validation are distinct.",
             ha="center", fontsize=7, color=GRAY)
    for suffix in ("svg", "pdf"):
        metadata = {"Date": None} if suffix == "svg" else {"CreationDate": None}
        path = args.directory / f"c1_evidence_to_action.{suffix}"
        fig.savefig(path, metadata=metadata)
        if suffix == "svg":
            path.write_bytes(b"\n".join(line.rstrip() for line in path.read_bytes().splitlines()) + b"\n")
    plt.close(fig)


if __name__ == "__main__":
    main()
