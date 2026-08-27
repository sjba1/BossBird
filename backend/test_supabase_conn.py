r"""本地验证 Supabase 连接串是否能连通。

用法：
    C:\Users\Administrator\Desktop\vibe_coding\Bird\backend\.venv\Scripts\python.exe test_supabase_conn.py "postgresql://postgres:密码@db.xxxxxx.supabase.co:5432/postgres"
"""
import sys

try:
    import psycopg2
except ImportError:
    print("[ERROR] 当前环境没装 psycopg2。请先激活 .venv 或运行：pip install psycopg2-binary")
    sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("用法：python test_supabase_conn.py '<URI>'")
        sys.exit(1)

    uri = sys.argv[1]
    try:
        conn = psycopg2.connect(uri)
        cur = conn.cursor()
        cur.execute("SELECT version(), current_database(), current_user")
        row = cur.fetchone()
        print("[OK] 连接成功")
        print(f"  数据库版本: {row[0].split(' on ')[0]}")
        print(f"  当前数据库: {row[1]}")
        print(f"  当前用户  : {row[2]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
