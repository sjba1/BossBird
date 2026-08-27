"""临时调试工具：直接读写本地 bird.db 的金币/已拥有皮肤。
用法:
  python set_wallet.py list
  python set_wallet.py set <username> <coins>            # 把金币改成指定值
  python set_wallet.py add <username> <delta>            # 在现有金币上加/减 delta
  python set_wallet.py owns <username> <ids>              # 把已拥有皮肤改成 0,1,2 这样的逗号串

⚠️ 只动本地 bird.db（不影响线上 Render/Neon），改完登录会看到。
"""
import sqlite3, sys

DB = r"C:\Users\Administrator\Desktop\vibe_coding\Bird\backend\bird.db"


def conn():
    return sqlite3.connect(DB)


def cmd_list():
    c = conn()
    for row in c.execute("SELECT username, coins, owned_skins FROM users ORDER BY id DESC"):
        print(f"  {row[0]:24s}  coins={row[1]:6d}  owned={row[2]}")
    c.close()


def cmd_set(user, coins):
    c = conn()
    cur = c.execute("UPDATE users SET coins=? WHERE username=?", (coins, user))
    c.commit()
    c.close()
    print(f"  ✅ {user} 金币 → {coins}（影响行 {cur.rowcount}）")


def cmd_add(user, delta):
    c = conn()
    cur = c.execute("UPDATE users SET coins = coins + ? WHERE username=?", (delta, user))
    c.commit()
    c.close()
    print(f"  ✅ {user} 金币 {delta:+d}（影响行 {cur.rowcount}）")


def cmd_owns(user, owned_csv):
    """owned_csv 形如 '0,1,2'，id0..3 内合法"""
    c = conn()
    cur = c.execute("UPDATE users SET owned_skins=? WHERE username=?", (owned_csv, user))
    c.commit()
    c.close()
    print(f"  ✅ {user} 拥有皮肤 → {owned_csv}（影响行 {cur.rowcount}）")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "list":
        print("=== 本地用户 ===")
        cmd_list()
    elif args[0] == "set" and len(args) == 3:
        cmd_set(args[1], int(args[2]))
    elif args[0] == "add" and len(args) == 3:
        cmd_add(args[1], int(args[2]))
    elif args[0] == "owns" and len(args) == 3:
        cmd_owns(args[1], args[2])
    else:
        print(__doc__)
