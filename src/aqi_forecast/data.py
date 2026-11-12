from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"date", "city", "aqi"}
OPTIONAL_WEATHER_COLUMNS = [
    "temperature_2m_mean",
    "relative_humidity_2m_mean",
    "wind_speed_10m_mean",
    "rain_sum",
    "boundary_layer_height",
    "fire_count",
]


@dataclass
class DataQualityReport:
    source: str
    provenance: str
    rows_read: int
    rows_valid: int
    duplicate_city_dates: int
    invalid_dates: int
    invalid_aqi: int
    missing_dates: int
    cities: list[str]
    min_date: str | None
    max_date: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def load_daily_aqi(
    source: str | Path | IO,
    *,
    provenance: str = "User-provided CSV; provenance not declared",
    source_name: str | None = None,
) -> tuple[pd.DataFrame, DataQualityReport]:
    """Load and validate daily city AQI.

    Duplicate city/date rows are reported and resolved by keeping the last row.
    AQI values outside CPCB's 0–500 reporting scale are invalidated.
    """
    df = pd.read_csv(source)
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

    rows_read = len(df)
    raw_dates = df["date"].copy()
    raw_aqi = df["aqi"].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["city"] = df["city"].astype("string").str.strip()
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")

    invalid_dates = int(df["date"].isna().sum())
    invalid_aqi_mask = df["aqi"].isna() | ~df["aqi"].between(0, 500)
    invalid_aqi = int(invalid_aqi_mask.sum())
    df.loc[invalid_aqi_mask, "aqi"] = np.nan
    invalid_city = df["city"].isna() | (df["city"].str.len() == 0)

    duplicate_city_dates = int(df.duplicated(["city", "date"], keep=False).sum())
    df = df.loc[~df["date"].isna() & ~invalid_city].copy()
    df = df.sort_values(["city", "date"]).drop_duplicates(["city", "date"], keep="last")

    for column in OPTIONAL_WEATHER_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_dates = 0
    for _, group in df.groupby("city"):
        if len(group):
            missing_dates += len(pd.date_range(group.date.min(), group.date.max(), freq="D")) - len(group)

    valid = df.dropna(subset=["aqi"]).reset_index(drop=True)
    label = source_name or (Path(source).name if isinstance(source, (str, Path)) else "uploaded.csv")
    report = DataQualityReport(
        source=label,
        provenance=provenance,
        rows_read=rows_read,
        rows_valid=len(valid),
        duplicate_city_dates=duplicate_city_dates,
        invalid_dates=invalid_dates,
        invalid_aqi=invalid_aqi,
        missing_dates=int(missing_dates),
        cities=sorted(valid["city"].dropna().unique().tolist()),
        min_date=valid.date.min().date().isoformat() if len(valid) else None,
        max_date=valid.date.max().date().isoformat() if len(valid) else None,
    )
    return valid, report


def reindex_city_daily(df: pd.DataFrame, city: str) -> pd.DataFrame:
    city_df = df.loc[df.city == city].sort_values("date").copy()
    if city_df.empty:
        raise ValueError(f"No valid observations for city {city!r}")
    index = pd.date_range(city_df.date.min(), city_df.date.max(), freq="D", name="date")
    city_df = city_df.set_index("date").reindex(index)
    city_df["city"] = city
    return city_df.reset_index()
