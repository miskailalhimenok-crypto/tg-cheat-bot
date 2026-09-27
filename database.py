# Python | database.py | python-telegram-bot 20+ | SQLite layer

import sqlite3
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                got_file    INTEGER DEFAULT 0,   -- 1 если уже получил файл
                joined_at   TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                downloaded_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))
        conn.commit()


def has_got_file(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT got_file FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row and row["got_file"])


def mark_got_file(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET got_file = 1 WHERE user_id = ?", (user_id,)
        )
        conn.execute(
            "INSERT INTO downloads (user_id) VALUES (?)", (user_id,)
        )
        conn.commit()


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        got   = conn.execute("SELECT COUNT(*) FROM users WHERE got_file=1").fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM downloads WHERE date(downloaded_at)=date('now')"
        ).fetchone()[0]
        return {"total_users": total, "got_file": got, "downloads_today": today}


def get_all_users() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users").fetchall()
        return [r["user_id"] for r in rows]
