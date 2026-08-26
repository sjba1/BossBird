"""数据层：本地开发用 SQLite，部署（Render）用 Postgres，靠 DATABASE_URL 切换。
等价于 live-py 的 Prisma users/scores 模型。

- 本地：不设 DATABASE_URL，回落到 SQLite（backend/bird.db 或 BIRD_DB_PATH 指定的文件）。
- 部署：设 DATABASE_URL=postgres://...（Render 关联 Postgres 实例后自动注入），走 pg8000 纯 Python 驱动。

对外暴露的接口（get_conn / init_db / now_iso）对调用方透明：
scores.py、auth.py 里的 SQL 继续用 ? 占位符即可，本模块在 Postgres 模式下自动翻译成 %s。
"""
import os
import random
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse

from config import DB_PATH, DATABASE_URL

# 好友码字母表：Crockford base32（去掉易混的 I L O U），
# 6 位 + "BB-" 前缀，约 32^6 ≈ 10 亿种组合，足够小游戏且难猜。
_FC_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'


def gen_friend_code():
    """生成一个形如 BB-7F3K9X 的随机好友码。"""
    return 'BB-' + ''.join(random.choice(_FC_ALPHABET) for _ in range(6))


def now_iso():
    """当前 UTC 时间，ISO8601 字符串。"""
    return datetime.now(timezone.utc).isoformat()


# 是否使用 Postgres：DATABASE_URL 以 postgres:// 或 postgresql:// 开头
USE_PG = bool(DATABASE_URL) and DATABASE_URL.startswith(("postgres://", "postgresql://"))

if USE_PG:
    import pg8000.dbapi

    # pg8000 只认 postgresql://，Render 给的是 postgres://，这里归一化一下
    _PG_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # 进程级连接复用：避免每次请求都新建连接 + 等 Neon 计算端点从休眠唤醒（1~2s）。
    # 首次唤醒后连接保持热，活跃期间请求降到几十 ms；连接断开（idle 超时）时自动重连。
    _pg_conn = None

    def _get_pg_conn():
        global _pg_conn
        if _pg_conn is not None:
            try:
                cur = _pg_conn.cursor()
                cur.execute("SELECT 1")
                cur.close()
                if os.environ.get("DB_DEBUG"):
                    print("[db] REUSE pg connection", flush=True)
                return _pg_conn
            except Exception:
                _pg_conn = None
        _pg_conn = pg8000.dbapi.connect(**_parse_pg_url(_PG_URL))
        if os.environ.get("DB_DEBUG"):
            print("[db] NEW pg connection", flush=True)
        return _pg_conn


def _parse_pg_url(url):
    """把 postgresql://... 解析成 pg8000.dbapi.connect 能吃的关键字参数。"""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/") or None,
        "user": parsed.username,
        "password": parsed.password,
        # Neon、Supabase 等托管 Postgres 强制 SSL，pg8000 用 ssl_context=True 开启默认 SSL 上下文
        "ssl_context": True,
    }


class _Row:
    """兼容 sqlite3.Row / psycopg2 DictRow 的行对象：支持 row['col'] 和 row[0]。"""

    def __init__(self, values, columns):
        self._values = tuple(values)
        self._columns = tuple(columns)
        self._col_index = {name: i for i, name in enumerate(columns)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._col_index[key]]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._col_index.keys()

    def __repr__(self):
        return repr(dict(zip(self._columns, self._values)))


class _Cursor:
    """游标包装：把 pg8000 返回的元组行包装成 _Row，保持与 sqlite3.Row 一致的访问方式。"""

    def __init__(self, cur):
        self._cur = cur

    def _wrap_row(self, row):
        if row is None:
            return None
        columns = [desc[0] for desc in self._cur.description]
        return _Row(row, columns)

    def execute(self, sql, params=()):
        self._cur.execute(sql, params)
        return self

    def fetchone(self):
        return self._wrap_row(self._cur.fetchone())

    def fetchall(self):
        return [self._wrap_row(r) for r in self._cur.fetchall()]

    def fetchmany(self, size=None):
        return [self._wrap_row(r) for r in self._cur.fetchmany(size)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cur.close()

    def __getattr__(self, name):
        return getattr(self._cur, name)


class _Conn:
    """连接包装：让 sqlite3 / pg8000 两种连接对调用方表现一致。

    - execute(sql, params) 返回 cursor（调用方照常用 .fetchone()/.fetchall()）。
    - Postgres 模式下把 SQL 里的 ? 占位符翻译成 %s（pg8000 也只认 %s）。
    - 结果行既能 row["col"] 也能 row[0]，兼容 sqlite3.Row 的写法。
    """

    def __init__(self, conn, persistent=False):
        self._conn = conn
        self._persistent = persistent

    def execute(self, sql, params=()):
        if USE_PG and "?" in sql:
            sql = sql.replace("?", "%s")
        cur = self._conn.cursor()
        cur.execute(sql, params)
        if USE_PG:
            return _Cursor(cur)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        if self._persistent:
            return  # PG 模式：归还连接池，不真正关闭，供后续请求复用
        self._conn.close()


def get_conn():
    if USE_PG:
        return _Conn(_get_pg_conn(), persistent=True)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return _Conn(conn, persistent=False)


def init_db():
    """建表：users（账号 + 金币/皮肤）、scores（每局成绩）。幂等。

    皮肤经济相关字段：
      coins        INTEGER  玩家总金币（每局得分 // 3 累加）
      owned_skins  TEXT     已拥有皮肤 id 列表，逗号分隔，默认 '0'（默认皮肤）
    """
    conn = get_conn()
    try:
        if USE_PG:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id          SERIAL PRIMARY KEY,
                    username    VARCHAR(64) UNIQUE NOT NULL,
                    pw_hash     TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    coins       INTEGER NOT NULL DEFAULT 0,
                    owned_skins TEXT NOT NULL DEFAULT '0',
                    uid         VARCHAR(16) NOT NULL DEFAULT ''
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
            # 对早期已存在的旧库补列（幂等）
            conn.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS coins INTEGER NOT NULL DEFAULT 0"
            )
            conn.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS owned_skins TEXT NOT NULL DEFAULT '0'"
            )
            conn.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS uid VARCHAR(16) NOT NULL DEFAULT ''"
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    username    TEXT UNIQUE NOT NULL,
                    pw_hash     TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    coins       INTEGER NOT NULL DEFAULT 0,
                    owned_skins TEXT NOT NULL DEFAULT '0',
                    uid         TEXT NOT NULL DEFAULT ''
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
            # SQLite 不支持 ADD COLUMN IF NOT EXISTS，先 PRAGMA 检查再补列
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "coins" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN coins INTEGER NOT NULL DEFAULT 0")
            if "owned_skins" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN owned_skins TEXT NOT NULL DEFAULT '0'")
            if "uid" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN uid TEXT NOT NULL DEFAULT ''")
        # 好友关系表：归一化对称对（user_a < user_b 字典序，避免重复/双向冗余）
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS friends (
                user_a      TEXT NOT NULL,
                user_b      TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                PRIMARY KEY (user_a, user_b)
            )
            """
        )
        # 历史账号补 uid（新注册在 auth.register 已生成）：给缺失 uid 的行分配唯一好友码
        orphan_rows = conn.execute(
            "SELECT username FROM users WHERE uid IS NULL OR uid = ''"
        ).fetchall()
        for _r in orphan_rows:
            _code = gen_friend_code()
            while conn.execute("SELECT id FROM users WHERE uid = ?", (_code,)).fetchone():
                _code = gen_friend_code()
            conn.execute("UPDATE users SET uid = ? WHERE username = ?", (_code, _r["username"]))
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scores_user ON scores(username)"
        )
        conn.commit()
    finally:
        conn.close()
