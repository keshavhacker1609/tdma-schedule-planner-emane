"""Figures used in the report and the presentation."""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
OUT = os.path.join(ROOT, "docs", "figures")
PALETTE = ["#1f6feb", "#e8590c", "#2f9e44", "#9c36b5", "#f08c00", "#0c8599",
           "#c2255c", "#5c7cfa", "#74b816", "#868e96"]


def topology(name, title, fname):
    s = json.load(open(os.path.join(ROOT, "examples", name), encoding="utf-8"))
    pos, slot, rng = s["positions"], s["node_to_slot"], s["radio_range_m"]
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    names = list(pos)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if math.dist(pos[a], pos[b]) <= rng:
                ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#ced4da", lw=0.9, zorder=1)
    for n in names:
        c = PALETTE[slot[n] % len(PALETTE)]
        ax.scatter(*pos[n][:2], s=520, color=c, zorder=2, edgecolor="white", lw=1.5)
        ax.text(pos[n][0], pos[n][1], str(slot[n]), ha="center", va="center", color="white",
                fontsize=11, fontweight="bold", zorder=3)
        ax.text(pos[n][0], pos[n][1] - 70, n[5:], ha="center", va="top", fontsize=7, color="#495057")
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.margins(0.1)
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), dpi=170)
    plt.close(fig)


def loss_chart():
    labels = ["Distance-2 schedule\n(9 slots)", "Plain distance-1\ncolouring (4 slots)"]
    vals = [0.8, 43.1]
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    bars = ax.bar(labels, vals, color=["#2f9e44", "#e03131"], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v}%", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("mean packet loss, 16 simultaneous flows (%)")
    ax.set_ylim(0, 52)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("EMANE 1.5.3 load test", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "emane_loss.png"), dpi=170)
    plt.close(fig)


def hidden_terminal():
    fig, ax = plt.subplots(figsize=(6.2, 2.0))
    xs = [0, 4, 8]
    for x, l in zip(xs, "ABC"):
        ax.scatter(x, 0, s=900, color="#1f6feb", zorder=2)
        ax.text(x, 0, l, color="white", ha="center", va="center", fontsize=14, fontweight="bold", zorder=3)
    ax.annotate("", xy=(3.4, 0.05), xytext=(0.6, 0.05), arrowprops=dict(arrowstyle="->", color="#e03131", lw=2))
    ax.annotate("", xy=(4.6, -0.05), xytext=(7.4, -0.05), arrowprops=dict(arrowstyle="->", color="#e03131", lw=2))
    ax.text(4, 0.55, "A and C cannot hear each other (800 m)\nbut both reach B: frames collide at B",
            ha="center", fontsize=9)
    ax.set_xlim(-1, 9)
    ax.set_ylim(-0.8, 1.2)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "hidden_terminal.png"), dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    topology("grid_16.schedule.json", "4x4 grid: node colour and number = TDMA slot", "grid_slots.png")
    topology("random_16.schedule.json", "Random layout: node colour and number = TDMA slot", "random_slots.png")
    loss_chart()
    hidden_terminal()
