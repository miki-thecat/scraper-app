"""ロギング設定モジュール"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from flask import Flask, g, has_request_context, request


def setup_logging(app: Flask) -> None:
    """アプリケーションのロギングを設定"""
    
    # ログレベル設定
    log_level = app.config.get("LOG_LEVEL", "INFO")
    
    # JSON形式のログフォーマッター
    if app.config.get("LOG_JSON", False):
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        )
    
    # ハンドラー設定
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    
    # Flaskアプリのロガー設定
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.propagate = False
    
    # リクエストID追加
    @app.before_request
    def add_request_id():
        """リクエストごとにユニークIDを付与"""
        import uuid
        g.request_id = str(uuid.uuid4())[:8]
    
    # リクエストログ
    @app.after_request
    def log_request(response):
        """リクエスト情報をログに記録"""
        if request.path == "/health":
            return response  # ヘルスチェックは除外
        
        extra = {
            "request_id": getattr(g, "request_id", "unknown"),
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "ip": request.remote_addr,
        }
        
        if response.status_code >= 400:
            app.logger.warning(
                f"{request.method} {request.path} - {response.status_code}",
                extra=extra
            )
        else:
            app.logger.info(
                f"{request.method} {request.path} - {response.status_code}",
                extra=extra
            )
        
        return response


class JsonFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式に変換"""
        import json
        
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # リクエストコンテキスト情報
        if has_request_context():
            log_data["request_id"] = getattr(g, "request_id", None)
            log_data["method"] = request.method
            log_data["path"] = request.path
            log_data["ip"] = request.remote_addr
        
        # カスタム属性を追加
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info"
            ]:
                log_data[key] = value
        
        # 例外情報
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)
