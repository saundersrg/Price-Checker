import re


def _parse_price(text: str):
    """Extract the first decimal number from a string like '$24.99' or '24,99'."""
    cleaned = text.replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(match.group()) if match else None


def get_price(url: str, selector: str, timeout: int = 20000):
    """
    Returns (price_float_or_None, raw_text_or_error_string).
    Uses a real Chromium browser so JS-rendered prices are visible.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "playwright not installed — run: pip install playwright && playwright install chromium"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_selector(selector, timeout=timeout)
            raw = (page.text_content(selector) or "").strip()
            return _parse_price(raw), raw
        except Exception as exc:
            return None, f"ERROR: {exc}"
        finally:
            browser.close()
