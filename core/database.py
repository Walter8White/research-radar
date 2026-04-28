import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


DB_PATH = Path("data/items.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cur.fetchall()]

    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_name TEXT,
            category TEXT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            author TEXT,
            published_at TEXT,
            raw_text TEXT,
            score REAL DEFAULT 0,
            momentum_score REAL DEFAULT 0,
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            open_issues INTEGER DEFAULT 0,
            watchers INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Safe migration if table already existed.
    ensure_column(cur, "items", "momentum_score", "REAL DEFAULT 0")
    ensure_column(cur, "items", "stars", "INTEGER DEFAULT 0")
    ensure_column(cur, "items", "forks", "INTEGER DEFAULT 0")
    ensure_column(cur, "items", "open_issues", "INTEGER DEFAULT 0")
    ensure_column(cur, "items", "watchers", "INTEGER DEFAULT 0")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS item_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_url TEXT NOT NULL,
            captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            open_issues INTEGER DEFAULT 0,
            watchers INTEGER DEFAULT 0,
            UNIQUE(item_url, captured_at)
        )
        """
    )

    conn.commit()
    conn.close()


def insert_item(item: Dict) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    inserted = False

    try:
        try:
            cur.execute(
                """
                INSERT INTO items (
                    source_type,
                    source_name,
                    category,
                    title,
                    url,
                    author,
                    published_at,
                    raw_text,
                    score,
                    momentum_score,
                    stars,
                    forks,
                    open_issues,
                    watchers
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.get("source_type"),
                    item.get("source_name"),
                    item.get("category"),
                    item.get("title"),
                    item.get("url"),
                    item.get("author"),
                    item.get("published_at"),
                    item.get("raw_text"),
                    item.get("score", 0),
                    item.get("momentum_score", 0),
                    item.get("stars", 0),
                    item.get("forks", 0),
                    item.get("open_issues", 0),
                    item.get("watchers", 0),
                ),
            )
            inserted = True

        except sqlite3.IntegrityError:
            cur.execute(
                """
                UPDATE items
                SET
                    score = ?,
                    momentum_score = ?,
                    stars = ?,
                    forks = ?,
                    open_issues = ?,
                    watchers = ?,
                    published_at = COALESCE(?, published_at),
                    raw_text = COALESCE(?, raw_text)
                WHERE url = ?
                """,
                (
                    item.get("score", 0),
                    item.get("momentum_score", 0),
                    item.get("stars", 0),
                    item.get("forks", 0),
                    item.get("open_issues", 0),
                    item.get("watchers", 0),
                    item.get("published_at"),
                    item.get("raw_text"),
                    item.get("url"),
                ),
            )
            inserted = False

        conn.commit()
        return inserted

    finally:
        conn.close()


def insert_metric(
    item_url: str,
    stars: int = 0,
    forks: int = 0,
    open_issues: int = 0,
    watchers: int = 0,
) -> None:
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT OR IGNORE INTO item_metrics (
                item_url,
                stars,
                forks,
                open_issues,
                watchers
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item_url,
                stars or 0,
                forks or 0,
                open_issues or 0,
                watchers or 0,
            ),
        )

        conn.commit()
    finally:
        conn.close()


def get_latest_metric_before(item_url: str, hours_ago: int) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM item_metrics
        WHERE item_url = ?
          AND captured_at <= datetime('now', ?)
        ORDER BY captured_at DESC
        LIMIT 1
        """,
        (item_url, f"-{hours_ago} hours"),
    )

    row = cur.fetchone()
    conn.close()

    return dict(row) if row else None


def get_top_items(limit: int = 40) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM items
        ORDER BY score DESC, momentum_score DESC, published_at DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_item_count() -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM items")
    count = cur.fetchone()[0]
    conn.close()
    return count
