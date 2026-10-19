from datetime import datetime, timezone

import requests

UA = {"User-Agent": "Mozilla/5.0 (personal stock journal)"}
BENCH = "^NSEI"


def _symbol(ticker: str) -> str:
    return ticker if ticker.startswith("^") else f"{ticker}.NS"


def daily_closes(ticker: str, range_: str = "6mo") -> list[tuple[str, float]]:
    """[(YYYY-MM-DD, close)] oldest first, trading days only."""
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{_symbol(ticker)}",
                     params={"range": range_, "interval": "1d"}, headers=UA, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    return [(datetime.fromtimestamp(ts, timezone.utc).astimezone().strftime("%Y-%m-%d"), float(c))
            for ts, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]) if c is not None]
