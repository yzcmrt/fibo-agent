from __future__ import annotations

from pathlib import Path

import pandas as pd

from analysis.fibonacci import FibGrid


def render_setup_chart(
    df: pd.DataFrame,
    grid: FibGrid,
    out_path: str | Path,
    title: str = "Crypto Fibo Agent",
) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    window = df.iloc[max(0, grid.start.index - 20) : min(len(df), grid.end.index + 40)]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(window.index, window["close"], color="#1f2937", linewidth=1.1)
    ax.axhline(grid.start.price, color="#6b7280", linestyle="--", linewidth=0.8)
    ax.axhline(grid.end.price, color="#111827", linestyle="--", linewidth=0.8)
    colors = {0.382: "#60a5fa", 0.5: "#f59e0b", 0.618: "#ef4444", 0.786: "#8b5cf6"}
    for ratio, price in grid.levels.items():
        if ratio in colors:
            ax.axhline(price, color=colors[ratio], linewidth=0.9, alpha=0.85)
            ax.text(window.index[0], price, f"  {ratio}", color=colors[ratio], va="bottom", fontsize=8)
    ax.set_title(title)
    ax.set_ylabel("Price")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
