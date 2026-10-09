"""Mürekkep - Basit bir blog uygulaması"""
import os

from flask import (Flask, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import or_

from forms import (BioForm, CommentForm, LoginForm, PasswordChangeForm,
                   PostForm, RegisterForm)
from datetime import timedelta
from models import Comment, Like, Post, User, db, follows, simdi
from utils import (POSTS_PER_PAGE, bas_harf_filter, guvenli_url, md_filter,
                   page_url, sayfa_no, tarih_filter, yeni_yazarlar)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "gelistirme-icin-gizli-anahtar")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "blog.db"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Bu sayfayı görmek için giriş yapmalısın."
login_manager.login_message_category = "warning"

# Şablon filtreleri ve global fonksiyonlar (utils.py içinde tanımlı)
app.add_template_filter(md_filter, "md")
app.add_template_filter(tarih_filter, "tarih")
app.add_template_filter(bas_harf_filter, "bas_harf")
app.add_template_global(page_url, "page_url")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ----------------------------- Hesap işlemleri -----------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip(),
                    email=form.email.data.lower().strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Hesabın oluşturuldu, şimdi giriş yapabilirsin.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        kimlik = form.login.data.strip()
        user = User.query.filter(or_(db.func.lower(User.username) == kimlik.lower(),
                                     User.email == kimlik.lower())).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Tekrar hoş geldin, {user.username}.", "success")
            hedef = request.args.get("next")
            return redirect(hedef if hedef and guvenli_url(hedef) else url_for("index"))
        flash("Kullanıcı adı veya parola hatalı.", "danger")
    return render_template("login.html", form=form)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Çıkış yaptın.", "info")
    return redirect(url_for("index"))


# ----------------------------- Yazılar -----------------------------

@app.route("/")
def index():
    sekme = request.args.get("sekme", "kesfet")
    sorgu = Post.query.filter_by(published=True)
    if sekme == "takip" and current_user.is_authenticated:
        sorgu = sorgu.join(follows, follows.c.followed_id == Post.author_id) \
                     .filter(follows.c.follower_id == current_user.id)
    else:
        sekme = "kesfet"
    sayfa = sorgu.order_by(Post.created_at.desc()).paginate(
        page=sayfa_no(), per_page=POSTS_PER_PAGE, error_out=False)
    return render_template("index.html", pagination=sayfa, sekme=sekme,
                           yazarlar=yeni_yazarlar())


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()[:100]
    sorgu = Post.query.filter_by(published=True)
    if q:
        kalip = f"%{q}%"
        sorgu = sorgu.join(User).filter(or_(Post.title.ilike(kalip),
                                            Post.content.ilike(kalip),
                                            User.username.ilike(kalip)))
    else:
        sorgu = sorgu.filter(db.false())
    sayfa = sorgu.order_by(Post.created_at.desc()).paginate(
        page=sayfa_no(), per_page=POSTS_PER_PAGE, error_out=False)
    return render_template("index.html", pagination=sayfa, sekme=None, q=q,
                           yazarlar=yeni_yazarlar())


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def post_new():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data.strip(), content=form.content.data,
                    published=form.published.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Yazın yayında." if post.published else "Taslak kaydedildi.", "success")
        return redirect(url_for("post_detail", post_id=post.id))
    return render_template("post_form.html", form=form, baslik="Yeni yazı")


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    post = db.get_or_404(Post, post_id)
    if not post.published and post.author_id != getattr(current_user, "id", None):
        abort(404)
    return render_template("post.html", post=post, form=CommentForm())


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def post_edit(post_id):
    post = db.get_or_404(Post, post_id)
    if post.author_id != current_user.id:
        abort(403)
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.title = form.title.data.strip()
        post.content = form.content.data
        post.published = form.published.data
        db.session.commit()
        flash("Yazı güncellendi.", "success")
        return redirect(url_for("post_detail", post_id=post.id))
    return render_template("post_form.html", form=form, baslik="Yazıyı düzenle")


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def post_delete(post_id):
    post = db.get_or_404(Post, post_id)
    if post.author_id != current_user.id:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash("Yazı silindi.", "info")
    return redirect(url_for("user_profile", username=current_user.username))


@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def post_like(post_id):
    post = db.get_or_404(Post, post_id)
    if not post.published:
        abort(404)
    like = Like.query.filter_by(user_id=current_user.id, post_id=post.id).first()
    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(user_id=current_user.id, post_id=post.id))
    db.session.commit()
    return redirect(url_for("post_detail", post_id=post.id))


@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def post_comment(post_id):
    post = db.get_or_404(Post, post_id)
    if not post.published:
        abort(404)
    form = CommentForm()
    if form.validate_on_submit():
        db.session.add(Comment(body=form.body.data.strip(), user_id=current_user.id,
                               post_id=post.id))
        db.session.commit()
        flash("Yorumun eklendi.", "success")
    else:
        flash("Yorum eklenemedi: boş olmamalı, en fazla 1000 karakter olmalı.", "danger")
    return redirect(url_for("post_detail", post_id=post.id) + "#yorumlar")


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def comment_delete(comment_id):
    c = db.get_or_404(Comment, comment_id)
    if current_user.id not in (c.user_id, c.post.author_id):
        abort(403)
    post_id = c.post_id
    db.session.delete(c)
    db.session.commit()
    flash("Yorum silindi.", "info")
    return redirect(url_for("post_detail", post_id=post_id) + "#yorumlar")


# ----------------------------- Profil ve takip -----------------------------

@app.route("/user/<username>")
def user_profile(username):
    user = User.query.filter(db.func.lower(User.username) == username.lower()).first_or_404()
    sorgu = Post.query.filter_by(author_id=user.id)
    if not (current_user.is_authenticated and current_user.id == user.id):
        sorgu = sorgu.filter_by(published=True)
    sayfa = sorgu.order_by(Post.created_at.desc()).paginate(
        page=sayfa_no(), per_page=POSTS_PER_PAGE, error_out=False)
    return render_template("profile.html", user=user, pagination=sayfa)


@app.route("/user/<username>/follow", methods=["POST"])
@login_required
def user_follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user.id == current_user.id:
        flash("Kendini takip edemezsin.", "warning")
    elif current_user.is_following(user):
        current_user.unfollow(user)
        db.session.commit()
        flash(f"{user.username} takibi bırakıldı.", "info")
    else:
        current_user.follow(user)
        db.session.commit()
        flash(f"{user.username} takip ediliyor.", "success")
    return redirect(request.referrer if request.referrer and guvenli_url(request.referrer)
                    else url_for("user_profile", username=user.username))


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = BioForm(obj=current_user)
    if form.validate_on_submit():
        current_user.bio = form.bio.data.strip()
        db.session.commit()
        flash("Profilin güncellendi.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", form=form, pform=PasswordChangeForm())


@app.route("/settings/password", methods=["POST"])
@login_required
def change_password():
    pform = PasswordChangeForm()
    if pform.validate_on_submit():
        if not current_user.check_password(pform.old_password.data):
            flash("Mevcut parola yanlış.", "danger")
        else:
            current_user.set_password(pform.password.data)
            db.session.commit()
            flash("Parolan değiştirildi.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", form=BioForm(obj=current_user), pform=pform)


# ----------------------------- Hata sayfaları -----------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", kod=403,
                           mesaj="Bu işlem için yetkin yok."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", kod=404,
                           mesaj="Aradığın sayfa bulunamadı."), 404


# ----------------------------- Başlangıç -----------------------------

@app.cli.command("seed")
def seed():
    """Örnek veri ekler: flask --app app seed"""
    db.create_all()
    if User.query.filter_by(username="deniz").first():
        print("Örnek veri zaten var.")
        return

    def gun_once(gun, saat=0):
        return simdi() - timedelta(days=gun, hours=saat)

    deniz = User(username="deniz", email="deniz@example.com",
                 bio="Kısa öyküler, uzun yürüyüşler.", created_at=gun_once(40))
    deniz.set_password("parola123")
    ada = User(username="ada", email="ada@example.com",
               bio="Şiir okur, deneme yazar.", created_at=gun_once(30))
    kerem = User(username="kerem", email="kerem@example.com",
                 bio="Kod yazar, teknolojiyi sorgular.", created_at=gun_once(20))
    mira = User(username="mira", email="mira@example.com",
                bio="Filmler, plaklar, uzun akşamlar.", created_at=gun_once(12))
    selin = User(username="selin", email="selin@example.com",
                 bio="Hekim, meraklı, notlar tutar.", created_at=gun_once(6))
    for u in (deniz, ada, kerem, mira, selin):
        u.set_password("parola123")
    db.session.add_all([deniz, ada, kerem, mira, selin])
    db.session.flush()

    # ----------------------------- Yazılar -----------------------------
    
    gece = Post(
        title="Gece Yürüyüşleri ve Şehrin Sessizliği", author=deniz,
        created_at=gun_once(2),
        content=(
            "Sokak lambalarının sarı ışığı altında adımları saymak bazen en iyi düşünme yolu.\n\n"
            "> Gürültü azaldıkça zihnin sesi daha net duyulur.\n\n"
            "Her köşede ayrı bir hikaye var ama geceleri hepsi aynı dinginlikte birleşiyor."))

    minimal = Post(
        title="Minimalizmin Getirdiği Ferahlık", author=ada,
        created_at=gun_once(1),
        content=(
            "Fazlalıklardan arınmak, yalnızca mekânda boşluk açmak değil; "
            "zihnin kendi yankısını duyabileceği **duru bir sessizlik** inşa etmektir.\n\n"
            "> Eşyanın ve lüzumsuz telaşın gölgesi çekildiğinde, insan sahip olduklarının ağırlığından "
            "sıyrılıp varoluşun yalın hafifliğiyle nefes almaya başlar.\n\n"
            "### Azalmanın Getirdikleri\n"
            "* **Hafiflik:** Sahip olunanların yükünden kurtulup zihinsel berraklığa kavuşmak.\n"
            "* **Denge:** Dış dünyayı doldurmak yerine iç dünyaya alan tanımak.\n"
            "* **Öz:** Azaldıkça eksilmeden, asıl olanın güzelliğinde çoğalabilmek.\n\n"
            "Çünkü **gerçek ferahlık**, dışarıyı doldurmakta değil, içeriye yer açabilmektedir."))

    yapay_zeka = Post(
        title="Yapay Zekâ Çağında Yavaş Okumak", author=kerem,
        created_at=gun_once(3),
        content=(
            "Bir yanıtı saniyeler içinde almaya alıştık. Soru sorarız, cevap gelir; "
            "cevabın nereden geldiğini ise çoğu zaman sormayız.\n\n"
            "> Hız, anlamanın yerini tutmaz; yalnızca beklemenin yerini tutar.\n\n"
            "### Yavaş okumanın üç alışkanlığı\n"
            "* **Durmak:** Bir paragrafı bitirince gözlerini sayfadan kaldır ve ne anlattığını kendi cümlenle söyle.\n"
            "* **Sorgulamak:** Bir bilgiyi, kaynağını bulana kadar kesin saymamak.\n"
            "* **Geri dönmek:** İyi bir metin ikinci okumada başka bir şey söyler.\n\n"
            "Teknoloji bizim yerimize özetleyebilir, ama **düşünmenin zahmetini** devredemeyiz. "
            "Araçlar hızlandıkça, yavaşlamayı seçmek bilinçli bir tavra dönüşüyor."))

    plak = Post(
        title="Bir Plağın Çizik Sesi", author=mira,
        created_at=gun_once(4),
        content=(
            "İğne ilk oluğa değdiğinde odadaki sessizlik bir an titrer. "
            "O hafif çıtırtı, müziğin sana ulaşmak için geçtiği yolun sesidir.\n\n"
            "> Kusursuz kayıtlar çok; ama çiziği olan bir plak yalnızca senindir.\n\n"
            "### Neden hâlâ dönüp duruyoruz?\n"
            "* **Ritüel:** Kılıfından çıkarmak, çevirmek, iğneyi bırakmak; dinlemeye hazırlanmanın kendisi.\n"
            "* **Bütünlük:** Şarkıları karıştırmak yerine albümü baştan sona, sanatçının sırasıyla dinlemek.\n"
            "* **Dokunmak:** Müziğin elle tutulur, kokusu olan bir nesneye dönüşmesi.\n\n"
            "Belki de bu yüzden plaklar eskimiyor: **müziği dinlemeyi, bir olay hâline getiriyorlar.**"))

    uyku = Post(
        title="Uykusuzluğun Bilimi: Beynimiz Geceleri Ne Yapar?", author=selin,
        created_at=gun_once(5),
        content=(
            "Uyuduğumuzda beynimiz kapanmaz; aksine gün boyu biriken işleri toparlamaya başlar.\n\n"
            "> Uyku bir duraklama değil, görünmeyen bir bakım vardiyasıdır.\n\n"
            "### Gece boyunca olup bitenler\n"
            "* **Pekiştirme:** Gün içinde öğrenilenler daha kalıcı hafızaya yerleşir.\n"
            "* **Temizlik:** Çalışmalar, derin uykuda beyindeki atıkların daha verimli temizlendiğini düşündürüyor.\n"
            "* **Duygusal denge:** Yetersiz uyku, öfke ve kaygıya verilen tepkileri keskinleştirebilir.\n\n"
            "Yetişkinler için genel öneri çoğunlukla **7-9 saat** uykudur, ancak ihtiyaç kişiden kişiye değişir. "
            "Uzun süren uykusuzluk yaşıyorsan bir sağlık uzmanına danışmak en doğrusudur.\n\n"
            "*Bu yazı genel bilgilendirme amaçlıdır, tıbbi tavsiye yerine geçmez.*"))

    kadraj = Post(
        title="Kadraj Dışında Kalanlar: Sessiz Filmlerin Dili", author=mira,
        created_at=gun_once(6),
        content=(
            "Sessiz sinema, sesin yokluğunda bile çok şey söyleyebildiğini gösterdi. "
            "Yüzler, eller ve ışık; hepsi birer cümleye dönüştü.\n\n"
            "> Söylenmeyen, bazen söylenenden daha yüksek sesle duyulur.\n\n"
            "### Sessizliğin kullandığı araçlar\n"
            "* **Jest ve mimik:** Oyuncunun bedeni, diyalogların yerini aldı.\n"
            "* **Ara yazılar:** Az ama öz cümleler; her sözcüğün ağırlığı fazlaydı.\n"
            "* **Canlı müzik:** Salonlarda çalınan müzik, her gösterimi biraz farklı kıldı.\n\n"
            "Bugün bol sesli ve efektli filmler izlerken, o **sadeliği** hatırlamak iyi geliyor."))

    makale = Post(
        title="Makale Yazmanın Sıkıcı Ama Kurtarıcı Kuralları", author=selin,
        created_at=gun_once(8),
        content=(
            "Akademik yazı çoğu zaman bürokratik görünür. Ama kurallar, düşünceyi "
            "başkasının okuyabileceği bir biçime sokmanın en kısa yoludur.\n\n"
            "> İyi bir makale, bir soruya verilmiş sabırlı bir cevaptır.\n\n"
            "### Hayat kurtaran dört kural\n"
            "* **Tek bir soru:** Makalenin cevapladığı soruyu tek cümleyle yazabilmelisin.\n"
            "* **Kaynak ver:** Kendi fikrinle başkasının fikrini birbirinden ayır.\n"
            "* **Önce kaba taslak:** Mükemmel ilk cümleyi aramak, yazmayı geciktirir.\n"
            "* **Sonra kısalt:** Okuru yormayan her cümle, çalışmaya saygıdır.\n\n"
            "Sıkıcı gelen bu düzen, aslında **özgür düşünmenin iskeleti.**"))

    taslak = Post(
        title="Taslak: Yarım Kalan Öykü", author=deniz, published=False,
        created_at=gun_once(0, 1),
        content=(
            "Tren garında bekleyen adamın elindeki bavul boştu. "
            "Bunu yalnızca kendisi ve perondaki güvercinler biliyordu...\n\n"
            "> *Not:* Karakterin geçmişine dair ipuçlarını buraya ekle. "
            "Gitmeyi mi istiyor, yoksa sadece kalmaktan mı kaçıyor?\n\n"
            "### Geliştirilecek Kısımlar\n"
            "* Saat kulesinin vuruşunu bir metafor olarak kullan.\n"
            "* Bilet kontrol memuru ile kısa, tedirgin bir diyalog yaz.\n\n"
            "*Cümle burada tıkandı. Belki sonbahar rüzgârı sahneyi tamamlar.*"))

    db.session.add_all([gece, minimal, yapay_zeka, plak, uyku, kadraj, makale, taslak])
    db.session.flush()

    # ----------------------------- Beğeniler -----------------------------

    begeniler = [
        (deniz, minimal), (kerem, minimal), (mira, minimal), (selin, minimal),
        (ada, gece), (mira, gece),
        (ada, yapay_zeka), (selin, yapay_zeka), (deniz, yapay_zeka),
        (deniz, plak), (kerem, plak),
        (ada, uyku), (kerem, uyku), (mira, uyku),
        (kerem, kadraj),
        (deniz, makale), (ada, makale),
    ]
    db.session.add_all(Like(user_id=u.id, post=p) for u, p in begeniler)

    # ----------------------------- Yorumlar -----------------------------

    db.session.add_all([
        Comment(body="Son cümle bütün yazıyı topluyor, çok güzel.", user=deniz, post=minimal),
        Comment(body="Bir de dijital minimalizmi eklesen harika olurdu.", user=kerem, post=minimal),
        Comment(body="Okurken bir gece yürüyüşüne çıkmak istedim.", user=ada, post=gece),
        Comment(body="Bunu öğrencilere de anlatmak lazım, teşekkürler.", user=selin, post=yapay_zeka),
        Comment(body="Dijitalde o ritüeli bulamıyorum, haklısın.", user=kerem, post=plak),
        Comment(body="Temizlik kısmını bilmiyordum, çok öğretici.", user=deniz, post=uyku),
    ])

    # ----------------------------- Takipçiler -----------------------------

    deniz.follow(ada); deniz.follow(mira)
    ada.follow(deniz); ada.follow(selin)
    kerem.follow(selin); kerem.follow(mira); kerem.follow(ada)
    mira.follow(kerem)
    selin.follow(ada); selin.follow(mira)

    db.session.commit()
    print("Örnek veri eklendi. Giriş: deniz / parola123 (ada, kerem, mira, selin için de aynı parola)")


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
