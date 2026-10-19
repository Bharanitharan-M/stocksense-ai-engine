import email.utils
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import timezone

import requests

UA = {"User-Agent": "Mozilla/5.0 (personal stock journal)"}


def fetch_company_news(names: list[str], limit: int = 10) -> list[dict]:
    """Google News RSS (India, last 2 days); one query covering all aliases of a company."""
    q = " OR ".join(f'"{n}"' for n in names) + " when:2d"
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q)
           + "&hl=en-IN&gl=IN&ceid=IN:en")
    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    items = []
    for it in list(ET.fromstring(r.content).iterfind(".//item"))[:limit]:
        pub = it.findtext("pubDate")
        pub_iso = email.utils.parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat() if pub else None
        items.append({"headline": (it.findtext("title") or "").strip(),
                      "url": (it.findtext("link") or "").strip(),
                      "published_at": pub_iso})
    return [i for i in items if i["url"] and i["headline"]]
