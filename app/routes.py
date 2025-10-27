from __future__ import annotations

import base64
import csv
import io
import os
from functools import wraps
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dateparser, tz
from sqlalchemy import or_, select
from sqlalchemy.orm import aliased

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

from .auth import session_manager
from .models.article import Article, InferenceResult
from .models.db import db
from .services import ai as ai_service
from .services import analytics, news_feed, parsing, risk, scraping

bp = Blueprint("main", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


def _allowed_tokens() -> set[str]:
    tokens = current_app.config.get("API_ACCESS_TOKENS", ())
    return {tok for tok in tokens if tok}


def _check_auth(header: str | None) -> bool:
    if not header or not header.startswith("Basic "):
        if not header:
            return False
        if header.startswith("Bearer "):
            token = header.split(" ", 1)[1].strip()
            return token in _allowed_tokens()
        return False
    try:
        encoded = header.split(" ", 1)[1]
        username, password = base64.b64decode(
            encoded).decode("utf-8").split(":", 1)
    except Exception:
        return False

    return (
        username == current_app.config["BASIC_AUTH_USERNAME"]
        and password == current_app.config["BASIC_AUTH_PASSWORD"]
    )


def requires_basic_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session_manager.is_authenticated():
            return view(*args, **kwargs)

        if _check_auth(request.headers.get("Authorization")):
            return view(*args, **kwargs)

        api_key = request.headers.get("X-API-Key")
        if api_key and api_key.strip() in _allowed_tokens():
            return view(*args, **kwargs)

        if request.blueprint == "api":
            resp = Response("Unauthorized", status=401)
            resp.headers["WWW-Authenticate"] = 'Basic realm="Restricted"'
            return resp

        flash("ログインしてください。", "error")
        login_url = url_for("auth.login", next=request.url)
        return redirect(login_url)
        return view(*args, **kwargs)

    return wrapped


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return dateparser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None


def _article_select(
    search_query: str,
    start_date: datetime | None,
    end_date: datetime | None,
    sort_key: str = "published_at",
    order: str = "desc",
    risk_band: risk.RiskBand | None = None,
):
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

    if risk_band is not None:
        latest = aliased(InferenceResult)
        latest_subquery = (
            select(InferenceResult.id)
            .where(InferenceResult.article_id == Article.id)
            .order_by(InferenceResult.created_at.desc(), InferenceResult.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        stmt = stmt.join(latest, latest.id == latest_subquery)
        stmt = stmt.where(latest.risk_score >= risk_band.min_score)
        if risk_band.max_score is not None:
            stmt = stmt.where(latest.risk_score <= risk_band.max_score)

    sort_columns = {
        "published_at": Article.published_at,
        "created_at": Article.created_at,
        "title": Article.title,
    }
    column = sort_columns.get(sort_key, Article.published_at)
    direction = column.desc() if order == "desc" else column.asc()

    return stmt.order_by(direction, Article.created_at.desc())


def _article_to_dict(article: Article) -> dict[str, Any]:
    history = [
        {
            "id": record.id,
            "risk_score": record.risk_score,
            "risk_level": _risk_level_payload(record.risk_score),
            "summary": record.summary,
            "model": record.model,
            "prompt_version": record.prompt_version,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in article.inferences
    ]
    return {
        "id": article.id,
        "url": article.url,
        "title": article.title,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "body": article.body,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "inference": history[0] if history else None,
        "inference_history": history,
        "risk_level": _risk_level_payload(article.latest_inference.risk_score) if article.latest_inference else None,
    }


def _risk_level_payload(score: int | None) -> dict[str, Any] | None:
    level = risk.classify(score)
    if level is None:
        return None
    return {
        "slug": level.slug,
        "name": level.name,
        "badge": level.badge,
        "description": level.description,
        "min_score": level.min_score,
        "max_score": level.max_score,
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
    sort_key = request.args.get("sort", "published_at")
    order = request.args.get("order", "desc")
    risk_param = request.args.get("risk", "").strip().lower()

    if sort_key not in {"published_at", "created_at", "title"}:
        sort_key = "published_at"
    if order not in {"asc", "desc"}:
        order = "desc"

    start_date = _parse_date(start_date_raw)
    end_date = _parse_date(end_date_raw)

    risk_band = risk.level_by_slug(risk_param)

    stmt = _article_select(search_query, start_date,
                           end_date, sort_key, order, risk_band)

    pagination = db.paginate(stmt, page=page, per_page=20, error_out=False)

    metrics = analytics.gather_metrics(db.session)
    latest_articles = _latest_articles_for_view(limit=6)

    return render_template(
        "index.html",
        articles=pagination.items,
        pagination=pagination,
        filters={
            "q": search_query,
            "start": start_date_raw or "",
            "end": end_date_raw or "",
            "sort": sort_key,
            "order": order,
            "risk": risk_param,
        },
        metrics=metrics,
        latest_articles=latest_articles,
        risk_classify=risk.classify,
        risk_levels=risk.levels(),
    )


@bp.get("/export.csv")
@requires_basic_auth
def export_csv():
    search_query = request.args.get("q", "").strip()
    start_date_raw = request.args.get("start")
    end_date_raw = request.args.get("end")
    sort_key = request.args.get("sort", "published_at")
    order = request.args.get("order", "desc")
    risk_param = request.args.get("risk", "").strip().lower()

    start_date = _parse_date(start_date_raw)
    end_date = _parse_date(end_date_raw)

    risk_band = risk.level_by_slug(risk_param)

    stmt = _article_select(search_query, start_date,
                           end_date, sort_key, order, risk_band)
    articles = db.session.scalars(stmt).all()

    buffer = io.StringIO()
    fieldnames = [
        "title",
        "url",
        "published_at",
        "created_at",
        "risk_score",
        "risk_level",
        "risk_label",
        "summary",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()

    for article in articles:
        payload = _article_to_dict(article)
        inference = payload.get("inference") or {}
        level = inference.get("risk_level") or payload.get("risk_level")
        writer.writerow(
            {
                "title": payload["title"],
                "url": payload["url"],
                "published_at": payload["published_at"],
                "created_at": payload["created_at"],
                "risk_score": inference.get("risk_score"),
                "risk_level": (level or {}).get("name") if level else "",
                "risk_label": (level or {}).get("badge") if level else "",
                "summary": inference.get("summary", ""),
            }
        )

    buffer.seek(0)
    filename = "scraper-report.csv"
    return Response(
        buffer.getvalue(),
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f"attachment; filename={filename}",
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
            ai_result = ai_service.summarize_and_score(
                parsed.title, parsed.body[:4000])
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
    return render_template(
        "result.html",
        article=article,
        inference=article.latest_inference,
    )


@bp.get("/result_ai/<article_id>")
@requires_basic_auth
def result_ai(article_id: str):
    article = db.session.get(Article, article_id)
    if article is None:
        abort(404)
    inference = article.latest_inference
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
        ai_result = ai_service.summarize_and_score(
            article.title, article.body[:4000])
    except ai_service.AIServiceUnavailable as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.result", article_id=article.id))

    inference = InferenceResult(
        article_id=article.id,
        risk_score=ai_result.risk_score,
        summary=ai_result.summary,
        model=ai_result.model,
        prompt_version=ai_result.prompt_version,
    )
    db.session.add(inference)

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
    sort_key = request.args.get("sort", "published_at")
    order = request.args.get("order", "desc")
    risk_param = request.args.get("risk", "").strip().lower()
    if sort_key not in {"published_at", "created_at", "title"}:
        sort_key = "published_at"
    if order not in {"asc", "desc"}:
        order = "desc"

    risk_band = risk.level_by_slug(risk_param)

    stmt = _article_select(search_query, start_date,
                           end_date, sort_key, order, risk_band)
    pagination = db.paginate(
        stmt, page=page, per_page=per_page, error_out=False)

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

    article = db.session.scalar(select(Article).where(Article.url == url))
    status = "cached"
    parsed = None

    needs_fetch = force or article is None

    if needs_fetch:
        try:
            response = scraping.fetch(url)
            parsed = parsing.parse_article(response.url, response.text)
        except scraping.ScrapeError as exc:
            current_app.logger.warning(
                "API scrape failed for %s: %s", url, exc)
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

    latest = article.latest_inference

    if run_ai and ai_enabled and (force_ai or latest is None or needs_fetch):
        try:
            ai_result = ai_service.summarize_and_score(
                article.title, article.body[:4000])
        except ai_service.AIServiceUnavailable as exc:
            ai_error = str(exc)
        else:
            inference = InferenceResult(
                article_id=article.id,
                risk_score=ai_result.risk_score,
                summary=ai_result.summary,
                model=ai_result.model,
                prompt_version=ai_result.prompt_version,
            )
            db.session.add(inference)
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


@api_bp.get("/reports/summary")
@requires_basic_auth
def api_report_summary():
    metrics = analytics.gather_metrics(db.session)
    highest = None
    if metrics.highest_risk_article_id:
        highest = {
            "article_id": metrics.highest_risk_article_id,
            "title": metrics.highest_risk_title,
            "risk_score": metrics.highest_risk_score,
        }

    return jsonify(
        {
            "total_articles": metrics.total_articles,
            "ai_coverage_ratio": metrics.ai_coverage_ratio,
            "average_risk_score": metrics.average_risk_score,
            "high_risk_articles": metrics.high_risk_articles,
            "highest_risk": highest,
            "risk_distribution": {
                band.slug: metrics.risk_distribution.get(band.slug, 0)
                for band in risk.levels()
            },
        }
    )


_TOKYO_TZ = tz.gettz("Asia/Tokyo")


def _latest_articles_for_view(limit: int, search_query: str = "") -> list[dict[str, Any]]:
    items = news_feed.fetch_latest_articles(
        limit=limit * 3)  # Fetch more for filtering
    latest: list[dict[str, Any]] = []

    search_lower = search_query.lower() if search_query else ""

    for item in items:
        # Filter by search query if provided
        if search_lower:
            title_match = search_lower in item.title.lower()
            source_match = search_lower in item.source.lower()
            if not (title_match or source_match):
                continue

        published_display = None
        published_iso = None
        if item.published_at:
            try:
                local_dt = item.published_at.astimezone(_TOKYO_TZ)
            except (ValueError, AttributeError):
                local_dt = None
            if local_dt:
                published_display = local_dt.strftime("%Y-%m-%d %H:%M")
                published_iso = local_dt.isoformat()

        latest.append(
            {
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "published_display": published_display,
                "published_iso": published_iso,
            }
        )

        # Limit results after filtering
        if len(latest) >= limit:
            break

    return latest


@bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@bp.get("/latest-feed")
@requires_basic_auth
def latest_feed():
    """最新Yahoo!ニュースの専用ページ（ページネーション＆検索対応）"""
    page_param = request.args.get("page", "1")
    try:
        page = max(int(page_param), 1)
    except ValueError:
        page = 1

    search_query = request.args.get("q", "").strip()
    per_page = 20

    # Fetch more articles to handle filtering (increased limit for more sources)
    all_items = news_feed.fetch_latest_articles(limit=500)

    # Filter by search query
    filtered_items = []
    search_lower = search_query.lower() if search_query else ""

    for item in all_items:
        if search_lower:
            title_match = search_lower in item.title.lower()
            source_match = search_lower in item.source.lower()
            if not (title_match or source_match):
                continue

        published_display = None
        published_iso = None
        if item.published_at:
            try:
                local_dt = item.published_at.astimezone(_TOKYO_TZ)
            except (ValueError, AttributeError):
                local_dt = None
            if local_dt:
                published_display = local_dt.strftime("%Y-%m-%d %H:%M")
                published_iso = local_dt.isoformat()

        filtered_items.append(
            {
                "title": item.title,
                "url": item.url,
                "source": item.source,
                "published_display": published_display,
                "published_iso": published_iso,
            }
        )

    # Manual pagination
    total_items = len(filtered_items)
    total_pages = (total_items + per_page -
                   1) // per_page if total_items > 0 else 1
    page = min(page, total_pages)

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = filtered_items[start_idx:end_idx]

    pagination_info = {
        "page": page,
        "pages": total_pages,
        "total": total_items,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "per_page": per_page,
    }

    return render_template(
        "latest_feed.html",
        articles=page_items,
        pagination=pagination_info,
        search_query=search_query,
    )


# ========================================
# Health Check Endpoints
# ========================================

@bp.route("/health")
def health_check():
    """ヘルスチェックエンドポイント（認証不要）"""
    health_status = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "scraper-app",
        "version": "1.0.0",
    }

    # データベース接続チェック
    try:
        db.session.execute(select(1))
        health_status["database"] = "ok"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = f"error: {str(e)}"

    # OpenAI API設定チェック（接続はしない）
    if os.getenv("OPENAI_API_KEY"):
        health_status["openai_configured"] = True
    else:
        health_status["openai_configured"] = False
        health_status["status"] = "degraded"

    status_code = 200 if health_status["status"] == "ok" else 503
    return jsonify(health_status), status_code


@bp.route("/health/ready")
def readiness_check():
    """Readinessチェック（Kubernetes等で使用）"""
    try:
        # データベース接続確認
        db.session.execute(select(1))
        return jsonify({"status": "ready"}), 200
    except Exception as e:
        return jsonify({"status": "not_ready", "error": str(e)}), 503


@bp.route("/health/live")
def liveness_check():
    """Livenessチェック（アプリケーションが生きているか）"""
    return jsonify({"status": "alive"}), 200
