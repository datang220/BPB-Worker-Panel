"""Feature engineering utilities for short video popularity modeling.

The features produced here rely solely on legally acquired, public metadata.
Ensure that any upstream data collection respected robots.txt directives,
rate limits, and platform Terms of Service. Never attempt to simulate traffic
or access restricted interfaces."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer


UPLOAD_PERIODS = {
    "late_night": (0, 5),
    "morning": (6, 11),
    "afternoon": (12, 17),
    "evening": (18, 23),
}


def _categorize_period(hour: pd.Series) -> pd.Series:
    labels = []
    for value in hour:
        label = "unknown"
        for name, (start, end) in UPLOAD_PERIODS.items():
            if start <= value <= end:
                label = name
                break
        labels.append(label)
    return pd.Series(labels, index=hour.index)


@dataclass
class FeatureBuilder:
    """Constructs a combined dense + sparse feature matrix."""

    text_max_features: int = 500
    _vectorizer: Optional[TfidfVectorizer] = field(default=None, init=False, repr=False)
    _dense_feature_names: List[str] = field(default_factory=list, init=False)

    def _prepare_text(self, df: pd.DataFrame) -> pd.Series:
        text = (
            df.get("title", "").astype(str)
            + " "
            + df.get("description", "").astype(str)
            + " "
            + df.get("tags", "").astype(str)
        )
        return text.fillna("")

    def _first_hour_rates(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        if "upload_ts" not in df.columns:
            return np.zeros(len(df)), np.zeros(len(df))
        snapshot = df["upload_ts"].max()
        hours_since_upload = (
            (snapshot - df["upload_ts"]).dt.total_seconds() / 3600
        ).clip(lower=1)
        views_rate = df.get("views", pd.Series(0, index=df.index)) / hours_since_upload
        interaction_rate = (
            (df.get("likes", pd.Series(0, index=df.index))
             + df.get("comments", pd.Series(0, index=df.index)))
            / hours_since_upload
        )
        return views_rate.to_numpy(), interaction_rate.to_numpy()

    def _compute_dense_features(self, df: pd.DataFrame, *, fit: bool) -> pd.DataFrame:
        upload_ts = df.get("upload_ts")
        upload_hour = upload_ts.dt.hour.fillna(-1) if upload_ts is not None else pd.Series(-1, index=df.index)
        upload_weekday = upload_ts.dt.weekday.fillna(-1) if upload_ts is not None else pd.Series(-1, index=df.index)

        title_length = df.get("title", pd.Series("", index=df.index)).str.len()
        description_length = df.get("description", pd.Series("", index=df.index)).str.len()
        tag_count = df.get("tags", pd.Series("", index=df.index)).apply(
            lambda x: len([t for t in str(x).split(",") if t.strip()])
        )

        views_per_hour, interaction_per_hour = self._first_hour_rates(df)

        interaction_rate = (
            (df.get("likes", pd.Series(0, index=df.index))
             + df.get("comments", pd.Series(0, index=df.index)))
            / df.get("views", pd.Series(1, index=df.index)).replace(0, np.nan)
        ).fillna(0)

        duration = df.get("duration", pd.Series(0, index=df.index))

        author_activity = df.get("author_video_count", pd.Series(0, index=df.index))
        author_avg_views = df.get("author_avg_views", pd.Series(0, index=df.index))

        period = _categorize_period(upload_hour.astype(int))
        period_dummies = pd.get_dummies(period, prefix="upload_period")
        device_dummies = pd.get_dummies(df.get("device_type", pd.Series("unknown", index=df.index)), prefix="device")
        country_dummies = pd.get_dummies(df.get("country", pd.Series("unknown", index=df.index)), prefix="country")

        dense = pd.DataFrame(
            {
                "title_length": title_length,
                "description_length": description_length,
                "tag_count": tag_count,
                "upload_hour": upload_hour,
                "upload_weekday": upload_weekday,
                "views_per_hour": views_per_hour,
                "interaction_per_hour": interaction_per_hour,
                "interaction_rate": interaction_rate,
                "duration": duration,
                "author_video_count": author_activity,
                "author_avg_views": author_avg_views,
            }
        )
        dense = pd.concat([dense, period_dummies, device_dummies, country_dummies], axis=1)
        dense = dense.fillna(0)
        if fit or not self._dense_feature_names:
            self._dense_feature_names = dense.columns.tolist()
        else:
            dense = dense.reindex(columns=self._dense_feature_names, fill_value=0)
        return dense

    def fit_transform(self, df: pd.DataFrame) -> sparse.csr_matrix:
        dense_features = self._compute_dense_features(df, fit=True)
        self._vectorizer = TfidfVectorizer(
            max_features=self.text_max_features,
            ngram_range=(1, 2),
            min_df=2,
        )
        text_matrix = self._vectorizer.fit_transform(self._prepare_text(df))
        return sparse.hstack([sparse.csr_matrix(dense_features.values), text_matrix])

    def transform(self, df: pd.DataFrame) -> sparse.csr_matrix:
        if self._vectorizer is None:
            raise ValueError("FeatureBuilder must be fitted before calling transform().")
        dense_features = self._compute_dense_features(df, fit=False)
        text_matrix = self._vectorizer.transform(self._prepare_text(df))
        return sparse.hstack([sparse.csr_matrix(dense_features.values), text_matrix])

    def get_feature_names(self) -> List[str]:
        if self._vectorizer is None:
            raise ValueError("FeatureBuilder must be fitted before retrieving feature names.")
        text_features = [f"tfidf_{name}" for name in self._vectorizer.get_feature_names_out()]
        return self._dense_feature_names + text_features


def build_target_views_hot(df: pd.DataFrame, quantile: float = 0.8, column: str = "views") -> pd.Series:
    """Create a binary popularity target from the views column."""
    threshold = df[column].quantile(quantile)
    return (df[column] >= threshold).astype(int)


__all__ = ["FeatureBuilder", "build_target_views_hot"]
