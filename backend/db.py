"""数据层：本地开发用 SQLite，部署（Render）用 Postgres，靠 DATABASE_URL 切换。
等价于 live-py 的 Prisma users/scores 模型。

- 本地：不设 DATABASE_URL，回落到 SQLite（backend/bird.db 或 BIRD_DB_PATH 指定的文件）。
- 部署：设 DATABASE_URL=postgres://...（Render 关联 Postgres 实例后自动注入），走 psycopg2。

对外暴露的接口（get_conn / init_db / now_iso）对调用方透明：
scores.py、auth.py 里的 SQL 继续用 ? 占位符即可，本模块在 Postgres 模式下自动翻译成 %s。
"""
import os
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH, DATABASE_URL


def now_iso():
    """当前 UTC 时间，ISO8601 字符串。"""
    return datetime.now(timezone.utc).isoformat()


# 是否使用 Postgres：DATABASE_URL 以 postgres:// 或 postgresql:// 开头
USE_PG = bool(DATABASE_URL) and DATABASE_URL.startswith(("postgres://", "postgresql://"))

if USE_PG:
    import psycopg2
    from psycopg2.extras import DictCursor

    # psycopg2 旧版本只认 postgresql://，Render 给的是 postgres://，这里归一化一下
    _PG_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


class _Conn:
    """连接包装：让 sqlite3 / psycopg2 两种连接对调用方表现一致。

    - execute(sql, params) 返回 cursor（调用方照常用 .fetchone()/.fetchall()）。
    - Postgres 模式下把 SQL 里的 ? 占位符翻译成 %s（psycopg2 只认 %s）。
    - 用 DictCursor，使结果既能 row["col"] 也能 row[0]，兼容 sqlite3.Row 的写法。
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        if USE_PG and "?" in sql:
            sql = sql.replace("?", "%s")
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_conn():
    if USE_PG:
        conn = psycopg2.connect(_PG_URL, cursor_factory=DictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    return _Conn(conn)


def init_db():
    """建表：users（账号）、scores（每局成绩）。幂等。"""
    conn = get_conn()
    try:
        if USE_PG:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    username   VARCHAR(64) UNIQUE NOT NULL,
                    pw_hash    TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (
                    id        SERIAL PRIMARY KEY,
                    username  VARCHAR(64) NOT NULL,
                    score     INTEGER NOT NULL,
                    played_at TEXT NOT NULL
                )
                """
            )
        else:
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
    finally:
        conn.close()
