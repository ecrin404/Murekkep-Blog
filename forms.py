"""Mürekkep - Form Sınıfları ve Doğrulayıcılar"""
import re

from flask_wtf import FlaskForm
from wtforms import (BooleanField, PasswordField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Regexp,
                                ValidationError)

from models import User, db


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
