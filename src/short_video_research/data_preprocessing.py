"""Data preprocessing utilities for short video popularity research.

All datasets processed here must be legally collected, respect the source
platform's robots.txt directives, enforce rate limits, and comply with the
platform's Terms of Service (TOS). Any personally identifiable information
must be anonymized or removed before analysis to remain compliant with data
protection regulations."""
from __future__ import annotations

import pandas as pd


def load_data(path: str) -> pd.DataFrame:
    """Load the CSV dataset and parse datetimes."""
    df = pd.read_csv(path)
    if "upload_ts" in df.columns:
        df["upload_ts"] = pd.to_datetime(df["upload_ts"], errors="coerce", utc=True)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning: drop duplicates and handle missing values."""
    cleaned = df.drop_duplicates(subset="video_id", keep="last").copy()
    # Fill missing textual fields with empty strings for downstream NLP features.
    text_columns = ["title", "description", "tags"]
    for col in text_columns:
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].fillna("")
    # Replace non-positive duration with NaN to avoid invalid rates, then fill with median.
    if "duration" in cleaned.columns:
        cleaned.loc[cleaned["duration"] <= 0, "duration"] = pd.NA
        cleaned["duration"] = cleaned["duration"].fillna(cleaned["duration"].median())
    numeric_defaults = {
        "views": cleaned.get("views", pd.Series(dtype=float)).median(),
        "likes": cleaned.get("likes", pd.Series(dtype=float)).median(),
        "comments": cleaned.get("comments", pd.Series(dtype=float)).median(),
    }
    for col, default in numeric_defaults.items():
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].fillna(default if pd.notna(default) else 0)
    return cleaned


def add_author_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute aggregate author activity signals."""
    if "author_id" not in df.columns:
        return df
    activity = (
        df.groupby("author_id")
        .agg(
            author_video_count=("video_id", "count"),
            author_avg_views=("views", "mean"),
            author_avg_likes=("likes", "mean"),
            author_avg_comments=("comments", "mean"),
        )
        .reset_index()
    )
    enriched = df.merge(activity, on="author_id", how="left")
    return enriched


__all__ = ["load_data", "clean_data", "add_author_statistics"]
