# BossBird 后端部署手册（Render + Postgres）

> 原规划用 Railway，但其免费额度（1 个服务）已用满，故改用 **Render**（免费版 Web Service 不限数量，且自带免费 Postgres）。
> 代码已同时兼容本地 SQLite 与部署 Postgres：不设 `DATABASE_URL` 走 SQLite，设了走 Postgres（由 Render 关联数据库后自动注入）。

## 代码改动一览（相对纯本地版）
- `backend/app.py`：模块级 `app` + 端口读 `$PORT` + 把 `backend/` 加入 `sys.path`（保证 gunicorn `backend.app:app` 能加载）。
- `backend/config.py`：新增 `DATABASE_URL`（Postgres 连接串，部署时由 Render 注入）。
- `backend/db.py`：双兼容数据层。Postgres 模式用 `psycopg2` + `DictCursor`，并把 SQL 里的 `?` 占位符自动翻译成 `%s`；`init_db` 按后端选 DDL（`SERIAL` vs `AUTOINCREMENT`）。
- `backend/requirements.txt`：新增 `psycopg2-binary>=2.9`。
- 新增 `Procfile`：`web: gunicorn backend.app:app --bind 0.0.0.0:$PORT`。

## 在 Render 上部署（一次性）
1. render.com 注册/登录（用 GitHub 授权）→ **New +** → **Web Service** → 连 GitHub 选 `sjba1/BossBird`。
2. 配置：
   - Runtime：**Python 3**
   - Build Command：留空（Render 自动读 requirements.txt 安装依赖）
   - Start Command：`gunicorn backend.app:app --bind 0.0.0.0:$PORT`
   - Plan：**Free**
3. 创建 **Postgres** 实例：左侧 **New +** → **PostgreSQL** → 选 Free → Create。
4. 回到 Web Service → **Environment** → 点 **Connect** 关联刚才的 Postgres 实例。关联后 Render 会自动注入 `DATABASE_URL` 环境变量（无需手填）。
5. 另外手动加一个环境变量（安全）：`BIRD_SECRET` = 一串随机长字符串（≥32 字节，别用默认值）。
6. 保存 → Render 自动构建部署。首次启动 `init_db()` 会自动建 `users`/`scores` 表。

## 验证
部署完拿到 `https://xxx.onrender.com`（自带 HTTPS）：
- 打开 → 注册账号 → 玩一局 → 成绩写入 Postgres。
- 换手机/电脑登录同一账号，成绩同步（数据在云端数据库，不因重启丢失）。
- 本地可让 AI 用 curl 验 `/api/register`、`/api/scores`。

## 本地开发
不设任何环境变量直接 `python app.py`（在 `backend/` 目录下），使用 `backend/bird.db`（SQLite），与线上逻辑一致。

## 注意
- Render 免费 Web Service 15 分钟无访问会休眠，首次访问需几秒冷启动，属正常。
- Postgres 免费版有存储/连接数上限，够小游戏用；如需更高配可在 Render 上升级。
- 本地 `backend/bird.db` 的旧分数不会自动同步到云端（云端是独立 Postgres 库）。
