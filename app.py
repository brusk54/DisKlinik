import sqlite3
import os
from flask import Flask, render_template_string, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = 'dis_klinik_gizli_anahtar'

# Veritabani ve tablo/sutunlarin guvenli kurulumu
def check_and_database_setup():
    db_path = 'klinik.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Hastalar tablosu
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
    
    # Eksik sutun kontrolu ve eklenmesi
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

# Guvenli SQL calistirma yardimcisi
def execute_query(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = None
    if fetchone:
        res = cursor.fetchone()
    elif fetchall:
        res = cursor.fetchall()
    conn.commit()
    conn.close()
    return res

@app.route('/')
def index():
    return redirect(url_for('doktor_giris'))

@app.route('/doktor-giris', methods=['GET', 'POST'])
def doktor_giris():
    if request.method == 'POST':
        sifre = request.form.get('sifre')
        if sifre == '1234':  # Örnek şifre
            session['doktor'] = True
            return redirect(url_for('doktor_panel'))
        else:
            return render_template_string('<h3>Hatalı Şifre!</h3><a href="/doktor-giris">Geri dön</a>')
    
    return '''
        <h2>Diş Klinik - Doktor Girişi</h2>
        <form method="POST">
            <input type="password" name="sifre" placeholder="Şifre" required>
            <button type="submit">Giriş Yap</button>
        </form>
    '''

@app.route('/doktor-panel')
def doktor_panel():
    if not session.get('doktor'):
        return redirect(url_for('doktor_giris'))
    
    klinik_id = 1  # Varsayılan klinik ID
    hastalar = execute_query("SELECT * FROM hastalar WHERE klinik_id = ? ORDER BY id DESC", (klinik_id,), fetchall=True) or []
    
    html = '''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Doktor Paneli</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f4f7f6; color: #333; }
            h2 { color: #0277bd; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #fff; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background: #0288d1; color: white; }
            form { margin-top: 20px; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            input { padding: 8px; margin-right: 10px; width: 200px; }
            button { padding: 9px 15px; background: #0288d1; color: white; border: none; cursor: pointer; border-radius: 4px; }
            button:hover { background: #01579b; }
            .logout { float: right; color: red; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <h2>Doktor Paneli <a href="/cikis" class="logout">Çıkış Yap</a></h2>
        
        <form action="/hasta-ekle" method="POST">
            <h3>Yeni Hasta Ekle</h3>
            <input type="text" name="ad_soyad" placeholder="Ad Soyad" required>
            <input type="text" name="telefon" placeholder="Telefon" required>
            <input type="date" name="randevu_tarihi" required>
            <input type="time" name="randevu_saati" required>
            <button type="submit">Kaydet</button>
        </form>

        <h3>Kayıtlı Hastalar</h3>
        <table>
            <tr>
                <th>ID</th>
                <th>Ad Soyad</th>
                <th>Telefon</th>
                <th>Randevu Tarihi</th>
                <th>Randevu Saati</th>
            </tr>
            {% for h in hastalar %}
            <tr>
                <td>{{ h[0] }}</td>
                <td>{{ h[1] }}</td>
                <td>{{ h[2] }}</td>
                <td>{{ h[3] }}</td>
                <td>{{ h[4] }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    '''
    return render_template_string(html, hastalar=hastalar)

@app.route('/hasta-ekle', methods=['POST'])
def hasta_ekle():
    if not session.get('doktor'):
        return redirect(url_for('doktor_giris'))
    
    ad_soyad = request.form.get('ad_soyad')
    telefon = request.form.get('telefon')
    randevu_tarihi = request.form.get('randevu_tarihi')
    randevu_saati = request.form.get('randevu_saati')
    klinik_id = 1
    
    execute_query(
        "INSERT INTO hastalar (ad_soyad, telefon, randevu_tarihi, randevu_saati, klinik_id) VALUES (?, ?, ?, ?, ?)",
        (ad_soyad, telefon, randevu_tarihi, randevu_saati, klinik_id)
    )
    return redirect(url_for('doktor_panel'))

@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('doktor_giris'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)