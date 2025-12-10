from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


def build_quality_metrics(data: pd.DataFrame) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    metrics["row_count"] = int(len(data))
    if "address_uuid" in data.columns:
        metrics["house_count"] = int(data["address_uuid"].nunique())
    if "date" in data.columns and not data["date"].isna().all():
        metrics["date_min"] = _normalize_datetime(data["date"].min())
        metrics["date_max"] = _normalize_datetime(data["date"].max())

    missing = {
        col: int(data[col].isna().sum())
        for col in data.columns
        if data[col].isna().any()
    }
    metrics["missing_values"] = missing

    if "is_anomaly" in data.columns:
        metrics["anomaly_count"] = int(data["is_anomaly"].sum())

    if "value" in data.columns:
        value_series = data["value"].dropna()
        if not value_series.empty:
            metrics["value_stats"] = {
                "min": float(value_series.min()),
                "max": float(value_series.max()),
                "mean": float(value_series.mean()),
            }
            metrics["negative_values"] = int((value_series < 0).sum())

    return metrics


def _normalize_datetime(value: Any) -> str | None:
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    try:
        ts = pd.to_datetime(value)
        if pd.isna(ts):
            return None
        return ts.isoformat()
    except Exception:
        return None
