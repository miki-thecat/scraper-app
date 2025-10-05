スクレイピング & AI要約/リスク評価 Webアプリ 仕様書
0. ゴール

課題①：URL入力→Yahooニュース記事の タイトル/日時/本文 を取得し、テーブル表示（BASIC認証つき/EC2+RDS）。

課題②：上記に リスクスコア(1–100) と 要約 をAIで付与し表示。

課題③：CLIで「企業概要文→業界分類（教師ありML, 正答率≥70%）」。

課題④：①②のビルド/デプロイを AWS CodeBuild で自動化。

1. システム構成（AWS）
1.1 アーキテクチャ

EC2 (Amazon Linux 2)：Flask + Gunicorn + Nginx（BASIC認証はNginx）。

RDS (PostgreSQL)：記事/推論結果保存。

VPC：EC2とRDSは同一VPC/サブネット。RDSはパブリック非公開、EC2 SG からのみ許可。

IAM：EC2用ロール（CloudWatch Logs、必要ならSSM）。

CloudWatch：アプリ/OSログ、メトリクス監視（請求もBudgetでアラート）。

Budget：月額 ¥上限 を超えそうならメール通知。

CodeBuild（課題④）：buildspec に沿ってテスト→Dockerイメージ作成→EC2へデプロイ（SCP/SSM or ECR+pull どちらでも可）。

1.2 コスト/無料枠対策

t3.micro（無料枠相当、低負荷で十分）。

RDS：db.t3.micro、ストレージ最小、停止スケジュール（夜間停止可）。

CloudWatch ログ保持 ≤ 7〜14日。

Budget アラート：50%/80%/100%。

2. リポジトリ構成
repo-root/
├─ app/
│  ├─ __init__.py
│  ├─ main.py                 # Flaskエントリ
│  ├─ routes.py               # 画面とAPI
│  ├─ services/
│  │   ├─ scraping.py         # Yahooニューススクレイピング
│  │   ├─ parsing.py          # HTML/JSON-LDパース
│  │   ├─ ai.py               # 要約/リスクスコア(OpenAI)
│  ├─ models/
│  │   ├─ db.py               # SQLAlchemy初期化
│  │   └─ article.py          # Article, InferenceResult
│  ├─ templates/
│  │   ├─ layout.html
│  │   └─ index.html          # 課題①UI
│  │   └─ result.html         # 課題②UI
│  ├─ static/
│  │   └─ styles.css
│  └─ auth/
│      └─ basic_auth_nopass.py # (開発時Flask BasicAuth, 本番はNginx)
├─ cli/
│  └─ classify_industry.py    # 課題③ CLI
├─ ml/
│  ├─ train.py                # 教師あり学習
│  ├─ evaluate.py             # 精度検証（≥70%）
│  ├─ vectorizer.joblib
│  └─ model.joblib
├─ tests/
│  ├─ test_scraping.py
│  ├─ test_parsing.py
│  ├─ test_ai.py
│  └─ test_ml.py
├─ deploy/
│  ├─ nginx.conf              # Basic認証+リバースプロキシ
│  ├─ htpasswd                # BASICユーザ（本番はSSMで配布 or EC2で生成）
│  ├─ systemd/
│  │   └─ app.service
│  └─ buildspec.yml           # 課題④ CodeBuild
├─ Dockerfile
├─ docker-compose.yml         # ローカル開発用
├─ requirements.txt
├─ .env.example
└─ docs/
   └─ spec.md                 # この仕様書

3. 画面/UI 仕様
3.1 共通

上部：タイトル「スクレイピングアプリケーション」。

中央：URL入力 + 「実行」ボタン。

下部：結果テーブル。

3.2 課題①（表示列）

タイトル｜日時｜本文（複数段落）

3.3 課題②（表示列）

タイトル｜リスクスコア｜要約｜本文

画像サンプルのレイアウトを踏襲。文字は折返し、セルは可変高さ。
初回ロード時は空テーブル、送信後リダイレクトで結果ページをレンダリング。

4. API / ルーティング

GET / … 入力フォーム表示

POST /scrape … フォーム受付（URLバリデーション→スクレイプ→保存→/result/<id>にリダイレクト）

GET /result/<article_id> … 課題①結果

GET /result_ai/<article_id> … 課題②結果（要約/リスク付き）

GET /healthz … LB/監視用

バリデーション

入力URLは https://news.yahoo.co.jp/articles/2fa8217e648db1410fbe27f3de9aa016d76be336 を prefix として許可（課題②は事故欄URLもOK）。

タイムアウト 10s、リトライ 2、User-Agent 明示、Robotsの遵守（私的・閉域/認証つきで利用）。

5. データモデル（PostgreSQL, SQLAlchemy）
5.1 テーブル

articles

id (PK, uuid)

url (unique)

title (text, index)

published_at (timestamp with time zone, nullable)

body (text) … 段落は \n\n 区切り

created_at (timestamptz, default now)

inference_results

id (PK, uuid)

article_id (FK→articles.id, index, unique) … 1記事につき1件

risk_score (int, 1–100)

summary (text)

model (varchar) … 使用したAIモデル名

prompt_version (varchar) … 後述のプロンプトバージョン

created_at (timestamptz, default now)

6. スクレイピング仕様
6.1 取得対象（Yahooニュースニュース記事）

タイトル：<title> もしくは OGP meta[property="og:title"]。

日時：構造化データ（application/ld+json の datePublished）優先。なければ記事内の timeタグや meta[name="pubdate"] を検索。

本文：記事本文DOM（見出し/リード除く）。段落 <p> のテキストを順番に結合。

堅牢性：

JSON-LD 最優先（構造変化に強い）。

BeautifulSoup で複数候補セレクタを順次試行。

文字化け対策：response.encoding = response.apparent_encoding。

6.2 実装方針

ライブラリ：requests, beautifulsoup4, lxml, dateutil.

タイムアウト/リトライ、429/5xxは指数バックオフ。

失敗時はユーザに「取得できませんでした（原因：…）」を表示し、サーバにはスタックトレースを残す。

7. AI（要約/リスクスコア）仕様（課題②）
7.1 入出力

入力：タイトル、本文（最大 ~4,000文字程度に整形）。

出力：

summary：日本語で3–5文、固有名詞・数値は保持。

risk_score：1–100 の整数（被害範囲/被害程度/社会的影響/死傷者・金額を考慮）。

7.2 推論フロー

サーバ側でプロンプトを作成（system + user）。

Chat Completions を呼ぶ（温度低め、再現性重視）。

risk_score は JSONで返すように指示（パース容易化）。

結果を inference_results に保存。

7.3 例：プロンプト（要約・スコア同時）

system

あなたは日本語のニュース記事のリスク評価官です。
出力は必ず JSON で返してください。
評価軸：被害範囲・被害程度・社会的影響・死傷者/被害金額の大きさ。


user

次の記事を要約し、1〜100 のリスクスコアを付与してください。
スコアは高いほど高リスク。
フィールド: {"summary": string, "risk_score": number(1-100)} のJSONのみ出力。

タイトル: {title}
本文:
{body_truncated}


注：モデル名は環境変数で切替（例：OPENAI_MODEL=gpt-4o-mini など）。料金はダッシュボードで管理。

8. セキュリティ（BASIC認証）
8.1 本番（Nginx）

nginx.conf で auth_basic "Restricted"; + auth_basic_user_file /etc/nginx/.htpasswd;

htpasswd は EC2 内で生成（sudo htpasswd -c /etc/nginx/.htpasswd user）。

すべてのパス（/ 以下）に適用。

8.2 開発（任意）

Flask の簡易 BasicAuth をミドルウェアで。

9. 環境変数（.env）
# Flask
FLASK_ENV=production
SECRET_KEY=change_me

# DB (RDS)
DATABASE_URL=postgresql+psycopg2://username:password@host:5432/dbname

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT=30

# App
REQUEST_TIMEOUT=10
PROMPT_VERSION=v1

10. 例外・ログ

例外は app.logger.exception で CloudWatch に送る。

重要イベント（スクレイプ成功/失敗、AI呼び出し、課題③推論）は INFO ログ。

PII なし。本文はDB保存のみ、ログへ全文は出さない。

11. テスト計画
11.1 ユニット

test_parsing.py：サンプルHTML/JSON-LDからタイトル・日時・本文を正しく抽出。

test_scraping.py：モックHTTPでタイムアウト/429/5xx/文字コードを網羅。

test_ai.py：AI応答のJSONスキーマ検証（モックに差し替え）。

test_ml.py：学習→検証データで精度算出（≥70%）。

11.2 E2E（手動）

実URLを入力→表に表示（①）。

事故欄の記事→要約/リスク表示（②）。

BASIC認証が必須（未認証は401）。

DBへ重複URL再入力時は再スクレイプせず既存データを表示（キャッシュ戦略）。

12. 課題③（教師あり学習：業界分類）
12.1 データ

指定スプレッドシートをCSVでダウンロードし ml/data/{train.csv, valid.csv} に置く。

12.2 前処理

文字正規化（全角半角/記号/改行統一）。

日本語トークン化はコストを抑え、TF-IDF (char-gram: 2–5) を基本。

学習：線形分類（LogisticRegression） または LinearSVC をまず採用。

ハイパラ：GridSearchCV でCなど少数パラメタを探索（時短）。

12.3 評価

evaluate.py で validation を読み、正答率 ≥ 0.70 を assert。

混同行列/上位誤分類例をログ出力。

12.4 CLI
$ python cli/classify_industry.py
> 概要文を入力してください:
...（入力）
=> 予測業界: 〇〇〇（確信度: 0.82）

13. デプロイ/運用
13.1 EC2 セットアップ（最小）

ユーザデータで Docker / git / nginx / certbot を導入（httpsのみは任意）。

docker-compose で web(Flask+Gunicorn) + nginx を起動。

.env と htpasswd は SSM Parameter Store か EC2 に直接配置。

13.2 RDS

パラメータグループ（タイムゾーン Asia/Tokyo）。

パブリック非公開。EC2 SG のみ許可。

自動バックアップON、メンテ窓は深夜。

14. CodeBuild（課題④）
14.1 deploy/buildspec.yml（例：EC2へSCPデプロイ）
version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
    commands:
      - pip install -r requirements.txt
      - pip install pytest
  pre_build:
    commands:
      - pytest -q
  build:
    commands:
      - echo "Build step (optionally build docker image)"
  post_build:
    commands:
      - echo "Deploy to EC2 via SSM or SCP"
      # 例: SSMを使う場合、aws ssm send-command ... で git pull & docker compose up -d を実行
artifacts:
  files:
    - deploy/nginx.conf
    - deploy/buildspec.yml
    - app/**/*
    - ml/**/*
    - cli/**/*


ECR を使う場合はここで docker build→docker push→EC2 側 docker pull。

15. 主要ファイルの実装指針（要点）
15.1 app/services/scraping.py

fetch(url) -> str：HTTP GET（UA, timeout, retries）。

is_allowed(url)：Yahooニュースニュース記事URLのみ True。

失敗時は ScrapeError 例外。

15.2 app/services/parsing.py

parse_article(html) -> ParsedArticle(title, published_at, body)

JSON-LD > OGP/meta > DOM の順でフォールバック。

published_at はUTCに正規化（DBはtimestamptz）。

15.3 app/services/ai.py

summarize_and_score(title, body) -> {summary, risk_score, model, prompt_version}

OpenAI SDK 呼び出しラッパ。

JSON strict モード（例外時は再試行）。

15.4 app/routes.py

/scrape：URL受領→存在すれば既存記事ID、なければ取得→保存→（課題②なら AI 推論）→リダイレクト。

テンプレートへ article & inference を渡す。

16. AI駆動開発（Codex等）運用ガイド
16.1 コード生成プロンプト雛形

目的・制約・出力フォーマット・完成定義 を毎回明示

目的: Flask + SQLAlchemy で「/scrape」POSTハンドラを実装する。
制約:
- 入力は news URL のみ、`services.scraping.is_allowed()` で検証。
- 既存URLならDB再利用。なければ requests+bs4 で取得、parsing.parse_article()で抽出する。
- 成功時は記事IDへリダイレクト。
出力: 変更差分の完全なコード。既存importを壊さない。pytestが通ること。
完成定義:
- tests/test_scraping.py と test_parsing.py が green。
- mypy/pylintの警告を追加しない。

16.2 AIにやらせるタスク分解（推奨順）

ルーティング骨格 → 2) パーサ関数 → 3) DBモデル → 4) OpenAIラッパ → 5) テンプレ → 6) 例外/ロギング → 7) テスト → 8) CodeBuild用ファイル。

16.3 レビュー・再生成ループ

生成→pytest→失敗箇所だけをプロンプトに貼る→原因/修正案を要求→再生成。

大きな変更はブランチを切る（例：feature/ai-summary）。

17. 受け入れ基準（Definition of Done）
課題①

指定URLで タイトル/日時/本文 が表示される。

BASIC認証が有効（未認証は401）。

RDS保存と重複URLの再利用が機能。

課題②

事故記事URLで リスクスコア(1–100) と 要約 が表示。

AI失敗時はユーザ向けの丁寧なメッセージ＋ログ。

課題③

python cli/classify_industry.py 実行で業界推定。

evaluate.py の accuracy ≥ 0.70。

課題④

CodeBuild で pytest 実行→成功→デプロイジョブ実行。

buildspec.yml と スクレイピングコードを提出。

18. 提出物チェックリスト

 アプリURL（BASIC認証つき）

 BASIC：ユーザ/パス

 GitHub Private リポジトリURL（招待先3名）

 課題③ ソース & モデル(joblib)

 deploy/buildspec.yml と主要コード

 README：セットアップ・環境変数・デプロイ手順
