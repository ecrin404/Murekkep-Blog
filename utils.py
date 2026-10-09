"""Mürekkep - Şablon Filtreleri ve Yardımcı Fonksiyonlar"""
from urllib.parse import urljoin, urlparse

import bleach
import markdown
from flask import request, url_for
from markupsafe import Markup

from models import User

POSTS_PER_PAGE = 6
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

IZINLI_ETIKETLER = ["p", "br", "h1", "h2", "h3", "h4", "strong", "em", "b", "i", "ul", "ol",
                    "li", "blockquote", "code", "pre", "a", "hr", "img", "table", "thead",
                    "tbody", "tr", "th", "td"]
IZINLI_OZELLIKLER = {"a": ["href", "title"], "img": ["src", "alt"]}


# --- Şablon filtreleri (app.py içinde kaydedilir) ---

def md_filter(text):
    html = markdown.markdown(text, extensions=["extra", "nl2br"])
    temiz = bleach.clean(html, tags=IZINLI_ETIKETLER, attributes=IZINLI_OZELLIKLER,
                         protocols=["http", "https", "mailto"])
    return Markup(temiz)


def tarih_filter(dt):
    return f"{dt.day} {AYLAR[dt.month - 1]} {dt.year}"


def bas_harf_filter(name):
    return name[:1].upper()


def page_url(page):
    args = request.args.to_dict()
    args["page"] = page
    return url_for(request.endpoint, **(request.view_args or {}), **args)


# --- Yardımcı fonksiyonlar ---

def guvenli_url(target):
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ("http", "https") and ref.netloc == test.netloc


def sayfa_no():
    return request.args.get("page", 1, type=int)


def yeni_yazarlar():
    return User.query.order_by(User.created_at.desc()).limit(5).all()
