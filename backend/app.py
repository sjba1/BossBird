"""Boss Bird 后端入口。
- /api/*  : 鉴权 + 分数 API（Blueprint）
- 其余路径: 托管前端静态文件（BossBird.html / index.html / manifest / sw.js）
完全复用直播平台 live-py 的分层套路：Flask Blueprint + JWT(Bearer) + PBKDF2 + 数据库。
"""
import os
import sys

# 保证 backend/ 始终在 sys.path 上：
# 本地 `python app.py`（cwd=backend/）和 gunicorn `backend.app:app`（cwd=仓库根）都能正确解析
# `from auth import ...` 这类同级导入。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory

from auth import auth_bp
from config import FRONTEND_DIR
from db import init_db
from scores import scores_bp


def create_app():
    # 静态目录指向 Bird/ 根，url_path 置空让 /BossBird.html、/sw.js、/manifest 等
    # 都能在根路径直接访问（匹配 PWA 的 start_url / scope）。
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
    init_db()
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(scores_bp, url_prefix="/api")

    @app.route("/")
    def index():
        # static_url_path='' 时 Flask 不会把 GET / 自动映射到 index.html，
        # 这里显式补上，使 PWA 的 start_url=/index.html 与 / 都能进游戏。
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


# 模块级创建 app 实例，便于 gunicorn 以 `backend.app:app` 方式加载
app = create_app()

if __name__ == "__main__":
    # 本地开发：0.0.0.0 便于手机同网段访问；PORT 读环境变量（部署平台注入）
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
