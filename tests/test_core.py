import io

import pandas as pd
import pytest

from aqi_forecast.categories import aqi_category
from aqi_forecast.data import load_daily_aqi
from aqi_forecast.features import make_supervised


@pytest.mark.unit
def test_cpcb_categories():
    assert aqi_category(50) == "Good"
    assert aqi_category(51) == "Satisfactory"
    assert aqi_category(200) == "Moderate"
    assert aqi_category(201) == "Poor"
    assert aqi_category(401) == "Severe"


@pytest.mark.unit
def test_ingestion_reports_duplicates_and_invalid_values():
    csv = io.StringIO("date,city,aqi\n2024-01-01,Delhi,100\n2024-01-01,Delhi,110\nbad,Delhi,99\n2024-01-03,Delhi,700\n")
    df, report = load_daily_aqi(csv)
    assert report.duplicate_city_dates == 2
    assert report.invalid_dates == 1
    assert report.invalid_aqi == 1
    assert len(df) == 1
    assert df.iloc[0].aqi == 110


@pytest.mark.unit
def test_features_use_only_issue_or_earlier_aqi():
    dates = pd.date_range("2023-01-01", periods=40)
    df = pd.DataFrame({"date": dates, "city": "Delhi", "aqi": range(40)})
    x, y, meta = make_supervised(df, "Delhi", 3)
    first = x.iloc[0]
    issue = meta.iloc[0].issue_date
    issue_value = df.loc[df.date == issue, "aqi"].iloc[0]
    assert first.aqi_latest == issue_value
    assert y.iloc[0] == issue_value + 3
    assert meta.iloc[0].forecast_date == issue + pd.Timedelta(days=3)
