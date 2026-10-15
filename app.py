from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# Veritabanı ve Tabloları Kurulumu
def init_db():
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    # Hastalar Tablosu (Randevu ve Bakiye alanları eklendi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hastalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT NOT NULL,
            yas TEXT,
            sikayet TEXT,
            alerji TEXT,
            randevu_tarihi TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Tedaviler ve Ücret Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tedaviler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hasta_id INTEGER,
            dis_no TEXT,
            islem TEXT,
            ucret REAL,
            odenen REAL,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hasta_id) REFERENCES hastalar (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Gelişmiş Arayüz ve Tasarım
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diş Kliniği Yönetim Sistemi</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f4f6f9; margin: 0; padding: 15px; color: #333; }
        .container { max-width: 650px; margin: auto; }
        .card { background: white; padding: 20px; border-radius: 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px; }
        h1 { color: #007aff; font-size: 20px; text-align: center; margin-top: 0; }
        h2 { color: #333; font-size: 18px; border-bottom: 2px solid #f0f0f0; padding-bottom: 8px; }
        label { font-size: 13px; font-weight: bold; color: #555; display: block; margin-top: 10px; }
        input, select { width: 100%; padding: 12px; margin-top: 5px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; box-sizing: border-box; }
        .btn { background-color: #007aff; color: white; border: none; padding: 14px; border-radius: 8px; font-size: 16px; width: 100%; cursor: pointer; font-weight: bold; margin-top: 15px; }
        .btn-green { background-color: #28a745; }
        .btn-wa { background-color: #25d366; text-decoration: none; display: block; text-align: center; padding: 10px; border-radius: 8px; color: white; font-weight: bold; margin-top: 10px; font-size: 14px; }
        .patient-item { background: #fafafa; border-left: 4px solid #007aff; padding: 14px; margin-top: 15px; border-radius: 6px; border: 1px solid #eee; }
        .patient-name { font-weight: bold; font-size: 17px; color: #111; }
        .patient-details { font-size: 14px; color: #555; margin-top: 4px; }
        .search-box { background: #eef2f7; padding: 12px; border-radius: 8px; margin-bottom: 15px; display: flex; gap: 8px; }
        .treatment-box { background: #fff; padding: 10px; border-radius: 8px; border: 1px solid #ddd; margin-top: 10px; }
        .finance-summary { background: #e8f5e9; padding: 10px; border-radius: 6px; margin-top: 8px; font-size: 14px; font-weight: bold; color: #2e7d32; }
    </style>
</head>
<body>
    <div class="container">
        
        <!-- Arama Çubuğu -->
        <div class="card" style="padding: 15px;">
            <form action="/" method="GET" class="search-box" style="margin:0; padding:0; background:none;">
                <input type="text" name="q" value="{{ arama }}" placeholder="🔍 Hasta Adı veya Telefon ile Ara..." style="margin:0;">
                <button type="submit" class="btn" style="width: 100px; margin-top:0; padding:10px;">Ara</button>
            </form>
        </div>

        <!-- Yeni Hasta Ekleme Kartı -->
        <div class="card">
            <h1>🦷 Profesyonel Diş Kliniği Takip</h1>
            <form action="/ekle" method="POST">
                <label>Ad Soyad:</label>
                <input type="text" name="ad_soyad" required placeholder="Örn: Mehmet Demir">
                
                <label>Telefon Numarası:</label>
                <input type="tel" name="telefon" required placeholder="0555...">
                
                <label>Yaş:</label>
                <input type="text" name="yas" placeholder="Örn: 35">
                
                <label>Şikayet / Başvuru Nedeni:</label>
                <input type="text" name="sikayet" placeholder="Örn: Şiddetli diş ağrısı">
                
                <label>Alerji / Sistemik Rahatsızlık:</label>
                <input type="text" name="alerji" placeholder="Örn: Tansiyon var">

                <label>Kontrol / Randevu Tarihi:</label>
                <input type="datetime-local" name="randevu_tarihi">
                
                <button type="submit" class="btn">Yeni Hasta Kaydet</button>
            </form>
        </div>

        <!-- Kayıtlı Hastalar Listesi ve Tedavi Modülü -->
        <div class="card">
            <h2>Hasta Listesi ve İşlemler ({{ hastalar|length }})</h2>
            {% if hastalar %}
                {% for h in hastalar %}
                <div class="patient-item">
                    <div class="patient-name">👤 {{ h[1] }} (Yaş: {{ h[3] }})</div>
                    <div class="patient-details">📞 Tel: <a href="tel:{{ h[2] }}">{{ h[2] }}</a></div>
                    <div class="patient-details">🩺 Şikayet: {{ h[4] }}</div>
                    <div class="patient-details" style="color: #d9534f;">⚠️ Alerji: {{ h[5] }}</div>
                    {% if h[6] %}
                    <div class="patient-details" style="color: #0277bd; font-weight: bold;">📅 Randevu: {{ h[6] }}</div>
                    {% endif %}

                    <!-- WhatsApp Hızlı Mesaj Butonu -->
                    <a class="btn-wa" href="https://wa.me/9{{ h[2] }}?text=Sayın%20{{ h[1] }},%20diş%20kliniğimizdeki%20tedavi%20ve%20randevu%20detaylarınız%20için%20ulaşıyoruz." target="_blank">
                        💬 WhatsApp ile Mesaj Gönder
                    </a>

                    <!-- Yapılan Tedaviler Listesi -->
                    {% set tedaviler = get_tedaviler(h[0]) %}
                    {% set toplam_borc = namespace(deger=0) %}
                    {% set toplam_odenen = namespace(deger=0) %}

                    {% if tedaviler %}
                        <div style="margin-top: 10px; font-size: 13px; font-weight: bold; color: #444;">Uygulanan Tedaviler:</div>
                        <ul style="margin: 5px 0; padding-left: 20px; font-size: 13px;">
                        {% for t in tedaviler %}
                            <li>Diş #{{ t[2] }} - {{ t[3] }} | Tutar: {{ t[4] }} TL | Ödenen: {{ t[5] }} TL</li>
                            {% set toplam_borc.deger = toplam_borc.deger + t[4] %}
                            {% set toplam_odenen.deger = toplam_odenen.deger + t[5] %}
                        {% endfor %}
                        </ul>
                        <div class="finance-summary">
                            Toplam Tutar: {{ toplam_borc.deger }} TL | Ödenen: {{ toplam_odenen.deger }} TL | Kalan Bakiye: <span style="color: {% if (toplam_borc.deger - toplam_odenen.odenen) > 0 %}red{% else %}green{% endif %};">{{ toplam_borc.deger - toplam_odenen.deger }} TL</span>
                        </div>
                    {% endif %}
                    
                    <!-- Tedavi ve Ücret Ekleme Formu -->
                    <form action="/tedavi_ekle" method="POST" class="treatment-box">
                        <input type="hidden" name="hasta_id" value="{{ h[0] }}">
                        <div style="display: flex; gap: 8px;">
                            <div style="flex: 1;">
                                <label style="margin-top:0;">Diş No:</label>
                                <select name="dis_no" style="padding: 8px; font-size: 13px;">
                                    <option value="Genel">Genel</option>
                                    <optgroup label="Üst Çene">
                                        <option value="18">18</option><option value="17">17</option><option value="16">16</option><option value="15">15</option><option value="14">14</option><option value="13">13</option><option value="12">12</option><option value="11">11</option>
                                        <option value="21">21</option><option value="22">22</option><option value="23">23</option><option value="24">24</option><option value="25">25</option><option value="26">26</option><option value="27">27</option><option value="28">28</option>
                                    </optgroup>
                                    <optgroup label="Alt Çene">
                                        <option value="48">48</option><option value="47">47</option><option value="46">46</option><option value="45">45</option><option value="44">44</option><option value="43">43</option><option value="42">42</option><option value="41">41</option>
                                        <option value="31">31</option><option value="32">32</option><option value="33">33</option><option value="34">34</option><option value="35">35</option><option value="36">36</option><option value="37">37</option><option value="38">38</option>
                                    </optgroup>
                                </select>
                            </div>
                            <div style="flex: 1.5;">
                                <label style="margin-top:0;">İşlem Türü:</label>
                                <select name="islem" style="padding: 8px; font-size: 13px;">
                                    <option value="Dolgu">Dolgu</option>
                                    <option value="Kanal Tedavisi">Kanal Tedavisi</option>
                                    <option value="Çekim">Çekim</option>
                                    <option value="Diş Taşı Temizliği">Diş Taşı Temizliği</option>
                                    <option value="İmplant">İmplant</option>
                                    <option value="Zirkonyum Kaplama">Zirkonyum Kaplama</option>
                                </select>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 6px;">
                            <div style="flex: 1;">
                                <label style="margin-top:0;">İşlem Ücreti (TL):</label>
                                <input type="number" step="0.01" name="ucret" placeholder="Örn: 2000" required style="padding: 8px; font-size: 13px;">
                            </div>
                            <div style="flex: 1;">
                                <label style="margin-top:0;">Alınan Ödeme (TL):</label>
                                <input type="number" step="0.01" name="odenen" placeholder="Örn: 1000" value="0" required style="padding: 8px; font-size: 13px;">
                            </div>
                        </div>
                        <button type="submit" class="btn btn-green" style="padding: 8px; font-size: 14px; margin-top: 8px;">Tedavi ve Ödeme Ekle</button>
                    </form>
                </div>
                {% endfor %}
            {% else %}
                <p style="text-align: center; color: #888;">Kayıtlı hasta bulunamadı.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

# Yardımcı fonksiyon: Hastanın tedavilerini çekmek için
def get_tedaviler(hasta_id):
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tedaviler WHERE hasta_id = ?', (hasta_id,))
    tedaviler = cursor.fetchall()
    conn.close()
    return tedaviler

@app.route('/')
def home():
    arama = request.args.get('q', '')
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    if arama:
        cursor.execute("SELECT * FROM hastalar WHERE ad_soyad LIKE ? OR telefon LIKE ? ORDER BY id DESC", ('%' + arama + '%', '%' + arama + '%'))
    else:
        cursor.execute('SELECT * FROM hastalar ORDER BY id DESC')
    hastalar = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, hastalar=hastalar, arama=arama, get_tedaviler=get_tedaviler)

@app.route('/ekle', methods=['POST'])
def ekle():
    ad_soyad = request.form['ad_soyad']
    telefon = request.form['telefon']
    yas = request.form['yas']
    sikayet = request.form['sikayet']
    alerji = request.form['alerji']
    randevu_tarihi = request.form['randevu_tarihi']
    
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO hastalar (ad_soyad, telefon, yas, sikayet, alerji, randevu_tarihi) VALUES (?, ?, ?, ?, ?, ?)',
                   (ad_soyad, telefon, yas, sikayet, alerji, randevu_tarihi))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/tedavi_ekle', methods=['POST'])
def tedavi_ekle():
    hasta_id = request.form['hasta_id']
    dis_no = request.form['dis_no']
    islem = request.form['islem']
    ucret = float(request.form['ucret'])
    odenen = float(request.form['odenen'])
    
    conn = sqlite3.connect('klinik.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tedaviler (hasta_id, dis_no, islem, ucret, odenen) VALUES (?, ?, ?, ?, ?)',
                   (hasta_id, dis_no, islem, ucret, odenen))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)