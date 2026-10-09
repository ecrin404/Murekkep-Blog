"""Mürekkep - Veritabanı Nesnesi ve Modeller"""
import re
from datetime import datetime, timezone

import bleach
import markdown
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import pbkdf2_sha256

# app.py içinde db.init_app(app) ile uygulamaya bağlanır.
db = SQLAlchemy()


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
