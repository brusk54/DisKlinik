from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'klinik360_gizli_anahtar'  # Oturum güvenliği için

DOKTOR_SIFRE = "1234"  # Doktor paneli giriş şifresi

# Veritabanı ve Tablolar
def init_db():
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    
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
    conn.commit()
    conn.close()

init_db()

# Ana Sayfa / Portalı Karşılama
@app.route('/')
def index():
    return render_template_string(GIRIS_SECIM_HTML)

# Doktor Giriş Sayfası
@app.route('/doktor-giris', methods=['GET', 'POST'])
def doktor_giris():
    hata = None
    if request.method == 'POST':
        sifre = request.form.get('sifre')
        if sifre == DOKTOR_SIFRE:
            session['doktor_giris'] = True
            return redirect(url_for('doktor_panel'))
        else:
            hata = "Hatalı şifre! Lütfen tekrar deneyin."
    return render_template_string(DOKTOR_GIRIS_HTML, hata=hata)

# Doktor Çıkış
@app.route('/doktor-cikis')
def doktor_cikis():
    session.pop('doktor_giris', None)
    return redirect(url_for('index'))

# Doktor Yönetici Paneli
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
    conn.close()
    return render_template_string(DOKTOR_PANEL_HTML, hastalar=hastalar, arama=arama)

# Hasta Kayıt (Doktor Tarafından)
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

# Doktor İçin Hasta Detay & Diş Şeması
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
    
    if not hasta:
        return "Hasta bulunamadı!", 404
        
    return render_template_string(HASTA_DETAY_HTML, hasta=hasta, islemler=islemler)

# Diş İşlemi Ekleme
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

# HASTA TARAFI: Hasta Giriş & Takip Paneli
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
            hata = "Bu telefon numarasına ait kayıt bulunamadı. Lütfen kliniğimiz ile iletişime geçin."
        conn.close()
        
    return render_template_string(HASTA_GIRIS_HTML, hata=hata)

# HASTA TARAFI: Profil ve Tedavi Görüntüleme
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

# --- TEMPLATE HTML KODLARI ---

GIRIS_SECIM_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Klinik360 - Diş Klinik Portalı</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 20px; text-align: center; color: #333; }
        .box { max-width: 450px; margin: 50px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .logo { max-width: 240px; width: 100%; border-radius: 8px; margin-bottom: 15px; }
        .btn { display: block; width: 100%; padding: 14px; margin: 15px 0; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold; color: white; box-sizing: border-box; }
        .btn-doktor { background: #007bff; }
        .btn-doktor:hover { background: #0056b3; }
        .btn-hasta { background: #28a745; }
        .btn-hasta:hover { background: #218838; }
    </style>
</head>
<body>
    <div class="box">
        <img class="logo" src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=500&q=80" alt="Klinik360 Logo">
        <h2>Klinik360 Portalı</h2>
        <p style="color: #666; margin-bottom: 25px;">Lütfen giriş türünüzü seçiniz:</p>
        <a href="/doktor-giris" class="btn btn-doktor">👩‍⚕️ Doktor / Yönetici Girişi</a>
        <a href="/hasta-giris" class="btn btn-hasta">📱 Hasta Randevu & Tedavi Takibi</a>
    </div>
</body>
</html>
'''

DOKTOR_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Doktor Girişi - Klinik360</title>
    <style>
        body { font-family: Arial, sans-serif; background: #e9ecef; margin: 0; padding: 20px; text-align: center; }
        .box { max-width: 380px; margin: 60px auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; text-align: center; font-size: 16px; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }
        .error { color: red; margin-bottom: 10px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>🔐 Doktor Girişi</h2>
        {% if hata %}<p class="error">{{ hata }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="sifre" placeholder="Doktor Giriş Şifresi" required>
            <button type="submit">Giriş Yap</button>
        </form>
        <br><a href="/" style="color: #666; text-decoration: none; font-size: 14px;">⬅ Ana Sayfaya Dön</a>
    </div>
</body>
</html>
'''

DOKTOR_PANEL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Yönetici Paneli - Klinik360</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 10px; color: #333; }
        .container { max-width: 850px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 15px; }
        .logo-container img { max-width: 180px; }
        form { background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        input, select, textarea { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        .checkbox-group { background: white; padding: 10px; border-radius: 5px; border: 1px solid #ccc; margin: 8px 0; }
        .checkbox-group label { display: block; margin-bottom: 5px; cursor: pointer; }
        button { background: #28a745; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 14px; }
        th { background: #007bff; color: white; }
        .search-box { display: flex; gap: 10px; margin-bottom: 15px; }
        .whatsapp-btn { background: #25d366; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px; }
        .detay-btn { background: #17a2b8; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px; margin-right: 5px; }
        .cikis-btn { background: #dc3545; color: white; padding: 6px 12px; text-decoration: none; border-radius: 5px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-container">
                <img src="https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=500&q=80" alt="Klinik360 Logo">
            </div>
            <div>
                <span style="font-weight: bold; color: #007bff;">👩‍⚕️ Doktor Paneli</span>
                <a href="/doktor-cikis" class="cikis-btn" style="margin-left: 10px;">Çıkış</a>
            </div>
        </div>

        <form action="/ekle" method="POST">
            <h3>Yeni Hasta Kaydı</h3>
            <input type="text" name="ad_soyad" placeholder="Hasta Adı Soyadı" required>
            <input type="text" name="telefon" placeholder="Telefon Numarası (Örn: 0555...)" required>
            <input type="number" name="yas" placeholder="Yaş">
            
            <label><b>Semptomlar ve Şikayetler:</b></label>
            <div class="checkbox-group">
                <label><input type="checkbox" name="semptomlar" value="Şiddetli Ağrı (Apse Şüphesi)"> Şiddetli Ağrı (Apse Şüphesi)</label>
                <label><input type="checkbox" name="semptomlar" value="Hassasiyet (Sıcak/Soğuk)"> Hassasiyet (Sıcak/Soğuk)</label>
                <label><input type="checkbox" name="semptomlar" value="Diş Eti Kanaması / Şişliği"> Diş Eti Kanaması / Şişliği</label>
                <label><input type="checkbox" name="semptomlar" value="Çürük / Kırık Diş"> Çürük / Kırık Diş</label>
                <label><input type="checkbox" name="semptomlar" value="Estetik / Dolgu / Beyazlatma"> Estetik / Dolgu / Beyazlatma</label>
                <label><input type="checkbox" name="semptomlar" value="Diş Gıcırdatma (Bruksizm)"> Diş Gıcırdatma (Bruksizm)</label>
            </div>

            <textarea name="ozel_not" placeholder="Özel Not / Doktor Açıklaması..." rows="3"></textarea>
            <input type="text" name="alerji" placeholder="Alerji Durumu (Varsa)">
            <input type="date" name="randevu_tarihi">
            <button type="submit">Hastayı Kaydet</button>
        </form>

        <form class="search-box" method="GET" action="/doktor-panel">
            <input type="text" name="arama" placeholder="İsim veya telefon ile hasta ara..." value="{{ arama }}">
            <button type="submit" style="width: 120px; margin:0;">Ara</button>
        </form>

        <h2>Kayıtlı Hastalar</h2>
        <table>
            <tr>
                <th>Ad Soyad</th>
                <th>Telefon</th>
                <th>Semptomlar & Not</th>
                <th>Randevu</th>
                <th>İşlemler / İletişim</th>
            </tr>
            {% for h in hastalar %}
            <tr>
                <td><b>{{ h[1] }}</b><br><small>Yaş: {{ h[3] }}</small></td>
                <td>{{ h[2] }}</td>
                <td>
                    <b>Semptom:</b> {{ h[4] }}<br>
                    {% if h[5] %}<b>Not:</b> {{ h[5] }}<br>{% endif %}
                    <small style="color: gray;">Alerji: {{ h[6] }}</small>
                </td>
                <td>{{ h[7] }}</td>
                <td>
                    <a class="detay-btn" href="/hasta-detay/{{ h[0] }}">Diş Şeması & İşlem</a>
                    <a class="whatsapp-btn" href="https://wa.me/9{{ h[2] }}?text=Sayın%20{{ h[1] }},%20Klinik360%20diş%20kliniğimizdeki%20{{ h[7] }}%20tarihli%20randevunuzu%20hatırlatmak%20isteriz.%20Sağlıklı%20günler%20dileriz." target="_blank">WhatsApp</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

HASTA_DETAY_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ hasta[1] }} - Diş Kartı | Klinik360</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 10px; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .info-box { background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        form { background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 20px; }
        input, select { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 14px; }
        th { background: #28a745; color: white; }
        .back-btn { background: #6c757d; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; display: inline-block; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <a class="back-btn" href="/doktor-panel">⬅ Doktor Paneline Dön</a>
        <h1>🦷 Hasta Diş Kartı & Tedaviler</h1>
        
        <div class="info-box">
            <h3>{{ hasta[1] }}</h3>
            <p><b>Telefon:</b> {{ hasta[2] }} | <b>Yaş:</b> {{ hasta[3] }}</p>
            <p><b>Semptomlar:</b> {{ hasta[4] }}</p>
            <p><b>Doktor Notu:</b> {{ hasta[5] }}</p>
            <p><b>Randevu Tarihi:</b> {{ hasta[7] }}</p>
        </div>

        <form action="/dis_islem_ekle/{{ hasta[0] }}" method="POST">
            <h3>Diş Tedavisi / İşlem Ekle</h3>
            <select name="dis_no" required>
                <option value="">-- Diş Seçiniz (ISO Numarası) --</option>
                <optgroup label="Üst Çene Sağ">
                    <option value="11">11 - Sağ Üst Kesici</option>
                    <option value="12">12 - Sağ Üst Yan Kesici</option>
                    <option value="13">13 - Sağ Üst Köpek</option>
                    <option value="14">14 - Sağ Üst 1. Küçük Azı</option>
                    <option value="15">15 - Sağ Üst 2. Küçük Azı</option>
                    <option value="16">16 - Sağ Üst 1. Büyük Azı</option>
                    <option value="17">17 - Sağ Üst 2. Büyük Azı</option>
                    <option value="18">18 - Sağ Üst 20 Yaş Dişi</option>
                </optgroup>
                <optgroup label="Üst Çene Sol">
                    <option value="21">21 - Sol Üst Kesici</option>
                    <option value="22">22 - Sol Üst Yan Kesici</option>
                    <option value="23">23 - Sol Üst Köpek</option>
                    <option value="24">24 - Sol Üst 1. Küçük Azı</option>
                    <option value="25">25 - Sol Üst 2. Küçük Azı</option>
                    <option value="26">26 - Sol Üst 1. Büyük Azı</option>
                    <option value="27">27 - Sol Üst 2. Büyük Azı</option>
                    <option value="28">28 - Sol Üst 20 Yaş Dişi</option>
                </optgroup>
                <optgroup label="Alt Çene Sol">
                    <option value="31">31 - Sol Alt Kesici</option>
                    <option value="32">32 - Sol Alt Yan Kesici</option>
                    <option value="33">33 - Sol Alt Köpek</option>
                    <option value="34">34 - Sol Alt 1. Küçük Azı</option>
                    <option value="35">35 - Sol Alt 2. Küçük Azı</option>
                    <option value="36">36 - Sol Alt 1. Büyük Azı</option>
                    <option value="37">37 - Sol Alt 2. Büyük Azı</option>
                    <option value="38">38 - Sol Alt 20 Yaş Dişi</option>
                </optgroup>
                <optgroup label="Alt Çene Sağ">
                    <option value="41">41 - Sağ Alt Kesici</option>
                    <option value="42">42 - Sağ Alt Yan Kesici</option>
                    <option value="43">43 - Sağ Alt Köpek</option>
                    <option value="44">44 - Sağ Alt 1. Küçük Azı</option>
                    <option value="45">45 - Sağ Alt 2. Küçük Azı</option>
                    <option value="46">46 - Sağ Alt 1. Büyük Azı</option>
                    <option value="47">47 - Sağ Alt 2. Büyük Azı</option>
                    <option value="48">48 - Sağ Alt 20 Yaş Dişi</option>
                </optgroup>
            </select>

            <select name="islem_turu" required>
                <option value="">-- Yapılan İşlem / Tedavi --</option>
                <option value="Dolgu">Kompozit / Amalgam Dolgu</option>
                <option value="Kanal Tedavisi">Kanal Tedavisi</option>
                <option value="Diş Çekimi">Diş Çekimi</option>
                <option value="Diş Taşı Temizliği">Diş Taşı Temizliği (Detartraj)</option>
                <option value="Kron / Kaplama">Kron / Porselen Kaplama</option>
                <option value="İmplant">İmplant</option>
                <option value="Diş Beyazlatma">Diş Beyazlatma (Bleaching)</option>
            </select>

            <input type="number" step="0.01" name="ucret" placeholder="İşlem Ücreti (TL)" required>
            <button type="submit">Diş İşlemini Kaydet</button>
        </form>

        <h2>Uygulanan Diş Tedavileri</h2>
        <table>
            <tr>
                <th>Diş No</th>
                <th>Yapılan İşlem</th>
                <th>Ücret</th>
            </tr>
            {% for i in islemler %}
            <tr>
                <td><b>Diş #{{ i[2] }}</b></td>
                <td>{{ i[3] }}</td>
                <td>{{ i[4] }} TL</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

HASTA_GIRIS_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hasta Girişi - Klinik360</title>
    <style>
        body { font-family: Arial, sans-serif; background: #e9ecef; margin: 0; padding: 20px; text-align: center; }
        .box { max-width: 400px; margin: 50px auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; text-align: center; font-size: 16px; }
        button { width: 100%; padding: 12px; background: #28a745; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }
        .error { color: red; margin-bottom: 10px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>📱 Hasta Tedavi & Randevu Takibi</h2>
        <p style="color: #666; font-size: 14px;">Randevu ve tedavi geçmişinizi görüntülemek için kayıtlı telefon numaranızı giriniz.</p>
        {% if hata %}<p class="error">{{ hata }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="telefon" placeholder="Telefon Numarası (Örn: 0555...)" required>
            <button type="submit">Randevumu Göster</button>
        </form>
        <br><a href="/" style="color: #666; text-decoration: none; font-size: 14px;">⬅ Ana Sayfaya Dön</a>
    </div>
</body>
</html>
'''

HASTA_PROFIL_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hasta Paneli - Klinik360</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 10px; color: #333; }
        .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        .card { background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #007bff; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 14px; }
        th { background: #007bff; color: white; }
        .back-btn { background: #6c757d; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; display: inline-block; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <a class="back-btn" href="/">⬅ Çıkış Yap</a>
        <h2>🦷 Klinik360 Hasta Bilgi Kartı</h2>
        
        <div class="card">
            <h3 style="margin-top:0;">Sayın {{ hasta[1] }}</h3>
            <p><b>🗓 Yaklaşan Randevu Tarihiniz:</b> <span style="color: #d9534f; font-weight: bold;">{{ hasta[7] if hasta[7] else 'Planlanmış Randevu Yok' }}</span></p>
            <p><b>👨‍⚕️ Doktorunuzun Notu:</b> {{ hasta[5] if hasta[5] else 'Ek not yok.' }}</p>
        </div>

        <h3>🦷 Uygulanan Diş Tedavileriniz</h3>
        {% if islemler %}
        <table>
            <tr>
                <th>Diş No</th>
                <th>Yapılan Tedavi</th>
            </tr>
            {% for i in islemler %}
            <tr>
                <td><b>Diş #{{ i[2] }}</b></td>
                <td>{{ i[3] }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p style="color: gray;">Henüz kayıtlı bir tedavi işleminiz bulunmamaktadır.</p>
        {% endif %}
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)