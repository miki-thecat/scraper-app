# Scraper App

Yahoo!ニュース記事をスクレイピングし、AIがリスク判定と要約を行うモダンなダッシュボードアプリです。Flask + SQLAlchemy を中心に、RSS取得、記事スクレイピング、AI推論、リスク分析まで一連のワークフローを自動化します。ポートフォリオとして提示しやすいよう、UI/UX・ドキュメント・テストを含めて総合的に仕上げています。

![スクリーンショット](docs/images/design.webp)

## ハイライト

- モダンなログイン体験：セッションベースのログイン画面を新設し、ダッシュボード利用とAPI利用の両方に対応。
- AI連携済み：スクレイピング直後に OpenAI API で要約とリスクスコアを取得。履歴管理にも対応。
- 豊富な可視化：ダッシュボードで記事数、平均リスク、分布、最新RSSなどを直感的に確認。
- API & CLI：Web UI に加え、REST API と管理 CLI を用意。自動化パイプラインに組み込み可能。
- 充実したテスト：主要ユースケースを `pytest` でカバーし、回帰を防止。
- デプロイ想定：AWS EC2 + CodeBuild + systemd を例に構成ファイルを同梱。

## 技術スタック

- **Backend**: Flask, SQLAlchemy, Alembic (DB初期化), Celery (オプション)
- **Frontend**: Jinja2 Templates, Vanilla CSS (グラデーション / Glassmorphism), 少量の HTMX/JS (必要箇所のみ)
- **AI / Data**: OpenAI API, カスタムリスク分類ロジック, ML再学習スクリプト
- **Infra**: SQLite / PostgreSQL, Gunicorn, Nginx, AWS (想定), Docker (オプション)
- **Tooling**: pytest, coverage, black/ruff (導入想定), GitHub Actions (CI想定)

## プロジェクト構造

```text
app/
  auth/               # ログインや認証周りのBlueprint
  models/             # SQLAlchemyモデルとDB初期化
  services/           # スクレイピング・AI・ニュースフィードなどのドメインロジック
  templates/          # Jinja2テンプレート（ログイン・ダッシュボード等）
  static/             # CSSや画像などのスタティックアセット
cli/                  # 追加CLIコマンド
deploy/               # 本番デプロイ用スクリプト・設定
docs/                 # ポートフォリオ資料・スクリーンショット
ml/                   # 学習/評価スクリプトとサンプルデータ
tests/                # pytestベースの自動テスト
```

## クイックスタート

### 1. 前提条件

- Python 3.11 以上
- OpenAI APIキー (AI機能を利用する場合)
- SQLite でも動作しますが、PostgreSQL を推奨

### 2. セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` に下記必須項目を設定してください。

```
FLASK_ENV=development
DATABASE_URL=sqlite:///local.db
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=change_me
OPENAI_API_KEY=sk-...
```

### 3. 初期化

```bash
flask --app app.main db upgrade   # 初回のみ
flask --app app.main seed sample  # サンプルデータ投入 (任意)
```

### 4. 開発サーバー起動

```bash
flask --app app.main run
# or
make dev
```

ブラウザで `http://localhost:5000` を開き、先ほど設定した認証情報でログインします。

### 5. テストと品質チェック

```bash
pytest
pytest --cov=app --cov-report=term-missing   # カバレッジ表示
ruff check .                                  # Lint (導入済みの場合)
black .                                      # 整形 (導入済みの場合)
```

## 主要機能とワークフロー

1. **記事取得**: Yahoo!ニュースのRSSから最新記事を提示。URL入力でもスクレイプ可能。
2. **スクレイピング**: 記事本文・公開日時・サマリー候補を抽出。失敗時はユーザーに通知。
3. **AI推論**: OpenAI API (モデル指定可) で要約とリスクスコアを生成。履歴として保存。
4. **リスク可視化**: 平均スコアや高リスク記事、リスク分布をダッシュボード表示。
5. **検索・フィルタリング**: キーワード検索、期間指定、リスク帯選択、ソートが可能。
6. **エクスポート**: CSV書き出し機能で分析ツールに持ち込み。
7. **API連携**: `/api/articles` などのREST APIで自動化や外部連携が可能。

## 認証とセキュリティ

- ブラウザアクセス: セッションベースのログインフォーム。
- APIアクセス: Basic認証または Bearer トークン (`API_ACCESS_TOKENS`)。
- レート制限: API Blueprint に対して `RATE_LIMIT_PER_MINUTE` で制御。
- セキュリティヘッダーやHTTPS終端はNginxなどリバースプロキシ側で設定を想定。

## API リファレンス

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/api/articles` | 記事一覧 (検索/期間/リスク絞り込み、ページング対応) |
| GET | `/api/articles/<article_id>` | 記事詳細 |
| POST | `/api/articles` | スクレイピング実行と記事作成 (`force`, `run_ai`, `force_ai` オプション) |
| GET | `/api/reports/summary` | リスク分布など集計情報 |

### リクエスト例

```bash
curl -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"url": "https://news.yahoo.co.jp/articles/example", "force_ai": true}' \
  http://localhost:5000/api/articles

curl -H "Authorization: Bearer my-token" \
  http://localhost:5000/api/articles
```

## CLIユーティリティ

```bash
flask --app app.main scrape feed   # RSSで最新記事をまとめて取得
flask --app app.main ai rerun      # 古い記事に対してAIを再実行
flask --app app.main export csv    # 分析用CSVエクスポート
```

詳細は `cli/` ディレクトリの実装や `flask --app app.main --help` を参照してください。

## MLワークフロー

`ml/` ディレクトリに学習・評価スクリプトとサンプルデータが同梱されています。自前データで再学習する場合は以下を参考にしてください。

```bash
python ml/train.py --train ml/data/train.csv --valid ml/data/valid.csv
python ml/evaluate.py --valid ml/data/valid.csv
```

モデルのハイパーパラメータや特徴量設計を調整し、`app/services/ai.py` から呼び出す推論ロジックを差し替えることで、独自のリスクスコアリングに対応できます。

## デプロイガイド

- `deploy/nginx.conf`: リバースプロキシ設定例
- `deploy/scraper-app.service`: systemd ユニット (Gunicornを想定)
- `deploy/buildspec.yml`: AWS CodeBuild 用設定
- `deploy/deploy.sh`: build artifact を EC2 に配布し、サービス再起動まで自動化

Dockerでの動作を想定する場合は以下のような `Dockerfile`/`docker-compose.yml` を用意するとスムーズです。

```bash
docker-compose up --build
```

## 制作背景とアピールポイント

- **課題意識**: ニュース記事の氾濫によりリスク情報の見逃しが増えている。企業のリスク管理部門向けに即時判定可能なツールを想定。
- **工夫した点**: スクレイピングからAI推論までの一貫したエラーハンドリング、再実行性、キャッシュ戦略を丁寧に設計。
- **UI/UX**: ダッシュボードとログイン画面を含む全体をガラス感のあるデザインで統一。レスポンシブ対応済み。
- **品質確保**: pytestベースの自動テストとレートリミット・認証制御を導入し、実サービスでも安全に扱える構成。
- **拡張性**: RSS以外のソース追加、Slack通知、BIツール連携などを容易に追加できる抽象化を実装。

## 今後のロードマップ

- Slack / Teams 連携によるアラート配信
- 自動スクレイピングスケジューラ (Celery + Beat)
- リアルタイムダッシュボード (WebSocket/Server-Sent Events)
- マルチユーザー対応と権限管理
- Docker Compose + Terraform を使った IaC 化

## ライセンス

MIT License

---

質問や改善案があれば Issues や Pull Request で気軽に連絡してください。
