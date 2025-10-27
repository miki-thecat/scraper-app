"""セキュリティヘッダーのテスト"""
from __future__ import annotations


def test_security_headers_present(client):
    """セキュリティヘッダーが設定されていることを確認"""
    resp = client.get("/health")

    # Content Security Policy
    assert "Content-Security-Policy" in resp.headers
    assert "default-src 'self'" in resp.headers["Content-Security-Policy"]

    # X-Frame-Options
    assert resp.headers.get("X-Frame-Options") == "DENY"

    # X-Content-Type-Options
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    # X-XSS-Protection
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"

    # Referrer-Policy
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    # Permissions-Policy
    assert "Permissions-Policy" in resp.headers


def test_hsts_header_in_production(app, client):
    """本番環境でHSTSヘッダーが設定されることを確認"""
    app.config["FLASK_ENV"] = "production"

    resp = client.get("/health")

    assert "Strict-Transport-Security" in resp.headers
    assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]
    assert "includeSubDomains" in resp.headers["Strict-Transport-Security"]


def test_hsts_header_not_in_development(client):
    """開発環境でHSTSヘッダーが設定されないことを確認"""
    resp = client.get("/health")

    # テスト環境ではHSTSは設定されない
    assert "Strict-Transport-Security" not in resp.headers
