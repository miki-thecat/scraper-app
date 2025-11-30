# Virtual News Reader 🚀

**AI搭載の次世代ニュース分析ダッシュボード - 技術デモンストレーション**

[![CI/CD](https://github.com/YOUR_USERNAME/scraper-app/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/YOUR_USERNAME/scraper-app/actions)
[![Coverage](https://codecov.io/gh/YOUR_USERNAME/scraper-app/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/scraper-app)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

> **📌 技術デモンストレーション**
> 本プロジェクトは**学習・ポートフォリオ目的**の技術デモです。
> 仮想ニュースサイト（Virtual News）を使用し、実際の外部サイトへのスクレイピングは行いません。
> Web スクレイピング、AI統合、モダンUI設計の技術力を実証するためのプロジェクトです。

![スクリーンショット](docs/images/design.webp)

## ✨ ハイライト

### 🎨 モダンUI
- **ダークテーマ + グラスモーフィズム**: 最先端のデザインシステム
- **アニメーション**: 浮遊グロー、シマーエフェクト
- **レスポンシブ**: モバイルファースト設計
- **アクセシビリティ**: WCAG AA準拠

### 🤖 AI統合
- **OpenAI GPT-4**: 記事要約 + リスクスコアリング
- **自動推論**: スクレイピング直後にAI実行
- **履歴管理**: 推論履歴の完全トラッキング
- **リスク分類**: 5段階評価 (MINIMAL → CRITICAL)

### 📰 Virtual News機能
- **仮想ニュースサイト**: デモ用の安全な記事データ
- **記事スクレイピング**: HTML解析とデータ抽出
- **自動取得**: 記事一覧から詳細ページへの自動遷移
- **リアルタイム分析**: スクレイプ直後にAI分析実行

### 🔒 セキュリティ
- **CSRF保護**: 全フォームでトークン検証
- **SQLインジェクション対策**: SQLAlchemy ORM
- **XSS対策**: Jinja2自動エスケープ
- **セキュリティヘッダー**: CSP, HSTS, X-Frame-Options

### 🚀 CI/CD
- **GitHub Actions**: 自動テスト・ビルド・デプロイ
- **Copilot Review**: AIによるコードレビュー
- **セキュリティスキャン**: Trivy, Bandit, Safety
- **マルチプラットフォーム**: amd64, arm64対応

### 📊 充実したテスト
- **76テストケース**: 全テスト成功 ✅
- **カバレッジ80%+**: 高品質保証
- **pytest + coverage**: 自動化テストスイート

## 🛠️ 技術スタック

### Backend
- **Framework**: Flask 3.0+
- **ORM**: SQLAlchemy 2.0+
- **Migration**: Alembic
- **DB**: PostgreSQL (production), SQLite (dev)
- **AI**: OpenAI API (GPT-4)

### Frontend
- **Template**: Jinja2
- **Styling**: Modern CSS (Glassmorphism, Gradients, Animations)
- **Icons**: CSS-based
- **Design**: Mobile-First, Responsive Grid

### Infrastructure
- **Server**: Gunicorn + Nginx
- **Container**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Security**: Trivy, Bandit, Safety

### Development
- **Testing**: pytest, pytest-cov
- **Linting**: Ruff, Black, isort
- **Type Check**: mypy
- **Security**: Bandit, Safety

## 📁 プロジェクト構造

```
scraper-app/
├── app/
│   ├── auth/              # 認証・セッション管理
│   ├── blueprints/        # Flaskブループリント
│   │   └── virtual_news.py # Virtual Newsサイト
│   ├── models/            # SQLAlchemyモデル
│   │   ├── article.py     # 記事モデル + AI推論結果
│   │   ├── user.py        # ユーザーモデル
│   │   └── db.py          # DB初期化
│   ├── services/          # ビジネスロジック
│   │   ├── scraping.py    # スクレイピングエンジン
│   │   ├── parsing.py     # HTMLパーサー
│   │   ├── virtual_news_parser.py # Virtual Newsパーサー
│   │   ├── articles.py    # 記事管理サービス
│   │   ├── ai.py          # OpenAI統合
│   │   ├── risk.py        # リスク分類ロジック
│   │   ├── news_feed.py   # ニュースフィード
│   │   └── analytics.py   # メトリクス集計
│   ├── templates/         # Jinja2テンプレート
│   │   ├── layout.html    # ベースレイアウト
│   │   ├── index.html     # ダッシュボード
│   │   ├── result.html    # 記事詳細
│   │   ├── login.html     # ログイン画面
│   │   └── virtual_news/  # Virtual Newsテンプレート
│   ├── static/
│   │   └── styles.css     # モダンCSS (1584 lines)
│   ├── routes.py          # ルーティング
│   └── __init__.py        # Flaskアプリ初期化
├── cli/                   # CLI管理コマンド
├── deploy/                # デプロイ設定
├── docs/                  # ドキュメント
│   ├── UI_DESIGN.md       # UIデザインガイド
│   └── CI_CD.md           # CI/CDガイド
├── ml/                    # 機械学習（将来拡張）
├── tests/                 # テストスイート (76 tests)
├── .github/
│   └── workflows/
│       ├── ci-cd.yml      # CI/CDパイプライン
│       └── code-review.yml # Copilotレビュー
├── requirements.txt
├── pyproject.toml
├── pytest.ini
└── README.md
```

## 🚀 クイックスタート

### 前提条件

- Python 3.11+ ([pyenv推奨](https://github.com/pyenv/pyenv))
- PostgreSQL 15+ (開発はSQLiteでもOK)
- OpenAI APIキー ([取得方法](https://platform.openai.com/api-keys))

### インストール

```bash
# リポジトリクローン
git clone https://github.com/YOUR_USERNAME/scraper-app.git
cd scraper-app

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env を編集してOpenAI APIキーなどを設定
```

### 環境変数

`.env` ファイルに以下を設定:

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///local.db  # または postgresql://...

# OpenAI API
OPENAI_API_KEY=sk-...
ENABLE_AI=true

# 認証 (Basic Auth)
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=secure-password

# API Access (optional)
API_ACCESS_TOKENS=token1,token2
```

### データベース初期化

```bash
# マイグレーション実行
flask db upgrade

# 初期ユーザー作成（オプション）
flask auth create-user admin password123
```

### 起動

```bash
# 開発サーバー起動
python run.py

# または Flask CLI
flask run --debug

# または Gunicorn (本番想定)
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

アプリケーションは http://localhost:5000 で起動します。

### Docker で起動

```bash
# イメージビルド
docker-compose build

# コンテナ起動
docker-compose up -d

# ログ確認
docker-compose logs -f web
```

## 📖 使い方

### ダッシュボード

1. **Virtual News閲覧**
   - `/virtual-news/` で仮想ニュースサイトにアクセス
   - 5つのモック記事を閲覧可能
   - 認証不要でアクセス可能

2. **記事スクレイピング**
   - Virtual NewsのURLを入力して「実行する」ボタン
   - 自動的に記事内容取得 + AI要約・リスク評価
   - 重複チェック機能付き

3. **リスク監視**
   - 登録済み記事数、AI解析率
   - 平均リスクスコア、高リスク記事数
   - リスク分布（5段階）をグラフ表示

4. **検索・フィルタ**
   - キーワード検索（タイトル・本文）
   - 期間指定（開始日・終了日）
   - リスクレベル絞り込み
   - ソート（公開日時・登録日時・タイトル）

5. **CSV エクスポート**
   - 検索結果をCSV形式でダウンロード
   - Excel / Google Sheets で分析可能

### CLI コマンド

```bash
# ユーザー管理
flask auth create-user <username> <password>
flask auth list-users

# AI推論を再実行
flask ai rerun --article-id <ID>

# CSV エクスポート
flask export-csv --output articles.csv
```

### API 利用

#### 認証

**Basic Auth**:
```bash
curl -u admin:password http://localhost:5000/api/articles
```

**Bearer Token**:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:5000/api/articles
```

**API Key Header**:
```bash
curl -H "X-API-Key: YOUR_TOKEN" \
     http://localhost:5000/api/articles
```

#### エンドポイント

**記事一覧取得**:
```bash
GET /api/articles?page=1&per_page=20&q=keyword&risk=high
```

**記事スクレイプ**:
```bash
POST /api/articles
Content-Type: application/json

{
  "url": "http://localhost:5000/virtual-news/article/1",
  "force": false,
  "run_ai": true
}
```

**メトリクス取得**:
```bash
GET /api/reports/summary
```

## 🧪 テスト

```bash
# 全テスト実行
pytest

# カバレッジ表示
pytest --cov=app --cov-report=term-missing

# Lint
ruff check .

# コード整形
black .
```

## 🐳 Dockerでの起動

### 開発環境

ホットリロード対応の開発環境を起動:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

アクセス先:
- アプリケーション: http://localhost:5000
- pgAdmin (DB管理): http://localhost:5050
- PostgreSQL: localhost:5433

### 本番環境

本番環境用の構成で起動:

```bash
# 環境変数を設定
cp .env.example .env
# .env を編集して必要な値を設定

# 起動
docker-compose up -d --build
```

アクセス先:
- アプリケーション: http://localhost:8080
- Nginx (リバースプロキシ): http://localhost:80

## 🚀 CI/CD

GitHub Actions による自動テスト・ビルド・デプロイパイプラインを構築済み:

- **テスト**: pytest + PostgreSQL サービスコンテナ
- **Lint**: ruff, black, isort によるコード品質チェック
- **ビルド**: Docker イメージを GitHub Container Registry にプッシュ
- **デプロイ**: main ブランチへのマージ時に自動デプロイ（要設定）

ワークフロー: `.github/workflows/ci-cd.yml`

## 📚 制作背景とアピールポイント

- **課題意識**: ニュース記事の氾濫によりリスク情報の見逃しが増えている。企業のリスク管理部門向けに即時判定可能なツールを想定。
- **工夫した点**: スクレイピングからAI推論までの一貫したエラーハンドリング、再実行性、キャッシュ戦略を丁寧に設計。
- **UI/UX**: ダッシュボードとログイン画面を含む全体をガラス感のあるデザインで統一。レスポンシブ対応済み。
- **品質確保**: pytestベースの自動テストとレートリミット・認証制御を導入し、実サービスでも安全に扱える構成。
- **拡張性**: 新しいニュースソース追加、Slack通知、BIツール連携などを容易に追加できる抽象化を実装。
- **安全性**: 実際の外部サイトをスクレイピングせず、仮想環境で技術を実証。

## 🗺️ 今後のロードマップ

- Slack / Teams 連携によるアラート配信
- 自動スクレイピングスケジューラ (Celery + Beat)
- リアルタイムダッシュボード (WebSocket/Server-Sent Events)
- マルチユーザー対応と権限管理
- Docker Compose + Terraform を使った IaC 化

## 📄 ライセンス

MIT License

---

質問や改善案があれば Issues や Pull Request で気軽に連絡してください。
