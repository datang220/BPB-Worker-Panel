"""Model training utilities using scikit-learn compatible estimators.

All training must rely on legally sourced public datasets. Respect robots.txt,
rate limits, and platform Terms of Service when collecting data. Never attempt
to bypass authentication or access restricted endpoints."""
from __future__ import annotations

from typing import Literal

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

try:
    from lightgbm import LGBMClassifier
except ImportError:  # pragma: no cover - LightGBM is optional
    LGBMClassifier = None  # type: ignore


ModelType = Literal["lightgbm", "random_forest"]


def split_data(
    X,
    y,
    test_size: float = 0.2,
    random_state: int = 42,
):
    return train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=y)


def create_model(model_type: ModelType = "lightgbm", random_state: int = 42):
    if model_type == "lightgbm":
        if LGBMClassifier is None:
            raise ImportError("lightgbm is not installed. Install it or choose random_forest.")
        model = LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=-1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1,
        )
    elif model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            random_state=random_state,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    return model


def train_model(model, X_train, y_train):
    model.fit(X_train, y_train)
    return model


def save_artifacts(model, feature_builder, path: str) -> None:
    joblib.dump({"model": model, "feature_builder": feature_builder}, path)


def load_artifacts(path: str):
    artifacts = joblib.load(path)
    model = artifacts["model"]
    feature_builder = artifacts["feature_builder"]
    return model, feature_builder


__all__ = [
    "split_data",
    "create_model",
    "train_model",
    "save_artifacts",
    "load_artifacts",
]
