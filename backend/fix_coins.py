"""一次性改金币/皮肤工具（双击或 python fix_coins.py 即可执行）。
修改下方两个变量后运行：
"""
USERNAME = "sjb"          # ← 改成你的账号
COINS = 500               # ← 改成你想要的金币数
OWNED = "0,1,2,3"         # ← 改成 "0" / "0,1" / "0,1,2,3" 任意逗号串

import sqlite3, os
DB = os.path.join(os.path.dirname(__file__), "bird.db")
c = sqlite3.connect(DB)
c.execute("UPDATE users SET coins=? WHERE username=?", (COINS, USERNAME))
c.execute("UPDATE users SET owned_skins=? WHERE username=?", (OWNED, USERNAME))
c.commit()
row = c.execute("SELECT coins, owned_skins FROM users WHERE username=?", (USERNAME,)).fetchone()
c.close()
print(f"✅ {USERNAME}: coins={row[0]}, owned={row[1]}")
