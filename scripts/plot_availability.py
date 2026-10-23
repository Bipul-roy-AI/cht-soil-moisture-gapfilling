"""Regenerate the provenance-safe availability figure from the committed CSV."""

import csv
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from audit_availability import audit


def main():
    # Keep vector text as text, making the evidence figure accessible and small.
    plt.rcParams["svg.fonttype"] = "none"
    root = Path(__file__).resolve().parents[1]
    path = root / "data/smap_daily_means.csv"
    summary, monthly = audit(path)
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    dates = [date.fromisoformat(r["date"]) for r in rows]
    valid = np.array([bool(r["SMAP_SM"].strip()) for r in rows])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11.8, 6.5),
                                   gridspec_kw={"height_ratios": [1, 1.2]},
                                   layout="constrained")
    fig.set_facecolor("#ffffff")
    ax1.scatter(np.asarray(dates)[valid], np.ones(valid.sum()),
                marker="|", s=90, linewidth=1.3, color="#177d73", label="Regional mean recorded")
    ax1.scatter(np.asarray(dates)[~valid], np.zeros((~valid).sum()),
                marker="|", s=90, linewidth=1.3, color="#c75e4d", label="No regional mean in CSV")
    ax1.set_yticks([0, 1], labels=["Missing", "Recorded"])
    ax1.set_ylim(-0.6, 1.6)
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax1.set_xlim(dates[0], dates[-1])
    ax1.grid(axis="x", alpha=0.2)
    ax1.set_title("Daily availability of recorded SMAP regional means — CHT bounding-box proxy, 2021",
                  loc="left", fontsize=12, fontweight="bold")
    ax1.legend(loc="upper right", frameon=False, ncol=2, fontsize=9)

    names = [r["month"][5:] for r in monthly]
    shares = [100 * r["missing_fraction"] for r in monthly]
    bars = ax2.bar(names, shares, color="#447f93", width=0.65)
    for bar, value in zip(bars, shares):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + 1.1,
                 f"{value:.0f}%", ha="center", va="bottom", fontsize=9)
    ax2.axhline(100 * summary["missing_fraction"], linestyle="--", linewidth=1.3,
                color="#c75e4d", label=f"Period mean: {100 * summary['missing_fraction']:.1f}%")
    ax2.set_ylim(0, 70)
    ax2.set_ylabel("Dates with missing regional mean (%)")
    ax2.set_xlabel("Month (2021)")
    ax2.set_title("Monthly availability — descriptive counts only", loc="left", fontsize=11)
    ax2.legend(frameon=False, loc="upper right", fontsize=9)
    ax2.grid(axis="y", alpha=0.18)
    ax2.set_axisbelow(True)

    fig.text(0.5, -0.015,
             "Source: committed data/smap_daily_means.csv (300 days). Missingness cause, retrieval quality and spatial support not determined.",
             ha="center", color="#4a5960", fontsize=9)
    output = root / "results/availability_verified.svg"
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
