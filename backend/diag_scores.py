import os, sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\vibe_coding\Bird\backend")
os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_2TwNPSAYL5EG@ep-mute-bird-ax8gdklv.c-4.us-east-2.aws.neon.tech/neondb?sslmode=require'

import db
import jwt_utils
import app as appmod
from app import app as flask_app

db.init_db()
tok = jwt_utils.encode_token('diag_probe_user')
print('TOKEN_OK', bool(tok))

with flask_app.test_client() as c:
    h = {'Authorization': 'Bearer ' + tok}
    r = c.post('/api/scores', json={'score': 77}, headers=h)
    print('POST', r.status_code, r.get_json())
    r2 = c.get('/api/scores?page=1&page_size=5', headers=h)
    print('GET', r2.status_code, r2.get_json())
