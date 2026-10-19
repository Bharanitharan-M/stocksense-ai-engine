import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("JOURNAL_DB", str(Path.home() / ".stocksense" / "journal.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    ticker TEXT NOT NULL,
    headline TEXT NOT NULL,
    summary TEXT,
    direction TEXT NOT NULL,          -- bullish | bearish | neutral
    confidence REAL NOT NULL,         -- 0..1
    source TEXT NOT NULL DEFAULT 'news',  -- news | filing
    published_at TEXT,                -- ISO UTC, from the source
    recorded_at TEXT NOT NULL,        -- ISO UTC, when we processed it
    ret_1d REAL, ret_5d REAL, ret_20d REAL,       -- stock return %
    bench_1d REAL, bench_5d REAL, bench_20d REAL  -- NIFTY return % over same window
);
CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY);  -- analysed and judged irrelevant; skip next time
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    p = path or DB_PATH
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(signals)")}
    if "source" not in cols:  # older databases
        conn.execute("ALTER TABLE signals ADD COLUMN source TEXT NOT NULL DEFAULT 'news'")
    return conn
