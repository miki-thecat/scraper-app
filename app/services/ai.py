from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from flask import current_app

try:  # pragma: no cover - ランタイムでのみ必要
    from openai import OpenAI
    from openai import APIStatusError
except Exception:  # pragma: no cover - optional dependency fallback
    OpenAI = None  # type: ignore
    APIStatusError = Exception  # type: ignore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AIResult:
    summary: str
    risk_score: int
    model: str
    prompt_version: str


class AIServiceUnavailable(RuntimeError):
    pass


def summarize_and_score(title: str, body: str) -> AIResult:
    if not current_app.config.get("ENABLE_AI", True):
        raise AIServiceUnavailable("AI機能は無効化されています。")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIServiceUnavailable("OpenAI APIキーが設定されていません。")

    if OpenAI is None:
        raise AIServiceUnavailable("openai パッケージが利用できません。")

    model = current_app.config["OPENAI_MODEL"]
    prompt_version = current_app.config.get("PROMPT_VERSION", "v1")

    system_prompt = (
        "あなたは日本語のニュース記事のリスク評価官です。\n"
        "出力は必ず JSON で返してください。\n"
        "評価軸：被害範囲・被害程度・社会的影響・死傷者/被害金額の大きさ。"
    )
    user_prompt = (
        "次の記事を要約し、1〜100 のリスクスコアを付与してください。\n"
        "スコアは高いほど高リスク。\n"
        'フィールド: {"summary": string, "risk_score": number(1-100)} のJSONのみ出力。\n'
        f"タイトル: {title}\n"
        "本文:\n"
        f"{body}"
    )

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
            timeout=current_app.config.get("OPENAI_TIMEOUT", 30),
        )
    except APIStatusError as exc:  # pragma: no cover - ネットワーク例外
        logger.exception("OpenAI API error: %s", exc)
        raise AIServiceUnavailable("OpenAI APIの呼び出しに失敗しました。") from exc

    result_text = _extract_text(response)

    try:
        payload: dict[str, Any] = json.loads(result_text)
    except json.JSONDecodeError as exc:
        logger.exception("AI応答のJSON変換に失敗: %s", exc)
        raise AIServiceUnavailable("AI応答の解析に失敗しました。") from exc

    summary = payload.get("summary")
    risk_score = payload.get("risk_score")

    if not isinstance(summary, str) or not isinstance(risk_score, (int, float)):
        raise AIServiceUnavailable("AI応答のフォーマットが不正です。")

    risk_score_int = int(risk_score)
    risk_score_int = max(1, min(100, risk_score_int))

    return AIResult(
        summary=summary.strip(),
        risk_score=risk_score_int,
        model=model,
        prompt_version=prompt_version,
    )


def _extract_text(response: Any) -> str:
    """OpenAI ChatCompletion レスポンスからテキストを抽出"""
    if hasattr(response, "choices") and len(response.choices) > 0:
        message = response.choices[0].message
        if hasattr(message, "content"):
            return message.content
    raise AIServiceUnavailable("AI応答フォーマットを解釈できませんでした。")
