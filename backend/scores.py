"""分数 Blueprint：取历史 / 存一局。均带 JWT 守卫。"""
from flask import Blueprint, jsonify, request

from db import get_conn, now_iso
from jwt_utils import decode_token

scores_bp = Blueprint("scores", __name__)

# 历史容量上限：每用户最多保留 / 返回最近 100 局
HISTORY_LIMIT = 100


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


@scores_bp.get("/scores")
def get_scores():
    username = _auth_username()
    if not username:
        return jsonify(error="未登录或登录已过期"), 401

    # 分页参数：page 从 1 起，page_size 单页上限 HISTORY_LIMIT
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 10, type=int)
    page = max(page, 1)
    page_size = max(1, min(page_size, HISTORY_LIMIT))

    conn = get_conn()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM scores WHERE username=?", (username,)
        ).fetchone()[0]
        total = min(total, HISTORY_LIMIT)  # 展示容量上限 100
        best_row = conn.execute(
            "SELECT MAX(score) FROM scores WHERE username=?", (username,)
        ).fetchone()[0]
        offset = (page - 1) * page_size
        rows = conn.execute(
            "SELECT score, played_at FROM scores WHERE username=? "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (username, page_size, offset),
        ).fetchall()
        coin_row = conn.execute(
            "SELECT coins, owned_skins FROM users WHERE username=?", (username,)
        ).fetchone()
    finally:
        conn.close()

    history = [{"score": r["score"], "played_at": r["played_at"]} for r in rows]
    total_pages = max(1, (total + page_size - 1) // page_size)
    return jsonify(
        username=username,
        history=history,
        best=best_row if best_row is not None else 0,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        coins=coin_row["coins"],
        owned_skins=coin_row["owned_skins"],
    ), 200


@scores_bp.post("/scores")
def post_score():
    username = _auth_username()
    if not username:
        return jsonify(error="未登录或登录已过期"), 401

    data = request.get_json(silent=True) or {}
    score = data.get("score")
    if not isinstance(score, int) or isinstance(score, bool) or score < 0:
        return jsonify(error="score 必须是非负整数"), 400
    # 本局金币：玩家游戏内实际吃到的金币道具数量（不再按得分折算）
    coins = data.get("coins")
    if not isinstance(coins, int) or isinstance(coins, bool) or coins < 0:
        return jsonify(error="coins 必须是非负整数"), 400

    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO scores (username, score, played_at) VALUES (?,?,?)",
            (username, score, now_iso()),
        )
        # 容量上限：只保留该用户最近 HISTORY_LIMIT 局，超出部分删掉
        conn.execute(
            "DELETE FROM scores WHERE username=? AND id NOT IN ("
            "  SELECT id FROM scores WHERE username=? ORDER BY id DESC LIMIT ?"
            ")",
            (username, username, HISTORY_LIMIT),
        )
        # 结算金币：按本局吃到的金币道具数量累加进玩家总金币
        gain = coins
        conn.execute(
            "UPDATE users SET coins = coins + ? WHERE username=?", (gain, username)
        )
        conn.commit()
        coin_row = conn.execute(
            "SELECT coins FROM users WHERE username=?", (username,)
        ).fetchone()
    finally:
        conn.close()

    return jsonify(ok=True, gain=gain, coins=coin_row["coins"]), 201


@scores_bp.post("/buy-skin")
def buy_skin():
    """用金币购买皮肤：校验合法性 / 未拥有 / 余额足够，扣币并写入 owned_skins。"""
    username = _auth_username()
    if not username:
        return jsonify(error="未登录或登录已过期"), 401

    data = request.get_json(silent=True) or {}
    skin_id = data.get("skin_id")
    if not isinstance(skin_id, int) or isinstance(skin_id, bool):
        return jsonify(error="skin_id 必须是整数"), 400

    # 价格表（须与前端 BossBird.html 的 SKINS.price 保持一致）
    PRICES = {0: 100, 1: 200, 2: 300, 3: 500}
    if skin_id not in PRICES:
        return jsonify(error="无效皮肤"), 400
    price = PRICES[skin_id]

    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT coins, owned_skins FROM users WHERE username=?", (username,)
        ).fetchone()
        owned = set(row["owned_skins"].split(",")) if row["owned_skins"] else set()
        if str(skin_id) in owned:
            return jsonify(error="已拥有该皮肤"), 409
        if row["coins"] < price:
            return jsonify(error="金币不足", need=price - row["coins"]), 402
        owned = owned | {str(skin_id)}
        owned_skins = ",".join(sorted(owned, key=lambda x: int(x)))
        new_coins = row["coins"] - price
        conn.execute(
            "UPDATE users SET coins=?, owned_skins=? WHERE username=?",
            (new_coins, owned_skins, username),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify(ok=True, coins=new_coins, owned_skins=owned_skins), 200
