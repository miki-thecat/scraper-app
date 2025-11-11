from __future__ import annotations

from __future__ import annotations

import csv
import io
from pathlib import Path

import click
from flask import Flask
from sqlalchemy import select

from .models.article import Article
from .models.db import db
from .services import articles as article_service
from .services import news_feed, risk


def register_cli_commands(app: Flask) -> None:
    """Flask CLIに便利コマンドを登録。"""

    @app.cli.command("list-articles")
    def list_articles() -> None:
        """DB内の記事IDとタイトルを列挙。"""
        with app.app_context():
            for article in db.session.query(Article).order_by(Article.created_at.desc()).all():
                print(f"{article.id}\t{article.title}")

    @app.cli.group("scrape")
    def scrape_group() -> None:
        """スクレイピング関連のコマンド群。"""

    @scrape_group.command("feed")
    @click.option("--limit", default=20, show_default=True, help="RSSから処理する記事数。")
    @click.option("--force", is_flag=True, help="既存記事も再取得します。")
    @click.option("--skip-ai", is_flag=True, help="AI要約/リスク算出をスキップします。")
    @click.option("--force-ai", is_flag=True, help="既存推論があってもAIを再実行します。")
    @click.option(
        "--provider",
        "-p",
        "providers",
        multiple=True,
        type=click.Choice(["yahoo", "nifty"]),
        help="対象ニュースプロバイダ（複数指定可）。省略時は有効な全プロバイダ。",
    )
    def scrape_feed(limit: int, force: bool, skip_ai: bool, force_ai: bool, providers: tuple[str, ...]) -> None:
        """最新RSSをまとめて取り込み。"""

        if limit <= 0:
            raise click.BadParameter("limit は1以上で指定してください。")

        with app.app_context():
            target_providers = providers or news_feed.enabled_providers()
            stats = {"created": 0, "updated": 0, "cached": 0, "errors": 0}
            for provider in target_providers:
                items = news_feed.fetch_latest_articles(limit=limit, provider=provider)
                if not items:
                    click.echo(f"{news_feed.provider_label(provider)} のRSSを取得できませんでした。")
                    continue

                click.echo(f"=== {news_feed.provider_label(provider)} ({len(items)} 件) ===")

                for item in items:
                    try:
                        result = article_service.ingest_article(
                            item.url,
                            force=force,
                            run_ai=not skip_ai,
                            force_ai=force_ai,
                        )
                    except article_service.ArticleIngestionError as exc:
                        stats["errors"] += 1
                        click.echo(f"[ERROR] {item.url} - {exc}", err=True)
                        continue

                    stats[result.status] += 1
                    published = article_service.format_timestamp(item.published_at)
                    click.echo(
                        f"[{result.status.upper():7}] {item.title} "
                        f"({published or '日時不明'})"
                    )

                    if result.ai_error:
                        click.echo(f"    ↳ AI: {result.ai_error}", err=True)

            click.echo(
                "created={created} updated={updated} "
                "cached={cached} errors={errors}".format(**stats)
            )

    @app.cli.group("ai")
    def ai_group() -> None:
        """AI関連のバッチ処理。"""

    @ai_group.command("rerun")
    @click.option("--limit", default=20, show_default=True, help="対象記事数。")
    @click.option(
        "--missing-only/--include-all",
        default=False,
        show_default=True,
        help="AI未実行の記事のみに限定するかを選択。",
    )
    def ai_rerun(limit: int, missing_only: bool) -> None:
        """古い記事のAI推論を再実行。"""

        if limit <= 0:
            raise click.BadParameter("limit は1以上で指定してください。")

        with app.app_context():
            stmt = select(Article).order_by(Article.created_at.asc())
            candidates = db.session.scalars(stmt).all()

            if missing_only:
                candidates = [article for article in candidates if not article.latest_inference]

            targets = candidates[:limit]
            if not targets:
                click.echo("再実行対象となる記事が見つかりませんでした。")
                return

            for article in targets:
                try:
                    result = article_service.ingest_article(
                        article.url,
                        force=False,
                        run_ai=True,
                        force_ai=True,
                    )
                except article_service.ArticleIngestionError as exc:
                    click.echo(f"[ERROR] {article.id} - {exc}", err=True)
                    continue

                if not result.ai_enabled:
                    click.echo("AI機能が無効化されています。処理を中断します。", err=True)
                    break

                if result.ai_error:
                    click.echo(f"[ERROR] {article.id} - AI: {result.ai_error}", err=True)
                    continue

                refreshed = result.article
                latest = refreshed.latest_inference
                score = latest.risk_score if latest else "-"
                click.echo(f"[OK] {refreshed.title} -> リスク {score}")

    @app.cli.group("export")
    def export_group() -> None:
        """エクスポート用コマンド。"""

    @export_group.command("csv")
    @click.option(
        "--output",
        "-o",
        default="scraper-report.csv",
        show_default=True,
        type=click.Path(dir_okay=False, writable=True, allow_dash=True),
        help="出力ファイルパス。'-' 指定で標準出力。",
    )
    @click.option("--query", "-q", default="", help="タイトル/本文の部分一致検索語。")
    @click.option("--start", help="開始日 (YYYY-MM-DD など)。")
    @click.option("--end", help="終了日 (YYYY-MM-DD など)。")
    @click.option(
        "--sort",
        type=click.Choice(["published_at", "created_at", "title"]),
        default="published_at",
        show_default=True,
    )
    @click.option(
        "--order",
        type=click.Choice(["asc", "desc"]),
        default="desc",
        show_default=True,
    )
    @click.option(
        "--risk",
        "risk_slug",
        type=click.Choice([band.slug for band in risk.levels()]),
        default=None,
        help="特定のリスク帯のみ出力。",
    )
    def export_csv(
        output: str,
        query: str,
        start: str | None,
        end: str | None,
        sort: str,
        order: str,
        risk_slug: str | None,
    ) -> None:
        """記事データをCSVでエクスポート。"""

        start_dt = article_service.parse_date(start)
        end_dt = article_service.parse_date(end)
        risk_band = risk.level_by_slug(risk_slug)

        with app.app_context():
            stmt = article_service.article_select(
                query.strip(),
                start_dt,
                end_dt,
                sort,
                order,
                risk_band,
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

        data = buffer.getvalue()
        if output == "-":
            click.echo(data, nl=False)
            return

        path = Path(output)
        path.write_text(data, encoding="utf-8")
        click.echo(f"{len(articles)}件を書き出しました -> {path}")
