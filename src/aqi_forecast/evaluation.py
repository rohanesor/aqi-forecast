from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .categories import aqi_category


def regression_metrics(y_true, y_pred) -> dict[str, float | int]:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    high = y > 200
    return {
        "mae": float(mean_absolute_error(y, p)),
        "rmse": float(mean_squared_error(y, p) ** 0.5),
        "r2": float(r2_score(y, p)) if len(y) > 1 else float("nan"),
        "category_accuracy": float(np.mean([aqi_category(a) == aqi_category(b) for a, b in zip(y, p)])),
        "high_pollution_days": int(high.sum()),
        "high_aqi_mae": float(mean_absolute_error(y[high], p[high])) if high.any() else float("nan"),
        "high_aqi_rmse": float(mean_squared_error(y[high], p[high]) ** 0.5) if high.any() else float("nan"),
        "n": int(len(y)),
    }


def add_persistence_improvement(metrics: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy()
    out["mae_improvement_vs_persistence_pct"] = np.nan
    for horizon, group in out.groupby("horizon"):
        base = group.loc[group.model == "persistence", "mae"]
        if len(base):
            b = float(base.iloc[0])
            idx = group.index
            out.loc[idx, "mae_improvement_vs_persistence_pct"] = 100 * (b - out.loc[idx, "mae"]) / b
    return out
