# Price Checker

Personal price monitoring tool. Watches product pages, records price history in SQLite, and sends email alerts via Amazon SES when a price drops.

## Architecture

```
checker.py        CLI entry point (add / remove / list / check / history)
web.py            Flask web interface (add items, test selectors)
scraper.py        Playwright headless browser — extracts price from a CSS selector
db.py             SQLite wrapper — price history only (items.yaml owns the watch list)
notifier.py       Amazon SES email alerts
items.yaml        Source of truth for the watch list — edit directly or via CLI/web
templates/
  index.html      Single-page web UI
prices.db         SQLite database (git-ignored, created on first run)
.env              Secrets — copy from .env.example (git-ignored)
```

## Key design decisions

- **`items.yaml` is the source of truth** for which items are watched. Both `checker.py` and `web.py` read and write this file directly. The database stores price history only.
- **Playwright for all scraping** — sites like Chemist Warehouse and Coles render prices via JS, so a real headless browser is required. Each `get_price()` call spawns and closes a fresh Chromium instance.
- **Manual CSS selector per item** — no auto-detection. When adding an item, open DevTools on the product page, inspect the price element, and copy its selector.
- **Alert on any price drop** — an email is sent whenever the new price is lower than the last recorded price for that URL.
- **Cron-triggered, not always-on** — `python checker.py check` is meant to be run via crontab, not a long-running process.

## Running

```bash
# Install dependencies (one-time)
pip install -r requirements.txt
playwright install chromium

# Copy secrets template and fill in AWS/SES credentials
cp .env.example .env

# CLI usage
python checker.py add "Item name" "https://..." ".css-selector"
python checker.py list
python checker.py check
python checker.py history "Item name"
python checker.py history --all

# Web interface (add items + test selectors)
python web.py        # http://localhost:5000

# Cron example (check twice daily)
0 8,17 * * * cd "/path/to/Price Checker" && python checker.py check
```

## Secrets (.env)

```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-southeast-2
SES_FROM_EMAIL=you@example.com
SES_TO_EMAIL=you@example.com
```

SES sender address must be verified in the AWS console before emails will send.

## Module responsibilities

| File | Key functions |
|---|---|
| `db.py` | `init_db()`, `record_price()`, `get_last_price(url)`, `get_history(url)`, `get_all_history()` |
| `scraper.py` | `get_price(url, selector) -> (float\|None, str)` |
| `notifier.py` | `send_price_drop(name, url, old_price, new_price)` |
| `web.py` | Routes: `GET /`, `POST /add`, `POST /remove`, `POST /test-price` |
