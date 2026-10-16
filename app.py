import sqlite3
import os
from flask import Flask, render_template_string, request, redirect, session, url_for, send_from_directory

app = Flask(__name__)
app.secret_key = 'dis_klinik_gizli_anahtar'

# Veritabani ve tablo/sutunlarin guvenli kurulumu
def check_and_database_setup():
    db_path = 'klinik.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Hastalar tablosu yoksa tum sutunlariyla birlikte olustur
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
    
    # Eger tablo onceden varsa ve bu sutunlar eksikse guvenli bir sekilde ekle
    cursor.execute("PRAGMA table_info(hastalar);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if columns:
        if 'klinik_id' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN klinik_id INTEGER;")
        if 'randevu_tarihi' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN randevu_tarihi TEXT;")
        if 'randevu_saati' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN randevu_saati TEXT;")
            
    conn.commit()
    conn.close()

check_and_database_setup()

@app.route('/')
def index():
    return "Dis Klinik Sistemi Aktif ve Calisiyor!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)