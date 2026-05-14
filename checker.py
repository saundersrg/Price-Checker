#!/usr/bin/env python3
"""
Price checker CLI.

Commands:
  add <name> <url> <selector>   Add an item to watch
  remove <name|url>             Remove an item
  list                          Show watched items + last known price
  check                         Scrape prices and send alerts on drops
  history [name] [--all]        Show price history
"""

import argparse
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import db  # noqa: E402  (after load_dotenv so creds are available)
import notifier
import scraper

ITEMS_FILE = Path(__file__).parent / "items.yaml"


# ---------------------------------------------------------------------------
# items.yaml helpers
# ---------------------------------------------------------------------------

def _load() -> list[dict]:
    if not ITEMS_FILE.exists():
        return []
    data = yaml.safe_load(ITEMS_FILE.read_text()) or {}
    return data.get("items", [])


def _save(items: list[dict]):
    ITEMS_FILE.write_text(yaml.dump({"items": items}, default_flow_style=False, allow_unicode=True))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add(args):
    items = _load()
    for item in items:
        if item["url"] == args.url:
            print(f"Already watching: {item['name']}")
            return
    items.append({"name": args.name, "url": args.url, "selector": args.selector})
    _save(items)
    print(f"Added: {args.name}")


def cmd_remove(args):
    items = _load()
    needle = args.name.lower()
    updated = [i for i in items if i["name"].lower() != needle and i["url"] != args.name]
    if len(updated) == len(items):
        print(f"No item found matching: {args.name}")
        return
    _save(updated)
    print(f"Removed {len(items) - len(updated)} item(s).")


def cmd_list(args):
    items = _load()
    if not items:
        print("Watch list is empty.  Use: checker.py add <name> <url> <selector>")
        return
    db.init_db()
    print(f"{'#':<4} {'Name':<35} {'Last price':>12}")
    print("-" * 54)
    for idx, item in enumerate(items, 1):
        last = db.get_last_price(item["url"])
        price_str = f"${last:.2f}" if last is not None else "not checked"
        print(f"{idx:<4} {item['name'][:34]:<35} {price_str:>12}")


def cmd_check(args):
    items = _load()
    if not items:
        print("Nothing to check.")
        return
    db.init_db()
    for item in items:
        name, url, selector = item["name"], item["url"], item["selector"]
        print(f"\nChecking: {name}")
        price, raw = scraper.get_price(url, selector)
        if price is None:
            print(f"  Could not extract price — raw: '{raw}'")
            db.record_price(name, url, None, raw)
            continue
        print(f"  ${price:.2f}  (raw: '{raw}')")
        last = db.get_last_price(url)
        db.record_price(name, url, price, raw)
        if last is None:
            print("  First check recorded.")
        elif price < last:
            print(f"  DROP from ${last:.2f}! Sending alert...")
            notifier.send_price_drop(name, url, last, price)
        else:
            print(f"  No drop (was ${last:.2f}).")


def cmd_history(args):
    db.init_db()
    if args.all or not args.name:
        rows = db.get_all_history(50)
        if not rows:
            print("No history yet.")
            return
        print(f"{'Date/Time':<22} {'Name':<30} {'Price':>10}  Raw")
        print("-" * 75)
        for r in rows:
            p = f"${r['price']:.2f}" if r["price"] is not None else "(error)"
            print(f"{r['checked_at']:<22} {r['item_name'][:29]:<30} {p:>10}  {r['raw_price']}")
        return

    items = _load()
    matches = [i for i in items if args.name.lower() in i["name"].lower()]
    if not matches:
        print(f"No item matching: {args.name}")
        return
    item = matches[0]
    rows = db.get_history(item["url"], 30)
    if not rows:
        print(f"No history for: {item['name']}")
        return
    print(f"History — {item['name']}")
    print(f"{'Date/Time':<22} {'Price':>10}  Raw")
    print("-" * 45)
    for r in rows:
        p = f"${r['price']:.2f}" if r["price"] is not None else "(error)"
        print(f"{r['checked_at']:<22} {p:>10}  {r['raw_price']}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    db.init_db()

    parser = argparse.ArgumentParser(
        prog="checker.py",
        description="Personal price checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("add", help="Add item to watch list")
    p.add_argument("name", help='Item name, e.g. "Whey Protein 1kg"')
    p.add_argument("url", help="Full product page URL")
    p.add_argument("selector", help="CSS selector for the price element")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("remove", help="Remove item by name or URL")
    p.add_argument("name", help="Item name or URL to remove")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("list", help="List watched items with last known price")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("check", help="Check all prices now and send drop alerts")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("history", help="Show price history")
    p.add_argument("name", nargs="?", default="", help="Item name (partial match)")
    p.add_argument("--all", action="store_true", help="Show latest checks across all items")
    p.set_defaults(func=cmd_history)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
