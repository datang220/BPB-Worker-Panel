"""Command-line training entry point for short video popularity modeling.

Use only datasets that were legally obtained. Always respect robots.txt files,
adhere to rate limits, and follow the platform's Terms of Service. Do not attempt
any authentication bypasses or access to restricted endpoints. Remove or anonymize
any personal data before running this script."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from sklearn.metrics import classification_report

# Allow importing from the local src/ directory without installing the package.
REPO_ROOT = Path(__file__).resolve().parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from short_video_research.data_preprocessing import (  # noqa: E402
    add_author_statistics,
    clean_data,
    load_data,
)
from short_video_research.evaluation import evaluate_predictions  # noqa: E402
from short_video_research.feature_engineering import (  # noqa: E402
    FeatureBuilder,
    build_target_views_hot,
)
from short_video_research.model_training import (  # noqa: E402
    create_model,
    save_artifacts,
    split_data,
    train_model,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a short video popularity model.")
    parser.add_argument("--input", required=True, help="Path to the public_videos.csv file")
    parser.add_argument(
        "--target",
        default="views_hot",
        help="Target column for prediction. Will be generated if set to views_hot.",
    )
    parser.add_argument(
        "--hot-quantile",
        type=float,
        default=0.8,
        help="Quantile threshold for defining a video as hot when generating views_hot.",
    )
    parser.add_argument(
        "--model-type",
        default="lightgbm",
        choices=["lightgbm", "random_forest"],
        help="Underlying estimator to use.",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts",
        help="Directory to store trained model artifacts and metrics.",
    )
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set proportion.")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed.")
    parser.add_argument(
        "--text-max-features",
        type=int,
        default=500,
        help="Maximum number of TF-IDF features to retain.",
    )
    return parser.parse_args()


def ensure_target(df, target_col: str, quantile: float) -> None:
    if target_col == "views_hot" and target_col not in df.columns:
        df[target_col] = build_target_views_hot(df, quantile=quantile)


def main() -> None:
    args = parse_args()
    df = load_data(args.input)
    df = clean_data(df)
    df = add_author_statistics(df)
    ensure_target(df, args.target, args.hot_quantile)
    if args.target not in df.columns:
        raise ValueError(f"Target column {args.target} not found and could not be generated.")

    y = df[args.target].astype(int).to_numpy()
    feature_df = df.drop(columns=[args.target])

    X_train_df, X_test_df, y_train, y_test = split_data(
        feature_df,
        y,
        test_size=args.test_size,
        random_state=args.random_state,
    )

    feature_builder = FeatureBuilder(text_max_features=args.text_max_features)
    X_train = feature_builder.fit_transform(X_train_df)
    X_test = feature_builder.transform(X_test_df)

    model = create_model(args.model_type, random_state=args.random_state)
    model = train_model(model, X_train, y_train)

    if hasattr(model, "predict_proba"):
        y_scores = model.predict_proba(X_test)[:, 1]
    else:
        y_scores = model.decision_function(X_test)
        y_scores = (y_scores - y_scores.min()) / (y_scores.max() - y_scores.min() + 1e-8)
    y_pred = (y_scores >= 0.5).astype(int)

    metrics_dict, playback = evaluate_predictions(y_test, y_scores, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = artifact_dir / "metrics.json"
    with metrics_path.open("w", encoding="utf-8") as fp:
        json.dump({"metrics": metrics_dict, "classification_report": report}, fp, indent=2)

    playback_path = artifact_dir / "playback_curve.csv"
    playback.to_csv(playback_path, index=False)

    model_path = artifact_dir / "model.joblib"
    save_artifacts(model, feature_builder, str(model_path))

    print("Training complete. Metrics saved to", metrics_path)
    print(json.dumps(metrics_dict, indent=2))


if __name__ == "__main__":
    main()
