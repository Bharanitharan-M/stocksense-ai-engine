import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .alerts import send_telegram
from .analyze import analyze
from .db import connect
from .filings import fetch_nse_filings
from .news import fetch_company_news

DEFAULT_WATCHLIST = Path(__file__).with_name("watchlist.json")
WORKERS = 4


def _collect(watchlist: dict[str, list[str]], conn) -> list[dict]:
    """Fetch filings + news for every ticker; keep only URLs we have never analysed."""
    todo = []
    for ticker, names in watchlist.items():
        for source, fetch in (("filing", lambda: fetch_nse_filings(ticker)), ("news", lambda: fetch_company_news(names))):
            try:
                items = fetch()
            except Exception as e:  # provider hiccup: skip this source for this ticker
                print(f"[warn] {ticker} {source}: {e}", flush=True)
                continue
            for it in items:
                known = conn.execute("SELECT 1 FROM signals WHERE url=? UNION SELECT 1 FROM seen WHERE url=?",
                                     (it["url"], it["url"])).fetchone()
                if not known:
                    todo.append({**it, "ticker": ticker, "names": names, "source": source})
        print(f"{ticker}: fetched, {len(todo)} to analyse so far", flush=True)
    return todo


def _analyse(it: dict):
    try:
        return it, analyze(it["ticker"], it["names"], it["headline"]), None
    except Exception as e:
        return it, None, e


def ingest(watchlist_path: Path = DEFAULT_WATCHLIST, db_path: str | None = None) -> int:
    conn = connect(db_path)
    alert_min = float(os.environ.get("ALERT_MIN_CONF", "0.7"))
    todo = _collect(json.loads(Path(watchlist_path).read_text()), conn)
    new, alerts = 0, []
    with ThreadPoolExecutor(WORKERS) as pool:
        for it, a, err in pool.map(_analyse, todo):  # DB writes stay on this thread
            if err:
                print(f"[warn] analysis failed for {it['ticker']}: {err}", flush=True)
                continue
            if a is None:
                conn.execute("INSERT OR IGNORE INTO seen (url) VALUES (?)", (it["url"],))
                conn.commit()
                continue
            conn.execute(
                """INSERT INTO signals (url,ticker,source,headline,summary,direction,confidence,published_at,recorded_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (it["url"], it["ticker"], it["source"], it["headline"], a.summary, a.direction, a.confidence,
                 it["published_at"], datetime.now(timezone.utc).isoformat()))
            conn.commit()  # save as we go; one failure must not lose earlier signals
            new += 1
            if a.direction != "neutral" and a.confidence >= alert_min:
                alerts.append({**it, "direction": a.direction, "confidence": a.confidence})
            print(f"[{it['source']:>6} {a.direction:>7} {a.confidence:.2f}] {it['ticker']}: {it['headline']}", flush=True)
    try:
        send_telegram(alerts)
    except Exception as e:  # an alert failure must never lose recorded signals
        print(f"[warn] telegram: {e}", flush=True)
    return new
