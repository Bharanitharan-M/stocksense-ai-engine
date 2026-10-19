# Personal signal journal

Not deployed (the Dockerfile copies only `src/` and `main.py`). Data: `~/.stocksense/journal.db`.

Run from the repo root:

    uv run python -m journal.cli ingest     # news + NSE filings -> Gemini -> record (+ Telegram alerts)
    uv run python -m journal.cli outcomes   # fill 1/5/20-day returns vs NIFTY
    uv run python -m journal.cli report     # hit rate and alpha after costs, split by source

`.env` (gitignored):

    GEMINI_API_KEYS=["your-key"]
    TELEGRAM_BOT_TOKEN=...      # optional: create via @BotFather
    TELEGRAM_CHAT_ID=...        # optional: your chat id
    ALERT_MIN_CONF=0.7          # optional

Suggested crontab (`crontab -e`; paths are yours to adjust), weekdays:

    30 9,15 * * 1-5  cd <repo> && uv run python -m journal.cli ingest
    45 18   * * 1-5  cd <repo> && uv run python -m journal.cli outcomes

Paper-trade 2-3 months; act on a report row only with 50+ samples and positive alpha-cost.
