from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# Veritabanı ve Tabloları Kurulumu
def init_db():
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    
    # Hastalar Tablosu
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
    
    # Diş Tedavi ve İşlemler Tablosu (İnteraktif Diş Şeması için)
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

# Ana Sayfa ve Hasta Listesi
@app.route('/')
def index():
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    
    arama = request.args.get('arama', '')
    if arama:
        cursor.execute("SELECT * FROM hastalar WHERE ad_soyad LIKE ? OR telefon LIKE ?", ('%' + arama + '%', '%' + arama + '%'))
    else:
        cursor.execute("SELECT * FROM hastalar ORDER BY id DESC")
        
    hastalar = cursor.fetchall()
    conn.close()
    return render_template_string(ANASAYFA_HTML, hastalar=hastalar, arama=arama)

# Hasta Ekleme Rotası
@app.route('/ekle', methods=['POST'])
def ekle():
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
    return redirect(url_for('index'))

# Hasta Detay ve Diş İşlemleri Sayfası
@app.route('/hasta/<int:hasta_id>')
def hasta_detay(hasta_id):
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

# Diş İşlemi Ekleme Rotası
@app.route('/dis_islem_ekle/<int:hasta_id>', methods=['POST'])
def dis_islem_ekle(hasta_id):
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

# HTML Arayüzü - Ana Sayfa
ANASAYFA_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Klinik360 - Diş Hasta Takip</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 10px; color: #333; }
        .container { max-width: 850px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h1, h2 { color: #007bff; text-align: center; }
        form { background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        input, select, textarea { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        .checkbox-group { background: white; padding: 10px; border-radius: 5px; border: 1px solid #ccc; margin: 8px 0; }
        .checkbox-group label { display: block; margin-bottom: 5px; font-weight: normal; cursor: pointer; }
        button { background: #28a745; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #218838; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 14px; }
        th { background: #007bff; color: white; }
        .search-box { display: flex; gap: 10px; margin-bottom: 15px; }
        .whatsapp-btn { background: #25d366; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px; }
        .detay-btn { background: #17a2b8; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; display: inline-block; font-size: 13px; margin-right: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 Klinik360</h1>
        <p style="text-align: center; color: #666; margin-top: -10px;">Profesyonel Diş Klinik Takip Sistemi</p>
        
        <!-- Hasta Ekleme Formu -->
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

        <!-- Arama Alanı -->
        <form class="search-box" method="GET" action="/">
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
                    <a class="detay-btn" href="/hasta/{{ h[0] }}">Diş Şeması & Detay</a>
                    <a class="whatsapp-btn" href="https://wa.me/9{{ h[2] }}?text=Sayın%20{{ h[1] }},%20Klinik360%20diş%20kliniğimizdeki%20{{ h[7] }}%20tarihli%20randevunuzu%20hatırlatmak%20isteriz.%20Sağlıklı%20günler%20dileriz." target="_blank">WhatsApp Hatırlat</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

# HTML Arayüzü - Hasta Detay ve Diş Şeması Sayfası
HASTA_DETAY_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ hasta[1] }} - Diş Şeması | Klinik360</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 10px; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: #007bff; text-align: center; }
        .info-box { background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        form { background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 20px; }
        input, select { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; padding: 12px; width: 100%; border-radius: 5px; font-size: 16px; cursor: pointer; }
        button:hover { background: #0056b3; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; font-size: 14px; }
        th { background: #28a745; color: white; }
        .back-btn { background: #6c757d; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; display: inline-block; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <a class="back-btn" href="/">⬅ Ana Sayfaya Dön</a>
        <h1>🦷 Hasta Diş Kartı & Şeması</h1>
        
        <div class="info-box">
            <h3>{{ hasta[1] }}</h3>
            <p><b>Telefon:</b> {{ hasta[2] }} | <b>Yaş:</b> {{ hasta[3] }}</p>
            <p><b>Semptomlar:</b> {{ hasta[4] }}</p>
            <p><b>Doktor Notu:</b> {{ hasta[5] }}</p>
            <p><b>Randevu Tarihi:</b> {{ hasta[7] }}</p>
        </div>

        <!-- Diş İşlemi Ekleme Formu -->
        <form action="/dis_islem_ekle/{{ hasta[0] }}" method="POST">
            <h3>Diş Tedavisi / İşlem Ekle</h3>
            <label><b>Diş Numarası Seçin (ISO Sistemi):</b></label>
            <select name="dis_no" required>
                <option value="">-- Diş Seçiniz --</option>
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)