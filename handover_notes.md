# Codex CLIへの引き継ぎノート

## 1. プロジェクトの概要

このプロジェクトは、Webスクレイピング機能を持つFlaskアプリケーションです。最近、アプリケーションの安定性とテスト容易性を向上させるため、「アプリケーションファクトリ」パターンにリファクタリングされました。

## 2. 現在の状況

*   **アプリケーション構造:**
    *   `scraper/` パッケージ内に主要なロジックが分割されています (`__init__.py`, `routes.py`, `models.py`, `scraper.py`)。
    *   `run.py` がアプリケーションのエントリーポイントです。
    *   `config.py` で設定が管理されています。
*   **テスト環境:**
    *   `pytest` を使用したテスト環境が構築されています。
    *   `requirements.txt` に `pytest` および `pytest-mock` が追加されています。
    *   `test_app.py` には以下のテストケースが含まれています:
        *   トップページの表示テスト (`test_index_page`)
        *   スクレイピング機能のテスト (`test_scrape_success`, `test_scrape_auth_failure`, `test_scrape_no_url`)
*   **現在の問題点:**
    *   `test_scrape_success` と `test_scrape_no_url` の2つのテストが `401 Unauthorized` エラーで失敗しています。
    *   これは、`scraper/routes.py` 内の `check_auth` 関数が、テスト実行時に設定される認証情報 (`test:test`) を正しく参照できていないことが原因です。

## 3. 次のステップ (Codex CLIへの依頼事項)

Codex CLIは、以下の手順で作業を引き継いでください。

1.  **`scraper/routes.py` の `check_auth` 関数の修正:**
    *   `check_auth` 関数内で、`BASIC_AUTH_USERNAME` と `BASIC_AUTH_PASSWORD` を `os.getenv` から取得している箇所を、`current_app.config` から取得するように修正してください。
    *   **修正対象ファイル:** `/workspaces/scraper-app/scraper/routes.py`
    *   **修正箇所:** `check_auth` 関数内の `user_ok` と `pass_ok` の定義行。
    *   **現在のコード:**
        ```python
                user_ok = compare_digest(username, os.getenv("BASIC_AUTH_USERNAME", "admin"))
                pass_ok = compare_digest(password, os.getenv("BASIC_AUTH_PASSWORD", "password"))
        ```
    *   **修正後のコード (例):**
        ```python
                user_ok = compare_digest(username, current_app.config["BASIC_AUTH_USERNAME"])
                pass_ok = compare_digest(password, current_app.config["BASIC_AUTH_PASSWORD"])
        ```
    *   **注意点:** `current_app` を使用するため、`from flask import ...` のインポート文に `current_app` が含まれていることを確認してください。

2.  **テストの再実行:**
    *   上記の修正後、プロジェクトのルートディレクトリで以下のコマンドを実行し、すべてのテストがパスすることを確認してください。
        ```bash
        pytest
        ```

3.  **Gitコミット:**
    *   すべてのテストがパスしたら、ここまでの変更をGitにコミットしてください。
    *   **コミットメッセージの提案:** `テスト: スクレイピング機能のテストを修正し、認証問題を解決`

---
以上で引き継ぎは完了です。Codex CLIの成功を祈ります。
