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
