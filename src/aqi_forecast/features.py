from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .data import OPTIONAL_WEATHER_COLUMNS, reindex_city_daily

# Main Diwali date. The flag covers ±1 day to represent the festival window.
DIWALI_DATES = {
    2018: "2018-11-07", 2019: "2019-10-27", 2020: "2020-11-14",
    2021: "2021-11-04", 2022: "2022-10-24", 2023: "2023-11-12",
    2024: "2024-11-01", 2025: "2025-10-20", 2026: "2026-11-08",
    2027: "2027-10-29", 2028: "2028-10-17", 2029: "2029-11-05",
    2030: "2030-10-26",
}


def season_from_month(month: int) -> int:
    # 0 winter, 1 pre-monsoon/summer, 2 monsoon, 3 post-monsoon
    if month in (12, 1, 2): return 0
    if month in (3, 4, 5): return 1
    if month in (6, 7, 8, 9): return 2
    return 3


def diwali_flag(value: pd.Timestamp | date) -> int:
    ts = pd.Timestamp(value).normalize()
    main = DIWALI_DATES.get(ts.year)
    return int(main is not None and abs((ts - pd.Timestamp(main)).days) <= 1)


def make_supervised(df: pd.DataFrame, city: str, horizon: int) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Build direct-horizon samples.

    Each row is issued after the daily CPCB observation at `issue_date` is known.
    Every AQI and weather-history feature is at or before that issue date. Calendar
    fields describe the target date. No backfilled/interpolated AQI is used.
    """
    if horizon not in (1, 2, 3):
        raise ValueError("horizon must be 1, 2, or 3")
    g = reindex_city_daily(df, city).sort_values("date").reset_index(drop=True)
    f = pd.DataFrame(index=g.index)
    f["aqi_latest"] = g["aqi"]
    for lag in (1, 2, 3, 7):
        f[f"aqi_lag_{lag}"] = g["aqi"].shift(lag)
    for window in (3, 7, 14):
        f[f"aqi_mean_{window}"] = g["aqi"].rolling(window, min_periods=window).mean()

    target_date = g["date"] + pd.to_timedelta(horizon, unit="D")
    f["target_month"] = target_date.dt.month
    f["target_season"] = f["target_month"].map(season_from_month)
    f["target_day_of_week"] = target_date.dt.dayofweek
    f["target_diwali"] = target_date.map(diwali_flag)

    # Historical weather known at issue time only. Future-weather fields must be
    # supplied as archived forecasts and are intentionally not inferred here.
    for column in OPTIONAL_WEATHER_COLUMNS:
        if column in g.columns and g[column].notna().sum() >= max(30, int(len(g) * 0.5)):
            f[f"issue_{column}"] = g[column]

    y = g["aqi"].shift(-horizon).rename("observed_aqi")
    meta = pd.DataFrame({"issue_date": g["date"], "forecast_date": target_date, "city": city})
    mask = f.notna().all(axis=1) & y.notna()
    return f.loc[mask].reset_index(drop=True), y.loc[mask].reset_index(drop=True), meta.loc[mask].reset_index(drop=True)


def latest_feature_row(df: pd.DataFrame, city: str, horizon: int, feature_names: list[str]) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    g = reindex_city_daily(df, city)
    # Add temporary unknown targets so make_supervised can construct the last issue row.
    last = g["date"].max()
    extension = pd.DataFrame({
        "date": pd.date_range(last + pd.Timedelta(days=1), last + pd.Timedelta(days=horizon), freq="D"),
        "city": city,
        "aqi": np.nan,
    })
    expanded = pd.concat([g, extension], ignore_index=True)
    # Recreate features without requiring a known target.
    x, _, _ = make_supervised_for_prediction(expanded, city, horizon)
    row = x.loc[x["issue_date"] == last]
    if row.empty:
        raise ValueError("Insufficient contiguous recent history to create a forecast")
    missing = [c for c in feature_names if c not in row.columns]
    if missing:
        raise ValueError(f"Current data lacks model features: {missing}")
    return row[feature_names].tail(1), last, last + pd.Timedelta(days=horizon)


def make_supervised_for_prediction(df: pd.DataFrame, city: str, horizon: int) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    g = reindex_city_daily(df, city).sort_values("date").reset_index(drop=True)
    f = pd.DataFrame(index=g.index)
    f["issue_date"] = g["date"]
    f["aqi_latest"] = g["aqi"]
    for lag in (1, 2, 3, 7): f[f"aqi_lag_{lag}"] = g["aqi"].shift(lag)
    for window in (3, 7, 14): f[f"aqi_mean_{window}"] = g["aqi"].rolling(window, min_periods=window).mean()
    target_date = g["date"] + pd.to_timedelta(horizon, unit="D")
    f["target_month"] = target_date.dt.month
    f["target_season"] = f["target_month"].map(season_from_month)
    f["target_day_of_week"] = target_date.dt.dayofweek
    f["target_diwali"] = target_date.map(diwali_flag)
    for column in OPTIONAL_WEATHER_COLUMNS:
        if column in g.columns and g[column].notna().sum() >= max(30, int(len(g) * 0.5)):
            f[f"issue_{column}"] = g[column]
    y = g["aqi"].shift(-horizon)
    meta = pd.DataFrame({"issue_date": g["date"], "forecast_date": target_date, "city": city})
    return f, y, meta
