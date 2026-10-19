from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-announcements",
}
# Routine compliance filings that never move a price; skipped before spending an LLM call.
NOISE = ("trading window", "loss of share certificate", "newspaper publication", "newspaper clipping", "duplicate share certificate",
         "analysts/institutional investor", "certificate under regulation 74", "compliances-reg",
         "shareholders meeting", "postal ballot", "reg. 39", "reg 40", "reg. 40", "scrutinizer")


def is_noise(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in NOISE)


def _parse_ts(value: str | None) -> datetime | None:
    try:
        return datetime.strptime(value or "", "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST).astimezone(timezone.utc)
    except ValueError:
        return None


def fetch_nse_filings(symbol: str, days: int = 2, limit: int = 15) -> list[dict]:
    """Recent NSE corporate announcements for a symbol, newest first, noise removed."""
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get("https://www.nseindia.com/", timeout=20)  # sets cookies; status code is irrelevant
    r = s.get("https://www.nseindia.com/api/corporate-announcements",
              params={"index": "equities", "symbol": symbol}, timeout=20)
    r.raise_for_status()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for a in r.json():
        published = _parse_ts(a.get("exchdisstime")) or _parse_ts(a.get("an_dt"))
        if published is None or published < cutoff:
            continue
        text = f"{a.get('desc', '')}: {a.get('attchmntText', '')}".strip(": ")
        if not a.get("attchmntFile") or is_noise(text):
            continue
        out.append({"headline": text[:500], "url": a["attchmntFile"], "published_at": published.isoformat()})
    out.sort(key=lambda x: x["published_at"], reverse=True)
    return out[:limit]
