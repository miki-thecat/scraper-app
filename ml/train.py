from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TRAIN = BASE_DIR / "data" / "train.csv"
DEFAULT_VALID = BASE_DIR / "data" / "valid.csv"
VECTORIZER_PATH = BASE_DIR / "vectorizer.joblib"
MODEL_PATH = BASE_DIR / "model.joblib"


def load_dataset(path: Path) -> tuple[pd.Series, pd.Series]:
    df = pd.read_csv(path)
    if not {"text", "label"}.issubset(df.columns):
        raise ValueError("CSVにはtext列とlabel列が必要です。")
    return df["text"].astype(str), df["label"].astype(str)


def build_pipeline() -> Pipeline:
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=2)
    classifier = LogisticRegression(max_iter=1000, solver="lbfgs")
    pipeline = Pipeline([
        ("vectorizer", vectorizer),
        ("classifier", classifier),
    ])
    return pipeline


def train(train_csv: Path, valid_csv: Path) -> None:
    X_train, y_train = load_dataset(train_csv)
    X_valid, y_valid = load_dataset(valid_csv)

    pipeline = build_pipeline()
    param_grid = {"classifier__C": [0.5, 1.0, 2.0]}
    class_counts = y_train.value_counts()
    min_class_count = int(class_counts.min()) if not class_counts.empty else 0
    cv_splits = min(3, min_class_count) if min_class_count else 0

    if cv_splits >= 2:
        search = GridSearchCV(
            pipeline, param_grid=param_grid, cv=cv_splits, n_jobs=-1, verbose=0
        )
        search.fit(X_train, y_train)
        best_pipeline = search.best_estimator_
    else:
        best_pipeline = pipeline.fit(X_train, y_train)

    valid_score = best_pipeline.score(X_valid, y_valid)
    print(f"Validation accuracy: {valid_score:.3f}")

    vectorizer: TfidfVectorizer = best_pipeline.named_steps["vectorizer"]
    model = best_pipeline.named_steps["classifier"]

    VECTORIZER_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(model, MODEL_PATH)
    print(f"Artifacts saved to {VECTORIZER_PATH} and {MODEL_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train industry classifier")
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--valid", type=Path, default=DEFAULT_VALID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    train(args.train, args.valid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
