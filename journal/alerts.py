import os

import requests

MAX_LEN = 4000  # Telegram limit is 4096 characters per message


def format_alert(sig: dict) -> str:
    arrow = {"bullish": "🟢", "bearish": "🔴"}.get(sig["direction"], "⚪")
    return (f"{arrow} {sig['ticker']} · {sig['direction']} {sig['confidence']:.0%} · {sig['source']}\n"
            f"{sig['headline'][:200]}\n{sig['url']}")


def dedupe(signals: list[dict]) -> list[dict]:
    """One alert per ticker+direction: prefer an exchange filing, then the highest confidence.
    The chosen alert notes how many other articles reported the same thing."""
    groups: dict[tuple, list[dict]] = {}
    for s in signals:
        groups.setdefault((s["ticker"], s["direction"]), []).append(s)
    out = []
    for g in groups.values():
        best = max(g, key=lambda s: (s["source"] == "filing", s["confidence"]))
        out.append({**best, "headline": best["headline"] + (f" (+{len(g) - 1} similar)" if len(g) > 1 else "")})
    return out


def send_telegram(signals: list[dict]) -> bool:
    """Sends one digest message. No-op (returns False) unless TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat and signals):
        return False
    text = "\n\n".join(format_alert(s) for s in dedupe(signals))[:MAX_LEN]
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text, "disable_web_page_preview": True}, timeout=15)
    r.raise_for_status()
    return True
