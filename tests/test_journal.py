from journal.db import connect
from journal.filings import is_noise
from journal.outcomes import _ret_after
from journal.report import build_report


def test_ret_after_uses_trading_days():
    closes = [("2026-01-01", 100.0), ("2026-01-02", 110.0), ("2026-01-05", 121.0)]
    assert abs(_ret_after(closes, "2026-01-01", 1) - 10.0) < 1e-9
    assert _ret_after(closes, "2026-01-01", 5) is None


def test_report_alpha_and_bearish_sign(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    c.execute("""INSERT INTO signals (url,ticker,source,headline,direction,confidence,recorded_at,ret_5d,bench_5d)
                 VALUES ('u1','TCS','filing','h','bullish',0.9,'2026-01-01',4.0,1.0)""")
    c.execute("""INSERT INTO signals (url,ticker,source,headline,direction,confidence,recorded_at,ret_5d,bench_5d)
                 VALUES ('u2','INFY','filing','h','bearish',0.9,'2026-01-01',-3.0,0.0)""")
    c.commit()
    out = build_report(db)
    assert "3.00" in out and "2.50" in out  # bullish alpha 3.0, minus 0.5 cost; bearish alpha also 3.0
    assert out.count("100.0") == 2


def test_noise_filter():
    assert is_noise("Trading Window: closure of trading window")
    assert not is_noise("Acquisition: TCS acquires a company for $500 million")


def test_old_database_gets_source_column(tmp_path):
    import sqlite3
    db = str(tmp_path / "old.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE signals (id INTEGER PRIMARY KEY, url TEXT, ticker TEXT, headline TEXT, direction TEXT,"
              " confidence REAL, recorded_at TEXT)")
    c.commit(); c.close()
    cols = {r[1] for r in connect(db).execute("PRAGMA table_info(signals)")}
    assert "source" in cols


def test_filing_timestamp_parsing():
    from journal.filings import _parse_ts
    assert _parse_ts("19-Oct-2026 11:30:08").isoformat() == "2026-10-19T06:00:08+00:00"
    assert _parse_ts("-") is None and _parse_ts(None) is None


def test_telegram_noop_without_credentials(monkeypatch):
    from journal.alerts import send_telegram
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert send_telegram([{"ticker": "TCS"}]) is False


def test_telegram_sends_digest(monkeypatch):
    import journal.alerts as al
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t"); monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
    sent = {}

    class R:
        def raise_for_status(self): pass

    monkeypatch.setattr(al.requests, "post", lambda url, json, timeout: sent.update(url=url, **json) or R())
    sig = {"ticker": "TCS", "direction": "bullish", "confidence": 0.9, "source": "filing",
           "headline": "Order win", "url": "http://x"}
    assert al.send_telegram([sig]) is True
    assert "TCS" in sent["text"] and "bot" in sent["url"]


def test_ingest_records_and_alerts(tmp_path, monkeypatch):
    import json
    import journal.ingest as ing
    from journal.analyze import SignalOutput
    wl = tmp_path / "wl.json"; wl.write_text(json.dumps({"TCS": ["TCS"]}))
    item = {"headline": "TCS wins $1bn deal", "url": "http://a", "published_at": None}
    monkeypatch.setattr(ing, "fetch_nse_filings", lambda t: [item])
    monkeypatch.setattr(ing, "fetch_company_news", lambda n: [])
    monkeypatch.setattr(ing, "analyze", lambda *a: SignalOutput(relevant=True, direction="bullish", confidence=0.9, summary="s"))
    got = []
    monkeypatch.setattr(ing, "send_telegram", lambda alerts: got.extend(alerts))
    db = str(tmp_path / "j.db")
    assert ing.ingest(wl, db) == 1
    assert ing.ingest(wl, db) == 0  # dedupe by url
    assert len(got) == 1 and got[0]["ticker"] == "TCS"


def test_alert_dedupe_prefers_filing_then_confidence():
    from journal.alerts import dedupe
    mk = lambda src, conf, h: {"ticker": "TCS", "direction": "bullish", "confidence": conf, "source": src, "headline": h, "url": h}
    out = dedupe([mk("news", 0.95, "a"), mk("filing", 0.7, "b"), mk("news", 0.8, "c"),
                  {**mk("news", 0.9, "d"), "direction": "bearish"}])
    assert len(out) == 2
    bull = next(o for o in out if o["direction"] == "bullish")
    assert bull["source"] == "filing" and "+2 similar" in bull["headline"]


def test_report_counts_one_event_per_ticker_direction_day(tmp_path):
    db = str(tmp_path / "t.db")
    c = connect(db)
    for i in range(5):  # five outlets, one story
        c.execute("""INSERT INTO signals (url,ticker,source,headline,direction,confidence,recorded_at,ret_5d,bench_5d)
                     VALUES (?,?,?,?,?,?,?,?,?)""", (f"u{i}", "TCS", "news", "h", "bullish", 0.9, "2026-01-01T10:00", 4.0, 1.0))
    c.commit()
    line = [l for l in build_report(db).splitlines() if l.startswith("news")][0]
    assert line.split()[3] == "1"
