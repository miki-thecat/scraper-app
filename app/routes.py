from __future__ import annotations

import base64
import csv
import io
import os
from functools import wraps
from datetime import datetime, timezone
from typing import Any

from dateutil import tz
from sqlalchemy import select

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
from .models.article import Article
from .models.db import db
from .models.user import User
from .services import analytics, news_feed, risk, scraping
from .services import articles as article_service

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

    return _validate_user_credentials(username, password)


def _validate_user_credentials(username: str, password: str) -> bool:
    if not username or not password:
        return False
    user = db.session.scalar(db.select(User).where(User.username == username))
    if user and user.verify_password(password):
        return True
    expected_username = current_app.config.get("BASIC_AUTH_USERNAME", "")
    expected_password = current_app.config.get("BASIC_AUTH_PASSWORD", "")
    return username == expected_username and password == expected_password


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

    start_date = article_service.parse_date(start_date_raw)
    end_date = article_service.parse_date(end_date_raw)

    risk_band = risk.level_by_slug(risk_param)

    stmt = article_service.article_select(
        search_query, start_date, end_date, sort_key, order, risk_band
    )

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

    start_date = article_service.parse_date(start_date_raw)
    end_date = article_service.parse_date(end_date_raw)

    risk_band = risk.level_by_slug(risk_param)

    stmt = article_service.article_select(
        search_query, start_date, end_date, sort_key, order, risk_band
    )
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
        payload = article_service.article_to_dict(article)
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

    try:
        result = article_service.ingest_article(url)
    except article_service.ArticleIngestionError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.index"))

    article = result.article

    if result.status == "created":
        flash("記事を保存しました。", "success")
    elif result.status == "updated":
        flash("記事を更新しました。", "info")
    else:
        flash("既存の記事を表示します。", "info")

    if result.ai_error:
        flash(result.ai_error, "warning")

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

    try:
        result = article_service.ingest_article(
            article.url,
            force=False,
            run_ai=True,
            force_ai=True,
        )
    except article_service.ArticleIngestionError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.result", article_id=article.id))

    if not result.ai_enabled:
        flash("AI機能は無効化されています。", "error")
        return redirect(url_for("main.result", article_id=article.id))

    if result.ai_error:
        flash(result.ai_error, "error")
        return redirect(url_for("main.result", article_id=article.id))

    if not result.ai_ran:
        flash("AI推論は実行されませんでした。", "info")
        return redirect(url_for("main.result", article_id=article.id))

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
    start_date = article_service.parse_date(request.args.get("start"))
    end_date = article_service.parse_date(request.args.get("end"))
    sort_key = request.args.get("sort", "published_at")
    order = request.args.get("order", "desc")
    risk_param = request.args.get("risk", "").strip().lower()
    if sort_key not in {"published_at", "created_at", "title"}:
        sort_key = "published_at"
    if order not in {"asc", "desc"}:
        order = "desc"

    risk_band = risk.level_by_slug(risk_param)

    stmt = article_service.article_select(
        search_query, start_date, end_date, sort_key, order, risk_band
    )
    pagination = db.paginate(
        stmt, page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "items": [article_service.article_to_dict(article) for article in pagination.items],
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
    return jsonify({"article": article_service.article_to_dict(article)})


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

    try:
        result = article_service.ingest_article(
            url,
            force=force,
            run_ai=run_ai,
            force_ai=force_ai,
        )
    except article_service.ArticleIngestionError as exc:
        current_app.logger.warning("API ingest failed for %s: %s", url, exc)
        return jsonify({"error": str(exc)}), exc.status_code

    response_body = {
        "article": article_service.article_to_dict(result.article),
        "status": result.status,
        "ai": {
            "enabled": result.ai_enabled,
            "run": result.ai_ran,
            "error": result.ai_error,
        },
    }

    return jsonify(response_body), 201 if result.status == "created" else 200


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
