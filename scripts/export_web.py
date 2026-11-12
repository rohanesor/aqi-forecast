"""Export trained artifacts to static JSON for the web frontend (web/public/data).

    python scripts/export_web.py [--artifacts artifacts] [--out web/public/data]

Read-only over artifacts/. For every city it writes one JSON bundle:
manifest, latest observation, the 3 forecasts with an empirical range, last 120 days of history, holdout
metrics (all candidates), walk-forward metrics, data quality, global + local SHAP with plain-language labels,
and a holdout sample (observed vs predicted) for the selected model. Plus index.json listing the cities.

The forecast range is EMPIRICAL: the 10th-90th percentile of the selected model's signed holdout errors for that
horizon, added to the point forecast. It is a calibration summary, not a guaranteed interval.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aqi_forecast.categories import CATEGORIES, aqi_category  # noqa: E402

# city -> lat/lon for the map (approximate city centres)
CITY_COORDS = {
    "Delhi": (28.61, 77.21), "Delhi — Anand Vihar station": (28.6476, 77.3159),
    "Chennai": (13.08, 80.27), "Mumbai": (19.08, 72.88), "Kolkata": (22.57, 88.36),
    "Bengaluru": (12.97, 77.59), "Hyderabad": (17.39, 78.49), "Ahmedabad": (23.02, 72.57), "Pune": (18.52, 73.86),
    "Lucknow": (26.85, 80.95), "Patna": (25.59, 85.14), "Jaipur": (26.91, 75.79), "Kanpur": (26.45, 80.33),
    "Tiruchirappalli": (10.80, 78.69), "Coimbatore": (11.02, 76.96), "Kochi": (9.93, 76.27), "Guwahati": (26.14, 91.74),
    "Chandigarh": (30.73, 76.78), "Bhopal": (23.26, 77.41), "Visakhapatnam": (17.69, 83.22), "Varanasi": (25.32, 82.97),
}

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
SEASONS = {0: "winter", 1: "summer", 2: "monsoon", 3: "post-monsoon"}


def feature_label(name: str) -> str:
    """Plain-language name for a model feature."""
    fixed = {
        "aqi_latest": "Latest observed AQI",
        "target_month": "Month of the forecast day",
        "target_season": "Season of the forecast day",
        "target_day_of_week": "Day of the week",
        "target_diwali": "Diwali festival window",
        "target_day_of_year": "Time of year",
    }
    if name in fixed:
        return fixed[name]
    if name.startswith("aqi_lag_"):
        n = int(name.rsplit("_", 1)[1])
        return "AQI the day before the latest" if n == 1 else f"AQI {n} days before the latest"
    if name.startswith("aqi_mean_"):
        return f"Average AQI over the last {name.rsplit('_', 1)[1]} days"
    return name.replace("_", " ").capitalize()


def value_text(name: str, value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    if name.startswith("aqi"):
        return f"{value:.0f}"
    if name == "target_month":
        return MONTHS[int(value)]
    if name == "target_day_of_week":
        return WEEKDAYS[int(value)]
    if name == "target_season":
        return SEASONS.get(int(value), str(int(value)))
    if name == "target_diwali":
        return "yes" if int(value) else "no"
    return f"{value:g}"


def clean(obj):
    """JSON-safe: NaN/inf -> None, numpy scalars -> python."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if not math.isfinite(v) else round(v, 4)
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def records(df: pd.DataFrame) -> list[dict]:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
    return clean(out.to_dict(orient="records"))


def export_city(art: Path) -> dict:
    manifest = json.loads((art / "manifest.json").read_text(encoding="utf-8"))
    city = manifest["city"]
    fc = pd.read_csv(art / "forecasts.csv", parse_dates=["issue_date", "forecast_date"]).sort_values("horizon")
    hold = pd.read_csv(art / "metrics_holdout.csv")
    wf = pd.read_csv(art / "metrics_walk_forward.csv") if (art / "metrics_walk_forward.csv").exists() else pd.DataFrame()
    preds = pd.read_csv(art / "holdout_predictions.csv", parse_dates=["forecast_date"])
    quality = json.loads((art / "data_quality.json").read_text(encoding="utf-8"))

    forecasts = []
    for row in fc.itertuples():
        h = int(row.horizon)
        sel = preds[(preds.horizon == h) & (preds.model == row.model)]
        err = (sel.observed_aqi - sel.predicted_aqi).dropna()
        lo_e, hi_e = (float(np.percentile(err, 10)), float(np.percentile(err, 90))) if len(err) >= 30 else (None, None)
        p = float(row.predicted_aqi)
        lo = max(0.0, p + lo_e) if lo_e is not None else None
        hi = min(500.0, p + hi_e) if hi_e is not None else None
        forecasts.append({
            "horizon": h, "issue_date": f"{row.issue_date:%Y-%m-%d}", "forecast_date": f"{row.forecast_date:%Y-%m-%d}",
            "aqi": p, "category": aqi_category(p), "model": row.model,
            "range_low": lo, "range_high": hi,
            "range_low_category": aqi_category(lo) if lo is not None else None,
            "range_high_category": aqi_category(hi) if hi is not None else None,
            "holdout_n": int(len(err)),
        })

    shap = {}
    for h in (1, 2, 3):
        g, l = art / f"shap_global_h{h}.csv", art / f"shap_local_h{h}.csv"
        if g.exists() and l.exists():
            gd = pd.read_csv(g).head(10)
            ld = pd.read_csv(l)
            ld = ld.reindex(ld.shap_value.abs().sort_values(ascending=False).index).head(8)
            shap[str(h)] = {
                "global": [{"feature": r.feature, "label": feature_label(r.feature), "mean_abs_shap": float(r.mean_abs_shap)}
                           for r in gd.itertuples()],
                "local": [{"feature": r.feature, "label": feature_label(r.feature), "value": r.feature_value,
                           "value_text": value_text(r.feature, float(r.feature_value)), "shap": float(r.shap_value)}
                          for r in ld.itertuples()],
            }

    history = pd.DataFrame()
    src = ROOT / manifest["source_file"]
    if src.exists():
        h = pd.read_csv(src, parse_dates=["date"])
        history = h[h.city == city].sort_values("date").tail(120)[["date", "aqi"]]

    sample = []
    champ1 = manifest["champions"].get("1")
    s = preds[(preds.horizon == 1) & (preds.model == champ1)].sort_values("forecast_date").tail(120)
    p1 = preds[(preds.horizon == 1) & (preds.model == "persistence")].set_index("forecast_date").predicted_aqi
    for r in s.itertuples():
        sample.append({"date": f"{r.forecast_date:%Y-%m-%d}", "observed": r.observed_aqi, "predicted": r.predicted_aqi,
                       "persistence": p1.get(r.forecast_date, np.nan)})

    lat, lon = CITY_COORDS.get(city, (None, None))
    latest_date = pd.Timestamp(manifest["latest_observation_date"]).normalize()
    data_age_days = max(0, int((pd.Timestamp.today().normalize() - latest_date).days))
    return clean({
        "city": city, "slug": art.name, "lat": lat, "lon": lon,
        "is_demo": bool(manifest.get("is_demo")),
        "experimental_short_history": bool(manifest.get("experimental_short_history")),
        "data_age_days": data_age_days, "is_stale": data_age_days > 3,
        "minimum_samples_required": manifest.get("minimum_samples_required", 450),
        "usable_samples": manifest.get("usable_samples", {}),
        "provenance": manifest.get("provenance"),
        "source_file": manifest.get("source_file"),
        "issue_rule": manifest.get("forecast_issue_time_definition"),
        "selection_basis": manifest.get("selection_basis"),
        "champions": manifest.get("champions"), "candidates": manifest.get("candidates"),
        "latest": {"date": manifest["latest_observation_date"], "aqi": float(manifest["latest_observed_aqi"]),
                   "category": aqi_category(float(manifest["latest_observed_aqi"]))},
        "forecasts": forecasts,
        "history": records(history) if not history.empty else [],
        "metrics_holdout": records(hold),
        "metrics_walk_forward": records(wf) if not wf.empty else [],
        "holdout_sample_h1": sample,
        "quality": quality,
        "shap": shap,
    })


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifacts", default=str(ROOT / "artifacts"))
    ap.add_argument("--out", default=str(ROOT / "web" / "public" / "data"))
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cities = []
    for art in sorted(Path(a.artifacts).glob("*/manifest.json")):
        bundle = export_city(art.parent)
        (out / f"{bundle['slug']}.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        f1 = bundle["forecasts"][0] if bundle["forecasts"] else None
        cities.append({"city": bundle["city"], "slug": bundle["slug"], "lat": bundle["lat"], "lon": bundle["lon"],
                       "latest_aqi": bundle["latest"]["aqi"], "latest_date": bundle["latest"]["date"],
                       "next_aqi": f1["aqi"] if f1 else None, "is_demo": bundle["is_demo"],
                       "experimental_short_history": bundle["experimental_short_history"]})
        print(f"exported {bundle['city']}: {len(bundle['forecasts'])} forecasts, {len(bundle['history'])} history days")
    index = {"cities": cities,
             "categories": [{"low": lo, "high": (None if math.isinf(hi) else hi), "label": lab, "colour": col}
                            for lo, hi, lab, col in CATEGORIES],
             "any_demo": any(c["is_demo"] for c in cities)}
    (out / "index.json").write_text(json.dumps(clean(index), ensure_ascii=False), encoding="utf-8")
    return 0 if cities else 1


if __name__ == "__main__":
    raise SystemExit(main())
