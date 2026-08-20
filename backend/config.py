"""Boss Bird 后端配置。"""
import os

# 后端目录（backend/）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# SQLite 数据库文件：默认 backend/bird.db；部署时用环境变量 BIRD_DB_PATH 指向持久卷（如 /data/bird.db）
DB_PATH = os.environ.get("BIRD_DB_PATH", os.path.join(BASE_DIR, "bird.db"))
# 前端静态目录（Bird/ 根目录，含 BossBird.html、index.html、manifest、sw.js）
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))

# JWT 签名密钥：生产环境务必通过环境变量 BIRD_SECRET 覆盖（需 >=32 字节）
SECRET_KEY = os.environ.get("BIRD_SECRET", "bossbird-dev-secret-key-change-me-now-32b")
# Token 有效期：60 天
TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 60
