"""Chart rendering for the report (embedded as base64 PNG so the HTML stays self-contained)."""

from __future__ import annotations

import base64
import io
from itertools import cycle

PALETTE = ("#2f5d8a", "#5b8fb9", "#9cc3e0", "#d9e7f2", "#7a8b99", "#c0ccd6")


def pie_chart_data_uri(counts: dict[str, int], title: str) -> str | None:
    """Return a ``data:image/png`` URI for a pie chart, or None if there is nothing to plot."""
    data = {label: count for label, count in counts.items() if count > 0}
    if not data:
        return None

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = [color for color, _ in zip(cycle(PALETTE), data)]
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        list(data.values()),
        labels=list(data.keys()),
        autopct="%1.1f%%",
        startangle=90,
        counterclock=False,
        colors=colors,
        wedgeprops={"edgecolor": "white"},
    )
    ax.axis("equal")
    ax.set_title(title)

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
