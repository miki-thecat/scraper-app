from base64 import b64decode
from functools import wraps
from hmac import compare_digest

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from .models import db, Article
from .scraper import scrape_nhk_article

# Blueprintを作成
main = Blueprint('main', __name__)

# --- Basic認証 --- #
def check_auth(auth_header: str) -> bool:
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        encoded = auth_header.split(" ")[1]
        userpass = b64decode(encoded).decode("utf-8")
        username, password = userpass.split(":", 1)
        # 環境変数からではなく、appの設定から取得する
        user_ok = compare_digest(username, current_app.config["BASIC_AUTH_USERNAME"])
        pass_ok = compare_digest(password, current_app.config["BASIC_AUTH_PASSWORD"])
        return user_ok and pass_ok
    except Exception:
        return False

def requires_basic_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not check_auth(auth):
            return ('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return wrapper

# --- ルーティング --- #
@main.route("/")
def index():
    articles = Article.query.order_by(Article.posted_at.desc()).all()
    return render_template("index.html", articles=articles)

@main.route("/scrape", methods=["POST"])
@requires_basic_auth
def scrape():
    url = request.form.get("url", "").strip()
    if not url:
        flash("URLを入力してください", "error")
        return redirect(url_for("main.index"))
    
    try:
        data = scrape_nhk_article(url)
        article = Article.query.filter_by(url=url).first()
        if article:
            article.title = data["title"]
            article.body = data["body"]
            article.posted_at = data["posted_at"]
        else:
            article = Article(**data)
            db.session.add(article)
        db.session.commit()
        flash("記事をスクレイプしました", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"エラーが発生しました: {e}", "error")
    finally:
        return redirect(url_for("main.index"))
