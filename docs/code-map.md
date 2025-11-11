# Scraper App コードマップ

このドキュメントは `scraper-app` リポジトリ全体の構造、使用ライブラリ、代表的な文法パターンを俯瞰できるようにまとめたものです。Flask を中心とした Web アプリケーション層から CLI/ML/テスト/デプロイ補助まで、どこに何が置かれているかを詳細に整理しています。

## 1. エントリポイントと設定

| ファイル | 役割 | 主なライブラリ / 概念 |
| --- | --- | --- |
| `run.py`, `app/main.py` | Flask アプリを生成し Gunicorn/開発サーバーで使えるようにするエントリポイント。 | `from app import create_app` によりアプリケーションファクトリを呼び出す。 |
| `app/__init__.py` | アプリケーションファクトリ。設定読み込み、DB初期化、CSRF保護、Blueprint 登録、レートリミット、セキュリティヘッダ設定を行う。 | Flask, `flask_sqlalchemy.SQLAlchemy`, `flask_migrate.Migrate`, `flask_wtf.CSRFProtect`, Blueprint, before_request/after_request フック。 |
| `app/config.py` | `.env` や環境変数を参照して Config/Test/Dev/Prod を定義。 | Python の `os.getenv`、`timedelta`。|

### 文法メモ
- アプリケーションファクトリは `def create_app(config_class: type[Config] | None = None) -> Flask:` のように Python 3.11 の `type | None` の Union 型ヒントを使っている。
- CSRF 除外は `csrf.exempt(api_bp)` のように Blueprint 単位で行う。

## 2. データモデルと DB 層

| ファイル | 役割 | 解説 |
| --- | --- | --- |
| `app/models/db.py` | `db = SQLAlchemy()` を定義し、`init_db` で Migrate を利用することを明示。 | Flask-Migrate を前提に `db.create_all()` は呼ばない。 |
| `app/models/article.py` | `Article` / `InferenceResult` モデル。UUID 文字列主キー、`mapped_column` を使った型ヒント付き ORM 定義。 | SQLAlchemy 2.0 スタイル、`relationship` で推論履歴を `order_by` + プロパティ `latest_inference` で整備。 |

### 文法メモ
- `Mapped[str] = mapped_column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))` のように `typing.Annotated` 代わりに SQLAlchemy の `Mapped` を用いる最新スタイル。

## 3. サービス層

| ファイル | 役割 | 主な技術 |
| --- | --- | --- |
| `app/services/articles.py` | 記事取得～保存～AI推論までを一括管理するサービス。`ArticleIngestionResult` dataclass で結果を返却し、CLI/API/UI 全体の共通ロジックとなる。 | dataclass, SQLAlchemy セッション、OpenAI API エラー補足。 |
| `app/services/scraping.py` | Yahoo!ニュース限定で HTTP GET を行うスクレイパ。`requests.Session` + `Retry` で再試行制御。 | `requests`, `urllib.parse.urlparse`, `HTTPAdapter`, CSRF ではなくユーザーユーティリティ。 |
| `app/services/parsing.py` | BeautifulSoup + JSON-LD 解析でタイトル/本文/日付を抽出。 | `bs4`, `lxml`, `dateutil.parser`。 |
| `app/services/ai.py` | OpenAI Chat Completions API 呼び出し。レスポンスを JSON として受け取り、要約とリスクスコアを返す。 | `openai` SDK, dataclass, `response_format={"type":"json_object"}` の使用例。 |
| `app/services/risk.py` | リスク帯のしきい値を `RiskBand` dataclass で定義。 | dataclass, immutability (`frozen=True`)。 |
| `app/services/news_feed.py` | Yahoo!ニュース RSS を `requests` + `xml.etree.ElementTree` で取得し、キャッシュする。 | `@dataclass`, グローバルキャッシュ dict。 |
| `app/services/analytics.py` | SQLAlchemy のウィンドウ関数 (`row_number()`) を使ったリスクメトリクス集計。 | `func.row_number().over(...)`。 |

## 4. Web ルーティング層

`app/routes.py` の構成:

1. 認証ヘルパ (`requires_basic_auth`) … セッション/Bearer/X-API-Key を許可。
2. フロント UI (`/`, `/scrape`, `/result`, `/latest-feed` など)。
3. REST API (`/api/articles`, `/api/reports/summary` など)。
4. ヘルスチェック (`/health`, `/health/ready`, `/health/live`).

### 主なライブラリと文法
- `flask.Blueprint` + ルートデコレータ。返り値は `render_template`, `flash`, `redirect`。
- `db.paginate(stmt, page=..., per_page=...)` で SQLAlchemy 2.0 の `select()` をそのままページング。
- REST レスポンスは `jsonify({...})` を返し、`article_service.article_to_dict()` で構造体を統一。
- CSRF 対応: Webフォームは `{{ csrf_token() }}` をテンプレートで挿入、API は Blueprint レベルで免除。

## 5. テンプレート & スタティック

| パス | 説明 |
| --- | --- |
| `app/templates/layout.html` | 共通レイアウト。meta `csrf-token` を埋め込み、ログイン状態 (`app.context_processor`) を参照してヘッダを切り替える。|
| `app/templates/index.html` | URL入力フォーム、ダッシュボードカード、最新RSSカードなどを描画。`{% for band in risk_levels %}` のようにサーバー側ロジックを直接使う。|
| `app/templates/latest_feed.html` | ページネーション UI。単純なループ + `pagination` dict を使った Prev/Next 表示。|
| `app/static/styles.css` | Glassmorphism テイストのCSS。|

## 6. CLI ユーティリティ

`app/cli.py` は Click で以下のコマンドを登録:

- `flask list-articles` … DB 内の ID/タイトル一覧。
- `flask scrape feed` … RSS を取得し `articles.ingest_article` でバルク処理。`--limit`, `--force`, `--skip-ai`, `--force-ai` を指定可能。
- `flask ai rerun` … 古い記事の AI 推論を再実行。`--missing-only` で未推論記事に限定。
- `flask export csv` … `--query`, `--start`, `--end`, `--risk` 等のフィルタ付きで CSV 出力。`--output -` で stdout に流せる。

### 文法のポイント
- Click の複数階層 (`@app.cli.group`) と boolean オプション (`--missing-only/--include-all`) の書き方。
- Flask CLI の実行時は `with app.app_context(): ...` を明示して DB にアクセス。

## 7. テストスイート

| ファイル | 内容 | 使っている手法 |
| --- | --- | --- |
| `tests/conftest.py` | `pytest.fixture` で Flask アプリ/クライアント/Basic 認証ヘッダを提供。 | `create_app(TestConfig)`、`db.create_all()` のセットアップ。 |
| `tests/test_routes.py` | Web UI のシナリオテスト。`mocker.patch` でスクレイプ/AIを差し替え。 | Flask クライアント、`follow_redirects`、CSRF をテスト内で無効化。 |
| `tests/test_api.py` | REST API の認証・検索・レートリミット・AI実行確認。 | `_RATE_BUCKETS` を直接参照し、状態をクリア。 |
| `tests/test_cli.py` | 新 CLI コマンドの動作検証。`app.test_cli_runner()` を使用。 | `SimpleNamespace` でダミー結果を構築。 |
| `tests/test_csrf.py` | POST エンドポイントの CSRF 保護を確認。HTML からメタタグ/hidden input を抽出。 | 正規表現でトークンを抜き取り、`with client` コンテキストでセッションを保持。 |
| `tests/test_ml.py`, `tests/test_ai.py` 等 | ML/AI サービスやスクレイピングのエッジケースを網羅。 | `pytest-mock`, `tmp_path`, `monkeypatch`. |

## 8. ML & CLI 補助

| ディレクトリ | 役割 |
| --- | --- |
| `ml/` | `train.py` / `evaluate.py` / サンプルデータ。`scikit-learn` の TF-IDF + LogisticRegression を Pipeline で構築。ジョブを `argparse` で定義。|
| `cli/classify_industry.py` | 学習済み `joblib` ファイルをロードし、標準入力の企業概要を予測する CLI。|

## 9. インフラ / デプロイ

| パス | 概要 |
| --- | --- |
| `Dockerfile` | 2段階ビルド。Builder で依存インストール → Runtime で Gunicorn。`HEALTHCHECK` や非rootユーザ設定を含む。|
| `docker-compose*.yml` | 開発/本番向け Compose。開発版はホットリロードと pgAdmin を付属。|
| `deploy/` | `deploy.sh` (Artifact 作成 + scp)、`nginx.conf`, `systemd`、`buildspec.yml` など AWS CodeBuild/EC2 連携例。|

## 10. ドキュメント & その他

| パス | 内容 |
| --- | --- |
| `README.md` | ハイレベルな機能説明、セットアップ、CLI 紹介 (今回実装済み)。|
| `docs/` | 仕様書 (`spec.md`)、スクリーンショット、今回のコードマップ。|

## 11. 使用ライブラリまとめ

- **Flask エコシステム**: Flask 3、SQLAlchemy 3、Flask-Migrate、Flask-WTF。
- **リクエスト/解析**: requests、BeautifulSoup4(lxml)、dateutil、xml.etree。
- **AI/ML**: OpenAI SDK、NumPy、pandas、scikit-learn、joblib。
- **CLI**: Click、Flask CLI。
- **テスト**: pytest、pytest-mock、pytest-cov。

## 12. 代表的な文法/パターン

1. **dataclass + slots**: メモリ効率と属性制限 (`@dataclass(slots=True)`).
2. **Typed ORM**: `Mapped[...]` で型安全にモデル定義。
3. **Flask Context Processors**: テンプレートへの共通値注入 (`@app.context_processor`).
4. **Blueprint-based API**: WebとAPIを別 Blueprint で管理し、CSRF やレートリミットを切り替え。
5. **Click Nested Commands**: `@app.cli.group` → `@group.command` で階層化。
6. **pytest Fixtures & monkeypatch**: アプリ全体を `pytest` で容易に差し替えるための fixture デザイン。

---
このマップを起点に、それぞれのディレクトリを掘り下げることで実装意図や依存関係を素早く把握できます。
