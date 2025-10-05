from __future__ import annotations

import io

import numpy as np

from cli import classify_industry


def test_load_artifacts_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(classify_industry, "VECTOR_PATH", tmp_path / "vec.joblib")
    monkeypatch.setattr(classify_industry, "MODEL_PATH", tmp_path / "model.joblib")

    try:
        classify_industry.load_artifacts()
    except FileNotFoundError:
        return
    raise AssertionError("Expected FileNotFoundError when artifacts are missing")


def test_main_predicts_and_prints(monkeypatch, capsys):
    class DummyVectorizer:
        def transform(self, texts):
            return np.array(texts)

    class DummyModel:
        def predict(self, features):
            return np.array(["IT" for _ in features])

        def predict_proba(self, features):
            return np.array([[0.9, 0.1] for _ in features])

    monkeypatch.setattr(
        classify_industry,
        "load_artifacts",
        lambda: (DummyVectorizer(), DummyModel()),
    )

    monkeypatch.setattr(classify_industry.sys, "stdin", io.StringIO("クラウドサービス概要"))

    exit_code = classify_industry.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "予測業界: IT" in captured.out
    assert "0.90" in captured.out
