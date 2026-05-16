#!/usr/bin/env python3
"""Minimal web interface for managing the price watch list and testing selectors."""

import os
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, redirect, render_template, request, url_for
import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import db
import scraper

app = Flask(__name__)

ITEMS_FILE = Path(__file__).parent / "items.yaml"


def _validate_url(url: str) -> bool:
    """Accept only http/https URLs — blocks file://, internal IPs via other schemes, etc."""
    scheme = urlparse(url).scheme
    return scheme in ("http", "https")


def _load():
    if not ITEMS_FILE.exists():
        return []
    data = yaml.safe_load(ITEMS_FILE.read_text()) or {}
    return data.get("items", [])


def _save(items):
    ITEMS_FILE.write_text(
        yaml.dump({"items": items}, default_flow_style=False, allow_unicode=True)
    )


@app.route("/")
def index():
    db.init_db()
    items = _load()
    for item in items:
        item["last_price"] = db.get_last_price(item["url"])
        item["direction"] = db.get_latest_direction(item["url"])
    return render_template("index.html", items=items)


@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"].strip()
    url = request.form["url"].strip()
    selector = request.form["selector"].strip()
    if name and url and selector and _validate_url(url):
        items = _load()
        if not any(i["url"] == url for i in items):
            items.append({"name": name, "url": url, "selector": selector})
            _save(items)
    return redirect(url_for("index"))


@app.route("/remove", methods=["POST"])
def remove():
    url = request.form["url"]
    items = [i for i in _load() if i["url"] != url]
    _save(items)
    return redirect(url_for("index"))


@app.route("/edit", methods=["POST"])
def edit():
    original_url = request.form.get("original_url", "").strip()
    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()
    selector = request.form.get("selector", "").strip()
    if not (original_url and name and url and selector and _validate_url(url)):
        return redirect(url_for("index"))
    items = _load()
    for item in items:
        if item["url"] == original_url:
            item["name"] = name
            item["selector"] = selector
            item["url"] = url
            break
    _save(items)
    if url != original_url:
        db.migrate_url(original_url, url)
    return redirect(url_for("index"))


@app.route("/autodetect", methods=["POST"])
def autodetect():
    url = request.form.get("url", "").strip()
    if not url:
        return {"error": "URL is required"}, 400
    if not _validate_url(url):
        return {"error": "Invalid URL scheme — only http and https are allowed"}, 400
    selector, price, raw = scraper.autodetect_selector(url)
    if selector is None:
        return {"error": raw}
    return {"selector": selector, "price": price, "raw": raw}


@app.route("/test-price", methods=["POST"])
def test_price():
    url = request.form.get("url", "").strip()
    selector = request.form.get("selector", "").strip()
    if not url or not selector:
        return {"error": "URL and selector are required"}, 400
    if not _validate_url(url):
        return {"error": "Invalid URL scheme — only http and https are allowed"}, 400
    price, raw = scraper.get_price(url, selector)
    if price is None:
        return {"error": raw or "Could not extract a price"}
    return {"price": price, "raw": raw}


@app.route("/logs")
def logs():
    rows = db.get_check_logs(200)
    return render_template("logs.html", rows=rows)


@app.route("/trend")
def trend():
    url = request.args.get("url", "").strip()
    if not url or not _validate_url(url):
        return redirect(url_for("index"))
    items = _load()
    item = next((i for i in items if i["url"] == url), None)
    name = item["name"] if item else url
    changes = db.get_price_changes(url)
    return render_template("trend.html", name=name, url=url, changes=changes)


if __name__ == "__main__":
    db.init_db()
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=8080)
