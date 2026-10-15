from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# Veritabanı ve Tabloları Kurulumu
def init_db():
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    # Hastalar Tablosuna semptom ve ozel_not sütunlarını ekliyoruz
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hastalar (
            id INTEGER INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT NOT NULL,
            yas TEXT,
            sikayet TEXT,
            semptomlar TEXT,
            ozel_not TEXT,
            alerji TEXT,
            randevu_tarihi TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bakiye ve Tedavi Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hasta_id INTEGER,
            islem_adi TEXT,
            ucret REAL,
            odenen REAL,
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
    
    # Seçilen semptomları birleştirip kaydediyoruz (birden fazla seçilebilir)
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

# HTML Arayüzü (Tasarım ve Formlar)
ANASAYFA_HTML = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diş Klinik Takip</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f7f6; margin: 0; padding: 10px; color: #333; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🦷 Diş Klinik Hasta Takip</h1>
        
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

            <textarea name="ozel_not" placeholder="Özel Not / Doktor Açıklaması (Ekstra detaylar...)" rows="3"></textarea>
            
            <input type="text" name="alerji" placeholder="Alerji Durumu (Varsa)">
            <input type="date" name="randevu_tarihi" placeholder="Randevu Tarihi">
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
                <th>İşlem</th>
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
                    <a class="whatsapp-btn" href="https://wa.me/9{{ h[2] }}?text=Sayın%20{{ h[1] }},%20diş%20kliniğimizdeki%20randevunuz%20hakkında..." target="_blank">WhatsApp</a>
                </td>
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