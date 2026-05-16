import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "prices.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_checks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name  TEXT NOT NULL,
                url        TEXT NOT NULL,
                price      REAL,
                raw_price  TEXT,
                checked_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS check_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name  TEXT NOT NULL,
                url        TEXT NOT NULL,
                result     TEXT NOT NULL,
                price      REAL,
                raw_price  TEXT,
                checked_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_changes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name  TEXT NOT NULL,
                url        TEXT NOT NULL,
                old_price  REAL NOT NULL,
                new_price  REAL NOT NULL,
                direction  TEXT NOT NULL,
                changed_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)


def record_price(item_name: str, url: str, price, raw_price: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO price_checks (item_name, url, price, raw_price) VALUES (?, ?, ?, ?)",
            (item_name, url, price, raw_price),
        )


def get_last_price(url: str):
    with _conn() as conn:
        row = conn.execute(
            "SELECT price FROM price_checks WHERE url = ? AND price IS NOT NULL ORDER BY checked_at DESC LIMIT 1",
            (url,),
        ).fetchone()
    return row["price"] if row else None


def get_history(url: str, limit: int = 20):
    with _conn() as conn:
        return conn.execute(
            "SELECT item_name, price, raw_price, checked_at FROM price_checks "
            "WHERE url = ? ORDER BY checked_at DESC LIMIT ?",
            (url, limit),
        ).fetchall()


def get_all_history(limit: int = 50):
    with _conn() as conn:
        return conn.execute(
            "SELECT item_name, url, price, raw_price, checked_at FROM price_checks "
            "ORDER BY checked_at DESC LIMIT ?",
            (limit,),
        ).fetchall()


def log_check(item_name: str, url: str, result: str, price, raw_price: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO check_log (item_name, url, result, price, raw_price) VALUES (?, ?, ?, ?, ?)",
            (item_name, url, result, price, raw_price),
        )


def get_check_logs(limit: int = 200):
    with _conn() as conn:
        return conn.execute(
            "SELECT item_name, url, result, price, raw_price, checked_at FROM check_log "
            "ORDER BY checked_at DESC LIMIT ?",
            (limit,),
        ).fetchall()


def record_price_change(item_name: str, url: str, old_price: float, new_price: float, direction: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO price_changes (item_name, url, old_price, new_price, direction) VALUES (?, ?, ?, ?, ?)",
            (item_name, url, old_price, new_price, direction),
        )


def migrate_url(old_url: str, new_url: str):
    """Rewrite the URL across all history tables so trends survive a URL change."""
    with _conn() as conn:
        for table in ("price_checks", "check_log", "price_changes"):
            conn.execute(f"UPDATE {table} SET url = ? WHERE url = ?", (new_url, old_url))


def get_latest_direction(url: str):
    """Returns 'drop', 'rise', or None based on the most recent price change."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT direction FROM price_changes WHERE url = ? ORDER BY changed_at DESC LIMIT 1",
            (url,),
        ).fetchone()
    return row["direction"] if row else None


def get_price_changes(url: str):
    with _conn() as conn:
        return conn.execute(
            "SELECT item_name, old_price, new_price, direction, changed_at FROM price_changes "
            "WHERE url = ? ORDER BY changed_at DESC",
            (url,),
        ).fetchall()
