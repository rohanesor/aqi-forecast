from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def candidate_registry(random_state: int = 42) -> dict:
    candidates = {
        "linear_regression": (
            Pipeline([("scale", StandardScaler()), ("model", LinearRegression())]),
            {},
        ),
        "random_forest": (
            RandomForestRegressor(random_state=random_state, n_jobs=-1),
            {"n_estimators": [250], "max_depth": [5, None], "min_samples_leaf": [2, 5]},
        ),
    }
    try:
        from xgboost import XGBRegressor
        candidates["xgboost"] = (
            XGBRegressor(
                objective="reg:squarederror", random_state=random_state, n_jobs=2,
                tree_method="hist", verbosity=0,
            ),
            {"n_estimators": [150, 300], "max_depth": [3, 5], "learning_rate": [0.03, 0.07],
             "subsample": [0.9], "colsample_bytree": [0.9]},
        )
    except ImportError:
        pass
    try:
        from lightgbm import LGBMRegressor
        candidates["lightgbm"] = (
            LGBMRegressor(random_state=random_state, verbosity=-1, n_jobs=2),
            {"n_estimators": [150, 300], "num_leaves": [15, 31], "learning_rate": [0.03, 0.07]},
        )
    except ImportError:
        pass
    return candidates


def tune_on_training_only(estimator, grid: dict, x, y, splits: int = 4):
    if not grid:
        return clone(estimator).fit(x, y), {}
    n_splits = min(splits, max(2, len(x) // 90))
    search = GridSearchCV(
        clone(estimator), grid, scoring="neg_mean_absolute_error",
        cv=TimeSeriesSplit(n_splits=n_splits), n_jobs=1, refit=True,
    )
    search.fit(x, y)
    return search.best_estimator_, search.best_params_


def expanding_predictions(estimator, x, y, *, min_train: int, step: int = 60) -> tuple[np.ndarray, np.ndarray]:
    """Walk-forward predictions where every prediction uses only earlier rows."""
    true_parts, pred_parts = [], []
    for start in range(min_train, len(x), step):
        stop = min(start + step, len(x))
        model = clone(estimator).fit(x.iloc[:start], y.iloc[:start])
        pred_parts.append(model.predict(x.iloc[start:stop]))
        true_parts.append(y.iloc[start:stop].to_numpy())
    return np.concatenate(true_parts), np.concatenate(pred_parts)
