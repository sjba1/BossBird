"""JWT 签发 / 校验（复用 live-py 的 Bearer 模式）。"""
import time

import jwt

from config import SECRET_KEY, TOKEN_EXPIRE_SECONDS


def encode_token(username):
    """为某用户签发一个 HS256 token，带 sub / iat / exp 声明。"""
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    """校验 token，返回 payload；非法/过期会抛 jwt 异常，由调用方捕获。"""
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
