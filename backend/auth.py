"""鉴权 Blueprint：注册 / 登录。
密码用 werkzeug 的 generate_password_hash（底层即 PBKDF2-SHA256），
与直播平台 live-py 的 PBKDF2 哈希策略一致。
"""
import re

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_conn, now_iso, gen_friend_code
from jwt_utils import encode_token

auth_bp = Blueprint("auth", __name__)

# 用户名规则：2-20 位，字母/数字/中文/下划线（与前端校验一致）
_USER_RE = re.compile(r"^[一-龥A-Za-z0-9_]{2,20}$")


def _username_valid(u):
    return bool(_USER_RE.match(u))


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(error="用户名和密码不能为空"), 400
    if not _username_valid(username):
        return jsonify(error="用户名 2-20 位（字母/数字/中文/下划线）"), 400
    if len(password) < 6:
        return jsonify(error="密码至少 6 位"), 400

    conn = get_conn()
    try:
        exists = conn.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        ).fetchone()
        if exists:
            return jsonify(error="该用户名已被注册"), 409
        # 生成唯一好友码（与已有账号不冲突）
        uid = gen_friend_code()
        while conn.execute("SELECT id FROM users WHERE uid=?", (uid,)).fetchone():
            uid = gen_friend_code()
        pw_hash = generate_password_hash(password)  # 默认 pbkdf2:sha256
        conn.execute(
            "INSERT INTO users (username, pw_hash, created_at, coins, owned_skins, uid) "
            "VALUES (?,?,?,?,?,?)",
            (username, pw_hash, now_iso(), 0, "0", uid),
        )
        conn.commit()
    finally:
        conn.close()

    # 注册成功返回 token（前端仍按 UX 决定要不要自动登录）
    token = encode_token(username)
    return jsonify(token=token, username=username), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(error="用户名和密码不能为空"), 400

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT pw_hash, coins, owned_skins, uid FROM users WHERE username=?", (username,)
        ).fetchone()
    finally:
        conn.close()

    if not row or not check_password_hash(row["pw_hash"], password):
        return jsonify(error="用户名或密码错误"), 401

    token = encode_token(username)
    return jsonify(
        token=token,
        username=username,
        coins=row["coins"],
        owned_skins=row["owned_skins"],
        uid=row["uid"],
    ), 200
