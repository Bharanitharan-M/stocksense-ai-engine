from collections import defaultdict
from itertools import product

from .db import connect

COST_PCT = 0.5  # assumed round-trip cost: brokerage, STT, slippage


def build_report(db_path: str | None = None, min_conf: float = 0.5) -> str:
    """One data point per EVENT, not per article: signals for the same ticker, direction and
    day collapse into one (returns are identical anyway), so five outlets repeating one story
    count once. An event counts as a 'filing' event if any of its signals came from a filing."""
    conn = connect(db_path)
    lines = [f"{'source':<8}{'horizon':<8}{'dir':<9}{'events':>6}{'hit%':>7}{'avg ret':>9}{'avg alpha':>11}{'alpha-cost':>12}"]
    for suf in ("1d", "5d", "20d"):
        events: dict[tuple, dict] = defaultdict(lambda: {"filing": False, "r": None, "b": None})
        for r in conn.execute(
                f"SELECT ticker, direction, source, substr(recorded_at,1,10) day, ret_{suf} r, bench_{suf} b "
                f"FROM signals WHERE ret_{suf} IS NOT NULL AND confidence>=? AND direction!='neutral'", (min_conf,)):
            e = events[(r["ticker"], r["direction"], r["day"])]
            e["filing"] |= r["source"] == "filing"
            e["r"], e["b"] = r["r"], r["b"]
        for source, direction in product(("filing", "news"), ("bullish", "bearish")):
            rows = [(k[1], e) for k, e in events.items() if k[1] == direction and (e["filing"] == (source == "filing"))]
            if not rows:
                continue
            sign = 1 if direction == "bullish" else -1  # a bearish signal profits when the stock falls
            rets = [sign * e["r"] for _, e in rows]
            a = sum(sign * (e["r"] - e["b"]) for _, e in rows) / len(rows)
            hit = 100 * sum(x > 0 for x in rets) / len(rows)
            lines.append(f"{source:<8}{suf:<8}{direction:<9}{len(rows):>6}{hit:>7.1f}{sum(rets)/len(rets):>9.2f}"
                         f"{a:>11.2f}{a - COST_PCT:>12.2f}")
    if len(lines) == 1:
        return "No completed signals yet. Run `ingest` daily and `outcomes` after a few days."
    lines.append(f"\n(confidence>={min_conf}; one data point per ticker/direction/day; "
                 "need 50+ events per row before trusting a number)")
    return "\n".join(lines)
