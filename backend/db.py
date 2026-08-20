"""SQLite 数据层（零依赖，等价于 live-py 的 Prisma users/scores 模型）。"""
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH


def now_iso():
    """当前 UTC 时间，ISO8601 字符串。"""
    return datetime.now(timezone.utc).isoformat()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让结果可以按列名访问
    return conn


def init_db():
    """建表：users（账号）、scores（每局成绩）。幂等。"""
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            pw_hash    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scores (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT NOT NULL,
            score     INTEGER NOT NULL,
            played_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_scores_user ON scores(username)"
    )
    conn.commit()
    conn.close()
