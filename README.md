# Mürekkep

Flask ile yazılmış, Substack benzeri bir blog uygulaması. Kullanıcılar kayıt olur, yazı yazar,
birbirini takip eder, yazıları beğenir ve yorum yapar.

## Özellikler
- Kayıt / giriş / çıkış, "beni hatırla", oturum yönetimi (Flask-Login)
- Parola hashleme: Passlib (PBKDF2-SHA256)
- Form doğrulama ve CSRF koruması (Flask-WTF)
- Yazı oluşturma, düzenleme, silme, listeleme, arama, sayfalama
- Taslak / yayınlanmış yazı, Markdown desteği (bleach ile temizlenir), okuma süresi
- Yazar profilleri, takip sistemi, "Takip ettiklerim" akışı
- Beğeni ve yorumlar
- Parola değiştirme, profil açıklaması
- Gece modu
- Veritabanı: SQLite + SQLAlchemy (`blog.db` ilk çalıştırmada otomatik oluşur)

## Kurulum
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Tarayıcıda http://127.0.0.1:5000 adresini aç.

Örnek veri için: `flask --app app seed` (kullanıcı: `deniz`, parola: `parola123`)

Yayına alırken `SECRET_KEY` ortam değişkenini mutlaka değiştir.
