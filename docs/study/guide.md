# Scraper App コード解説ガイド

このドキュメントは、Scraper App の主要なコードを俯瞰しながら理解するためのハンズオンガイドです。ポートフォリオ閲覧者や学習者が短時間で全体像を掴めるよう、コンポーネントごとに読み方のポイントと確認すべき挙動を整理しました。

## 1. エントリーポイントとアプリケーション構成

| ファイル | 役割 | 読みどころ |
| --- | --- | --- |
| `app/__init__.py` | Flaskアプリの初期化 | Blueprint登録、DB初期化、レートリミット、テンプレート向けコンテキスト変数 |
| `run.py` / `app/main.py` | エントリーポイント | `create_app()` を呼び出し Gunicorn / Flask CLI から実行 |

まずは `app/__init__.py` を開き、以下の観点をチェックしましょう。

1. **設定注入**: `app.config.from_object(Config)` の仕組みと `.env` からの値の流れ。
2. **Blueprint構成**: `auth`, `main`, `api` の3層構造で、UI/API/ログインを分離。
3. **before_requestフック**: API向けレートリミットの実装を確認し、`_rate_limit_key()` がクライアントをどう識別しているか把握します。

## 2. 認証フロー

| ファイル | 役割 |
| --- | --- |
| `app/auth/routes.py` | ログイン・ログアウトのUI処理、セッション制御 |
| `app/auth/session_manager.py` | セッション変数の読取/書込をカプセル化 |
| `app/routes.py` | `requires_basic_auth` デコレータでブラウザアクセスとAPIアクセスを両立 |

読解ポイント:

- `_is_safe_redirect()` がリダイレクト先を検証してオープンリダイレクトを防いでいる点。
- `requires_basic_auth` がセッション・Basic認証・APIキーの3通りを順番にチェックする仕組み。
- テンプレート側では `is_authenticated` と `auth_username` が `app/__init__.py` の context processor により全ページで利用可能。

## 3. ドメインロジック層

| ディレクトリ | 主な責務 |
| --- | --- |
| `app/services/scraping.py` | リクエスト送信、リトライ戦略、allowed URL 判定 |
| `app/services/parsing.py` | HTMLから本文・タイトル・公開日時の抽出 |
| `app/services/ai.py` | OpenAI API への問い合わせ、例外クラス定義 |
| `app/services/analytics.py` | ダッシュボード用メトリクス集計 |

流れを追うには `app/routes.py` の `/scrape` ハンドラを起点に、サービス層の呼び出し順をトレースするのが効果的です。

1. `scraping.fetch()` が HTTP レスポンスを取得し、`parsing.parse_article()` が構造化データを返す。
2. DBに保存した後、`ai_service.summarize_and_score()` がリスクスコアを生成。
3. 結果を `InferenceResult` として保存し、最新状態は `Article.latest_inference` で参照。

## 4. モデルとデータベース

| モデル | 特徴 |
| --- | --- |
| `Article` | 記事本体。URLユニーク制約、公開日時・本文・作成日時を保持 |
| `InferenceResult` | AI推論結果。リスクスコアと要約、モデル名、生成日時 |

`Article.inferences` のリレーションと `latest_inference` プロパティの実装を把握すると、結果ページやダッシュボード表示の仕組みが理解しやすくなります。

## 5. テンプレートとUI

| テンプレート | 説明 |
| --- | --- |
| `app/templates/layout.html` | 共通レイアウト。トップバー、背景演出、フラッシュメッセージ |
| `app/templates/login.html` | ログイン画面。グラデーション背景とフォームバリデーション |
| `app/templates/index.html` | ダッシュボード。スクレイプフォーム、メトリクスカード、最新RSS、検索フォーム |
| `app/templates/result.html` | 記事詳細。AI要約とリスク履歴 |

読み方のコツ:

- `layout.html` で `block hero` を定義し、ログイン画面だけヒーローコンポーネントを差し替え。
- CSS (`app/static/styles.css`) はセクションごとにコメント不要なほど命名が明瞭。`.hero__inner--compact` や `.auth-card` など BEM ライクな名前に注目。

## 6. APIレイヤー

RESTエンドポイントは `app/routes.py` の `api_bp` Blueprint 内にあり、共通の `_article_select()` で検索条件を組み立てています。

- 認証: `requires_basic_auth` を共有。
- ページング: `db.paginate` を使用し、結果を JSON シリアライズ。
- AI実行制御: `POST /api/articles` の `run_ai` や `force_ai` パラメータに注目。

## 7. テスト戦略

| テスト | 目的 |
| --- | --- |
| `tests/test_routes.py` | UI向けルートの認証挙動、検索・ソート、スクレイピングフロー |
| `tests/test_api.py` | API認証、スクレイプとAI実行、レート制限 |
| その他 | 各サービスごとの単体テストやフィード取得テスト |

テストを読む際は、`conftest.py` のフィクスチャでアプリケーションコンテキストをセットアップし、Basic認証ヘッダーを注入している点を押さえてください。

## 8. 学習タスクリスト

1. `app/routes.py` を読み、Web UI と API のエントリーポイントを把握する。
2. スクレイプ実行 (`POST /scrape`) から結果表示 (`GET /result/<id>`) までの処理を時系列でメモにまとめる。
3. `tests/test_routes.py` を参照し、どのユースケースがテストされているか確認。自分ならどんなテストを追加するか考える。
4. `.env.example` を作成して、開発で必要な環境変数を整理する (演習タスク)。
5. README の「今後のロードマップ」から、実装してみたい項目を1つ選び、設計メモを作成する。

## 9. 参考リンク

- [Flask Application Factory パターン](https://flask.palletsprojects.com/en/latest/patterns/appfactories/)
- [SQLAlchemy ORM Tutorials](https://docs.sqlalchemy.org/en/20/orm/) (モデル定義とリレーションの理解に最適)
- [OpenAI API Docs](https://platform.openai.com/docs/introduction) (AIサービスの詳細)

---

このガイドを起点に、ソースコードを実際に追いながら学習を進めてください。理解が進んだら、`docs/study/handson.md` の演習にも挑戦してみましょう。
