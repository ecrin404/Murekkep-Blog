"""Mürekkep - Basit bir blog uygulaması"""
import os
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import bleach
import markdown
from flask import (Flask, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from markupsafe import Markup
from passlib.hash import pbkdf2_sha256
from sqlalchemy import or_
from wtforms import (BooleanField, PasswordField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Regexp,
                                ValidationError)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "gelistirme-icin-gizli-anahtar")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "blog.db"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Bu sayfayı görmek için giriş yapmalısın."
login_manager.login_message_category = "warning"

POSTS_PER_PAGE = 6
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


# ----------------------------- Modeller -----------------------------

def simdi():
    return datetime.now(timezone.utc)


follows = db.Table(
    "follows",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=simdi)

    posts = db.relationship("Post", backref="author", lazy=True,
                            cascade="all, delete-orphan")
    followed = db.relationship(
        "User", secondary=follows,
        primaryjoin=(follows.c.follower_id == id),
        secondaryjoin=(follows.c.followed_id == id),
        backref=db.backref("followers", lazy="dynamic"), lazy="dynamic")

    def set_password(self, password):
        self.password_hash = pbkdf2_sha256.hash(password)

    def check_password(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)

    def is_following(self, user):
        return self.followed.filter(follows.c.followed_id == user.id).count() > 0

    def follow(self, user):
        if user.id != self.id and not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=simdi, index=True)
    updated_at = db.Column(db.DateTime, default=simdi, onupdate=simdi)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    comments = db.relationship("Comment", backref="post", lazy=True,
                               cascade="all, delete-orphan",
                               order_by="Comment.created_at")
    likes = db.relationship("Like", backref="post", lazy="dynamic",
                            cascade="all, delete-orphan")

    @property
    def reading_time(self):
        return max(1, round(len(self.content.split()) / 200))

    @property
    def excerpt(self):
        html = markdown.markdown(self.content)
        text = bleach.clean(html, tags=[], strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text) <= 180 else text[:180].rsplit(" ", 1)[0] + "…"

    def liked_by(self, user):
        return user.is_authenticated and \
            self.likes.filter_by(user_id=user.id).count() > 0


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=simdi)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user = db.relationship("User")


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "post_id"),)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ----------------------------- Formlar -----------------------------

def guclu_parola(form, field):
    p = field.data or ""
    if not (re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]", p) and re.search(r"\d", p)):
        raise ValidationError("Parola en az bir harf ve bir rakam içermeli.")


class RegisterForm(FlaskForm):
    username = StringField("Kullanıcı adı", validators=[
        DataRequired("Kullanıcı adı zorunlu."),
        Length(3, 20, "Kullanıcı adı 3-20 karakter olmalı."),
        Regexp(r"^[A-Za-z0-9_]+$", message="Sadece harf, rakam ve alt çizgi kullanılabilir.")])
    email = StringField("E-posta", validators=[
        DataRequired("E-posta zorunlu."), Email("Geçerli bir e-posta gir."),
        Length(max=120)])
    password = PasswordField("Parola", validators=[
        DataRequired("Parola zorunlu."),
        Length(8, 64, "Parola 8-64 karakter olmalı."), guclu_parola])
    confirm = PasswordField("Parola (tekrar)", validators=[
        DataRequired("Parolayı tekrar gir."),
        EqualTo("password", "Parolalar eşleşmiyor.")])
    submit = SubmitField("Hesap oluştur")

    def validate_username(self, field):
        if User.query.filter(db.func.lower(User.username) == field.data.lower()).first():
            raise ValidationError("Bu kullanıcı adı alınmış.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("Bu e-posta ile zaten bir hesap var.")


class LoginForm(FlaskForm):
    login = StringField("Kullanıcı adı veya e-posta",
                        validators=[DataRequired("Bu alan zorunlu.")])
    password = PasswordField("Parola", validators=[DataRequired("Parola zorunlu.")])
    remember = BooleanField("Beni hatırla")
    submit = SubmitField("Giriş yap")


class PostForm(FlaskForm):
    title = StringField("Başlık", validators=[
        DataRequired("Başlık zorunlu."), Length(3, 150, "Başlık 3-150 karakter olmalı.")])
    content = TextAreaField("Yazı", validators=[
        DataRequired("Yazı boş olamaz."), Length(min=20, message="Yazı en az 20 karakter olmalı.")])
    published = BooleanField("Hemen yayınla", default=True)
    submit = SubmitField("Kaydet")


class CommentForm(FlaskForm):
    body = TextAreaField("Yorumun", validators=[
        DataRequired("Yorum boş olamaz."), Length(max=1000, message="En fazla 1000 karakter.")])
    submit = SubmitField("Yorum yap")


class BioForm(FlaskForm):
    bio = StringField("Hakkında", validators=[Length(max=200, message="En fazla 200 karakter.")])
    submit = SubmitField("Kaydet")


class PasswordChangeForm(FlaskForm):
    old_password = PasswordField("Mevcut parola", validators=[DataRequired("Zorunlu.")])
    password = PasswordField("Yeni parola", validators=[
        DataRequired("Zorunlu."), Length(8, 64, "Parola 8-64 karakter olmalı."), guclu_parola])
    confirm = PasswordField("Yeni parola (tekrar)", validators=[
        DataRequired("Zorunlu."), EqualTo("password", "Parolalar eşleşmiyor.")])
    submit = SubmitField("Parolayı değiştir")


# ----------------------------- Yardımcılar -----------------------------

IZINLI_ETIKETLER = ["p", "br", "h1", "h2", "h3", "h4", "strong", "em", "b", "i", "ul", "ol",
                    "li", "blockquote", "code", "pre", "a", "hr", "img", "table", "thead",
                    "tbody", "tr", "th", "td"]
IZINLI_OZELLIKLER = {"a": ["href", "title"], "img": ["src", "alt"]}


@app.template_filter("md")
def md_filter(text):
    html = markdown.markdown(text, extensions=["extra", "nl2br"])
    temiz = bleach.clean(html, tags=IZINLI_ETIKETLER, attributes=IZINLI_OZELLIKLER,
                         protocols=["http", "https", "mailto"])
    return Markup(temiz)


@app.template_filter("tarih")
def tarih_filter(dt):
    return f"{dt.day} {AYLAR[dt.month - 1]} {dt.year}"


@app.template_filter("bas_harf")
def bas_harf_filter(name):
    return name[:1].upper()


@app.template_global()
def page_url(page):
    args = request.args.to_dict()
    args["page"] = page
    return url_for(request.endpoint, **(request.view_args or {}), **args)


def guvenli_url(target):
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ("http", "https") and ref.netloc == test.netloc


def sayfa_no():
    return request.args.get("page", 1, type=int)


def yeni_yazarlar():
    return User.query.order_by(User.created_at.desc()).limit(5).all()


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
    deniz = User(username="deniz", email="deniz@example.com",
                 bio="Kısa öyküler, uzun yürüyüşler.")
    deniz.set_password("parola123")
    ada = User(username="ada", email="ada@example.com",
               bio="Şiir okur, deneme yazar.")
    ada.set_password("parola123")
    db.session.add_all([deniz, ada])
    db.session.flush()
    db.session.add_all([
        Post(title="Gece Yürüyüşleri ve Şehrin Sessizliği", 
             author=deniz, 
             content=(
            "Sokak lambalarının sarı ışığı altında adımları saymak bazen en iyi düşünme yolu.\n\n"
            "> Gürültü azaldıkça zihnin sesi daha net duyulur.\n\n"
            "Her köşede ayrı bir hikaye var ama geceleri hepsi aynı dinginlikte birleşiyor.")),
        
        Post(title="Minimalizmin Getirdiği Ferahlık", 
             author=ada, 
             content=(
            "Fazlalıklardan arınmak, yalnızca mekânda boşluk açmak değil; "
            "zihnin kendi yankısını duyabileceği **duru bir sessizlik** inşa etmektir.\n\n"
            "> Eşyanın ve lüzumsuz telaşın gölgesi çekildiğinde, insan sahip olduklarının ağırlığından "
            "sıyrılıp varoluşun yalın hafifliğiyle nefes almaya başlar.\n\n"
            "### Azalmanın Getirdikleri\n"
            "* **Hafiflik:** Sahip olunanların yükünden kurtulup zihinsel berraklığa kavuşmak.\n"
            "* **Denge:** Dış dünyayı doldurmak yerine iç dünyaya alan tanımak.\n"
            "* **Öz:** Azaldıkça eksilmeden, asıl olanın güzelliğinde çoğalabilmek.\n\n"
            "Çünkü **gerçek ferahlık**, dışarıyı doldurmakta değil, içeriye yer açabilmektedir.")),
        
        Post(title="Taslak: Yarım Kalan Öykü", 
             author=deniz, 
             published=False,
             content="Tren garında bekleyen adamın elindeki bavul boştu. "
            "Bunu yalnızca kendisi ve perondaki güvercinler biliyordu...\n\n"
            "> *Not:* Karakterin geçmişine dair ipuçlarını buraya ekle. "
            "Gitmeyi mi istiyor, yoksa sadece kalmaktan mı kaçıyor?\n\n"
            "### Geliştirilecek Kısımlar\n"
            "* Saat kulesinin vuruşunu bir metafor olarak kullan.\n"
            "* Bilet kontrol memuru ile kısa, tedirgin bir diyalog yaz.\n\n"
            "*Cümle burada tıkandı. Belki sonbahar rüzgârı sahneyi tamamlar.*"),
    ])
    db.session.commit()
    print("Örnek veri eklendi. Giriş: deniz / parola123")


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
