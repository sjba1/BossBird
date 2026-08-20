# BossBird 部署到 Railway 运行手册

把 Flask 后端 + PWA 整工程同源部署到 Railway（Python 云主机）。
部署后后端 7×24 跑在云端，**不再依赖这台公司电脑开机**；成绩落在云端持久卷，换手机/电脑登录同一账号即可同步。

## 已完成的代码改造（无需你再改）
- `backend/app.py`：`app` 提到模块级，端口读环境变量 `$PORT`（gunicorn 以 `backend.app:app` 加载）。
- `backend/config.py`：`DB_PATH` 支持环境变量 `BIRD_DB_PATH`，默认仍是 `backend/bird.db`。
- `backend/requirements.txt`：新增 `gunicorn`（生产 WSGI 服务器）。
- `Procfile`：`web: gunicorn backend.app:app --bind 0.0.0.0:$PORT`。
- **前端零改动**：Flask 同源托管 PWA，`/api/` 相对路径原样生效，无需 CORS。

## 部署步骤
1. 注册 https://railway.app 账号（可用 GitHub 登录）。
2. 推代码到 GitHub（本机已 `git init` 并提交）：
   ```
   git remote add origin <你的仓库地址>
   git push -u origin main
   ```
   （不想用 GitHub，也可装 Railway CLI 后 `railway link` + `railway up` 直接拖文件夹部署。）
3. Railway 控制台 → New Project → Deploy from GitHub repo，选 Bird 仓库。
4. 加持久卷（关键，否则 SQLite 重启被清空）：
   Project → Volumes → 新建 Volume，挂载路径填 `/data`。
5. 设环境变量（Project → Variables）：
   - `BIRD_SECRET` = 一串随机串，生成：`python -c "import secrets;print(secrets.token_urlsafe(32))"`
   - `BIRD_DB_PATH` = `/data/bird.db`
   - `PORT` 由平台自动注入，**不用设**。
6. 部署完成后 Railway 分配一个 `*.up.railway.app` 域名（自带 HTTPS）。
7. 打开该域名 → 注册/登录 → 玩一局，成绩写入云端 SQLite。
8. 安装 PWA：浏览器"添加到主屏幕"，之后换设备登录同一账号，成绩都在。

## 注意事项
- 本地已有的 `sjb` 账号和历史分数在 `backend/bird.db`，**不会自动同步**到云端（云端是空库，首次访问自动建表）。需要迁移旧数据可后续单独处理。
- 多设备同步的前提：各设备登录**同一账号**。token 存在浏览器 localStorage（每台设备各自登录一次即可）。
- 不要在本地用内网穿透（ngrok/frp）把这台电脑暴露公网当服务器——电脑一关就挂、还暴露公司内网。
- 升级/改代码后，推一次 GitHub（或 `railway up`）即触发重新部署，云端自动拉新版本。
