"""Render the documented live and synthetic pathways; no measured results."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as PlotPath

root = Path(__file__).resolve().parents[1]
fig, ax = plt.subplots(figsize=(12, 7.6))
fig.patch.set_facecolor("#f8fafc")
ax.set(xlim=(-0.7, 10.7), ylim=(-0.85, 6.5))
ax.axis("off")
ax.text(0, 6.1, "SteadyState Studio", fontsize=21, fontweight="bold", color="#15304f")
ax.text(
    0,
    5.65,
    "Team Beta Band | EEG music BCI and controlled synthetic replay",
    fontsize=12,
    color="#526477",
)
nodes = [
    (0, 4.3, "PsychoPy\nstimuli", "#e3edf8"),
    (2.6, 4.3, "Participant", "#e3edf8"),
    (5.2, 4.3, "EEG signal", "#e3edf8"),
    (7.8, 4.3, "Unicorn / LSL", "#e3edf8"),
    (7.8, 2.4, "Preprocessing", "#dcefe9"),
    (5.2, 2.4, "FBCCA", "#dcefe9"),
    (2.6, 2.4, "Decision logic", "#dcefe9"),
    (2.6, 0.5, "LSL command", "#f9e9d8"),
    (5.2, 0.5, "Music menu", "#f9e9d8"),
    (7.8, 0.5, "Sonic Pi", "#f9e9d8"),
]
width, height = 2.15, 0.82
for x, y, label, color in nodes:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.04,rounding_size=0.10",
            facecolor=color,
            edgecolor="#8398ad",
            linewidth=1.2,
        )
    )
    ax.text(
        x + width / 2,
        y + height / 2,
        label,
        ha="center",
        va="center",
        fontsize=12,
        color="#15304f",
    )


def arrow(a, b, label=None):
    ax.annotate(
        "",
        xy=b,
        xytext=a,
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#536980",
            "lw": 1.5,
            "mutation_scale": 14,
        },
    )
    if label:
        ax.text(
            (a[0] + b[0]) / 2,
            (a[1] + b[1]) / 2 + 0.12,
            label,
            ha="center",
            fontsize=9,
            color="#536980",
        )


for x in (0, 2.6, 5.2):
    arrow((x + width, 4.71), (x + 2.6, 4.71))
arrow((8.875, 4.3), (8.875, 3.22))
arrow((7.8, 2.81), (7.35, 2.81))
arrow((5.2, 2.81), (4.75, 2.81))
arrow((3.675, 2.4), (3.675, 1.32))
arrow((4.75, 0.91), (5.2, 0.91))
arrow((7.35, 0.91), (7.8, 0.91))
ax.text(7.58, 1.48, "OSC / UDP", ha="center", fontsize=10, color="#965716")
ax.text(8.875, 3.63, "raw samples", ha="center", fontsize=10, color="#536980")
ax.add_patch(
    FancyBboxPatch(
        (0, 2.38),
        2.0,
        0.86,
        boxstyle="round,pad=0.04,rounding_size=0.10",
        facecolor="white",
        edgecolor="#399c8c",
        linestyle="--",
        linewidth=1.4,
    )
)
ax.text(
    1,
    2.81,
    "Synthetic generator\n+ saved replay",
    ha="center",
    va="center",
    fontsize=11,
    color="#21786c",
)
ax.add_patch(
    FancyArrowPatch(
        path=PlotPath(
            [(1, 3.28), (1, 3.50), (8.4, 3.50), (8.4, 3.28)],
            [PlotPath.MOVETO, PlotPath.LINETO, PlotPath.LINETO, PlotPath.LINETO],
        ),
        arrowstyle="-|>",
        color="#399c8c",
        linewidth=1.4,
        linestyle="--",
        mutation_scale=12,
    )
)
ax.text(
    4.6,
    3.65,
    "Controlled signals enter the same processing path",
    ha="center",
    fontsize=10,
    color="#21786c",
)
ax.text(
    0,
    -0.28,
    "Synthetic checks establish software behavior; they do not measure live-EEG accuracy.",
    fontsize=11,
    color="#526477",
)
for ext in ("png", "svg"):
    fig.savefig(root / "docs" / f"architecture.{ext}", dpi=180, bbox_inches="tight")
plt.close(fig)
