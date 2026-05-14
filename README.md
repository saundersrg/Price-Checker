# Price Checker

A lightweight personal price monitoring tool. Add product pages to a watch list, check prices on a schedule, and receive an email when something drops in price.

- Handles JavaScript-rendered pages (Chemist Warehouse, Coles, JB Hi-Fi, etc.)
- Stores full price history in a local SQLite database
- Sends email alerts via Amazon SES
- Minimal web interface for adding items and testing selectors
- CLI for everything else

---

## Requirements

- Python 3.11+
- An AWS account with SES set up (free tier is fine for personal use)

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/saundersrg/price-checker.git
cd price-checker

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install the Chromium browser used for scraping
playwright install chromium

# 4. Create your secrets file
cp .env.example .env
```

Edit `.env` and fill in your AWS credentials and email addresses:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-southeast-2
SES_FROM_EMAIL=you@example.com
SES_TO_EMAIL=you@example.com
```

> The sender address (`SES_FROM_EMAIL`) must be verified in the AWS SES console before emails will send.

---

## Adding items to watch

### Option 1 — Web interface

Start the local web server:

```bash
python web.py
```

Open [http://localhost:5000](http://localhost:5000). Fill in the item name, URL, and CSS selector, then click **Test price** to verify the selector pulls the right value before saving.

### Option 2 — CLI

```bash
python checker.py add "Whey Protein 1kg" "https://www.chemistwarehouse.com.au/..." ".product-price .Price"
```

### Finding the CSS selector

The selector tells the tool exactly which element on the page contains the price.

1. Open the product page in Chrome
2. Right-click the price and choose **Inspect**
3. In DevTools, right-click the highlighted element → **Copy** → **Copy selector**
4. Paste it into the selector field

The **Test price** button in the web interface lets you verify the selector works before adding the item.

---

## Checking prices

Run a one-off check across all watched items:

```bash
python checker.py check
```

This scrapes each item, records the price, and sends an email alert for any item where the price has dropped since the last check.

---

## Scheduling automatic checks

Add a crontab entry to run checks automatically. To check twice daily at 8am and 5pm:

```bash
crontab -e
```

```
0 8,17 * * * cd "/path/to/price-checker" && python checker.py check
```

---

## Other CLI commands

```bash
# List all watched items with their last known price
python checker.py list

# Show price history for a specific item
python checker.py history "Whey Protein"

# Show recent checks across all items
python checker.py history --all

# Remove an item
python checker.py remove "Whey Protein 1kg"
```

---

## How it works

```
items.yaml          Watch list — source of truth, edited by CLI or web interface
prices.db           SQLite database storing full price history
checker.py          CLI — orchestrates checks, compares to last price, triggers alerts
scraper.py          Launches a headless Chromium browser and extracts the price text
                    using the CSS selector you provided
notifier.py         Sends an HTML email via Amazon SES when a price drop is detected
web.py              Local Flask web server for managing the watch list
```

Each time `checker.py check` runs, it:
1. Reads the watch list from `items.yaml`
2. Scrapes the current price for each item using Playwright
3. Compares it to the last recorded price in the database
4. Records the new price
5. Sends an email alert for any item where the price has fallen

---

## Project structure

```
price-checker/
├── checker.py          CLI entry point
├── web.py              Web interface (Flask)
├── scraper.py          Playwright price extraction
├── db.py               SQLite price history
├── notifier.py         Amazon SES alerts
├── items.yaml          Watch list
├── templates/
│   └── index.html      Web UI
├── .env.example        Secrets template
├── requirements.txt
└── .gitignore          Excludes .env and prices.db
```

---

## Notes

- `prices.db` and `.env` are git-ignored — your credentials and price history stay local
- The scraper sets a realistic browser user-agent to avoid basic bot detection
- Page load timeout is 20 seconds per item — some JS-heavy sites are slow
- Tested on macOS; should work on Linux with no changes
