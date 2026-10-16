import sqlite3
import os
from flask import Flask, render_template_string, request, redirect, session, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'dis_klinik_gizli_anahtar_2026'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Veritabani ve tablo/sutunlarin guvenli otomatik kurulumu
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
            klinik_id INTEGER,
            ucret TEXT,
            dis_notu TEXT
        )
    ''')
    
    # Fotolar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fotolar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hasta_id INTEGER,
            dosya_adi TEXT
        )
    ''')
    
    # Eksik sutun kontrolu ve eklenmesi (Guvenlik kalkani)
    cursor.execute("PRAGMA table_info(hastalar);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if columns:
        if 'klinik_id' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN klinik_id INTEGER;")
        if 'randevu_tarihi' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN randevu_tarihi TEXT;")
        if 'randevu_saati' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN randevu_saati TEXT;")
        if 'ucret' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN ucret TEXT;")
        if 'dis_notu' not in columns:
            cursor.execute("ALTER TABLE hastalar ADD COLUMN dis_notu TEXT;")
            
    conn.commit()
    conn.close()

check_and_database_setup()

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
        if sifre == '1234':
            session['doktor'] = True
            return redirect(url_for('doktor_panel'))
        else:
            return render_template_string('<h3>Hatalı Şifre!</h3><a href="/doktor-giris">Geri dön</a>')
    
    return '''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Diş Klinik - Doktor Girişi</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-box { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); width: 300px; text-align: center; }
            input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
            button { width: 100%; padding: 10px; background: #0288d1; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
            button:hover { background: #01579b; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>Diş Klinik Giriş</h2>
            <form method="POST">
                <input type="password" name="sifre" placeholder="Doktor Şifresi" required>
                <button type="submit">Giriş Yap</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/doktor-panel')
def doktor_panel():
    if not session.get('doktor'):
        return redirect(url_for('doktor_giris'))
    
    klinik_id = 1
    hastalar = execute_query("SELECT * FROM hastalar WHERE klinik_id = ? ORDER BY id DESC", (klinik_id,), fetchall=True) or []
    
    html = '''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Doktor Paneli</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 30px; background: #f4f7f6; color: #333; }
            h2 { color: #0277bd; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #fff; border-radius: 6px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
            th { background: #0288d1; color: white; }
            tr:hover { background: #f1f5f8; }
            form { margin-top: 20px; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); display: flex; gap: 10px; flex-wrap: wrap; }
            input { padding: 9px; flex: 1; min-width: 150px; border: 1px solid #ccc; border-radius: 4px; }
            button { padding: 10px 20px; background: #0288d1; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; }
            button:hover { background: #01579b; }
            .logout { float: right; color: #d32f2f; text-decoration: none; font-weight: bold; }
            .btn-detay { background: #2e7d32; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; font-size: 14px; }
            .btn-detay:hover { background: #1b5e20; }
        </style>
    </head>
    <body>
        <h2>Doktor Paneli <a href="/cikis" class="logout">Çıkış Yap</a></h2>
        
        <form action="/hasta-ekle" method="POST">
            <input type="text" name="ad_soyad" placeholder="Ad Soyad" required>
            <input type="text" name="telefon" placeholder="Telefon" required>
            <input type="date" name="randevu_tarihi" required>
            <input type="time" name="randevu_saati" required>
            <input type="text" name="ucret" placeholder="Tedavi Ücreti (TL)">
            <button type="submit">Hasta Ekle</button>
        </form>

        <h3>Kayıtlı Hastalar</h3>
        <table>
            <tr>
                <th>ID</th>
                <th>Ad Soyad</th>
                <th>Telefon</th>
                <th>Randevu Tarihi</th>
                <th>Randevu Saati</th>
                <th>Ücret</th>
                <th>İşlemler</th>
            </tr>
            {% for h in hastalar %}
            <tr>
                <td>{{ h[0] }}</td>
                <td>{{ h[1] }}</td>
                <td>{{ h[2] }}</td>
                <td>{{ h[3] }}</td>
                <td>{{ h[4] }}</td>
                <td>{{ h[6] if h[6] else '-' }} TL</td>
                <td><a href="/hasta/{{ h[0] }}" class="btn-detay">Detay / Diş Şeması & Foto</a></td>
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
    ucret = request.form.get('ucret')
    klinik_id = 1
    
    execute_query(
        "INSERT INTO hastalar (ad_soyad, telefon, randevu_tarihi, randevu_saati, klinik_id, ucret) VALUES (?, ?, ?, ?, ?, ?)",
        (ad_soyad, telefon, randevu_tarihi, randevu_saati, klinik_id, ucret)
    )
    return redirect(url_for('doktor_panel'))

@app.route('/hasta/<int:hasta_id>', methods=['GET', 'POST'])
def hasta_detay(hasta_id):
    if not session.get('doktor'):
        return redirect(url_for('doktor_giris'))
    
    if request.method == 'POST':
        dis_notu = request.form.get('dis_notu')
        execute_query("UPDATE hastalar SET dis_notu = ? WHERE id = ?", (dis_notu, hasta_id))
        return redirect(url_for('hasta_detay', hasta_id=hasta_id))
    
    hasta = execute_query("SELECT * FROM hastalar WHERE id = ?", (hasta_id,), fetchone=True)
    fotolar = execute_query("SELECT * FROM fotolar WHERE hasta_id = ?", (hasta_id,), fetchall=True) or []
    
    html = '''
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>Hasta Detay - {{ hasta[1] }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 30px; background: #f4f7f6; color: #333; }
            h2, h3 { color: #0277bd; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            textarea { width: 100%; height: 100px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; margin-top: 10px; }
            button { padding: 10px 20px; background: #0288d1; color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: bold; margin-top: 10px; }
            button:hover { background: #01579b; }
            .gallery { display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px; }
            .photo-card { background: #fff; padding: 10px; border: 1px solid #ddd; border-radius: 6px; text-align: center; }
            .photo-card img { max-width: 150px; height: 150px; object-fit: cover; border-radius: 4px; display: block; margin-bottom: 5px; }
            .back-link { display: inline-block; margin-bottom: 20px; color: #0288d1; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <a href="/doktor-panel" class="back-link">&larr; Panele Geri Dön</a>
        
        <div class="card">
            <h2>Hasta: {{ hasta[1] }}</h2>
            <p><strong>Telefon:</strong> {{ hasta[2] }}</p>
            <p><strong>Randevu:</strong> {{ hasta[3] }} Saat: {{ hasta[4] }}</p>
            <p><strong>Ücret:</strong> {{ hasta[6] if hasta[6] else 'Belirtilmedi' }} TL</p>
        </div>

        <div class="card">
            <h3>🦷 Diş Şeması ve Tedavi Notları</h3>
            <form method="POST">
                <textarea name="dis_notu" placeholder="Diş muayene bulguları ve tedavi notlarını buraya yazın...">{{ hasta[7] if hasta[7] else '' }}</textarea>
                <button type="submit">Notları Kaydet</button>
            </form>
        </div>

        <div class="card">
            <h3>📷 Öncesi / Sonrası Tedavi Fotoğrafları</h3>
            <form action="/hasta/{{ hasta[0] }}/foto-ekle" method="POST" enctype="multipart/form-data">
                <input type="file" name="foto" required accept="image/*">
                <button type="submit">Fotoğraf Yükle</button>
            </form>

            <div class="gallery">
                {% for f in fotolar %}
                <div class="photo-card">
                    <img src="{{ url_for('static', filename='uploads/' + f[2]) }}" alt="Tedavi Foto">
                    <small>Fotoğraf ID: {{ f[0] }}</small>
                </div>
                {% else %}
                <p style="color: #666; margin-top: 10px;">Henüz fotoğraf yüklenmemiş.</p>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, hasta=hasta, fotolar=fotolar)

@app.route('/hasta/<int:hasta_id>/foto-ekle', methods=['POST'])
def foto_ekle(hasta_id):
    if not session.get('doktor'):
        return redirect(url_for('doktor_giris'))
    
    if 'foto' in request.files:
        file = request.files['foto']
        if file.filename != '':
            filename = secure_filename(file.filename)
            unique_filename = f"{hasta_id}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            
            execute_query("INSERT INTO fotolar (hasta_id, dosya_adi) VALUES (?, ?)", (hasta_id, unique_filename))
            
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/cikis')
def cikis():
    session.clear()
    return redirect(url_for('doktor_giris'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)