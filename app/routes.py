from __future__ import annotations

import base64
from functools import wraps
from datetime import datetime
from typing import Any

from dateutil import parser as dateparser
from sqlalchemy import or_, select

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
api_bp = Blueprint("api", __name__, url_prefix="/api")


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


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return dateparser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None


def _article_select(search_query: str, start_date: datetime | None, end_date: datetime | None):
    stmt = select(Article)

    if search_query:
        like_pattern = f"%{search_query}%"
        stmt = stmt.where(
            or_(
                Article.title.ilike(like_pattern),
                Article.body.ilike(like_pattern),
            )
        )

    if start_date is not None:
        stmt = stmt.where(Article.published_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(Article.published_at <= end_date)

    return stmt.order_by(Article.published_at.desc(), Article.created_at.desc())


def _article_to_dict(article: Article) -> dict[str, Any]:
    inference = article.inference
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "body": article.body,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "inference": None
        if inference is None
        else {
            "id": inference.id,
            "risk_score": inference.risk_score,
            "summary": inference.summary,
            "model": inference.model,
            "prompt_version": inference.prompt_version,
            "created_at": inference.created_at.isoformat() if inference.created_at else None,
        },
    }


@bp.get("/")
@requires_basic_auth
def index():
    page_param = request.args.get("page", "1")
    try:
        page = max(int(page_param), 1)
    except ValueError:
        page = 1

    search_query = request.args.get("q", "").strip()
    start_date_raw = request.args.get("start")
    end_date_raw = request.args.get("end")

    start_date = _parse_date(start_date_raw)
    end_date = _parse_date(end_date_raw)

    stmt = _article_select(search_query, start_date, end_date)

    pagination = db.paginate(stmt, page=page, per_page=20, error_out=False)

    return render_template(
        "index.html",
        articles=pagination.items,
        pagination=pagination,
        filters={
            "q": search_query,
            "start": start_date_raw or "",
            "end": end_date_raw or "",
        },
    )


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

    article = db.session.scalar(select(Article).where(Article.url == url))
    if article:
        flash("既存の記事を表示します。", "info")
        return redirect(url_for("main.result", article_id=article.id))

    try:
        response = scraping.fetch(url)
        parsed = parsing.parse_article(response.url, response.text)
    except scraping.ScrapeError as exc:
        current_app.logger.warning("Scraping failed for %s: %s", url, exc)
        flash(str(exc), "error")
        return redirect(url_for("main.index"))
    except parsing.ParseError as exc:
        current_app.logger.warning("Parsing failed for %s: %s", url, exc)
        flash("記事の本文を解析できませんでした。", "error")
        return redirect(url_for("main.index"))

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


@bp.post("/result_ai/<article_id>/rerun")
@requires_basic_auth
def rerun_ai(article_id: str):
    article = db.session.get(Article, article_id)
    if article is None:
        abort(404)

    if not current_app.config.get("ENABLE_AI", True):
        flash("AI機能は無効化されています。", "error")
        return redirect(url_for("main.result", article_id=article.id))

    try:
        ai_result = ai_service.summarize_and_score(article.title, article.body[:4000])
    except ai_service.AIServiceUnavailable as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.result", article_id=article.id))

    inference = article.inference
    if inference is None:
        inference = InferenceResult(
            article_id=article.id,
            risk_score=ai_result.risk_score,
            summary=ai_result.summary,
            model=ai_result.model,
            prompt_version=ai_result.prompt_version,
        )
        db.session.add(inference)
    else:
        inference.risk_score = ai_result.risk_score
        inference.summary = ai_result.summary
        inference.model = ai_result.model
        inference.prompt_version = ai_result.prompt_version

    db.session.commit()
    flash("AI推論を再実行しました。", "success")
    return redirect(url_for("main.result_ai", article_id=article.id))


@api_bp.get("/articles")
@requires_basic_auth
def api_list_articles():
    page_param = request.args.get("page", "1")
    per_page_param = request.args.get("per_page", "20")
    try:
        page = max(int(page_param), 1)
    except ValueError:
        page = 1
    try:
        per_page = min(100, max(int(per_page_param), 1))
    except ValueError:
        per_page = 20

    search_query = request.args.get("q", "").strip()
    start_date = _parse_date(request.args.get("start"))
    end_date = _parse_date(request.args.get("end"))

    stmt = _article_select(search_query, start_date, end_date)
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "items": [_article_to_dict(article) for article in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
            "total": pagination.total,
        }
    )


@api_bp.get("/articles/<article_id>")
@requires_basic_auth
def api_get_article(article_id: str):
    article = db.session.get(Article, article_id)
    if article is None:
        return jsonify({"error": "記事が見つかりません。"}), 404
    return jsonify({"article": _article_to_dict(article)})


@api_bp.post("/articles")
@requires_basic_auth
def api_create_article():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()
    force = bool(payload.get("force"))
    run_ai = payload.get("run_ai", True)
    force_ai = bool(payload.get("force_ai"))

    if not url:
        return jsonify({"error": "url は必須です。"}), 400
    if not scraping.is_allowed(url):
        return jsonify({"error": "Yahoo!ニュースの記事URLのみ対応しています。"}), 400

    article = Article.query.filter_by(url=url).first()
    status = "cached"
    parsed = None

    needs_fetch = force or article is None

    if needs_fetch:
        try:
            response = scraping.fetch(url)
            parsed = parsing.parse_article(response.url, response.text)
        except scraping.ScrapeError as exc:
            current_app.logger.warning("API scrape failed for %s: %s", url, exc)
            return jsonify({"error": str(exc)}), 502
        except parsing.ParseError as exc:
            current_app.logger.warning("API parse failed for %s: %s", url, exc)
            return jsonify({"error": "記事の本文を解析できませんでした。"}), 422

        if article is None:
            article = Article(
                url=parsed.url,
                title=parsed.title,
                published_at=parsed.published_at,
                body=parsed.body,
            )
            db.session.add(article)
            status = "created"
        else:
            article.url = parsed.url
            article.title = parsed.title
            article.published_at = parsed.published_at
            article.body = parsed.body
            status = "updated"

    db.session.flush()

    ai_enabled = current_app.config.get("ENABLE_AI", True)
    ai_ran = False
    ai_error: str | None = None

    if run_ai and ai_enabled and (force_ai or article.inference is None or needs_fetch):
        try:
            ai_result = ai_service.summarize_and_score(article.title, article.body[:4000])
        except ai_service.AIServiceUnavailable as exc:
            ai_error = str(exc)
        else:
            inference = article.inference
            if inference is None:
                inference = InferenceResult(
                    article_id=article.id,
                    risk_score=ai_result.risk_score,
                    summary=ai_result.summary,
                    model=ai_result.model,
                    prompt_version=ai_result.prompt_version,
                )
                db.session.add(inference)
            else:
                inference.risk_score = ai_result.risk_score
                inference.summary = ai_result.summary
                inference.model = ai_result.model
                inference.prompt_version = ai_result.prompt_version
            ai_ran = True

    db.session.commit()

    response_body = {
        "article": _article_to_dict(article),
        "status": status,
        "ai": {
            "enabled": ai_enabled,
            "run": ai_ran,
            "error": ai_error,
        },
    }

    return jsonify(response_body), 201 if status == "created" else 200
@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})
