"""CSRF保護のテスト"""
from types import SimpleNamespace
import re


from app.auth import session_manager


_TOKEN_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')
_META_TOKEN_RE = re.compile(r'<meta name="csrf-token" content="([^"]+)"')


def _set_logged_in(client) -> None:
    with client.session_transaction() as sess:
        sess[session_manager._SESSION_AUTH_FLAG] = True  # type: ignore[attr-defined]
        sess[session_manager._SESSION_USERNAME] = "test"  # type: ignore[attr-defined]


def _extract_csrf_token(response_text: str) -> str:
    match = _TOKEN_RE.search(response_text)
    if match:
        return match.group(1)
    meta = _META_TOKEN_RE.search(response_text)
    assert meta is not None
    return meta.group(1)


class TestCSRFProtection:
    """CSRF保護機能のテストスイート"""

    def test_scrape_without_csrf_token_returns_400(self, client):
        """CSRFトークンなしでPOSTすると400エラー"""
        response = client.post(
            "/scrape",
            data={
                "url": "https://news.yahoo.co.jp/articles/test123",
            },
        )
        assert response.status_code == 400

    def test_scrape_with_invalid_csrf_token_returns_400(self, client):
        """間違ったCSRFトークンでPOSTすると400エラー"""
        response = client.post(
            "/scrape",
            data={
                "url": "https://news.yahoo.co.jp/articles/test123",
                "csrf_token": "invalid-token-value",
            },
        )
        assert response.status_code == 400

    def test_scrape_with_valid_csrf_token_succeeds(self, client, mocker):
        """正しいCSRFトークンがあれば成功"""
        mocker.patch(
            "app.services.articles.ingest_article",
            return_value=SimpleNamespace(
                article=SimpleNamespace(id="123e4567-e89b-12d3-a456-426614174000"),
                status="created",
                ai_error=None,
            ),
        )

        with client:
            _set_logged_in(client)
            response = client.get("/")
            assert response.status_code == 200

            csrf_token = _extract_csrf_token(response.get_data(as_text=True))

            response = client.post(
                "/scrape",
                data={
                    "url": "https://news.yahoo.co.jp/articles/test123",
                    "csrf_token": csrf_token,
                },
            )

            assert response.status_code == 302

    def test_login_without_csrf_token_returns_400(self, client):
        """ログインフォームでもCSRF保護が有効"""
        response = client.post(
            "/login",
            data={
                "username": "test",
                "password": "test",
            },
        )
        assert response.status_code == 400

    def test_login_with_valid_csrf_token_succeeds(self, client):
        """正しいCSRFトークンでログイン成功"""
        with client:
            response = client.get("/login")
            assert response.status_code == 200

            csrf_token = _extract_csrf_token(response.get_data(as_text=True))

            response = client.post(
                "/login",
                data={
                    "username": "test",
                    "password": "test",
                    "csrf_token": csrf_token,
                },
            )

            assert response.status_code == 302

    def test_logout_without_csrf_token_returns_400(self, client):
        """ログアウトでもCSRF保護が有効"""
        _set_logged_in(client)

        response = client.post("/logout")
        assert response.status_code == 400

    def test_get_request_not_protected_by_csrf(self, client):
        """GETリクエストはCSRF保護の対象外"""
        _set_logged_in(client)

        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/login")
        assert response.status_code in [200, 302]

    def test_csrf_token_in_meta_tag(self, client):
        """layout.htmlにCSRFトークンがmeta tagとして埋め込まれている"""
        _set_logged_in(client)

        response = client.get("/")
        assert response.status_code == 200
        assert b'name="csrf-token"' in response.data

    def test_csrf_error_handler_returns_custom_message(self, client):
        """CSRFエラー時にカスタムエラーメッセージを返す"""
        response = client.post(
            "/scrape",
            data={
                "url": "https://news.yahoo.co.jp/articles/test123",
            },
        )
        assert response.status_code == 400
        json_data = response.get_json()
        assert json_data is not None
        assert "error" in json_data
        assert "セキュリティ" in json_data["error"]
