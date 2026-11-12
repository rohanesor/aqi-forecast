from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone

from .data import load_daily_aqi
from .evaluation import add_persistence_improvement, regression_metrics
from .features import latest_feature_row, make_supervised
from .models import candidate_registry, tune_on_training_only


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def nested_walk_forward(estimator, grid, x, y, min_train: int, folds: int = 4):
    remaining = len(x) - min_train
    step = max(30, remaining // folds)
    ys, ps, dates = [], [], []
    for start in range(min_train, len(x), step):
        stop = min(start + step, len(x))
        fitted, _ = tune_on_training_only(estimator, grid, x.iloc[:start], y.iloc[:start], splits=3)
        ys.extend(y.iloc[start:stop].tolist())
        ps.extend(fitted.predict(x.iloc[start:stop]).tolist())
        dates.extend(range(start, stop))
    return np.asarray(ys), np.asarray(ps), np.asarray(dates)


def explain_tree(model, x_background: pd.DataFrame, x_latest: pd.DataFrame, output_dir: Path, horizon: int):
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        values = explainer(x_background.tail(500))
        global_df = pd.DataFrame({
            "feature": x_background.columns,
            "mean_abs_shap": np.abs(values.values).mean(axis=0),
        }).sort_values("mean_abs_shap", ascending=False)
        global_df.to_csv(output_dir / f"shap_global_h{horizon}.csv", index=False)
        local = explainer(x_latest)
        pd.DataFrame({
            "feature": x_latest.columns,
            "feature_value": x_latest.iloc[0].values,
            "shap_value": local.values[0],
        }).sort_values("shap_value", key=np.abs, ascending=False).to_csv(
            output_dir / f"shap_local_h{horizon}.csv", index=False
        )
    except Exception as exc:
        (output_dir / f"shap_h{horizon}_error.txt").write_text(str(exc), encoding="utf-8")


def train_city(csv_path: str, city: str, output_root: str, provenance: str, model_names: list[str],
               min_samples: int = 450):
    df, quality = load_daily_aqi(csv_path, provenance=provenance)
    if city not in quality.cities:
        raise ValueError(f"City {city!r} not found. Available: {quality.cities}")

    output_dir = Path(output_root) / slugify(city)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data_quality.json").write_text(json.dumps(quality.to_dict(), indent=2), encoding="utf-8")

    registry = candidate_registry()
    absent = [m for m in model_names if m != "persistence" and m not in registry]
    if absent:
        raise RuntimeError(f"Unavailable model dependencies: {absent}")

    holdout_rows, cv_rows, prediction_rows, forecasts, selections = [], [], [], [], {}
    usable_samples = {}
    for horizon in (1, 2, 3):
        x, y, meta = make_supervised(df, city, horizon)
        usable_samples[str(horizon)] = len(x)
        if len(x) < min_samples:
            raise ValueError(f"{city} has only {len(x)} usable day+{horizon} samples; at least {min_samples} required")
        split = int(len(x) * 0.8)
        x_train, y_train = x.iloc[:split], y.iloc[:split]
        x_test, y_test = x.iloc[split:], y.iloc[split:]
        meta_test = meta.iloc[split:].reset_index(drop=True)
        # Retain the production minimum of 180 where possible. A lower value is
        # used only when an explicit lower --min-samples threshold was requested.
        min_train = min(max(60, int(len(x_train) * 0.55)), max(60, len(x_train) - 30))
        if len(x) >= 450:
            min_train = max(180, min_train)

        # Persistence requires no fitting and predicts all horizons as the latest AQI.
        p_hold = x_test["aqi_latest"].to_numpy()
        m = regression_metrics(y_test, p_hold)
        holdout_rows.append({"horizon": horizon, "model": "persistence", **m})
        p_cv = x_train.iloc[min_train:]["aqi_latest"].to_numpy()
        mcv = regression_metrics(y_train.iloc[min_train:], p_cv)
        cv_rows.append({"horizon": horizon, "model": "persistence", **mcv})
        prediction_rows.extend([
            {"horizon": horizon, "model": "persistence", "forecast_date": d.date().isoformat(),
             "observed_aqi": float(a), "predicted_aqi": float(p)}
            for d, a, p in zip(meta_test.forecast_date, y_test, p_hold)
        ])

        fitted_models = {}
        for name in [n for n in model_names if n != "persistence"]:
            estimator, grid = registry[name]
            y_cv, p_cv, cv_indices = nested_walk_forward(estimator, grid, x_train, y_train, min_train)
            cv_rows.append({"horizon": horizon, "model": name, **regression_metrics(y_cv, p_cv)})
            fitted, best_params = tune_on_training_only(estimator, grid, x_train, y_train)
            fitted_models[name] = fitted
            joblib.dump({"model": fitted, "features": list(x.columns), "best_params": best_params},
                        output_dir / f"model_h{horizon}_{name}.joblib")
            p = fitted.predict(x_test)
            holdout_rows.append({"horizon": horizon, "model": name, **regression_metrics(y_test, p)})
            prediction_rows.extend([
                {"horizon": horizon, "model": name, "forecast_date": d.date().isoformat(),
                 "observed_aqi": float(a), "predicted_aqi": float(b)}
                for d, a, b in zip(meta_test.forecast_date, y_test, p)
            ])

        # Select on training-only walk-forward MAE; the holdout remains a report-only test.
        cv_h = [r for r in cv_rows if r["horizon"] == horizon and r["model"] in model_names]
        champion = min(cv_h, key=lambda r: r["mae"])["model"]
        selections[str(horizon)] = champion
        x_latest, issue_date, forecast_date = latest_feature_row(df, city, horizon, list(x.columns))
        if champion == "persistence":
            predicted = float(x_latest["aqi_latest"].iloc[0])
        else:
            predicted = float(fitted_models[champion].predict(x_latest)[0])
        forecasts.append({"city": city, "horizon": horizon, "issue_date": issue_date.date().isoformat(),
                          "forecast_date": forecast_date.date().isoformat(), "predicted_aqi": max(0, min(500, predicted)),
                          "model": champion})

        explain_name = champion if champion in fitted_models and champion in {"xgboost", "lightgbm", "random_forest"} else None
        if explain_name:
            explain_tree(fitted_models[explain_name], x_test, x_latest, output_dir, horizon)

    holdout = add_persistence_improvement(pd.DataFrame(holdout_rows))
    cv = add_persistence_improvement(pd.DataFrame(cv_rows))
    holdout.to_csv(output_dir / "metrics_holdout.csv", index=False)
    cv.to_csv(output_dir / "metrics_walk_forward.csv", index=False)
    pd.DataFrame(prediction_rows).to_csv(output_dir / "holdout_predictions.csv", index=False)
    pd.DataFrame(forecasts).to_csv(output_dir / "forecasts.csv", index=False)

    latest = df.loc[df.city == city].sort_values("date").iloc[-1]
    manifest = {
        "project_version": "0.1.0", "city": city, "source_file": str(csv_path),
        "provenance": provenance, "is_demo": "demo" in provenance.lower(),
        "latest_observation_date": latest.date.date().isoformat(), "latest_observed_aqi": float(latest.aqi),
        "forecast_issue_time_definition": "After the latest CPCB daily AQI observation is available; no future AQI inputs.",
        "selection_basis": "Lowest training-only nested walk-forward MAE, separately for each horizon.",
        "champions": selections, "candidates": model_names,
        "minimum_samples_required": min_samples, "usable_samples": usable_samples,
        "experimental_short_history": min_samples < 450,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description="Train direct day+1/day+2/day+3 AQI models")
    parser.add_argument("--data", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--output", default="artifacts")
    parser.add_argument("--provenance", default="Official CPCB daily bulletin CSV supplied by user")
    parser.add_argument("--models", default="persistence,xgboost",
                        help="Comma-separated: persistence,linear_regression,random_forest,xgboost,lightgbm")
    parser.add_argument("--min-samples", type=int, default=450,
                        help="Minimum usable samples per horizon (production default: 450)")
    args = parser.parse_args()
    if args.min_samples < 120:
        parser.error("--min-samples must be at least 120")
    output = train_city(args.data, args.city, args.output, args.provenance,
                        [x.strip() for x in args.models.split(",") if x.strip()], args.min_samples)
    print(f"Artifacts written to {output}")


if __name__ == "__main__":
    main()
