# 🖋️ Mürekkep-Blog

> Flask ile yazılmış, modern ve Substack benzeri bir blog platformu.

Mürekkep; kullanıcıların kayıt olup yazı yazabildiği, birbirini takip edebildiği, yazıları beğenip yorum yapabildiği zengin özellikli bir blog uygulamasıdır.

## 📸 Ekran Görüntüleri

| Karşılama / Ana Sayfa | Keşfet / Akış |
| :---: | :---: |
| ![Ana Sayfa](images/anasayfa.png) | ![Akış](images/akis.png) |

| Yazı Detay & Okuma | Profil Sayfası | Gece Modu |
| :---: | :---: | :---: |
| ![Yazı](images/yazi.png) | ![Profil](images/profil.png) | ![Gece Modu](images/gece-modu.png) |

---

## ✨ Özellikler

- 🔐 **Gelişmiş Kimlik Doğrulama:** Kayıt / giriş / çıkış, "beni hatırla" mekanizması ve oturum yönetimi (`Flask-Login`).
- 🛡️ **Güvenlik Odaklı:** Passlib ile güvenli parola hashleme (`PBKDF2-SHA256`), CSRF koruması ve `Flask-WTF` ile form doğrulama.
- 📝 **Zengin İçerik Yönetimi:** Yazı oluşturma, düzenleme, silme, arama ve sayfalama (`pagination`) desteği.
- 🖋️ **Markdown & Güvenlik:** Taslak/yayınlanmış yazı yönetimi, Markdown desteği ve `bleach` ile güvenli HTML sanitizasyonu (okuma süresi hesaplama özelliği ile).
- 👥 **Sosyal Özellikler:** Yazar profilleri, takip sistemi ve "Takip ettiklerim" özel akışı.
- ❤️ **Etkileşim:** Yazılara beğeni bırakma ve yorum yapma.
- ⚙️ **Kullanıcı Deneyimi:** Parola değiştirme, profil açıklaması düzenleme ve göz yormayan **Gece Modu (Dark Mode)** desteği.
- 🗄️ **Veritabanı:** `SQLite` + `SQLAlchemy` (`blog.db` ilk çalıştırmada otomatik oluşur).

---

## 🚀 Hızlı Başlangıç & Kurulum

Projeyi kendi bilgisayarınızda çalıştırmak için terminalinizde şu adımları takip edin:

```bash
# Depoyu klonlayın
git clone [https://github.com/ecrin404/Murekkep-Blog.git](https://github.com/ecrin404/Murekkep-Blog.git)
cd Murekkep-Blog

# Sanal ortam oluşturun ve aktifleştirin
python -m venv venv
venv\Scripts\activate        # Windows için
source venv/bin/activate     # macOS / Linux için

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Uygulamayı başlatın
python app.py
```
Tarayıcınızda http://127.0.0.1:5000 adresini açarak uygulamayı inceleyebilirsiniz.

Örnek veri için: `flask --app app seed` (kullanıcı: `deniz`, parola: `parola123`)


