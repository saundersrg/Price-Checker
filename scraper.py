import re

# Tried in order — first match that yields a valid price wins.
CANDIDATE_SELECTORS = [
    # Schema.org microdata — reliable across many retailers
    "[itemprop='price']",
    # Common data attributes
    "[data-price]",
    "[data-product-price]",
    "[data-current-price]",
    # Australian retailers
    ".product-price .Price",        # Chemist Warehouse
    ".prices .sell-price",          # JB Hi-Fi
    "[data-testid='price-value']",  # Coles
    ".primary__offer-text",         # Woolworths
    ".prcAct",                      # Harvey Norman
    # Generic patterns (most specific first)
    ".price--current",
    ".price__current",
    ".current-price",
    ".sale-price",
    ".offer-price",
    ".special-price",
    "#price",
    ".price",
]


def _parse_price(text: str):
    """
    Extract a price from text like '$24.99', '24,99 €', or '1,299.00'.
    Distinguishes European decimal commas (59,90) from thousands separators (1,299.00).
    """
    # European format: digits, comma, exactly 1-2 digits, then non-digit or end
    # e.g. "59,90" or "1.299,90"
    euro_match = re.search(r"\d+(?:\.\d{3})*,(\d{1,2})(?:\D|$)", text)
    if euro_match:
        # Replace thousands dots, then convert decimal comma to dot
        cleaned = re.sub(r"\.(?=\d{3})", "", text)
        cleaned = cleaned.replace(",", ".")
        m = re.search(r"\d+\.\d+", cleaned)
        return float(m.group()) if m else None

    # Standard format: optional thousands commas, dot decimal — e.g. "$1,299.00" or "$24.99"
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


def autodetect_selector(url: str, timeout: int = 20000):
    """
    Returns (selector, price_float, raw_text) on success, or (None, None, error_string).
    Tries CANDIDATE_SELECTORS in order, then falls back to a JS heuristic scan.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, None, "playwright not installed — run: pip install playwright && playwright install chromium"

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

            # Phase 1: try each candidate selector
            for sel in CANDIDATE_SELECTORS:
                try:
                    el = page.query_selector(sel)
                    if el is None:
                        continue
                    raw = (el.text_content() or "").strip()
                    # For data-price attributes, also try the attribute value
                    if not raw and sel.startswith("[data-"):
                        attr = sel.strip("[]").split("=")[0]
                        raw = (el.get_attribute(attr) or "").strip()
                    price = _parse_price(raw)
                    if price is not None and price > 0:
                        return sel, price, raw
                except Exception:
                    continue

            # Phase 2: JS heuristic — find elements whose visible text looks like a price
            results = page.evaluate("""() => {
                const priceRe = /\\$[\\d,]+(?:\\.\\d{1,2})?/;
                const candidates = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    { acceptNode: n => priceRe.test(n.textContent) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP }
                );
                let node;
                while ((node = walker.nextNode()) && candidates.length < 10) {
                    const el = node.parentElement;
                    if (!el || el.offsetParent === null) continue;
                    const tag = el.tagName.toLowerCase();
                    const id = el.id ? '#' + el.id : '';
                    const cls = el.className && typeof el.className === 'string'
                        ? '.' + el.className.trim().split(/\\s+/)[0] : '';
                    candidates.push({
                        selector: id || (cls ? tag + cls : tag),
                        text: el.innerText.trim().slice(0, 40)
                    });
                }
                return candidates;
            }""")

            for candidate in (results or []):
                sel = candidate.get("selector", "")
                raw = candidate.get("text", "")
                if not sel or not raw:
                    continue
                price = _parse_price(raw)
                if price is not None and price > 0:
                    return sel, price, raw

            return None, None, "Could not detect a price selector on this page"

        except Exception as exc:
            return None, None, f"ERROR: {exc}"
        finally:
            browser.close()
