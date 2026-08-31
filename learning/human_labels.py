from __future__ import annotations

from typing import Any


def reviews_from_store(store) -> list[dict[str, Any]]:
    try:
        df = store.query(
            """
            SELECT r.label, d.symbol, d.timeframe, d.swing_low, d.swing_high, d.origin_mode
            FROM drawing_reviews r
            JOIN live_drawings d ON d.id = r.drawing_id
            WHERE r.label IN ('hold', 'fail')
            """
        )
    except Exception:  # noqa: BLE001
        return []
    if df is None or getattr(df, "empty", True):
        return []
    return df.to_dict(orient="records")


def apply_human_overrides(
    rows: list[dict[str, Any]],
    labels: list[int],
    reviews: list[dict[str, Any]],
    copies: int = 3,
) -> tuple[list[dict[str, Any]], list[int], int]:
    """Human hold/fail wins. Extra copies raise weight vs automatic labels."""
    if not rows or not reviews:
        return rows, labels, 0
    out_rows = list(rows)
    out_labels = list(labels)
    n_hit = 0
    for rev in reviews:
        human = 1 if str(rev.get("label")) == "hold" else 0
        low = rev.get("swing_low")
        high = rev.get("swing_high")
        mid = None
        try:
            if low is not None and high is not None:
                mid = (float(low) + float(high)) / 2.0
        except (TypeError, ValueError):
            mid = None
        best_i = 0
        if mid is not None:
            best = None
            for i, row in enumerate(rows):
                close = float(row.get("close") or 0.0)
                dist = abs(close - mid)
                if best is None or dist < best:
                    best, best_i = dist, i
        if out_labels[best_i] != human:
            n_hit += 1
        out_labels[best_i] = human
        seed = dict(out_rows[best_i])
        seed["human_label"] = float(human)
        for _ in range(max(0, copies)):
            out_rows.append(seed)
            out_labels.append(human)
    return out_rows, out_labels, n_hit
