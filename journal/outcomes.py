from datetime import datetime

from . import prices
from .db import connect

HORIZONS = (1, 5, 20)


def _ret_after(closes: list[tuple[str, float]], start_date: str, n: int) -> float | None:
    """% return from the first close on/after start_date to the close n trading days later."""
    idx = next((i for i, (d, _) in enumerate(closes) if d >= start_date), None)
    if idx is None or idx + n >= len(closes):
        return None
    return (closes[idx + n][1] / closes[idx][1] - 1) * 100


def fill_outcomes(db_path: str | None = None) -> int:
    conn = connect(db_path)
    rows = conn.execute("SELECT * FROM signals WHERE ret_20d IS NULL").fetchall()
    cache = {prices.BENCH: prices.daily_closes(prices.BENCH)}
    updated = 0
    for r in rows:
        try:
            closes = cache.get(r["ticker"]) or cache.setdefault(r["ticker"], prices.daily_closes(r["ticker"]))
        except Exception as e:
            print(f"[warn] {r['ticker']}: {e}")
            continue
        # Entry = first close AFTER the signal was recorded (we can't trade at a close that already happened)
        start = datetime.fromisoformat(r["recorded_at"]).astimezone().strftime("%Y-%m-%d")
        sets, vals = [], []
        for n in HORIZONS:
            s, b = _ret_after(closes, start, n), _ret_after(cache[prices.BENCH], start, n)
            if s is not None and b is not None:
                sets += [f"ret_{n}d=?", f"bench_{n}d=?"]
                vals += [s, b]
        if sets:
            conn.execute(f"UPDATE signals SET {','.join(sets)} WHERE id=?", (*vals, r["id"]))
            updated += 1
    conn.commit()
    return updated
