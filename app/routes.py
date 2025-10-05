from __future__ import annotations

import base64
from functools import wraps

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from .models.article import Article, InferenceResult
from .models.db import db
from .services import ai as ai_service
from .services import parsing, scraping

bp = Blueprint("main", __name__)


def _check_auth(header: str | None) -> bool:
    if not header or not header.startswith("Basic "):
        return False
    try:
        encoded = header.split(" ", 1)[1]
        username, password = base64.b64decode(encoded).decode("utf-8").split(":", 1)
    except Exception:
        return False

    return (
        username == current_app.config["BASIC_AUTH_USERNAME"]
        and password == current_app.config["BASIC_AUTH_PASSWORD"]
    )


def requires_basic_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not _check_auth(request.headers.get("Authorization")):
            resp = Response("Unauthorized", status=401)
            resp.headers["WWW-Authenticate"] = 'Basic realm="Restricted"'
            return resp
        return view(*args, **kwargs)

    return wrapped


@bp.get("/")
@requires_basic_auth
def index():
    articles = Article.query.order_by(Article.created_at.desc()).limit(50).all()
    return render_template("index.html", articles=articles)


@bp.post("/scrape")
@requires_basic_auth
def scrape():
    url = request.form.get("url", "").strip()
    if not url:
        flash("URLを入力してください。", "error")
        return redirect(url_for("main.index"))

    if not scraping.is_allowed(url):
        flash("Yahoo!ニュースの記事URLのみ対応しています。", "error")
        return redirect(url_for("main.index"))

    article = Article.query.filter_by(url=url).first()
    if article:
        flash("既存の記事を表示します。", "info")
        return redirect(url_for("main.result", article_id=article.id))

    response = scraping.fetch(url)
    parsed = parsing.parse_article(response.url, response.text)

    article = Article(
        url=parsed.url,
        title=parsed.title,
        published_at=parsed.published_at,
        body=parsed.body,
    )
    db.session.add(article)
    db.session.commit()

    if current_app.config.get("ENABLE_AI", True):
        try:
            ai_result = ai_service.summarize_and_score(parsed.title, parsed.body[:4000])
        except ai_service.AIServiceUnavailable as exc:
            flash(str(exc), "warning")
        else:
            inference = InferenceResult(
                article_id=article.id,
                risk_score=ai_result.risk_score,
                summary=ai_result.summary,
                model=ai_result.model,
                prompt_version=ai_result.prompt_version,
            )
            db.session.add(inference)
            db.session.commit()

    flash("記事を保存しました。", "success")
    return redirect(url_for("main.result", article_id=article.id))


@bp.get("/result/<article_id>")
@requires_basic_auth
def result(article_id: str):
    article = db.session.get(Article, article_id)
    if article is None:
        abort(404)
    return render_template("result.html", article=article, inference=None)


@bp.get("/result_ai/<article_id>")
@requires_basic_auth
def result_ai(article_id: str):
    article = db.session.get(Article, article_id)
    if article is None:
        abort(404)
    inference = article.inference
    if inference is None:
        flash("AI推論はまだ利用できません。", "info")
        return redirect(url_for("main.result", article_id=article.id))
    return render_template("result.html", article=article, inference=inference)


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})
