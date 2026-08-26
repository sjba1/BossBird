"""好友 Blueprint：查好友列表（含好友排行榜）/ 按好友码互加好友。均带 JWT 守卫。"""
from flask import Blueprint, jsonify, request

from db import get_conn, now_iso
from jwt_utils import decode_token

friends_bp = Blueprint("friends", __name__)


def _auth_username():
    """从 Authorization: Bearer <token> 解出用户名；失败返回 None。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    try:
        payload = decode_token(token)
    except Exception:
        return None
    return payload.get("sub")


@friends_bp.get("/friends")
def list_friends():
    username = _auth_username()
    if not username:
        return jsonify(error="未登录或登录已过期"), 401

    conn = get_conn()
    try:
        me = conn.execute(
            "SELECT uid FROM users WHERE username=?", (username,)
        ).fetchone()
        my_uid = me["uid"] if me else ""
        my_best_row = conn.execute(
            "SELECT MAX(score) FROM scores WHERE username=?", (username,)
        ).fetchone()
        my_best = my_best_row[0] if (my_best_row and my_best_row[0] is not None) else 0

        # 好友 = 与我成对（user_a 或 user_b 任一侧为我）的所有其他用户
        rows = conn.execute(
            "SELECT u.username, u.uid, "
            "(SELECT MAX(score) FROM scores s WHERE s.username=u.username) AS best "
            "FROM users u WHERE u.username IN ("
            "  SELECT user_b FROM friends WHERE user_a=? "
            "  UNION "
            "  SELECT user_a FROM friends WHERE user_b=?"
            ")",
            (username, username),
        ).fetchall()
    finally:
        conn.close()

    # 排行榜包含「自己」+ 所有好友，按最高分降序统一排序
    friends = [{"username": username, "uid": my_uid, "best": my_best, "me": True}]
    for r in rows:
        friends.append(
            {"username": r["username"], "uid": r["uid"], "best": r["best"] or 0, "me": False}
        )
    friends.sort(key=lambda x: -x["best"])
    return jsonify(uid=my_uid, friends=friends), 200


@friends_bp.post("/friends/add")
def add_friend():
    username = _auth_username()
    if not username:
        return jsonify(error="未登录或登录已过期"), 401

    data = request.get_json(silent=True) or {}
    code = (data.get("friend_uid") or "").strip().upper()
    if not code:
        return jsonify(error="请输入好友码"), 400

    conn = get_conn()
    try:
        target = conn.execute(
            "SELECT username, uid FROM users WHERE uid=?", (code,)
        ).fetchone()
        if not target:
            return jsonify(error="好友码不存在"), 404
        if target["username"] == username:
            return jsonify(error="不能添加自己为好友"), 400
        # 归一化对称对（字母序小的在前），避免 (A,B) 与 (B,A) 重复
        a, b = sorted([username, target["username"]])
        exists = conn.execute(
            "SELECT 1 FROM friends WHERE user_a=? AND user_b=?", (a, b)
        ).fetchone()
        if exists:
            return jsonify(error="已经是好友了"), 409
        conn.execute(
            "INSERT INTO friends (user_a, user_b, created_at) VALUES (?,?,?)",
            (a, b, now_iso()),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify(ok=True, friend=target["username"]), 200
