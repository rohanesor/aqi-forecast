import json

import numpy as np
import pandas as pd
import pytest

from aqi_forecast.train import train_city


@pytest.mark.integration
def test_ingest_train_predict_artifact_flow(tmp_path):
    dates = pd.date_range("2024-01-01", periods=520, freq="D")
    values = 120 + 35 * np.sin(np.arange(len(dates)) / 25) + 8 * np.sin(np.arange(len(dates)) / 7)
    csv_path = tmp_path / "official_format.csv"
    pd.DataFrame({"date": dates, "city": "Test City", "aqi": values.round(1)}).to_csv(csv_path, index=False)

    artifact_dir = train_city(
        str(csv_path), "Test City", str(tmp_path / "artifacts"),
        "TEST FIXTURE — NOT CPCB DATA", ["persistence"],
    )

    manifest = json.loads((artifact_dir / "manifest.json").read_text())
    forecasts = pd.read_csv(artifact_dir / "forecasts.csv")
    metrics = pd.read_csv(artifact_dir / "metrics_holdout.csv")

    assert manifest["champions"] == {"1": "persistence", "2": "persistence", "3": "persistence"}
    assert forecasts.horizon.tolist() == [1, 2, 3]
    assert pd.to_datetime(forecasts.forecast_date).diff().dropna().eq(pd.Timedelta(days=1)).all()
    assert set(metrics.model) == {"persistence"}
    assert {"mae", "rmse", "r2", "category_accuracy", "high_pollution_days"}.issubset(metrics.columns)
