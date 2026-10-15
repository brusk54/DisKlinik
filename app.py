from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'klinik360_gizli_anahtar'

DOKTOR_SIFRE = "1234"

# Veritabanı ve Eksik Sütun Kontrolü (Migration)
def init_db():
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    
    # Hastalar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hastalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT NOT NULL,
            yas TEXT,
            semptomlar TEXT,
            ozel_not TEXT,
            alerji TEXT,
            randevu_tarihi TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Diş işlemleri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dis_islemleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hasta_id INTEGER,
            dis_no TEXT,
            islem_turu TEXT,
            ucret REAL,
            FOREIGN KEY (hasta_id) REFERENCES hastalar (id)
        )
    ''')
    
    # Eski veritabanlarında eksik olabilecek sütunları güvenle ekle
    try:
        cursor.execute("ALTER TABLE hastalar ADD COLUMN randevu_tarihi TEXT")
    except sqlite3.OperationalError:
        pass # Sütun zaten varsa hata verme, devam et

    try:
        cursor.execute("ALTER TABLE hastalar ADD COLUMN alerji TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE hastalar ADD COLUMN ozel_not TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(GIRIS_SECIM_HTML)

@app.route('/doktor-giris', methods=['GET', 'POST'])
def doktor_giris():
    hata = None
    if request.method == 'POST':
        sifre = request.form.get('sifre')
        if sifre == DOKTOR_SIFRE:
            session['doktor_giris'] = True
            return redirect(url_for('doktor_panel'))
        else:
            hata = "Hatalı şifre!"
    return render_template_string(DOKTOR_GIRIS_HTML, hata=hata)

@app.route('/doktor-cikis')
def doktor_cikis():
    session.pop('doktor_giris', None)
    return redirect(url_for('index'))

@app.route('/doktor-panel')
def doktor_panel():
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    
    arama = request.args.get('arama', '')
    if arama:
        cursor.execute("SELECT * FROM hastalar WHERE ad_soyad LIKE ? OR telefon LIKE ?", ('%' + arama + '%', '%' + arama + '%'))
    else:
        cursor.execute("SELECT * FROM hastalar ORDER BY id DESC")
        
    hastalar = cursor.fetchall()

    cursor.execute("SELECT id, ad_soyad, telefon, randevu_tarihi FROM hastalar WHERE randevu_tarihi IS NOT NULL AND randevu_tarihi != '' ORDER BY randevu_tarihi ASC")
    randevular = cursor.fetchall()

    conn.close()
    return render_template_string(DOKTOR_PANEL_HTML, hastalar=hastalar, randevular=randevular, arama=arama)

@app.route('/ekle', methods=['POST'])
def ekle():
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    ad_soyad = request.form['ad_soyad']
    telefon = request.form['telefon']
    yas = request.form['yas']
    secilen_semptomlar = request.form.getlist('semptomlar')
    semptomlar_str = ", ".join(secilen_semptomlar) if secilen_semptomlar else "Belirtilmemiş"
    ozel_not = request.form.get('ozel_not', '')
    alerji = request.form['alerji']
    randevu_tarihi = request.form['randevu_tarihi']

    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO hastalar (ad_soyad, telefon, yas, semptomlar, ozel_not, alerji, randevu_tarihi)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (ad_soyad, telefon, yas, semptomlar_str, ozel_not, alerji, randevu_tarihi))
    conn.commit()
    conn.close()
    return redirect(url_for('doktor_panel'))

@app.route('/hasta-duzenle/<int:hasta_id>', methods=['GET', 'POST'])
def hasta_duzenle(hasta_id):
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        ad_soyad = request.form['ad_soyad']
        telefon = request.form['telefon']
        yas = request.form['yas']
        ozel_not = request.form['ozel_not']
        alerji = request.form['alerji']
        randevu_tarihi = request.form['randevu_tarihi']

        cursor.execute('''
            UPDATE hastalar 
            SET ad_soyad=?, telefon=?, yas=?, ozel_not=?, alerji=?, randevu_tarihi=?
            WHERE id=?
        ''', (ad_soyad, telefon, yas, ozel_not, alerji, randevu_tarihi, hasta_id))
        conn.commit()
        conn.close()
        return redirect(url_for('doktor_panel'))

    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    conn.close()
    return render_template_string(HASTA_DUZENLE_HTML, hasta=hasta)

@app.route('/hasta-sil/<int:hasta_id>')
def hasta_sil(hasta_id):
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    cursor.execute("DELETE FROM hastalar WHERE id = ?", (hasta_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('doktor_panel'))

@app.route('/islem-sil/<int:islem_id>/<int:hasta_id>')
def islem_sil(islem_id, hasta_id):
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dis_islemleri WHERE id = ?", (islem_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/hasta-detay/<int:hasta_id>')
def hasta_detay(hasta_id):
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    cursor.execute("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    islemler = cursor.fetchall()
    conn.close()
    return render_template_string(HASTA_DETAY_HTML, hasta=hasta, islemler=islemler)

@app.route('/dis_islem_ekle/<int:hasta_id>', methods=['POST'])
def dis_islem_ekle(hasta_id):
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    dis_no = request.form['dis_no']
    islem_turu = request.form['islem_turu']
    ucret = request.form['ucret']
    
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO dis_islemleri (hasta_id, dis_no, islem_turu, ucret)
        VALUES (?, ?, ?, ?)
    ''', (hasta_id, dis_no, islem_turu, ucret))
    conn.commit()
    conn.close()
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/hasta-rapor/<int:hasta_id>')
def hasta_rapor(hasta_id):
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    cursor.execute("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    islemler = cursor.fetchall()
    conn.close()
    return render_template_string(HASTA_RAPOR_HTML, hasta=hasta, islemler=islemler)

@app.route('/hasta-giris', methods=['GET', 'POST'])
def hasta_giris():
    hata = None
    if request.method == 'POST':
        telefon = request.form.get('telefon', '').strip()
        conn = sqlite3.connect('klinik.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hastalar WHERE telefon LIKE ?", ('%' + telefon + '%',))
        hasta = cursor.fetchone()
        
        if hasta:
            session['hasta_id'] = hasta[0]
            return redirect(url_for('hasta_profil'))
        else:
            hata = "Kayıt bulunamadı."
        conn.close()
    return render_template_string(HASTA_GIRIS_HTML, hata=hata)

@app.route('/hasta-profil')
def hasta_profil():
    hasta_id = session.get('hasta_id')
    if not hasta_id:
        return redirect(url_for('hasta_giris'))
        
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    cursor.execute("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    islemler = cursor.fetchall()
    conn.close()
    return render_template_string(HASTA_PROFIL_HTML, hasta=hasta, islemler=islemler)

# --- HTML TEMPLATES ---

GIRIS_SECIM_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Klinik360 Portalı</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; text-align: center; color: #333; }
        .box { max-width: 450px; margin: 50px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .logo { max-width: 240px; width: 100%; border-radius: 8px; margin-bottom: 15px; }
        .btn { display: block; width: 100%; padding: 14px; margin: 15px 0; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold; color: white; box-sizing: border-box; }
        .btn-doktor { background: #007bff; }
        .btn-hasta { background: #28a745; }
    </style>
</head>
<body>
    <div class="box">
        <img class="logo" src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=500&q=80">
        <h2>Klinik360 Portalı</h2>
        <a href="/doktor-giris" class="btn btn-doktor">👩‍⚕️ Doktor / Yönetici Girişi</a>
        <a href="/hasta-giris" class="btn btn-hasta">📱 Hasta Randevu & Takip</a>
    </div>
</body>
</html>
'''

DOKTOR_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Doktor Girişi</title>
<style>body{font-family:Arial;background:#e9ecef;padding:20px;text-align:center}.box{max-width:380px;margin:60px auto;background:white;padding:25px;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.1)}input{width:100%;padding:12px;margin:15px 0;border:1px solid #ccc;border-radius:6px;text-align:center;box-sizing:border-box}button{width:100%;padding:12px;background:#007bff;color:white;border:none;border-radius:6px;cursor:pointer}</style></head>
<body>
<div class="box">
    <h2>🔐 Doktor Girişi</h2>
    {% if hata %}<p style="color:red;">{{ hata }}</p>{% endif %}
    <form method="POST">
        <input type="password" name="sifre" placeholder="Şifre (1234)" required>
        <button type="submit">Giriş Yap</button>
    </form>
    <br><a href="/" style="color:#666;text-decoration:none;">⬅ Ana Sayfa</a>
</div>
</body></html>
'''

DOKTOR_PANEL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Doktor Paneli</title>
<style>
body{font-family:Arial;background:#f4f7f6;padding:10px;color:#333}
.container{max-width:900px;margin:auto;background:white;padding:20px;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.1)}
.header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #eee;padding-bottom:10px;margin-bottom:15px}
.logo-container img{max-width:150px}
.takvim-box{background:#e3f2fd;padding:12px;border-radius:8px;margin-bottom:20px;border-left:5px solid #007bff}
form{background:#e9ecef;padding:15px;border-radius:8px;margin-bottom:20px}
input,select,textarea{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:5px;box-sizing:border-box}
.checkbox-group{background:white;padding:10px;border-radius:5px;border:1px solid #ccc;margin:8px 0}
.checkbox-group label{display:block;margin-bottom:5px;cursor:pointer}
button{background:#28a745;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer;font-size:16px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ddd;padding:8px;text-align:left;font-size:13px}
th{background:#007bff;color:white}
.btn-sm{padding:4px 8px;text-decoration:none;border-radius:4px;font-size:12px;display:inline-block;margin:2px}
.btn-info{background:#17a2b8;color:white}.btn-wa{background:#25d366;color:white}.btn-edit{background:#ffc107;color:#000}.btn-del{background:#dc3545;color:white}
</style></head>
<body>
<div class="container">
    <div class="header">
        <div class="logo-container"><img src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=500&q=80"></div>
        <div><span>👩‍⚕️ Doktor Paneli</span> <a href="/doktor-cikis" style="background:#dc3545;color:white;padding:6px 12px;text-decoration:none;border-radius:5px;margin-left:10px;">Çıkış</a></div>
    </div>

    <div class="takvim-box">
        <h3 style="margin-top:0;color:#0056b3;">📆 Yaklaşan Randevu Takvimi</h3>
        {% if randevular %}
            <ul style="margin:0;padding-left:20px;">
            {% for r in randevular %}
                <li><b>{{ r[3] }}</b> - {{ r[1] }} (Tel: {{ r[2] }})</li>
            {% endfor %}
            </ul>
        {% else %}
            <p style="margin:0;color:gray;">Planlanmış randevu yok.</p>
        {% endif %}
    </div>

    <form action="/ekle" method="POST">
        <h3>Yeni Hasta Kaydı</h3>
        <input type="text" name="ad_soyad" placeholder="Hasta Adı Soyadı" required>
        <input type="text" name="telefon" placeholder="Telefon Numarası (0555...)" required>
        <input type="number" name="yas" placeholder="Yaş">
        
        <label><b>Semptomlar ve Şikayetler:</b></label>
        <div class="checkbox-group">
            <label><input type="checkbox" name="semptomlar" value="Şiddetli Ağrı (Apse)"> Şiddetli Ağrı (Apse)</label>
            <label><input type="checkbox" name="semptomlar" value="Hassasiyet (Sıcak/Soğuk)"> Hassasiyet (Sıcak/Soğuk)</label>
            <label><input type="checkbox" name="semptomlar" value="Diş Eti Kanaması"> Diş Eti Kanaması</label>
            <label><input type="checkbox" name="semptomlar" value="Çürük / Kırık Diş"> Çürük / Kırık Diş</label>
            <label><input type="checkbox" name="semptomlar" value="Estetik / Dolgu"> Estetik / Dolgu</label>
        </div>

        <textarea name="ozel_not" placeholder="Doktor Açıklaması..." rows="2"></textarea>
        <input type="text" name="alerji" placeholder="Alerji Durumu (Varsa)">
        <input type="date" name="randevu_tarihi">
        <button type="submit">Hastayı Kaydet</button>
    </form>

    <form method="GET" action="/doktor-panel" style="background:none;padding:0;">
        <input type="text" name="arama" placeholder="İsim veya telefon ile ara..." value="{{ arama }}">
    </form>

    <h2>Kayıtlı Hastalar</h2>
    <table>
        <tr><th>Ad Soyad</th><th>Telefon</th><th>Semptom & Not</th><th>Randevu</th><th>İşlemler</th></tr>
        {% for h in hastalar %}
        <tr>
            <td><b>{{ h[1] }}</b><br><small>Yaş: {{ h[3] }}</small></td>
            <td>{{ h[2] }}</td>
            <td><b>Semptom:</b> {{ h[4] }}<br>{% if h[5] %}<b>Not:</b> {{ h[5] }}{% endif %}</td>
            <td>{{ h[7] }}</td>
            <td>
                <a class="btn-sm btn-info" href="/hasta-detay/{{ h[0] }}">Diş Kartı</a>
                <a class="btn-sm btn-wa" href="https://wa.me/9{{ h[2] }}?text=Sayın%20{{ h[1] }},%20Klinik360%20randevunuzu%20hatırlatırız." target="_blank">WhatsApp</a>
                <a class="btn-sm btn-edit" href="/hasta-duzenle/{{ h[0] }}">Düzenle</a>
                <a class="btn-sm btn-del" href="/hasta-sil/{{ h[0] }}" onclick="return confirm('Silmek istediğinize emin misiniz?')">Sil</a>
            </td>
        </tr>
        {% endfor %}
    </table>
</div>
</body></html>
'''

HASTA_DUZENLE_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Düzenle</title><style>body{font-family:Arial;padding:20px;background:#f4f7f6}.box{max-width:500px;margin:auto;background:white;padding:20px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}input,textarea{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:5px;box-sizing:border-box}button{background:#28a745;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer}</style></head>
<body><div class="box">
    <h2>✏️ Hasta Bilgilerini Düzenle</h2>
    <form method="POST">
        <label>Ad Soyad:</label><input type="text" name="ad_soyad" value="{{ hasta[1] }}" required>
        <label>Telefon:</label><input type="text" name="telefon" value="{{ hasta[2] }}" required>
        <label>Yaş:</label><input type="number" name="yas" value="{{ hasta[3] }}">
        <label>Doktor Notu:</label><textarea name="ozel_not" rows="3">{{ hasta[5] }}</textarea>
        <label>Alerji:</label><input type="text" name="alerji" value="{{ hasta[6] }}">
        <label>Randevu Tarihi:</label><input type="date" name="randevu_tarihi" value="{{ hasta[7] }}">
        <button type="submit">GÜNCELLE</button>
    </form>
    <br><a href="/doktor-panel" style="color:gray;">İptal</a>
</div></body></html>
'''

HASTA_DETAY_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Diş Kartı</title><style>body{font-family:Arial;padding:10px;background:#f4f7f6}.container{max-width:800px;margin:auto;background:white;padding:20px;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.1)}.info-box{background:#e9ecef;padding:15px;border-radius:8px;margin-bottom:20px}form{background:#f8f9fa;padding:15px;border-radius:8px;border:1px solid #ddd;margin-bottom:20px}input,select{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:5px;box-sizing:border-box}button{background:#007bff;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer}table{width:100%;border-collapse:collapse;margin-top:15px}th,td{border:1px solid #ddd;padding:10px;text-align:left}th{background:#28a745;color:white}.btn-pdf{background:#17a2b8;color:white;padding:8px 15px;text-decoration:none;border-radius:5px;float:right}</style></head>
<body><div class="container">
    <a href="/doktor-panel" style="background:#6c757d;color:white;padding:8px 12px;text-decoration:none;border-radius:5px;">⬅ Geri</a>
    <a class="btn-pdf" href="/hasta-rapor/{{ hasta[0] }}" target="_blank">📄 PDF / Reçete Çıktısı Al</a>
    <h1 style="color:#007bff;">🦷 Hasta Diş Kartı</h1>
    <div class="info-box">
        <h3>{{ hasta[1] }}</h3>
        <p><b>Telefon:</b> {{ hasta[2] }} | <b>Yaş:</b> {{ hasta[3] }}</p>
        <p><b>Semptomlar:</b> {{ hasta[4] }}</p>
        <p><b>Doktor Notu:</b> {{ hasta[5] }}</p>
    </div>
    <form action="/dis_islem_ekle/{{ hasta[0] }}" method="POST">
        <h3>Diş Tedavisi / İşlem Ekle</h3>
        <select name="dis_no" required>
            <option value="">-- Diş Seçiniz (ISO Numarası) --</option>
            <option value="11">11 - Sağ Üst Kesici</option>
            <option value="12">12 - Sağ Üst Yan Kesici</option>
            <option value="13">13 - Sağ Üst Köpek</option>
            <option value="14">14 - Sağ Üst 1. Küçük Azı</option>
            <option value="15">15 - Sağ Üst 2. Küçük Azı</option>
            <option value="16">16 - Sağ Üst 1. Büyük Azı</option>
            <option value="17">17 - Sağ Üst 2. Büyük Azı</option>
            <option value="21">21 - Sol Üst Kesici</option>
            <option value="22">22 - Sol Üst Yan Kesici</option>
            <option value="23">23 - Sol Üst Köpek</option>
            <option value="24">24 - Sol Üst 1. Küçük Azı</option>
            <option value="25">25 - Sol Üst 2. Küçük Azı</option>
            <option value="26">26 - Sol Üst 1. Büyük Azı</option>
            <option value="31">31 - Sol Alt Kesici</option>
            <option value="36">36 - Sol Alt 1. Büyük Azı</option>
            <option value="41">41 - Sağ Alt Kesici</option>
            <option value="46">46 - Sağ Alt 1. Büyük Azı</option>
        </select>
        <select name="islem_turu" required>
            <option value="">-- Yapılan İşlem / Tedavi --</option>
            <option value="Dolgu">Kompozit / Amalgam Dolgu</option>
            <option value="Kanal Tedavisi">Kanal Tedavisi</option>
            <option value="Diş Çekimi">Diş Çekimi</option>
            <option value="Diş Taşı Temizliği">Diş Taşı Temizliği</option>
            <option value="Kron / Kaplama">Kron / Porselen Kaplama</option>
            <option value="İmplant">İmplant</option>
        </select>
        <input type="number" step="0.01" name="ucret" placeholder="İşlem Ücreti (TL)" required>
        <button type="submit">İşlemi Kaydet</button>
    </form>
    <h2>Uygulanan Diş Tedavileri</h2>
    <table>
        <tr><th>Diş No</th><th>Tedavi</th><th>Ücret</th><th>Eylem</th></tr>
        {% for i in islemler %}
        <tr>
            <td><b>Diş #{{ i[2] }}</b></td><td>{{ i[3] }}</td><td>{{ i[4] }} TL</td>
            <td><a href="/islem-sil/{{ i[0] }}/{{ hasta[0] }}" style="color:red;text-decoration:none;" onclick="return confirm('Silmek istediğinize emin misiniz?')">🗑️ Sil</a></td>
        </tr>
        {% endfor %}
    </table>
</div></body></html>
'''

HASTA_RAPOR_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Rapor</title><style>body{font-family:Arial;padding:40px;color:#333}.header{text-align:center;border-bottom:2px solid #007bff;padding-bottom:10px;margin-bottom:30px}.logo{max-width:150px}.box{background:#f9f9f9;padding:15px;border-radius:5px;margin-bottom:20px;border:1px solid #ddd}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #333;padding:8px;text-align:left}th{background:#eee}.print-btn{background:#28a745;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-size:16px;margin-bottom:20px}@media print{.print-btn{display:none}}</style></head>
<body>
<button class="print-btn" onclick="window.print()">🖨️ Sayfayı Yazdır / PDF İndir</button>
<div class="header">
    <img class="logo" src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=500&q=80">
    <h2>KLİNİK360 DİŞ SAĞLIĞI & TEDAVİ RAPORU</h2>
</div>
<div class="box">
    <h3>Hasta Bilgileri</h3>
    <p><b>Adı Soyadı:</b> {{ hasta[1] }} | <b>Telefon:</b> {{ hasta[2] }} | <b>Yaş:</b> {{ hasta[3] }}</p>
    <p><b>Alerji / Özel Durum:</b> {{ hasta[6] if hasta[6] else 'Yok' }}</p>
    <p><b>Doktor Notu:</b> {{ hasta[5] }}</p>
</div>
<h3>Uygulanan Tedaviler</h3>
<table>
    <tr><th>Diş No (ISO)</th><th>Tedavi Açıklaması</th></tr>
    {% for i in islemler %}
    <tr><td>Diş #{{ i[2] }}</td><td>{{ i[3] }}</td></tr>
    {% endfor %}
</table>
</body></html>
'''

HASTA_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Hasta Girişi</title><style>body{font-family:Arial;background:#e9ecef;padding:20px;text-align:center}.box{max-width:400px;margin:50px auto;background:white;padding:25px;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.1)}input{width:100%;padding:12px;margin:15px 0;border:1px solid #ccc;border-radius:6px;text-align:center;box-sizing:border-box}button{width:100%;padding:12px;background:#28a745;color:white;border:none;border-radius:6px;cursor:pointer}</style></head>
<body>
<div class="box">
    <h2>📱 Hasta Takip</h2>
    {% if hata %}<p style="color:red;">{{ hata }}</p>{% endif %}
    <form method="POST">
        <input type="text" name="telefon" placeholder="Telefon Numarası (0555...)" required>
        <button type="submit">Randevumu Göster</button>
    </form>
    <br><a href="/" style="color:#666;text-decoration:none;">⬅ Ana Sayfa</a>
</div>
</body></html>
'''

HASTA_PROFIL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Hasta Paneli</title><style>body{font-family:Arial;padding:10px;background:#f4f7f6}.container{max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.1)}.card{background:#e3f2fd;padding:15px;border-radius:8px;margin-bottom:20px;border-left:5px solid #007bff}table{width:100%;border-collapse:collapse;margin-top:15px}th,td{border:1px solid #ddd;padding:10px;text-align:left}th{background:#007bff;color:white}</style></head>
<body>
<div class="container">
    <a href="/" style="background:#6c757d;color:white;padding:8px 12px;text-decoration:none;border-radius:5px;">⬅ Çıkış</a>
    <h2>🦷 Klinik360 Hasta Bilgi Kartı</h2>
    <div class="card">
        <h3>Sayın {{ hasta[1] }}</h3>
        <p><b>🗓 Yaklaşan Randevunuz:</b> <span style="color:#d9534f;font-weight:bold;">{{ hasta[7] if hasta[7] else 'Yok' }}</span></p>
        <p><b>👨‍⚕️ Doktor Notu:</b> {{ hasta[5] if hasta[5] else 'Yok' }}</p>
    </div>
    <h3>🦷 Tedavileriniz</h3>
    {% if islemler %}
    <table>
        <tr><th>Diş No</th><th>Yapılan Tedavi</th></tr>
        {% for i in islemler %}
        <tr><td><b>Diş #{{ i[2] }}</b></td><td>{{ i[3] }}</td></tr>
        {% endfor %}
    </table>
    {% else %}
    <p style="color:gray;">Kayıtlı tedavi bulunmuyor.</p>
    {% endif %}
</div>
</body></html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)