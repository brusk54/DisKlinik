from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory, abort
import sqlite3
import os
import urllib.parse
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'klinik360_super_gizli_anahtar_2026')

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    if DATABASE_URL:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn
    else:
        conn = sqlite3.connect('klinik.db')
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    cursor = conn.cursor()
    if DATABASE_URL:
        query = query.replace('?', '%s')
    cursor.execute(query, params)
    
    result = None
    if fetchone:
        row = cursor.fetchone()
        if row and not DATABASE_URL:
            result = dict(row)
        elif row and DATABASE_URL:
            colnames = [desc[0] for desc in cursor.description]
            result = dict(zip(colnames, row))
    elif fetchall:
        rows = cursor.fetchall()
        if rows and not DATABASE_URL:
            result = [dict(r) for r in rows]
        elif rows and DATABASE_URL:
            colnames = [desc[0] for desc in cursor.description]
            result = [dict(zip(colnames, r)) for r in rows]
            
    if commit:
        conn.commit()
    conn.close()
    return result

def init_db():
    pk_type = "SERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    execute_query(f'''
        CREATE TABLE IF NOT EXISTS klinikler (
            id {pk_type},
            klinik_adi TEXT NOT NULL,
            doktor_adi TEXT NOT NULL,
            telefon TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''', commit=True)
    
    execute_query(f'''
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id {pk_type},
            klinik_id INTEGER NOT NULL,
            kullanici_adi TEXT NOT NULL,
            sifre_hash TEXT NOT NULL,
            rol TEXT NOT NULL,
            ad_soyad TEXT NOT NULL,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''', commit=True)

    varsayilan_klinik = execute_query("SELECT * FROM klinikler WHERE id = 1", fetchone=True)
    if not varsayilan_klinik:
        execute_query("INSERT INTO klinikler (id, klinik_adi, doktor_adi, telefon) VALUES (1, ?, ?, ?)",
                      ("Klinik360 Diş Polikliniği", "Dt. Mehmet Güzel", "05550000000"), commit=True)
        
    doktor_user = execute_query("SELECT * FROM kullanicilar WHERE kullanici_adi = 'doktor'", fetchone=True)
    if not doktor_user:
        hash_1234 = generate_password_hash("1234")
        execute_query("INSERT INTO kullanicilar (klinik_id, kullanici_adi, sifre_hash, rol, ad_soyad) VALUES (1, 'doktor', ?, 'doktor', 'Dt. Mehmet Güzel')", (hash_1234,), commit=True)
        
    sekreter_user = execute_query("SELECT * FROM kullanicilar WHERE kullanici_adi = 'sekreter'", fetchone=True)
    if not sekreter_user:
        hash_5678 = generate_password_hash("5678")
        execute_query("INSERT INTO kullanicilar (klinik_id, kullanici_adi, sifre_hash, rol, ad_soyad) VALUES (1, 'sekreter', ?, 'sekreter', 'Klinik Sekreteri')", (hash_5678,), commit=True)

    execute_query(f'''
        CREATE TABLE IF NOT EXISTS hastalar (
            id {pk_type},
            klinik_id INTEGER NOT NULL DEFAULT 1,
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
    ''', commit=True)

    execute_query(f'''
        CREATE TABLE IF NOT EXISTS dis_islemleri (
            id {pk_type},
            klinik_id INTEGER NOT NULL DEFAULT 1,
            hasta_id INTEGER NOT NULL,
            dis_no TEXT,
            islem_turu TEXT,
            ucret REAL,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''', commit=True)

    execute_query(f'''
        CREATE TABLE IF NOT EXISTS hasta_fotolar (
            id {pk_type},
            klinik_id INTEGER NOT NULL DEFAULT 1,
            hasta_id INTEGER NOT NULL,
            tip TEXT,
            dosya_adi TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''', commit=True)

    execute_query(f'''
        CREATE TABLE IF NOT EXISTS fiyat_tarifesi (
            id {pk_type},
            klinik_id INTEGER NOT NULL DEFAULT 1,
            islem_adi TEXT NOT NULL,
            varsayilan_fiyat REAL NOT NULL
        )
    ''', commit=True)

    tarife_count = execute_query("SELECT COUNT(*) as cnt FROM fiyat_tarifesi WHERE klinik_id = 1", fetchone=True)
    if tarife_count and tarife_count['cnt'] == 0:
        sabit_fiyatlar = [
            (1, "Kompozit Dolgu", 1500),
            (1, "Kanal Tedavisi", 3000),
            (1, "Diş Çekimi", 1000),
            (1, "Diş Taşı Temizliği", 1200),
            (1, "Porselen Kron Kaplama", 4500),
            (1, "İmplant", 12000),
            (1, "Zirkonyum Kaplama", 5500),
            (1, "Diş Beyazlatma", 4000)
        ]
        for tf in sabit_fiyatlar:
            execute_query("INSERT INTO fiyat_tarifesi (klinik_id, islem_adi, varsayilan_fiyat) VALUES (?, ?, ?)", tf, commit=True)

init_db()

DARK_MODE_STYLE = '''
<style>
:root {
    --bg-color: #f4f7f6; --card-bg: #ffffff; --text-color: #333333; --border-color: #dddddd; --form-bg: #e9ecef; --table-header-bg: #007bff; --table-header-color: #ffffff; --table-row-hover: #f1f1f1;
}
[data-theme="dark"] {
    --bg-color: #121212; --card-bg: #1e1e1e; --text-color: #e0e0e0; --border-color: #333333; --form-bg: #2a2a2a; --table-header-bg: #1f4068; --table-header-color: #ffffff; --table-row-hover: #2c2c2c;
}
body { background-color: var(--bg-color) !important; color: var(--text-color) !important; transition: background-color 0.3s, color 0.3s; }
.container, .box, .info-box, .photo-card { background-color: var(--card-bg) !important; color: var(--text-color) !important; border-color: var(--border-color) !important; }
form { background-color: var(--form-bg) !important; color: var(--text-color) !important; }
input, select, textarea { background-color: var(--card-bg) !important; color: var(--text-color) !important; border: 1px solid var(--border-color) !important; }
table { background-color: var(--card-bg) !important; color: var(--text-color) !important; }
th { background-color: var(--table-header-bg) !important; color: var(--table-header-color) !important; }
td { border-color: var(--border-color) !important; }
tr:hover { background-color: var(--table-row-hover) !important; }
.theme-toggle-btn { background: transparent; border: 2px solid #007bff; color: #007bff; padding: 6px 12px; border-radius: 20px; cursor: pointer; font-weight: bold; font-size: 13px; display: inline-flex; align-items: center; gap: 5px; transition: 0.2s; }
[data-theme="dark"] .theme-toggle-btn { border-color: #ffc107; color: #ffc107; }
@media (max-width: 768px) { .container { padding: 10px !important; } .stats-grid { grid-template-columns: 1fr !important; } .tooth-grid { grid-template-columns: repeat(4, 1fr) !important; } table { display: block; overflow-x: auto; white-space: nowrap; } }
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
    if (btn) { btn.innerHTML = theme === 'dark' ? '☀️ Aydınlık Mod' : '🌙 Karanlık Mod'; }
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
        sifre = request.form.get('sifre', '')
        kullanicilar = execute_query("SELECT * FROM kullanicilar WHERE klinik_id = 1", fetchall=True) or []
        giris_basarili = False
        for u in kullanicilar:
            if check_password_hash(u['sifre_hash'], sifre):
                session['kullanici_id'] = u['id']
                session['klinik_id'] = u['klinik_id']
                session['kullanici_rolu'] = u['rol']
                session['ad_soyad'] = u['ad_soyad']
                giris_basarili = True
                break
        if giris_basarili:
            return redirect(url_for('doktor_panel'))
        else:
            hata = "Hatalı şifre!"
    return render_template_string(DOKTOR_GIRIS_HTML, hata=hata)

@app.route('/doktor-cikis')
def doktor_cikis():
    session.clear()
    return redirect(url_for('index'))

@app.route('/doktor-panel')
def doktor_panel():
    rol = session.get('kullanici_rolu')
    klinik_id = session.get('klinik_id', 1)
    if not rol:
        return redirect(url_for('doktor_giris'))
        
    ayar = execute_query("SELECT * FROM klinikler WHERE id = ?", (klinik_id,), fetchone=True)
    arama = request.args.get('arama', '')
    if arama:
        hastalar = execute_query("SELECT * FROM hastalar WHERE klinik_id = ? AND (ad_soyad LIKE ? OR telefon LIKE ? OR tc_no LIKE ?) ORDER BY id DESC", 
                                 (klinik_id, '%' + arama + '%', '%' + arama + '%', '%' + arama + '%'), fetchall=True) or []
    else:
        hastalar = execute_query("SELECT * FROM hastalar WHERE klinik_id = ? ORDER BY id DESC", (klinik_id,), fetchall=True) or []

    randevular = execute_query("SELECT id, ad_soyad, telefon, randevu_tarihi, randevu_saati FROM hastalar WHERE klinik_id = ? AND randevu_tarihi IS NOT NULL AND randevu_tarihi != '' ORDER BY randevu_tarihi ASC, randevu_saati ASC", (klinik_id,), fetchall=True) or []
    toplam_hasta = (execute_query("SELECT COUNT(*) as toplam FROM hastalar WHERE klinik_id = ?", (klinik_id,), fetchone=True) or {'toplam': 0})['toplam']
    toplam_randevu = (execute_query("SELECT COUNT(*) as toplam FROM hastalar WHERE klinik_id = ? AND randevu_tarihi IS NOT NULL AND randevu_tarihi != ''", (klinik_id,), fetchone=True) or {'toplam': 0})['toplam']
    toplam_islem = (execute_query("SELECT COUNT(*) as toplam FROM dis_islemleri WHERE klinik_id = ?", (klinik_id,), fetchone=True) or {'toplam': 0})['toplam']
    tarifeler = execute_query("SELECT * FROM fiyat_tarifesi WHERE klinik_id = ? ORDER BY islem_adi ASC", (klinik_id,), fetchall=True) or []

    return render_template_string(DOKTOR_PANEL_HTML, hastalar=hastalar, randevular=randevular, arama=arama, toplam_hasta=toplam_hasta, toplam_randevu=toplam_randevu, toplam_islem=toplam_islem, ayar=ayar, tarifeler=tarifeler, rol=rol)

@app.route('/fiyat-guncelle', methods=['POST'])
def fiyat_guncelle():
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('doktor_panel'))
    klinik_id = session.get('klinik_id', 1)
    for key, val in request.form.items():
        if key.startswith('fiyat_'):
            tarife_id = key.split('_')[1]
            execute_query("UPDATE fiyat_tarifesi SET varsayilan_fiyat = ? WHERE id = ? AND klinik_id = ?", (val, tarife_id, klinik_id), commit=True)
    return redirect(url_for('doktor_panel'))

@app.route('/ekle', methods=['POST'])
def ekle():
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
    klinik_id = session.get('klinik_id', 1)
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

    execute_query('''
        INSERT INTO hastalar (klinik_id, ad_soyad, telefon, tc_no, dogum_tarihi, yas, semptomlar, anamnez, ozel_not, alerji, randevu_tarihi, randevu_saati)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (klinik_id, ad_soyad, telefon, tc_no, dogum_tarihi, yas, semptomlar_str, anamnez_str, ozel_not, alerji, randevu_tarihi, randevu_saati), commit=True)
    return redirect(url_for('doktor_panel'))

@app.route('/hasta-duzenle/<int:hasta_id>', methods=['GET', 'POST'])
def hasta_duzenle(hasta_id):
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
    klinik_id = session.get('klinik_id', 1)
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

        execute_query('''
            UPDATE hastalar 
            SET ad_soyad=?, telefon=?, tc_no=?, dogum_tarihi=?, yas=?, ozel_not=?, alerji=?, randevu_tarihi=?, randevu_saati=?
            WHERE id=? AND klinik_id=?
        ''', (ad_soyad, telefon, tc_no, dogum_tarihi, yas, ozel_not, alerji, randevu_tarihi, randevu_saati, hasta_id, klinik_id), commit=True)
        return redirect(url_for('doktor_panel'))

    hasta = execute_query("SELECT * FROM hastalar WHERE id = ? AND klinik_id = ?", (hasta_id, klinik_id), fetchone=True)
    return render_template_string(HASTA_DUZENLE_HTML, hasta=hasta)

@app.route('/hasta-sil/<int:hasta_id>')
def hasta_sil(hasta_id):
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('doktor_panel'))
    klinik_id = session.get('klinik_id', 1)
    execute_query("DELETE FROM dis_islemleri WHERE hasta_id = ? AND klinik_id = ?", (hasta_id, klinik_id), commit=True)
    execute_query("DELETE FROM hasta_fotolar WHERE hasta_id = ? AND klinik_id = ?", (hasta_id, klinik_id), commit=True)
    execute_query("DELETE FROM hastalar WHERE id = ? AND klinik_id = ?", (hasta_id, klinik_id), commit=True)
    return redirect(url_for('doktor_panel'))

@app.route('/islem-sil/<int:islem_id>/<int:hasta_id>')
def islem_sil(islem_id, hasta_id):
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('hasta_detay', hasta_id=hasta_id))
    klinik_id = session.get('klinik_id', 1)
    execute_query("DELETE FROM dis_islemleri WHERE id = ? AND klinik_id = ?", (islem_id, klinik_id), commit=True)
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/foto-sil/<int:foto_id>/<int:hasta_id>')
def foto_sil(foto_id, hasta_id):
    if session.get('kullanici_rolu') != 'doktor':
        return redirect(url_for('hasta_detay', hasta_id=hasta_id))
    klinik_id = session.get('klinik_id', 1)
    foto = execute_query("SELECT dosya_adi FROM hasta_fotolar WHERE id = ? AND klinik_id = ?", (foto_id, klinik_id), fetchone=True)
    if foto:
        dosya_yolu = os.path.join(app.config['UPLOAD_FOLDER'], foto['dosya_adi'])
        if os.path.exists(dosya_yolu):
            os.remove(dosya_yolu)
    execute_query("DELETE FROM hasta_fotolar WHERE id = ? AND klinik_id = ?", (foto_id, klinik_id), commit=True)
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/foto-goster/<int:foto_id>')
def foto_goster(foto_id):
    foto = execute_query("SELECT * FROM hasta_fotolar WHERE id = ?", (foto_id,), fetchone=True)
    if not foto:
        return abort(404)
    
    doktor_rol = session.get('kullanici_rolu')
    giris_yapan_hasta_id = session.get('hasta_id')
    
    if doktor_rol:
        klinik_id = session.get('klinik_id', 1)
        if foto['klinik_id'] != klinik_id:
            return abort(403)
    elif giris_yapan_hasta_id:
        if foto['hasta_id'] != giris_yapan_hasta_id:
            return abort(403)
    else:
        return redirect(url_for('index'))
        
    guvenli_dosya = os.path.basename(foto['dosya_adi'])
    return send_from_directory(app.config['UPLOAD_FOLDER'], guvenli_dosya)

@app.route('/hasta-detay/<int:hasta_id>')
def hasta_detay(hasta_id):
    rol = session.get('kullanici_rolu')
    klinik_id = session.get('klinik_id', 1)
    if not rol:
        return redirect(url_for('doktor_giris'))
        
    hasta = execute_query("SELECT * FROM hastalar WHERE id = ? AND klinik_id = ?", (hasta_id, klinik_id), fetchone=True)
    islemler = execute_query("SELECT * FROM dis_islemleri WHERE hasta_id = ? AND klinik_id = ?", (hasta_id, klinik_id), fetchall=True) or []
    fotolar = execute_query("SELECT * FROM hasta_fotolar WHERE hasta_id = ? AND klinik_id = ?", (hasta_id, klinik_id), fetchall=True) or []
    ayar = execute_query("SELECT * FROM klinikler WHERE id = ?", (klinik_id,), fetchone=True)
    tarifeler = execute_query("SELECT * FROM fiyat_tarifesi WHERE klinik_id = ? ORDER BY islem_adi ASC", (klinik_id,), fetchall=True) or []
    return render_template_string(HASTA_DETAY_HTML, hasta=hasta, islemler=islemler, fotolar=fotolar, ayar=ayar, tarifeler=tarifeler, rol=rol)

@app.route('/dis_islem_ekle/<int:hasta_id>', methods=['POST'])
def dis_islem_ekle(hasta_id):
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
    klinik_id = session.get('klinik_id', 1)
    dis_no = request.form.get('dis_no', '')
    islem_turu = request.form.get('islem_turu', '')
    ucret = request.form.get('ucret', 0)
    execute_query('''
        INSERT INTO dis_islemleri (klinik_id, hasta_id, dis_no, islem_turu, ucret)
        VALUES (?, ?, ?, ?, ?)
    ''', (klinik_id, hasta_id, dis_no, islem_turu, ucret), commit=True)
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/foto-ekle/<int:hasta_id>', methods=['POST'])
def foto_ekle(hasta_id):
    if not session.get('kullanici_rolu'):
        return redirect(url_for('doktor_giris'))
    klinik_id = session.get('klinik_id', 1)
    tip = request.form.get('tip', 'once')
    dosya = request.files.get('foto')
    if dosya and dosya.filename != '':
        filename = secure_filename(f"hasta_{hasta_id}_{os.urandom(4).hex()}_{dosya.filename}")
        dosya.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        execute_query("INSERT INTO hasta_fotolar (klinik_id, hasta_id, tip, dosya_adi) VALUES (?, ?, ?, ?)", (klinik_id, hasta_id, tip, filename), commit=True)
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/hasta-rapor/<int:hasta_id>')
def hasta_rapor(hasta_id):
    klinik_id = session.get('klinik_id', 1)
    hasta = execute_query("SELECT * FROM hastalar WHERE id = ? AND klinik_id = ?", (hasta_id, klinik_id), fetchone=True)
    islemler = execute_query("SELECT * FROM dis_islemleri WHERE hasta_id = ? AND klinik_id = ?", (hasta_id, klinik_id), fetchall=True) or []
    fotolar = execute_query("SELECT * FROM hasta_fotolar WHERE hasta_id = ? AND klinik_id = ?", (hasta_id, klinik_id), fetchall=True) or []
    ayar = execute_query("SELECT * FROM klinikler WHERE id = ?", (klinik_id,), fetchone=True)
    recete_secimi = request.args.get('recete', '')
    return render_template_string(HASTA_RAPOR_HTML, hasta=hasta, islemler=islemler, fotolar=fotolar, recete_secimi=recete_secimi, ayar=ayar)

@app.route('/hasta-giris', methods=['GET', 'POST'])
def hasta_giris():
    hata = None
    if request.method == 'POST':
        girdi = request.form.get('girdi', '').strip()
        hasta = execute_query("SELECT * FROM hastalar WHERE telefon LIKE ? OR tc_no = ?", ('%' + girdi + '%', girdi), fetchone=True)
        if hasta:
            session['hasta_id'] = hasta['id']
            return redirect(url_for('hasta_profil'))
        else:
            hata = "Girdiğiniz bilgilere ait kayıt bulunamadı."
    return render_template_string(HASTA_GIRIS_HTML, hata=hata)

@app.route('/hasta-profil')
def hasta_profil():
    hasta_id = session.get('hasta_id')
    if not hasta_id:
        return redirect(url_for('hasta_giris'))
    hasta = execute_query("SELECT * FROM hastalar WHERE id = ?", (hasta_id,), fetchone=True)
    if not hasta:
        return redirect(url_for('hasta_giris'))
    klinik_id = hasta['klinik_id']
    islemler = execute_query("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,), fetchall=True) or []
    fotolar = execute_query("SELECT * FROM hasta_fotolar WHERE hasta_id = ?", (hasta_id,), fetchall=True) or []
    ayar = execute_query("SELECT * FROM klinikler WHERE id = ?", (klinik_id,), fetchone=True)
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
<style>body { font-family: Arial, sans-serif; margin: 0; padding: 20px; text-align: center; } .box { max-width: 450px; margin: 60px auto; padding: 40px 30px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); } .btn { display: block; width: 100%; padding: 14px; margin: 15px 0; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold; color: white; box-sizing: border-box; transition: 0.2s; } .btn-doktor { background: #007bff; } .btn-hasta { background: #28a745; }</style></head>
<body>
    <div style="text-align: right; max-width: 450px; margin: auto;"><button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button></div>
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
<div style="text-align: right; max-width: 380px; margin: auto;"><button id="theme-toggle-btn" class="theme-toggle-btn" onclick="toggleTheme()">🌙 Karanlık Mod</button></div>
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

import sqlite3
import os

# Veritabani ve klinik_id kontrolu
import sqlite3
import os

# Veritabani ve eksik sutunlarin kontrolu / eklenmesi
def check_and_database_setup():
    db_path = 'klinik.db'
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Hastalar tablosundaki mevcut sutunlari al
        cursor.execute("PRAGMA table_info(hastalar);")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Eksik sutunlari kontrol et ve ekle
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