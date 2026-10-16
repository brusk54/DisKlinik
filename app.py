from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'klinik360_gizli_anahtar'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DOKTOR_SIFRE = "1234"
SEKRETER_SIFRE = "5678"

def get_db():
    conn = sqlite3.connect('klinik.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hastalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT NOT NULL,
            tc_no TEXT,
            dogum_tarihi TEXT,
            yas TEXT,
            semptomlar TEXT,
            ozel_not TEXT,
            alerji TEXT,
            anamnez TEXT,
            randevu_tarihi TEXT,
            randevu_saati TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hasta_fotolar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hasta_id INTEGER,
            tip TEXT,
            dosya_adi TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hasta_id) REFERENCES hastalar (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ayarlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doktor_adi TEXT,
            klinik_adi TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fiyat_tarifesi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            islem_adi TEXT UNIQUE,
            varsayilan_fiyat REAL
        )
    ''')
    
    # Varsayılan ayar
    cursor.execute("SELECT COUNT(*) as cnt FROM ayarlar")
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute("INSERT INTO ayarlar (doktor_adi, klinik_adi) VALUES (?, ?)", ("Dt. Mehmet Güzel", "Klinik360 Diş Polikliniği"))
        conn.commit()
        
    # Varsayılan Fiyat Tarifesi
    cursor.execute("SELECT COUNT(*) as cnt FROM fiyat_tarifesi")
    if cursor.fetchone()['cnt'] == 0:
        sabit_fiyatlar = [
            ("Kompozit Dolgu", 1500),
            ("Kanal Tedavisi", 3000),
            ("Diş Çekimi", 1000),
            ("Diş Taşı Temizliği", 1200),
            ("Porselen Kron Kaplama", 4500),
            ("İmplant", 12000),
            ("Zirkonyum Kaplama", 5500),
            ("Diş Beyazlatma", 4000)
        ]
        cursor.executemany("INSERT INTO fiyat_tarifesi (islem_adi, varsayilan_fiyat) VALUES (?, ?)", sabit_fiyatlar)
        conn.commit()
    
    # Tablo güncelleme kontrolleri
    cursor.execute("PRAGMA table_info(hastalar)")
    sutunlar = [row[1] for row in cursor.fetchall()]
    
    yeni_sutunlar = {
        "tc_no": "TEXT",
        "dogum_tarihi": "TEXT",
        "randevu_tarihi": "TEXT",
        "randevu_saati": "TEXT",
        "alerji": "TEXT",
        "ozel_not": "TEXT",
        "semptomlar": "TEXT",
        "anamnez": "TEXT",
        "yas": "TEXT"
    }
    
    for sutun, tip in yeni_sutunlar.items():
        if sutun not in sutunlar:
            try:
                cursor.execute(f"ALTER TABLE hastalar ADD COLUMN {sutun} {tip}")
            except Exception:
                pass
        
    conn.commit()
    conn.close()

init_db()

# --- ORTAK TEMA SCRIPT VE CSS ---
DARK_MODE_STYLE = '''
<style>
:root {
    --bg-color: #f4f7f6;
    --card-bg: #ffffff;
    --text-color: #333333;
    --border-color: #dddddd;
    --form-bg: #e9ecef;
    --table-header-bg: #007bff;
    --table-header-color: #ffffff;
    --table-row-hover: #f1f1f1;
}

[data-theme="dark"] {
    --bg-color: #121212;
    --card-bg: #1e1e1e;
    --text-color: #e0e0e0;
    --border-color: #333333;
    --form-bg: #2a2a2a;
    --table-header-bg: #1f4068;
    --table-header-color: #ffffff;
    --table-row-hover: #2c2c2c;
}

body {
    background-color: var(--bg-color) !important;
    color: var(--text-color) !important;
    transition: background-color 0.3s, color 0.3s;
}

.container, .box, .info-box, .photo-card {
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border-color: var(--border-color) !important;
}

form {
    background-color: var(--form-bg) !important;
    color: var(--text-color) !important;
}

input, select, textarea {
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border: 1px solid var(--border-color) !important;
}

table {
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
}

th {
    background-color: var(--table-header-bg) !important;
    color: var(--table-header-color) !important;
}

td {
    border-color: var(--border-color) !important;
}

tr:hover {
    background-color: var(--table-row-hover) !important;
}

.theme-toggle-btn {
    background: transparent;
    border: 2px solid #007bff;
    color: #007bff;
    padding: 6px 12px;
    border-radius: 20px;
    cursor: pointer;
    font-weight: bold;
    font-size: 13px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: 0.2s;
}

[data-theme="dark"] .theme-toggle-btn {
    border-color: #ffc107;
    color: #ffc107;
}

@media (max-width: 768px) {
    .container { padding: 10px !important; }
    .stats-grid { grid-template-columns: 1fr !important; }
    .tooth-grid { grid-template-columns: repeat(4, 1fr) !important; }
    table { display: block; overflow-x: auto; white-space: nowrap; }
}
</style>

<script>
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeBtnText();
}

function updateThemeBtnText() {
    const theme = document.documentElement.getAttribute('data-theme');
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
        btn.innerHTML = theme === 'dark' ? '☀️ Aydınlık Mod' : '🌙 Karanlık Mod';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeBtnText();
});
</script>
'''

@app.route('/')
def index():
    return render_template_string(GIRIS_SECIM_HTML)

@app.route('/doktor-giris', methods=['GET', 'POST'])
def doktor_giris():
    hata = None
    if request.method == 'POST':
        sifre = request.form.get('sifre')
        if sifre == DOKTOR_SIFRE:
            session['kullanici_rolu'] = 'doktor'
            return redirect(url_for('doktor_panel'))
        elif sifre == SEKRETER_SIFRE:
            session['kullanici_rolu'] = 'sekreter'
            return redirect(url_for('doktor_panel'))
        else:
            hata = "Hatalı şifre!"
    return render_template_string(DOKTOR_GIRIS_HTML, hata=hata)

@app.route('/doktor-cikis')
def doktor_cikis():
    session.pop('kullanici_rolu', None)
    return redirect(url_for('index'))

@app.route('/doktor-panel')
def doktor_panel():
    rol = session.get('kullanici_rolu')
    if not rol:
        return redirect(url_for('doktor_giris'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM ayarlar WHERE id = 1")
    ayar = cursor.fetchone()
    
    arama = request.args.get('arama', '')
    if arama:
        cursor.execute("SELECT * FROM hastalar WHERE ad_soyad LIKE ? OR telefon LIKE ? OR tc_no LIKE ? ORDER BY id DESC", ('%' + arama + '%', '%' + arama + '%', '%' + arama + '%'))
    else:
        cursor.execute("SELECT * FROM hastalar ORDER BY id DESC")
        
    hastalar = cursor.fetchall()

    cursor.execute("SELECT id, ad_soyad, telefon, randevu_tarihi, randevu_saati FROM hastalar WHERE randevu_tarihi IS NOT NULL AND randevu_tarihi != '' ORDER BY randevu_tarihi ASC, randevu_saati ASC")
    randevular = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) as toplam FROM hastalar")
    toplam_hasta = cursor.fetchone()['toplam']

    cursor.execute("SELECT COUNT(*) as toplam FROM hastalar WHERE randevu_tarihi IS NOT NULL AND randevu_tarihi != ''")
    toplam_randevu = cursor.fetchone()['toplam']

    cursor.execute("SELECT COUNT(*) as toplam FROM dis_islemleri")
    toplam_islem = cursor.fetchone()['toplam']

    cursor.execute("SELECT * FROM fiyat_tarifesi ORDER BY islem_adi ASC")
    tarifeler = cursor.fetchall()

    conn.close()
    return render_template_string(DOKTOR_PANEL_HTML, hastalar=hastalar, randevular=randevular, arama=arama, toplam_hasta=toplam_hasta, toplam_randevu=toplam_randevu, toplam_islem=toplam_islem, ayar=ayar, tarifeler=tarifeler, rol=rol)

@app.route('/fiyat-guncelle', methods=['POST'])
def fiyat_guncelle():
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('doktor_panel'))
        
    conn = get_db()
    cursor = conn.cursor()
    
    for key, val in request.form.items():
        if key.startswith('fiyat_'):
            tarife_id = key.split('_')[1]
            cursor.execute("UPDATE fiyat_tarifesi SET varsayilan_fiyat = ? WHERE id = ?", (val, tarife_id))
            
    conn.commit()
    conn.close()
    return redirect(url_for('doktor_panel'))

@app.route('/ekle', methods=['POST'])
def ekle():
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
        
    ad_soyad = request.form.get('ad_soyad', '')
    telefon = request.form.get('telefon', '')
    tc_no = request.form.get('tc_no', '')
    dogum_tarihi = request.form.get('dogum_tarihi', '')
    yas = request.form.get('yas', '')
    secilen_semptomlar = request.form.getlist('semptomlar')
    semptomlar_str = ", ".join(secilen_semptomlar) if secilen_semptomlar else "Belirtilmemiş"
    
    secilen_anamnez = request.form.getlist('anamnez')
    anamnez_str = ", ".join(secilen_anamnez) if secilen_anamnez else "Özellik yok"

    ozel_not = request.form.get('ozel_not', '')
    alerji = request.form.get('alerji', '')
    randevu_tarihi = request.form.get('randevu_tarihi', '')
    randevu_saati = request.form.get('randevu_saati', '')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO hastalar (ad_soyad, telefon, tc_no, dogum_tarihi, yas, semptomlar, anamnez, ozel_not, alerji, randevu_tarihi, randevu_saati)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (ad_soyad, telefon, tc_no, dogum_tarihi, yas, semptomlar_str, anamnez_str, ozel_not, alerji, randevu_tarihi, randevu_saati))
    conn.commit()
    conn.close()
    return redirect(url_for('doktor_panel'))

@app.route('/hasta-duzenle/<int:hasta_id>', methods=['GET', 'POST'])
def hasta_duzenle(hasta_id):
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
        
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        ad_soyad = request.form.get('ad_soyad', '')
        telefon = request.form.get('telefon', '')
        tc_no = request.form.get('tc_no', '')
        dogum_tarihi = request.form.get('dogum_tarihi', '')
        yas = request.form.get('yas', '')
        ozel_not = request.form.get('ozel_not', '')
        alerji = request.form.get('alerji', '')
        randevu_tarihi = request.form.get('randevu_tarihi', '')
        randevu_saati = request.form.get('randevu_saati', '')

        cursor.execute('''
            UPDATE hastalar 
            SET ad_soyad=?, telefon=?, tc_no=?, dogum_tarihi=?, yas=?, ozel_not=?, alerji=?, randevu_tarihi=?, randevu_saati=?
            WHERE id=?
        ''', (ad_soyad, telefon, tc_no, dogum_tarihi, yas, ozel_not, alerji, randevu_tarihi, randevu_saati, hasta_id))
        conn.commit()
        conn.close()
        return redirect(url_for('doktor_panel'))

    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    conn.close()
    return render_template_string(HASTA_DUZENLE_HTML, hasta=hasta)

@app.route('/hasta-sil/<int:hasta_id>')
def hasta_sil(hasta_id):
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('doktor_panel'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    cursor.execute("DELETE FROM hasta_fotolar WHERE hasta_id = ?", (hasta_id,))
    cursor.execute("DELETE FROM hastalar WHERE id = ?", (hasta_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('doktor_panel'))

@app.route('/islem-sil/<int:islem_id>/<int:hasta_id>')
def islem_sil(islem_id, hasta_id):
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('hasta_detay', hasta_id=hasta_id))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dis_islemleri WHERE id = ?", (islem_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/foto-sil/<int:foto_id>/<int:hasta_id>')
def foto_sil(foto_id, hasta_id):
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('hasta_detay', hasta_id=hasta_id))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT dosya_adi FROM hasta_fotolar WHERE id = ?", (foto_id,))
    foto = cursor.fetchone()
    if foto:
        dosya_yolu = os.path.join(app.config['UPLOAD_FOLDER'], foto['dosya_adi'])
        if os.path.exists(dosya_yolu):
            os.remove(dosya_yolu)
    cursor.execute("DELETE FROM hasta_fotolar WHERE id = ?", (foto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/hasta-detay/<int:hasta_id>')
def hasta_detay(hasta_id):
    rol = session.get('kullanici_rolu')
    if not rol:
        return redirect(url_for('doktor_giris'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    cursor.execute("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    islemler = cursor.fetchall()
    cursor.execute("SELECT * FROM hasta_fotolar WHERE hasta_id = ?", (hasta_id,))
    fotolar = cursor.fetchall()
    cursor.execute("SELECT * FROM ayarlar WHERE id = 1")
    ayar = cursor.fetchone()
    cursor.execute("SELECT * FROM fiyat_tarifesi ORDER BY islem_adi ASC")
    tarifeler = cursor.fetchall()
    conn.close()
    return render_template_string(HASTA_DETAY_HTML, hasta=hasta, islemler=islemler, fotolar=fotolar, ayar=ayar, tarifeler=tarifeler, rol=rol)

@app.route('/dis_islem_ekle/<int:hasta_id>', methods=['POST'])
def dis_islem_ekle(hasta_id):
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
        
    dis_no = request.form.get('dis_no', '')
    islem_turu = request.form.get('islem_turu', '')
    ucret = request.form.get('ucret', 0)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO dis_islemleri (hasta_id, dis_no, islem_turu, ucret)
        VALUES (?, ?, ?, ?)
    ''', (hasta_id, dis_no, islem_turu, ucret))
    conn.commit()
    conn.close()
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/foto-ekle/<int:hasta_id>', methods=['POST'])
def foto_ekle(hasta_id):
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
        
    tip = request.form.get('tip', 'once')
    dosya = request.files.get('foto')
    
    if dosya and dosya.filename != '':
        filename = secure_filename(f"hasta_{hasta_id}_{os.urandom(4).hex()}_{dosya.filename}")
        dosya.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO hasta_fotolar (hasta_id, tip, dosya_adi) VALUES (?, ?, ?)", (hasta_id, tip, filename))
        conn.commit()
        conn.close()
        
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/hasta-rapor/<int:hasta_id>')
def hasta_rapor(hasta_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    cursor.execute("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    islemler = cursor.fetchall()
    cursor.execute("SELECT * FROM hasta_fotolar WHERE hasta_id = ?", (hasta_id,))
    fotolar = cursor.fetchall()
    cursor.execute("SELECT * FROM ayarlar WHERE id = 1")
    ayar = cursor.fetchone()
    
    recete_secimi = request.args.get('recete', '')
    conn.close()
    return render_template_string(HASTA_RAPOR_HTML, hasta=hasta, islemler=islemler, fotolar=fotolar, recete_secimi=recete_secimi, ayar=ayar)

@app.route('/hasta-giris', methods=['GET', 'POST'])
def hasta_giris():
    hata = None
    if request.method == 'POST':
        girdi = request.form.get('girdi', '').strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hastalar WHERE telefon LIKE ? OR tc_no = ?", ('%' + girdi + '%', girdi))
        hasta = cursor.fetchone()
        
        if hasta:
            session['hasta_id'] = hasta['id']
            conn.close()
            return redirect(url_for('hasta_profil'))
        else:
            hata = "Girdiğiniz bilgilere ait kayıt bulunamadı."
        conn.close()
    return render_template_string(HASTA_GIRIS_HTML, hata=hata)

@app.route('/hasta-profil')
def hasta_profil():
    hasta_id = session.get('hasta_id')
    if not hasta_id:
        return redirect(url_for('hasta_giris'))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    cursor.execute("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    islemler = cursor.fetchall()
    cursor.execute("SELECT * FROM hasta_fotolar WHERE hasta_id = ?", (hasta_id,))
    fotolar = cursor.fetchall()
    cursor.execute("SELECT * FROM ayarlar WHERE id = 1")
    ayar = cursor.fetchone()
    conn.close()
    return render_template_string(HASTA_PROFIL_HTML, hasta=hasta, islemler=islemler, fotolar=fotolar, ayar=ayar)

# --- HTML TEMPLATES ---

LOGO_HTML = '''
<div style="display: inline-flex; align-items: center; justify-content: center; gap: 10px; background: linear-gradient(135deg, #007bff, #00d2ff); padding: 12px 24px; border-radius: 50px; color: white; box-shadow: 0 4px 15px rgba(0,123,255,0.3); margin-bottom: 15px;">
    <span style="font-size: 28px;">🦷</span>
    <span style="font-size: 22px; font-weight: bold; letter-spacing: 1px;">Klinik360</span>
</div>
'''

GIRIS_SECIM_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Klinik360 Portalı</title>
''' + DARK_MODE_STYLE + '''
<style>
body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; }
.box { max-width: 450px; margin: 60px auto; padding: 40px 30px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
.btn { display: block; width: 100%; padding: 14px; margin: 15px 0; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold; color: white; box-sizing: border-box; transition: 0.2s; }
.btn-doktor { background: #007bff; } .btn-hasta { background: #28a745; }
</style></head>
<body>
    <div style="text-align: right; max-width: 450px; margin: auto;">
        <button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button>
    </div>
    <div class="box">
        ''' + LOGO_HTML + '''
        <p style="opacity: 0.8; margin-bottom: 25px; font-size: 15px;">Profesyonel Diş Klinik Yönetim Sistemi</p>
        <a href="/doktor-giris" class="btn btn-doktor">👩‍⚕️ Personel / Yönetici Girişi</a>
        <a href="/hasta-giris" class="btn btn-hasta">📱 Hasta Randevu & Takip</a>
    </div>
</body></html>
'''

DOKTOR_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Personel Girişi</title>
''' + DARK_MODE_STYLE + '''
<style>body{font-family:Arial;padding:20px;text-align:center}.box{max-width:380px;margin:60px auto;padding:30px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.1)}input{width:100%;padding:12px;margin:15px 0;border-radius:6px;text-align:center;box-sizing:border-box;font-size:16px}button{width:100%;padding:12px;background:#007bff;color:white;border:none;border-radius:6px;cursor:pointer;font-size:16px}</style></head>
<body>
<div style="text-align: right; max-width: 380px; margin: auto;">
    <button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button>
</div>
<div class="box">
    ''' + LOGO_HTML + '''
    <h2>Klinik Personel Girişi</h2>
    {% if hata %}<p style="color:red; font-size:14px;">{{ hata }}</p>{% endif %}
    <form method="POST">
        <input type="password" name="sifre" placeholder="Personel Şifresi" required>
        <button type="submit">Giriş Yap</button>
    </form>
    <br><a href="/" style="color:#007bff;text-decoration:none;font-size:14px;">⬅ Ana Sayfa</a>
</div>
</body></html>
'''

DOKTOR_PANEL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Doktor Paneli - Klinik360</title>
''' + DARK_MODE_STYLE + '''
<style>
body{font-family:Arial;padding:10px;}
.container{max-width:1000px;margin:auto;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}
.header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #eee;padding-bottom:10px;margin-bottom:20px; flex-wrap: wrap; gap: 10px;}
.stats-grid{display:grid; grid-template-columns: repeat(3, 1fr); gap:15px; margin-bottom:20px;}
.stat-card{background:linear-gradient(135deg, #007bff, #00c6ff); color:white; padding:15px; border-radius:10px; text-align:center;}
.stat-card:nth-child(2){background:linear-gradient(135deg, #28a745, #20c997);}
.stat-card:nth-child(3){background:linear-gradient(135deg, #ffc107, #ff9800); color:#333;}
.takvim-box{padding:15px;border-radius:8px;margin-bottom:20px;border-left:5px solid #007bff; border: 1px solid var(--border-color);}
.tarife-box{padding:15px;border-radius:8px;margin-bottom:20px;border-left:5px solid #ffc107; border: 1px solid var(--border-color);}
form{padding:20px;border-radius:8px;margin-bottom:20px}
input,select,textarea{width:100%;padding:10px;margin:8px 0;border-radius:5px;box-sizing:border-box}
.checkbox-group{padding:10px;border-radius:5px;border:1px solid var(--border-color);margin:8px 0}
.checkbox-group label{display:block;margin-bottom:5px;cursor:pointer;font-size:13px;}
button{background:#28a745;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer;font-size:16px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ddd;padding:10px;text-align:left;font-size:13px}
.btn-sm{padding:5px 8px;text-decoration:none;border-radius:4px;font-size:11px;display:inline-block;margin:2px}
.btn-info{background:#17a2b8;color:white}.btn-wa{background:#25d366;color:white}.btn-sms{background:#6f42c1;color:white}.btn-edit{background:#ffc107;color:#000}.btn-del{background:#dc3545;color:white}
.badge-danger{background:#dc3545; color:white; padding:2px 6px; border-radius:4px; font-size:11px;}
.badge-role{background:#17a2b8; color:white; padding:3px 8px; border-radius:12px; font-size:12px; font-weight:bold;}
</style></head>
<body>
<div class="container">
    <div class="header">
        <div>
            <span style="font-size: 22px; font-weight: bold; color: #007bff;">🦷 Klinik360</span> 
            <span style="font-size: 14px; opacity: 0.8;">| {{ ayar['doktor_adi'] }}</span>
            <span class="badge-role">{{ '👨‍⚕️ Doktor Yetkisi' if rol == 'doktor' else '📋 Sekreter Yetkisi' }}</span>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
            <button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button>
            <a href="/doktor-cikis" style="background:#dc3545;color:white;padding:8px 15px;text-decoration:none;border-radius:6px;font-size:14px;">Çıkış Yap</a>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <h4 style="margin:0; font-size:14px;">Toplam Hasta</h4>
            <p style="margin:5px 0 0 0; font-size:24px; font-weight:bold;">{{ toplam_hasta }}</p>
        </div>
        <div class="stat-card">
            <h4 style="margin:0; font-size:14px;">Aktif Randevular</h4>
            <p style="margin:5px 0 0 0; font-size:24px; font-weight:bold;">{{ toplam_randevu }}</p>
        </div>
        <div class="stat-card">
            <h4 style="margin:0; font-size:14px;">Yapılan İşlemler</h4>
            <p style="margin:5px 0 0 0; font-size:24px; font-weight:bold;">{{ toplam_islem }}</p>
        </div>
    </div>

    <!-- SAAT ÇAKIŞMASIZ RANDEVU TAKVİMİ -->
    <div class="takvim-box">
        <h3 style="margin-top:0;color:#007bff;">📅 Saatli Randevu Takvimi</h3>
        {% if randevular %}
            <table style="margin-top:5px;">
                <tr><th>Tarih & Saat</th><th>Hasta Adı Soyadı</th><th>İletişim Telefonu</th></tr>
                {% for r in randevular %}
                <tr>
                    <td><b>⏰ {{ r['randevu_tarihi'] }} - {{ r['randevu_saati'] or 'Saat Belirtilmedi' }}</b></td>
                    <td>{{ r['ad_soyad'] }}</td>
                    <td>{{ r['telefon'] }}</td>
                </tr>
                {% endfor %}
            </table>
        {% else %}
            <p style="margin:0;opacity:0.7;">Planlanmış randevu yok.</p>
        {% endif %}
    </div>

    {% if rol == 'doktor' %}
    <!-- DİŞ TEDAVİSİ FİYAT TARİFESİ DÜZENLEME (SADECE DOKTOR) -->
    <div class="tarife-box">
        <h3 style="margin-top:0; color:#ffc107;">📋 Kliniğe Özel Diş Tedavisi Fiyat Tarifesi</h3>
        <form action="/fiyat-guncelle" method="POST" style="background:transparent; padding:0; margin:0;">
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:10px;">
                {% for t in tarifeler %}
                <div style="display:flex; align-items:center; gap:5px; padding:5px 10px; border-radius:5px; border:1px solid var(--border-color);">
                    <span style="font-size:12px; font-weight:bold; flex:1;">{{ t['islem_adi'] }}:</span>
                    <input type="number" name="fiyat_{{ t['id'] }}" value="{{ t['varsayilan_fiyat'] }}" style="width:100px; margin:0; padding:4px;" step="50"> TL
                </div>
                {% endfor %}
            </div>
            <button type="submit" style="margin-top:10px; background:#ffc107; color:#333; font-weight:bold;">Fiyat Tarifesini Güncelle</button>
        </form>
    </div>
    {% endif %}

    <form action="/ekle" method="POST">
        <h3 style="margin-top:0; color:#007bff;">Yeni Hasta Kaydı & Tıbbi Anamnez</h3>
        <input type="text" name="ad_soyad" placeholder="Hasta Adı Soyadı" required>
        <input type="text" name="telefon" placeholder="Telefon Numarası (0555...)" required>
        <input type="text" name="tc_no" placeholder="TC Kimlik Numarası (11 Haneli)" maxlength="11">
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <div style="flex:1; min-width:140px;"><label style="font-size:12px; opacity:0.8;">Doğum Tarihi:</label><input type="date" name="dogum_tarihi"></div>
            <div style="flex:1; min-width:140px;"><label style="font-size:12px; opacity:0.8;">Yaş:</label><input type="number" name="yas" placeholder="Yaş"></div>
        </div>
        
        <label><b>Semptomlar ve Şikayetler:</b></label>
        <div class="checkbox-group">
            <label><input type="checkbox" name="semptomlar" value="Şiddetli Ağrı (Apse)"> Şiddetli Ağrı (Apse)</label>
            <label><input type="checkbox" name="semptomlar" value="Hassasiyet (Sıcak/Soğuk)"> Hassasiyet (Sıcak/Soğuk)</label>
            <label><input type="checkbox" name="semptomlar" value="Diş Eti Kanaması"> Diş Eti Kanaması</label>
            <label><input type="checkbox" name="semptomlar" value="Çürük / Kırık Diş"> Çürük / Kırık Diş</label>
            <label><input type="checkbox" name="semptomlar" value="Estetik / Dolgu"> Estetik / Dolgu</label>
        </div>

        <label><b>Anamnez / Tıbbi Geçmiş (Kritik Sağlık Durumları):</b></label>
        <div class="checkbox-group" style="border-left: 4px solid #dc3545;">
            <label><input type="checkbox" name="anamnez" value="Kan Sulandırıcı Kullanıyor"> 🩸 Kan Sulandırıcı Kullanıyor</label>
            <label><input type="checkbox" name="anamnez" value="Diyabet (Şeker Hastalığı)"> 🩺 Diyabet (Şeker Hastalığı)</label>
            <label><input type="checkbox" name="anamnez" value="Hipertansiyon (Yüksek Tansiyon)"> ❤️ Hipertansiyon (Yüksek Tansiyon)</label>
            <label><input type="checkbox" name="anamnez" value="Kalp Rahatsızlığı"> 🫀 Kalp Rahatsızlığı</label>
            <label><input type="checkbox" name="anamnez" value="Bulaşıcı Hastalık Riski"> ⚠️ Bulaşıcı Hastalık Riski</label>
        </div>

        <textarea name="ozel_not" placeholder="Doktor Açıklaması / Klinik Not..." rows="2"></textarea>
        <input type="text" name="alerji" placeholder="Alerji Durumu (Örn: Penisilin Alerjisi)">
        
        <div style="display:flex; gap:10px; flex-wrap:wrap;">
            <div style="flex:1; min-width:140px;"><label style="font-size:12px; opacity:0.8;">Randevu Tarihi:</label><input type="date" name="randevu_tarihi"></div>
            <div style="flex:1; min-width:140px;"><label style="font-size:12px; opacity:0.8;">Randevu Saati:</label>
                <select name="randevu_saati">
                    <option value="">-- Saat Seçin --</option>
                    <option value="09:00">09:00</option><option value="09:30">09:30</option>
                    <option value="10:00">10:00</option><option value="10:30">10:30</option>
                    <option value="11:00">11:00</option><option value="11:30">11:30</option>
                    <option value="13:00">13:00</option><option value="13:30">13:30</option>
                    <option value="14:00">14:00</option><option value="14:30">14:30</option>
                    <option value="15:00">15:00</option><option value="15:30">15:30</option>
                    <option value="16:00">16:00</option><option value="16:30">16:30</option>
                    <option value="17:00">17:00</option>
                </select>
            </div>
        </div>
        <button type="submit">Hastayı Kaydet</button>
    </form>

    <form method="GET" action="/doktor-panel" style="background:none;padding:0;">
        <input type="text" name="arama" placeholder="🔍 İsim, telefon veya TC No ile ara..." value="{{ arama }}">
    </form>

    <h2>Kayıtlı Hastalar & İletişim Şablonları</h2>
    <table>
        <tr><th>Kimlik & Ad Soyad</th><th>İletişim & TC</th><th>Kritik Anamnez & Notlar</th><th>Randevu</th><th>WhatsApp & SMS Mesajları</th><th>İşlemler</th></tr>
        {% for h in hastalar %}
        <tr>
            <td><b>{{ h['ad_soyad'] }}</b><br><small>Doğum: {{ h['dogum_tarihi'] or '-' }} (Yaş: {{ h['yas'] or '-' }})</small></td>
            <td>Tel: {{ h['telefon'] }}<br><small>TC: {{ h['tc_no'] or '-' }}</small></td>
            <td>
                {% if h['anamnez'] and h['anamnez'] != 'Özellik yok' %}
                    <span class="badge-danger">{{ h['anamnez'] }}</span><br>
                {% endif %}
                <b>Semptom:</b> {{ h['semptomlar'] or '' }}<br>
                {% if h['ozel_not'] %}<b>Not:</b> {{ h['ozel_not'] }}<br>{% endif %}
                {% if h['alerji'] %}<small style="color:red; font-weight:bold;">Alerji: {{ h['alerji'] }}</small>{% endif %}
            </td>
            <td>{{ h['randevu_tarihi'] or '' }}<br><small>{{ h['randevu_saati'] or '' }}</small></td>
            <td>
                <!-- WHATSAPP HAZIR ŞABLONLARI -->
                <a class="btn-sm btn-wa" href="https://wa.me/9{{ h['telefon'] }}?text=Sayin%20{{ h['ad_soyad'] }},%20{{ h['randevu_tarihi'] }}%20günü%20saat%20{{ h['randevu_saati'] or '' }}%20klinik%20randevunuzu%20hatirlatiriz.%20{{ ayar['klinik_adi'] }}%20-%20{{ ayar['doktor_adi'] }}" target="_blank">📲 WhatsApp Hatırlat</a><br>
                <!-- DOĞRUDAN SMS ŞABLONU -->
                <a class="btn-sm btn-sms" href="sms:{{ h['telefon'] }}?body=Sayin%20{{ h['ad_soyad'] }},%20{{ h['randevu_tarihi'] }}%20saat%20{{ h['randevu_saati'] or '' }}%20klinik%20randevunuzu%20hatirlatiriz.%20{{ ayar['klinik_adi'] }}">✉️ Başlıklı SMS Gönder</a>
            </td>
            <td>
                <a class="btn-sm btn-info" href="/hasta-detay/{{ h['id'] }}">Diş Kartı</a>
                <a class="btn-sm btn-edit" href="/hasta-duzenle/{{ h['id'] }}">Düzenle</a>
                {% if rol == 'doktor' %}
                <a class="btn-sm btn-del" href="/hasta-sil/{{ h['id'] }}" onclick="return confirm('Silmek istediğinize emin misiniz?')">Sil</a>
                {% endif %}
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
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Düzenle</title>
''' + DARK_MODE_STYLE + '''
<style>body{font-family:Arial;padding:20px;}.box{max-width:500px;margin:auto;padding:25px;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}input,textarea,select{width:100%;padding:10px;margin:8px 0;border-radius:5px;box-sizing:border-box}button{background:#28a745;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer;font-size:16px}</style></head>
<body>
<div style="text-align: right; max-width: 500px; margin: auto;">
    <button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button>
</div>
<div class="box">
    <h2 style="color:#007bff; margin-top:0;">✏️ Hasta Bilgilerini Düzenle</h2>
    <form method="POST">
        <label>Ad Soyad:</label><input type="text" name="ad_soyad" value="{{ hasta['ad_soyad'] }}" required>
        <label>Telefon:</label><input type="text" name="telefon" value="{{ hasta['telefon'] }}" required>
        <label>TC Kimlik No:</label><input type="text" name="tc_no" value="{{ hasta['tc_no'] or '' }}" maxlength="11">
        <label>Doğum Tarihi:</label><input type="date" name="dogum_tarihi" value="{{ hasta['dogum_tarihi'] or '' }}">
        <label>Yaş:</label><input type="number" name="yas" value="{{ hasta['yas'] or '' }}">
        <label>Doktor Notu:</label><textarea name="ozel_not" rows="3">{{ hasta['ozel_not'] or '' }}</textarea>
        <label>Alerji:</label><input type="text" name="alerji" value="{{ hasta['alerji'] or '' }}">
        <label>Randevu Tarihi:</label><input type="date" name="randevu_tarihi" value="{{ hasta['randevu_tarihi'] or '' }}">
        <label>Randevu Saati:</label>
        <input type="text" name="randevu_saati" value="{{ hasta['randevu_saati'] or '' }}" placeholder="Örn: 14:00">
        <button type="submit">GÜNCELLE</button>
    </form>
    <br><a href="/doktor-panel" style="color:#007bff;text-decoration:none;">⬅ İptal</a>
</div></body></html>
'''

HASTA_DETAY_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Diş Kartı</title>
''' + DARK_MODE_STYLE + '''
<style>
body{font-family:Arial;padding:10px;}
.container{max-width:900px;margin:auto;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}
.info-box{padding:15px;border-radius:8px;margin-bottom:20px; border:1px solid var(--border-color);}
form{padding:15px;border-radius:8px;border:1px solid var(--border-color);margin-bottom:20px}
input,select{width:100%;padding:10px;margin:8px 0;border-radius:5px;box-sizing:border-box}
button{background:#007bff;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer;font-size:16px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ddd;padding:10px;text-align:left}
.btn-pdf{background:#17a2b8;color:white;padding:8px 15px;text-decoration:none;border-radius:5px;float:right;display:inline-block;}
.badge-danger{background:#dc3545; color:white; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:bold;}
.tooth-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 5px; margin-bottom: 10px; }
.tooth-btn { background: #007bff; color: white; padding: 8px; text-align: center; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 13px; }
.tooth-btn:hover { background: #0056b3; }
.gallery { display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px; }
.photo-card { border: 1px solid var(--border-color); border-radius: 6px; padding: 10px; width: 200px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
.photo-card img { width: 100%; height: 140px; object-fit: cover; border-radius: 4px; margin-bottom: 8px; }
</style>
<script>
function disSec(no) {
    document.getElementById('dis_no_input').value = no;
    document.getElementById('islem_formu_baslik').innerText = "ISO Diş #" + no + " İçin İşlem Ekle";
}

function fiyatGetir() {
    var select = document.getElementById('islem_select');
    var selectedOption = select.options[select.selectedIndex];
    var fiyat = selectedOption.getAttribute('data-fiyat');
    if (fiyat) {
        document.getElementById('ucret_input').value = fiyat;
    }
}
</script>
</head>
<body><div class="container">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; flex-wrap:wrap; gap:10px;">
        <a href="/doktor-panel" style="background:#6c757d;color:white;padding:8px 12px;text-decoration:none;border-radius:6px;">⬅ Geri</a>
        <div style="display:flex; gap:10px; align-items:center;">
            <button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button>
            <a class="btn-pdf" href="/hasta-rapor/{{ hasta['id'] }}" target="_blank">📄 PDF / Reçete & Rapor Al</a>
        </div>
    </div>
    
    <h1 style="color:#007bff;">🦷 İnteraktif Diş Şeması & Tedavi Planı</h1>
    
    <div class="info-box">
        <h3>{{ hasta['ad_soyad'] }}</h3>
        {% if hasta['anamnez'] and hasta['anamnez'] != 'Özellik yok' %}
            <p><b>Kritik Anamnez:</b> <span class="badge-danger">{{ hasta['anamnez'] }}</span></p>
        {% endif %}
        <p><b>TC No:</b> {{ hasta['tc_no'] or 'Belirtilmemiş' }} | <b>Telefon:</b> {{ hasta['telefon'] }}</p>
        <p><b>Doğum Tarihi:</b> {{ hasta['dogum_tarihi'] or '-' }} | <b>Yaş:</b> {{ hasta['yas'] or '-' }}</p>
        <p><b>Semptomlar:</b> {{ hasta['semptomlar'] or '' }}</p>
        <p><b>Doktor Notu:</b> {{ hasta['ozel_not'] or '' }}</p>
    </div>

    <!-- İNTERAKTİF DİŞ ŞEMASI -->
    <div style="padding:15px; border-radius:8px; border:1px solid var(--border-color); margin-bottom:20px;">
        <h3 style="margin-top:0; color:#007bff; text-align:center;">🦷 İnteraktif Çene & Diş Haritası (Tıklayarak Seçin)</h3>
        <p style="text-align:center; font-size:12px; opacity:0.8;">İşlem yapmak istediğiniz dişe tıklayın.</p>
        
        <p style="margin:5px 0; font-size:12px; font-weight:bold;">Üst Çene</p>
        <div class="tooth-grid">
            {% for d in ['18','17','16','15','14','13','12','11','21','22','23','24','25','26','27','28'] %}
            <div class="tooth-btn" onclick="disSec('{{ d }}')">{{ d }}</div>
            {% endfor %}
        </div>
        <div class="tooth-grid" style="margin-top:10px;">
            {% for d in ['48','47','46','45','44','43','42','41','31','32','33','34','35','36','37','38'] %}
            <div class="tooth-btn" onclick="disSec('{{ d }}')">{{ d }}</div>
            {% endfor %}
        </div>
        <p style="margin:5px 0; font-size:12px; font-weight:bold; text-align:right;">Alt Çene</p>
    </div>

    <!-- TARİFEDEN OTOMATİK FİYAT HESAPLAYICI DİŞ İŞLEMİ EKLEME -->
    <form action="/dis_islem_ekle/{{ hasta['id'] }}" method="POST">
        <h3 id="islem_formu_baslik" style="margin-top:0; color:#007bff;">Diş İşlemi & Ücreti Ekle</h3>
        <input type="text" id="dis_no_input" name="dis_no" placeholder="Diş Numarası (Yukarıdan Tıklayın veya Yazın)" required>
        
        <select id="islem_select" name="islem_turu" onchange="fiyatGetir()" required>
            <option value="">-- Tarifeden Yapılan İşlemi Seçin --</option>
            {% for t in tarifeler %}
            <option value="{{ t['islem_adi'] }}" data-fiyat="{{ t['varsayilan_fiyat'] }}">{{ t['islem_adi'] }} ({{ t['varsayilan_fiyat'] }} TL)</option>
            {% endfor %}
        </select>
        
        <label style="font-size:12px; opacity:0.8;">Uygulanacak Tutar (TL):</label>
        <input type="number" id="ucret_input" name="ucret" placeholder="Ücret (TL)" required>

        <button type="submit">İşlemi ve Ücreti Kaydet</button>
    </form>

    <h2>Uygulanan Diş Tedavileri</h2>
    <table>
        <tr><th>Diş No</th><th>Tedavi</th><th>İşlem Tutarı</th>{% if rol == 'doktor' %}<th>Eylem</th>{% endif %}</tr>
        {% for i in islemler %}
        <tr>
            <td><b>Diş #{{ i['dis_no'] }}</b></td>
            <td>{{ i['islem_turu'] }}</td>
            <td><b>{{ i['ucret'] or 0 }} TL</b></td>
            {% if rol == 'doktor' %}
            <td><a href="/islem-sil/{{ i['id'] }}/{{ hasta['id'] }}" style="color:red;text-decoration:none;" onclick="return confirm('Silmek istediğinize emin misiniz?')">🗑️ Sil</a></td>
            {% endif %}
        </tr>
        {% endfor %}
    </table>

    <hr style="margin:30px 0; border-color: var(--border-color);">

    <!-- ÖNCE / SONRA FOTOĞRAF GALERİSİ -->
    <h3 style="color:#007bff;">📸 Öncesi / Sonrası Tedavi Fotoğrafları</h3>
    <form action="/foto-ekle/{{ hasta['id'] }}" method="POST" enctype="multipart/form-data">
        <label><b>Fotoğraf Tipi:</b></label>
        <select name="tip">
            <option value="once">Tedavi Öncesi (Before)</option>
            <option value="sonra">Tedavi Sonrası (After)</option>
        </select>
        <input type="file" name="foto" accept="image/*" required>
        <button type="submit" style="background:#17a2b8;">Fotoğrafı Yükle</button>
    </form>

    <div class="gallery">
        {% for f in fotolar %}
        <div class="photo-card">
            <span style="font-size:12px; font-weight:bold; color: {% if f['tip'] == 'once' %}#dc3545{% else %}#28a745{% endif %};">
                {{ 'Tedavi Öncesi' if f['tip'] == 'once' else 'Tedavi Sonrası' }}
            </span>
            <a href="{{ url_for('static', filename='uploads/' + f['dosya_adi']) }}" target="_blank">
                <img src="{{ url_for('static', filename='uploads/' + f['dosya_adi']) }}" alt="Fotoğraf">
            </a>
            <br>
            {% if rol == 'doktor' %}
            <a href="/foto-sil/{{ f['id'] }}/{{ hasta['id'] }}" style="color:red; font-size:12px; text-decoration:none;" onclick="return confirm('Fotoğrafı silmek istiyor musunuz?')">🗑️ Sil</a>
            {% endif %}
        </div>
        {% else %}
        <p style="opacity:0.7;">Henüz yüklenmiş fotoğraf yok.</p>
        {% endfor %}
    </div>

</div></body></html>
'''

HASTA_RAPOR_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Reçete ve Rapor</title>
<style>
body{font-family:Arial;padding:40px;color:#333; max-width:800px; margin:auto; background:white !important;}
.header{text-align:center;border-bottom:2px solid #007bff;padding-bottom:10px;margin-bottom:20px}
.box{background:#f9f9f9;padding:15px;border-radius:5px;margin-bottom:20px;border:1px solid #ddd}
table{width:100%;border-collapse:collapse;margin-top:15px; background:white;}
th,td{border:1px solid #333;padding:8px;text-align:left}th{background:#eee; color:#333;}
.print-btn{background:#28a745;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-size:16px;margin-bottom:20px}
.recete-box{background:#e8f4fd; border:1px dashed #007bff; padding:15px; border-radius:8px; margin-top:20px;}
.gallery { display: flex; gap: 15px; flex-wrap: wrap; margin-top: 15px; }
.photo-card { border: 1px solid #ddd; padding: 5px; width: 150px; text-align: center; }
.photo-card img { width: 100%; height: 100px; object-fit: cover; }
@media print{.print-btn, .no-print{display:none}}
</style></head>
<body>
<button class="print-btn" onclick="window.print()">🖨️ Sayfayı Yazdır / PDF İndir</button>

<div class="header">
    <h1 style="color: #007bff; margin: 0;">🦷 {{ ayar['klinik_adi'] }}</h1>
    <h2>DİŞ SAĞLIĞI TEDAVİ & REÇETE RAPORU</h2>
</div>

<div class="box">
    <h3>Hasta Bilgileri</h3>
    {% if hasta['anamnez'] and hasta['anamnez'] != 'Özellik yok' %}
        <p style="color:red; font-weight:bold;">⚠️ Kritik Anamnez: {{ hasta['anamnez'] }}</p>
    {% endif %}
    <p><b>Adı Soyadı:</b> {{ hasta['ad_soyad'] }} | <b>TC No:</b> {{ hasta['tc_no'] or '-' }}</p>
    <p><b>Telefon:</b> {{ hasta['telefon'] }} | <b>Doğum Tarihi:</b> {{ hasta['dogum_tarihi'] or '-' }} (Yaş: {{ hasta['yas'] or '-' }})</p>
    <p><b>Alerji Durumu:</b> <span style="color:red;">{{ hasta['alerji'] or 'Yok' }}</span></p>
    <p><b>Doktor Notu:</b> {{ hasta['ozel_not'] or '' }}</p>
</div>

<h3>Uygulanan Tedaviler</h3>
<table>
    <tr><th>Diş No (ISO)</th><th>Tedavi Açıklaması</th><th>Tutar</th></tr>
    {% for i in islemler %}
    <tr><td>Diş #{{ i['dis_no'] }}</td><td>{{ i['islem_turu'] }}</td><td>{{ i['ucret'] or 0 }} TL</td></tr>
    {% endfor %}
</table>

{% if fotolar %}
<h3>Tedavi Fotoğrafları</h3>
<div class="gallery">
    {% for f in fotolar %}
    <div class="photo-card">
        <small>{{ 'Öncesi' if f['tip'] == 'once' else 'Sonrası' }}</small><br>
        <img src="{{ url_for('static', filename='uploads/' + f['dosya_adi']) }}">
    </div>
    {% endfor %}
</div>
{% endif %}

<div class="no-print" style="margin-top:25px;">
    <h3>💊 Hazır Reçete Şablonu Seç</h3>
    <a href="/hasta-rapor/{{ hasta['id'] }}?recete=agri" style="background:#007bff; color:white; padding:8px 12px; text-decoration:none; border-radius:4px; margin-right:10px; display:inline-block;">Ağrı Kesici Şablonu</a>
    <a href="/hasta-rapor/{{ hasta['id'] }}?recete=antibiyotik" style="background:#17a2b8; color:white; padding:8px 12px; text-decoration:none; border-radius:4px; margin-right:10px; display:inline-block;">Apse / Antibiyotik Şablonu</a>
    <a href="/hasta-rapor/{{ hasta['id'] }}?recete=gargara" style="background:#6c757d; color:white; padding:8px 12px; text-decoration:none; border-radius:4px; display:inline-block;">Diş Eti & Gargara Şablonu</a>
</div>

{% if request.args.get('recete') %}
<div class="recete-box">
    <h3>📝 Doktor Reçetesi</h3>
    {% if request.args.get('recete') == 'agri' %}
        <p><b>1. Majezik 100 mg Film Tablet</b><br>Kullanım: Günde 2 defa tok karnına (Ağrı durumunda).</p>
        <p><b>2. Apranax Fort 550 mg</b><br>Kullanım: 12 saatte bir tok karnına.</p>
    {% elif request.args.get('recete') == 'antibiyotik' %}
        <p><b>1. Augmentin-BID 1000 mg Film Tablet</b><br>Kullanım: 12 saatte bir tok karnına (10 gün süreyle eksiksiz kullanım).</p>
        <p><b>2. Flotac 75 mg Tablet</b><br>Kullanım: Günde 1 kez tok karnına.</p>
    {% elif request.args.get('recete') == 'gargara' %}
        <p><b>1. Kloroben Gargara 200 ml</b><br>Kullanım: Günde 3 defa yemeklerden sonra 1 dakika çalkalayıp tükürünüz.</p>
        <p><b>2. Curaprox Diş İpi & Fırçası</b></p>
    {% endif %}
    <br><br>
    <p style="text-align:right;"><b>Hekim Kaşesi & İmza</b><br>{{ ayar['doktor_adi'] }}<br>{{ ayar['klinik_adi'] }}</p>
</div>
{% endif %}

</body></html>
'''

HASTA_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Hasta Girişi</title>
''' + DARK_MODE_STYLE + '''
<style>body{font-family:Arial;padding:20px;text-align:center}.box{max-width:400px;margin:60px auto;padding:30px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.1)}input{width:100%;padding:12px;margin:15px 0;border-radius:6px;text-align:center;box-sizing:border-box;font-size:16px}button{width:100%;padding:12px;background:#28a745;color:white;border:none;border-radius:6px;cursor:pointer;font-size:16px}</style></head>
<body>
<div style="text-align: right; max-width: 400px; margin: auto;">
    <button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button>
</div>
<div class="box">
    ''' + LOGO_HTML + '''
    <h2>Hasta Takip Paneli</h2>
    <p style="opacity:0.8; font-size:14px;">Telefon numaranız veya TC Kimlik numaranız ile giriş yapabilirsiniz.</p>
    {% if hata %}<p style="color:red; font-size:14px;">{{ hata }}</p>{% endif %}
    <form method="POST">
        <input type="text" name="girdi" placeholder="Telefon veya TC Kimlik No" required>
        <button type="submit">Randevumu Göster</button>
    </form>
    <br><a href="/" style="color:#007bff;text-decoration:none;font-size:14px;">⬅ Ana Sayfa</a>
</div>
</body></html>
'''

HASTA_PROFIL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Hasta Paneli</title>
''' + DARK_MODE_STYLE + '''
<style>body{font-family:Arial;padding:10px;}.container{max-width:600px;margin:auto;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}.card{padding:15px;border-radius:8px;margin-bottom:20px;border-left:5px solid #007bff; border:1px solid var(--border-color);}table{width:100%;border-collapse:collapse;margin-top:15px}th,td{border:1px solid #ddd;padding:10px;text-align:left}.gallery{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}.photo-card{border:1px solid var(--border-color);padding:5px;width:120px;text-align:center}.photo-card img{width:100%;height:90px;object-fit:cover}</style></head>
<body>
<div class="container">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
        <a href="/" style="background:#6c757d;color:white;padding:8px 12px;text-decoration:none;border-radius:6px;">⬅ Çıkış</a>
        <button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button>
    </div>
    <h2 style="color:#007bff;">🦷 {{ ayar['klinik_adi'] }}</h2>
    <div class="card">
        <h3 style="margin-top:0;">Sayın {{ hasta['ad_soyad'] }}</h3>
        <p><b>TC No:</b> {{ hasta['tc_no'] or '-' }} | <b>Doğum Tarihi:</b> {{ hasta['dogum_tarihi'] or '-' }}</p>
        <p><b>🗓 Yaklaşan Randevunuz:</b> <span style="color:#d9534f;font-weight:bold;">{{ hasta['randevu_tarihi'] or 'Yok' }} {% if hasta['randevu_saati'] %}(Saat: {{ hasta['randevu_saati'] }}){% endif %}</span></p>
        <p><b>👨‍⚕️ Hekim Notu:</b> {{ hasta['ozel_not'] or 'Yok' }}</p>
    </div>
    <h3>🦷 Tedavileriniz</h3>
    {% if islemler %}
    <table>
        <tr><th>Diş No</th><th>Yapılan Tedavi</th></tr>
        {% for i in islemler %}
        <tr><td><b>Diş #{{ i['dis_no'] }}</b></td><td>{{ i['islem_turu'] }}</td></tr>
        {% endfor %}
    </table>
    {% else %}
    <p style="opacity:0.7;">Kayıtlı tedavi bulunmuyor.</p>
    {% endif %}

    {% if fotolar %}
    <h3 style="margin-top:20px;">📸 Tedavi Fotoğraflarınız</h3>
    <div class="gallery">
        {% for f in fotolar %}
        <div class="photo-card">
            <small>{{ 'Öncesi' if f['tip'] == 'once' else 'Sonrası' }}</small><br>
            <a href="{{ url_for('static', filename='uploads/' + f['dosya_adi']) }}" target="_blank">
                <img src="{{ url_for('static', filename='uploads/' + f['dosya_adi']) }}">
            </a>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div></body></html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)