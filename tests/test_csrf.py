"""CSRF保護のテスト"""
import pytest


class TestCSRFProtection:
    """CSRF保護機能のテストスイート"""

    def test_scrape_without_csrf_token_returns_400(self, client):
        """CSRFトークンなしでPOSTすると400エラー"""
        response = client.post('/scrape', data={
            'url': 'https://news.yahoo.co.jp/articles/test123'
        })
        assert response.status_code == 400

    def test_scrape_with_invalid_csrf_token_returns_400(self, client):
        """間違ったCSRFトークンでPOSTすると400エラー"""
        response = client.post('/scrape', data={
            'url': 'https://news.yahoo.co.jp/articles/test123',
            'csrf_token': 'invalid-token-value'
        })
        assert response.status_code == 400

    def test_scrape_with_valid_csrf_token_succeeds(self, client, mocker):
        """正しいCSRFトークンがあれば成功"""
        # スクレイピング関数をモック
        mock_scrape = mocker.patch('app.services.scraping.scrape_and_save')
        mock_article = mocker.Mock()
        mock_article.id = '123e4567-e89b-12d3-a456-426614174000'
        mock_scrape.return_value = mock_article

        with client:
            # Step 1: GETでページを取得してトークン生成（ログイン済み）
            with client.session_transaction() as sess:
                sess['username'] = 'test'
            
            response = client.get('/')
            assert response.status_code == 200

            # セッションからトークン取得
            with client.session_transaction() as sess:
                csrf_token = sess.get('csrf_token')

            assert csrf_token is not None

            # Step 2: トークン付きでPOST
            response = client.post('/scrape', data={
                'url': 'https://news.yahoo.co.jp/articles/test123',
                'csrf_token': csrf_token
            })

            # リダイレクト
            assert response.status_code == 302

    def test_login_without_csrf_token_returns_400(self, client):
        """ログインフォームでもCSRF保護が有効"""
        response = client.post('/login', data={
            'username': 'test',
            'password': 'test'
        })
        assert response.status_code == 400

    def test_login_with_valid_csrf_token_succeeds(self, client):
        """正しいCSRFトークンでログイン成功"""
        with client:
            # Step 1: ログインページ取得
            response = client.get('/login')
            assert response.status_code == 200

            # セッションからトークン取得
            with client.session_transaction() as sess:
                csrf_token = sess.get('csrf_token')

            assert csrf_token is not None

            # Step 2: トークン付きでログイン
            response = client.post('/login', data={
                'username': 'test',
                'password': 'test',
                'csrf_token': csrf_token
            })

            # リダイレクト（ログイン成功）
            assert response.status_code == 302

    def test_logout_without_csrf_token_returns_400(self, client):
        """ログアウトでもCSRF保護が有効"""
        # ログイン
        with client.session_transaction() as sess:
            sess['username'] = 'test'

        # CSRFトークンなしでログアウト試行
        response = client.post('/logout')
        assert response.status_code == 400

    def test_get_request_not_protected_by_csrf(self, client):
        """GETリクエストはCSRF保護の対象外"""
        # ログイン状態で
        with client.session_transaction() as sess:
            sess['username'] = 'test'
            
        response = client.get('/')
        assert response.status_code == 200

        response = client.get('/login')
        # ログイン済みの場合リダイレクトされる可能性がある
        assert response.status_code in [200, 302]

    def test_csrf_token_in_meta_tag(self, client):
        """layout.htmlにCSRFトークンがmeta tagとして埋め込まれている"""
        # ログイン状態で
        with client.session_transaction() as sess:
            sess['username'] = 'test'
            
        response = client.get('/')
        assert response.status_code == 200
        assert b'name="csrf-token"' in response.data

    def test_csrf_error_handler_returns_custom_message(self, client):
        """CSRFエラー時にカスタムエラーメッセージを返す"""
        response = client.post('/scrape', data={
            'url': 'https://news.yahoo.co.jp/articles/test123'
        })
        assert response.status_code == 400
        # JSONレスポンスの確認
        json_data = response.get_json()
        assert json_data is not None
        assert 'error' in json_data
        assert 'セキュリティ' in json_data['error']
