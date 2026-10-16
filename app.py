from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'klinik360_gizli_anahtar'

DOKTOR_SIFRE = "1234"

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
    
    # Sütun kontrolü ve eksikse ekleme
    cursor.execute("PRAGMA table_info(hastalar)")
    sutunlar = [row[1] for row in cursor.fetchall()]
    
    yeni_sutunlar = {
        "tc_no": "TEXT",
        "dogum_tarihi": "TEXT",
        "randevu_tarihi": "TEXT",
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
        
    conn = get_db()
    cursor = conn.cursor()
    
    arama = request.args.get('arama', '')
    if arama:
        cursor.execute("SELECT * FROM hastalar WHERE ad_soyad LIKE ? OR telefon LIKE ? OR tc_no LIKE ? ORDER BY id DESC", ('%' + arama + '%', '%' + arama + '%', '%' + arama + '%'))
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

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO hastalar (ad_soyad, telefon, tc_no, dogum_tarihi, yas, semptomlar, anamnez, ozel_not, alerji, randevu_tarihi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (ad_soyad, telefon, tc_no, dogum_tarihi, yas, semptomlar_str, anamnez_str, ozel_not, alerji, randevu_tarihi))
    conn.commit()
    conn.close()
    return redirect(url_for('doktor_panel'))

@app.route('/hasta-duzenle/<int:hasta_id>', methods=['GET', 'POST'])
def hasta_duzenle(hasta_id):
    if not session.get('doktor_giris'):
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

        cursor.execute('''
            UPDATE hastalar 
            SET ad_soyad=?, telefon=?, tc_no=?, dogum_tarihi=?, yas=?, ozel_not=?, alerji=?, randevu_tarihi=?
            WHERE id=?
        ''', (ad_soyad, telefon, tc_no, dogum_tarihi, yas, ozel_not, alerji, randevu_tarihi, hasta_id))
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
        
    conn = get_db()
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
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dis_islemleri WHERE id = ?", (islem_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('hasta_detay', hasta_id=hasta_id))

@app.route('/hasta-detay/<int:hasta_id>')
def hasta_detay(hasta_id):
    if not session.get('doktor_giris'):
        return redirect(url_for('doktor_giris'))
        
    conn = get_db()
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

@app.route('/hasta-rapor/<int:hasta_id>')
def hasta_rapor(hasta_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hastalar WHERE id = ?", (hasta_id,))
    hasta = cursor.fetchone()
    cursor.execute("SELECT * FROM dis_islemleri WHERE hasta_id = ?", (hasta_id,))
    islemler = cursor.fetchall()
    
    recete_secimi = request.args.get('recete', '')
    conn.close()
    return render_template_string(HASTA_RAPOR_HTML, hasta=hasta, islemler=islemler, recete_secimi=recete_secimi)

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
    conn.close()
    return render_template_string(HASTA_PROFIL_HTML, hasta=hasta, islemler=islemler)

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
<style>
body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; text-align: center; color: #333; }
.box { max-width: 450px; margin: 60px auto; background: white; padding: 40px 30px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
.btn { display: block; width: 100%; padding: 14px; margin: 15px 0; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold; color: white; box-sizing: border-box; transition: 0.2s; }
.btn-doktor { background: #007bff; } .btn-hasta { background: #28a745; }
</style></head>
<body>
    <div class="box">
        ''' + LOGO_HTML + '''
        <p style="color: #666; margin-bottom: 25px; font-size: 15px;">Diş Klinik Yönetim Sistemi</p>
        <a href="/doktor-giris" class="btn btn-doktor">👩‍⚕️ Doktor / Yönetici Girişi</a>
        <a href="/hasta-giris" class="btn btn-hasta">📱 Hasta Randevu & Takip</a>
    </div>
</body></html>
'''

DOKTOR_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Doktor Girişi</title>
<style>body{font-family:Arial;background:#e9ecef;padding:20px;text-align:center}.box{max-width:380px;margin:80px auto;background:white;padding:30px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.1)}input{width:100%;padding:12px;margin:15px 0;border:1px solid #ccc;border-radius:6px;text-align:center;box-sizing:border-box;font-size:16px}button{width:100%;padding:12px;background:#007bff;color:white;border:none;border-radius:6px;cursor:pointer;font-size:16px}</style></head>
<body>
<div class="box">
    ''' + LOGO_HTML + '''
    <h2>Doktor Girişi</h2>
    {% if hata %}<p style="color:red; font-size:14px;">{{ hata }}</p>{% endif %}
    <form method="POST">
        <input type="password" name="sifre" placeholder="Şifre (1234)" required>
        <button type="submit">Giriş Yap</button>
    </form>
    <br><a href="/" style="color:#666;text-decoration:none;font-size:14px;">⬅ Ana Sayfa</a>
</div>
</body></html>
'''

DOKTOR_PANEL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Doktor Paneli - Klinik360</title>
<style>
body{font-family:Arial;background:#f4f7f6;padding:10px;color:#333}
.container{max-width:1000px;margin:auto;background:white;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}
.header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #eee;padding-bottom:10px;margin-bottom:20px}
.takvim-box{background:#e3f2fd;padding:15px;border-radius:8px;margin-bottom:20px;border-left:5px solid #007bff}
form{background:#e9ecef;padding:20px;border-radius:8px;margin-bottom:20px}
input,select,textarea{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:5px;box-sizing:border-box}
.checkbox-group{background:white;padding:10px;border-radius:5px;border:1px solid #ccc;margin:8px 0}
.checkbox-group label{display:block;margin-bottom:5px;cursor:pointer;font-size:13px;}
button{background:#28a745;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer;font-size:16px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ddd;padding:10px;text-align:left;font-size:13px}
th{background:#007bff;color:white}
.btn-sm{padding:5px 10px;text-decoration:none;border-radius:4px;font-size:12px;display:inline-block;margin:2px}
.btn-info{background:#17a2b8;color:white}.btn-wa{background:#25d366;color:white}.btn-edit{background:#ffc107;color:#000}.btn-del{background:#dc3545;color:white}
.badge-danger{background:#dc3545; color:white; padding:2px 6px; border-radius:4px; font-size:11px;}
</style></head>
<body>
<div class="container">
    <div class="header">
        <div><span style="font-size: 22px; font-weight: bold; color: #007bff;">🦷 Klinik360</span> <span style="font-size: 14px; color: #666;">| Doktor Paneli</span></div>
        <div><a href="/doktor-cikis" style="background:#dc3545;color:white;padding:8px 15px;text-decoration:none;border-radius:6px;font-size:14px;">Çıkış Yap</a></div>
    </div>

    <div class="takvim-box">
        <h3 style="margin-top:0;color:#0056b3;">📆 Yaklaşan Randevu Takvimi</h3>
        {% if randevular %}
            <ul style="margin:0;padding-left:20px;">
            {% for r in randevular %}
                <li><b>{{ r['randevu_tarihi'] }}</b> - {{ r['ad_soyad'] }} (Tel: {{ r['telefon'] }})</li>
            {% endfor %}
            </ul>
        {% else %}
            <p style="margin:0;color:gray;">Planlanmış randevu yok.</p>
        {% endif %}
    </div>

    <form action="/ekle" method="POST">
        <h3 style="margin-top:0; color:#007bff;">Yeni Hasta Kaydı & Tıbbi Anamnez</h3>
        <input type="text" name="ad_soyad" placeholder="Hasta Adı Soyadı" required>
        <input type="text" name="telefon" placeholder="Telefon Numarası (0555...)" required>
        <input type="text" name="tc_no" placeholder="TC Kimlik Numarası (11 Haneli)" maxlength="11">
        <div style="display:flex; gap:10px;">
            <div style="flex:1;"><label style="font-size:12px; color:#666;">Doğum Tarihi:</label><input type="date" name="dogum_tarihi"></div>
            <div style="flex:1;"><label style="font-size:12px; color:#666;">Yaş:</label><input type="number" name="yas" placeholder="Yaş"></div>
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
        <input type="date" name="randevu_tarihi">
        <button type="submit">Hastayı Kaydet</button>
    </form>

    <form method="GET" action="/doktor-panel" style="background:none;padding:0;">
        <input type="text" name="arama" placeholder="🔍 İsim, telefon veya TC No ile ara..." value="{{ arama }}">
    </form>

    <h2>Kayıtlı Hastalar</h2>
    <table>
        <tr><th>Kimlik & Ad Soyad</th><th>İletişim & TC</th><th>Kritik Anamnez & Notlar</th><th>Randevu</th><th>İşlemler</th></tr>
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
            <td>{{ h['randevu_tarihi'] or '' }}</td>
            <td>
                <a class="btn-sm btn-info" href="/hasta-detay/{{ h['id'] }}">Diş Kartı</a>
                <a class="btn-sm btn-wa" href="https://wa.me/9{{ h['telefon'] }}?text=Sayın%20{{ h['ad_soyad'] }},%20Klinik360%20randevunuzu%20hatırlatırız." target="_blank">WhatsApp</a>
                <a class="btn-sm btn-edit" href="/hasta-duzenle/{{ h['id'] }}">Düzenle</a>
                <a class="btn-sm btn-del" href="/hasta-sil/{{ h['id'] }}" onclick="return confirm('Silmek istediğinize emin misiniz?')">Sil</a>
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
<head><meta charset="UTF-8"><title>Düzenle</title><style>body{font-family:Arial;padding:20px;background:#f4f7f6}.box{max-width:500px;margin:auto;background:white;padding:25px;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}input,textarea{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:5px;box-sizing:border-box}button{background:#28a745;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer;font-size:16px}</style></head>
<body><div class="box">
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
        <button type="submit">GÜNCELLE</button>
    </form>
    <br><a href="/doktor-panel" style="color:gray;text-decoration:none;">⬅ İptal</a>
</div></body></html>
'''

HASTA_DETAY_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Diş Kartı</title>
<style>
body{font-family:Arial;padding:10px;background:#f4f7f6}
.container{max-width:850px;margin:auto;background:white;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}
.info-box{background:#e9ecef;padding:15px;border-radius:8px;margin-bottom:20px}
form{background:#f8f9fa;padding:15px;border-radius:8px;border:1px solid #ddd;margin-bottom:20px}
input,select{width:100%;padding:10px;margin:8px 0;border:1px solid #ccc;border-radius:5px;box-sizing:border-box}
button{background:#007bff;color:white;border:none;padding:12px;width:100%;border-radius:5px;cursor:pointer;font-size:16px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ddd;padding:10px;text-align:left}
th{background:#28a745;color:white}
.btn-pdf{background:#17a2b8;color:white;padding:8px 15px;text-decoration:none;border-radius:5px;float:right;display:inline-block;}
.badge-danger{background:#dc3545; color:white; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:bold;}
</style></head>
<body><div class="container">
    <a href="/doktor-panel" style="background:#6c757d;color:white;padding:8px 12px;text-decoration:none;border-radius:6px;">⬅ Geri</a>
    <a class="btn-pdf" href="/hasta-rapor/{{ hasta['id'] }}" target="_blank">📄 PDF / Reçete & Rapor Al</a>
    <h1 style="color:#007bff;">🦷 Hasta Diş Kartı & Tedavi Planı</h1>
    
    <div class="info-box">
        <h3>{{ hasta['ad_soyad'] }}</h3>
        {% if hasta['anamnez'] and hasta['anamnez'] != 'Özellik yok' %}
            <p><b>Kritik Anamnez:</b> <span class="badge-danger">{{ hasta['anamnez'] }}</span></p>
        {% endif %}
        <p><b>TC No:</b> {{ hasta['tc_no'] or 'Belirtilmemiş' }} | <b>Telefon:</b> {{ hasta['telefon'] }}</p>
        <p><b>Doğum Tarihi:</b> {{ hasta['dogum_tarihi'] or '-' }} | <b>Yaş:</b> {{ hasta['yas'] or '-' }}</p>
        <p><b>Semptomlar:</b> {{ hasta['semptomlar'] or '' }}</p>
        <p><b>Doktor Notu:</b> {{ hasta['ozel_not'] or '' }}</p>
        <p><b>Alerji:</b> <span style="color:red; font-weight:bold;">{{ hasta['alerji'] or 'Yok' }}</span></p>
    </div>

    <form action="/dis_islem_ekle/{{ hasta['id'] }}" method="POST">
        <h3 style="margin-top:0; color:#007bff;">ISO Diş Numaralandırma & Tedavi Ekle</h3>
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
            <option value="Kompozit Dolgu">Kompozit Dolgu</option>
            <option value="Kanal Tedavisi">Kanal Tedavisi</option>
            <option value="Diş Çekimi">Diş Çekimi</option>
            <option value="Diş Taşı Temizliği">Diş Taşı Temizliği</option>
            <option value="Porselen Kron Kaplama">Porselen Kron Kaplama</option>
            <option value="İmplant">İmplant</option>
        </select>
        <button type="submit">İşlemi Kaydet</button>
    </form>

    <h2>Uygulanan Diş Tedavileri</h2>
    <table>
        <tr><th>Diş No</th><th>Tedavi</th><th>Eylem</th></tr>
        {% for i in islemler %}
        <tr>
            <td><b>Diş #{{ i['dis_no'] }}</b></td><td>{{ i['islem_turu'] }}</td>
            <td><a href="/islem-sil/{{ i['id'] }}/{{ hasta['id'] }}" style="color:red;text-decoration:none;" onclick="return confirm('Silmek istediğinize emin misiniz?')">🗑️ Sil</a></td>
        </tr>
        {% endfor %}
    </table>
</div></body></html>
'''

HASTA_RAPOR_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Reçete ve Rapor</title>
<style>
body{font-family:Arial;padding:40px;color:#333; max-width:800px; margin:auto;}
.header{text-align:center;border-bottom:2px solid #007bff;padding-bottom:10px;margin-bottom:20px}
.box{background:#f9f9f9;padding:15px;border-radius:5px;margin-bottom:20px;border:1px solid #ddd}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #333;padding:8px;text-align:left}th{background:#eee}
.print-btn{background:#28a745;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-size:16px;margin-bottom:20px}
.recete-box{background:#e8f4fd; border:1px dashed #007bff; padding:15px; border-radius:8px; margin-top:20px;}
@media print{.print-btn, .no-print{display:none}}
</style></head>
<body>
<button class="print-btn" onclick="window.print()">🖨️ Sayfayı Yazdır / PDF İndir</button>

<div class="header">
    <h1 style="color: #007bff; margin: 0;">🦷 Klinik360</h1>
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
    <tr><th>Diş No (ISO)</th><th>Tedavi Açıklaması</th></tr>
    {% for i in islemler %}
    <tr><td>Diş #{{ i['dis_no'] }}</td><td>{{ i['islem_turu'] }}</td></tr>
    {% endfor %}
</table>

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
    <p style="text-align:right;"><b>Hekim Kaşesi & İmza</b><br>Klinik360 Diş Polikliniği</p>
</div>
{% endif %}

</body></html>
'''

HASTA_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Hasta Girişi</title><style>body{font-family:Arial;background:#e9ecef;padding:20px;text-align:center}.box{max-width:400px;margin:60px auto;background:white;padding:30px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.1)}input{width:100%;padding:12px;margin:15px 0;border:1px solid #ccc;border-radius:6px;text-align:center;box-sizing:border-box;font-size:16px}button{width:100%;padding:12px;background:#28a745;color:white;border:none;border-radius:6px;cursor:pointer;font-size:16px}</style></head>
<body>
<div class="box">
    ''' + LOGO_HTML + '''
    <h2>Hasta Takip Paneli</h2>
    <p style="color:#666; font-size:14px;">Telefon numaranız veya TC Kimlik numaranız ile giriş yapabilirsiniz.</p>
    {% if hata %}<p style="color:red; font-size:14px;">{{ hata }}</p>{% endif %}
    <form method="POST">
        <input type="text" name="girdi" placeholder="Telefon veya TC Kimlik No" required>
        <button type="submit">Randevumu Göster</button>
    </form>
    <br><a href="/" style="color:#666;text-decoration:none;font-size:14px;">⬅ Ana Sayfa</a>
</div>
</body></html>
'''

HASTA_PROFIL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><title>Hasta Paneli</title><style>body{font-family:Arial;padding:10px;background:#f4f7f6}.container{max-width:600px;margin:auto;background:white;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.08)}.card{background:#e3f2fd;padding:15px;border-radius:8px;margin-bottom:20px;border-left:5px solid #007bff}table{width:100%;border-collapse:collapse;margin-top:15px}th,td{border:1px solid #ddd;padding:10px;text-align:left}th{background:#007bff;color:white}</style></head>
<body>
<div class="container">
    <a href="/" style="background:#6c757d;color:white;padding:8px 12px;text-decoration:none;border-radius:6px;">⬅ Çıkış</a>
    <h2 style="color:#007bff;">🦷 Klinik360 Hasta Bilgi Kartı</h2>
    <div class="card">
        <h3 style="margin-top:0;">Sayın {{ hasta['ad_soyad'] }}</h3>
        <p><b>TC No:</b> {{ hasta['tc_no'] or '-' }} | <b>Doğum Tarihi:</b> {{ hasta['dogum_tarihi'] or '-' }}</p>
        <p><b>🗓 Yaklaşan Randevunuz:</b> <span style="color:#d9534f;font-weight:bold;">{{ hasta['randevu_tarihi'] or 'Yok' }}</span></p>
        <p><b>👨‍⚕️ Doktor Notu:</b> {{ hasta['ozel_not'] or 'Yok' }}</p>
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
    <p style="color:gray;">Kayıtlı tedavi bulunmuyor.</p>
    {% endif %}
</div>
</body></html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)