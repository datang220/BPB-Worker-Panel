"""Generate SHAP explanations for the trained short video popularity model.

Only use legally sourced public datasets that comply with robots.txt directives,
rate limits, and platform Terms of Service. Never attempt to access restricted
interfaces or handle personal data without proper anonymization and consent."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import shap

REPO_ROOT = Path(__file__).resolve().parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from short_video_research.data_preprocessing import (  # noqa: E402
    add_author_statistics,
    clean_data,
    load_data,
)
from short_video_research.feature_engineering import build_target_views_hot  # noqa: E402
from short_video_research.model_training import load_artifacts  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SHAP analysis on the trained model.")
    parser.add_argument("--model", required=True, help="Path to the trained model.joblib file")
    parser.add_argument("--data", required=True, help="Path to the dataset used for training")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=200,
        help="Number of samples to use for SHAP calculations (to limit memory usage).",
    )
    parser.add_argument(
        "--output",
        default="artifacts/shap_top_features.json",
        help="Where to save the top feature importances as JSON.",
    )
    parser.add_argument(
        "--hot-quantile",
        type=float,
        default=0.8,
        help="Quantile threshold used when generating the views_hot target.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model, feature_builder = load_artifacts(args.model)

    df = load_data(args.data)
    df = clean_data(df)
    df = add_author_statistics(df)
    if "views_hot" not in df.columns:
        df["views_hot"] = build_target_views_hot(df, quantile=args.hot_quantile)

    X = feature_builder.transform(df)
    feature_names = feature_builder.get_feature_names()

    sample_size = min(args.sample_size, X.shape[0])
    if sample_size <= 0:
        raise ValueError("Sample size must be positive")
    if sample_size < X.shape[0]:
        rng = np.random.default_rng(42)
        indices = rng.choice(X.shape[0], size=sample_size, replace=False)
        X_sample = X[indices]
    else:
        X_sample = X

    # Convert sparse matrices to dense arrays for SHAP when necessary.
    if hasattr(X_sample, "toarray"):
        X_sample = X_sample.toarray()

    if shap.utils.safe_isinstance(model, "lightgbm.sklearn.LGBMClassifier"):
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        if isinstance(shap_values, list):
            shap_matrix = shap_values[1]
        else:
            shap_matrix = shap_values
    elif shap.utils.safe_isinstance(model, "sklearn.ensemble._forest.RandomForestClassifier"):
        explainer = shap.TreeExplainer(model)
        shap_matrix = explainer.shap_values(X_sample)[1]
    else:
        explainer = shap.KernelExplainer(model.predict_proba, X_sample)
        shap_matrix = explainer.shap_values(X_sample)[1]

    mean_abs_values = np.mean(np.abs(shap_matrix), axis=0)
    top_indices = np.argsort(mean_abs_values)[::-1][:10]
    top_features = [
        {"feature": feature_names[idx], "mean_abs_shap": float(mean_abs_values[idx])}
        for idx in top_indices
    ]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump({"top_features": top_features}, fp, indent=2)

    print("Top 10 features saved to", output_path)
    for item in top_features:
        print(f"{item['feature']}: {item['mean_abs_shap']:.6f}")


if __name__ == "__main__":
    main()
