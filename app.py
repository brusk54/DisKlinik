import sqlite3
import os
from flask import Flask

app = Flask(__name__)
app.secret_key = 'dis_klinik_gizli_anahtar'

def check_and_database_setup():
    db_path = 'klinik.db'
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hastalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_soyad TEXT,
                telefon TEXT,
                randevu_tarihi TEXT,
                randevu_saati TEXT,
                klinik_id INTEGER
            )
        ''')
        conn.commit()
        conn.close()

check_and_database_setup()

@app.route('/')
def index():
    return "Dis Klinik Sistemi Aktif ve Calisiyor!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)