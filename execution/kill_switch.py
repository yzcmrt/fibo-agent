from __future__ import annotations

import time
from pathlib import Path

from data.store import Store

FLAG = "execution_enabled"


def is_killed(store: Store) -> bool:
    df = store.query("SELECT value FROM runtime_flags WHERE name=:n", {"n": FLAG})
    if df.empty:
        return True
    return str(df.iloc[0]["value"]).lower() in {"0", "false", "off", "kill"}


def set_enabled(store: Store, enabled: bool) -> None:
    store.execute(
        """
        INSERT INTO runtime_flags (name, value, updated_ts)
        VALUES (:n, :v, :t)
        ON CONFLICT(name) DO UPDATE SET value=excluded.value, updated_ts=excluded.updated_ts
        """,
        {"n": FLAG, "v": "true" if enabled else "false", "t": int(time.time() * 1000)},
    )


def kill_file(root: Path) -> Path:
    return root / "data" / "KILL"
