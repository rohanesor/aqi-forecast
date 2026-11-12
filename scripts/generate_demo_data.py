"""Generate visibly synthetic data for UI/pipeline verification only.

This is NOT CPCB data and must never be reported as measured project performance.
"""
from pathlib import Path

import numpy as np
import pandas as pd


def city_series(city: str, seed: int, offset: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2019-01-01", pd.Timestamp.today().normalize(), freq="D")
    n = len(dates)
    month = dates.month.to_numpy()
    winter = np.where(np.isin(month, [10, 11, 12, 1]), 85, 0)
    monsoon = np.where(np.isin(month, [7, 8, 9]), -35, 0)
    weekly = 10 * np.sin(2 * np.pi * np.arange(n) / 7)
    seasonal = 30 * np.cos(2 * np.pi * (dates.dayofyear.to_numpy() - 15) / 365.25)
    target = 75 + offset + winter + monsoon + weekly + seasonal + rng.normal(0, 18, n)
    aqi = np.zeros(n)
    aqi[0] = target[0]
    for i in range(1, n):
        aqi[i] = 0.58 * aqi[i - 1] + 0.42 * target[i]
    # Ensure the alert path can be verified in the demo interface.
    if city == "Delhi":
        aqi[-12:] = np.linspace(215, 268, 12) + rng.normal(0, 3, 12)
    return pd.DataFrame({"date": dates.date, "city": city, "aqi": np.clip(aqi, 15, 480).round(1)})


out = pd.concat([city_series("Delhi", 42, 25), city_series("Chennai", 84, -15)], ignore_index=True)
Path("data").mkdir(exist_ok=True)
out.to_csv("data/demo_cpcb_format_NOT_OFFICIAL.csv", index=False)
print(f"Wrote {len(out)} synthetic rows. NOT OFFICIAL CPCB DATA.")
