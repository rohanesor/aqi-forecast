"""Pre-compute 'what-if' predictions for a range of today's AQI values.

For each city with a trained model, vary aqi_latest from 0..500 in steps of 5,
hold all other features at their latest real values, and run the trained models.
Output: web/public/data/whatif_<slug>.json
"""
from __future__ import annotations
import json, sys, math
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aqi_forecast.categories import aqi_category  # noqa: E402

STEP = 5
AQI_RANGE = list(range(0, 501, STEP))


def load_city(art_dir: Path) -> dict | None:
    manifest = json.loads((art_dir / "manifest.json").read_text())
    city = manifest["city"]
    champions = manifest.get("champions", {})
    
    results = {"city": city, "slug": art_dir.name, "horizons": {}}
    
    for h in (1, 2, 3):
        champ = champions.get(str(h))
        if not champ or champ == "persistence":
            # Persistence: prediction = input AQI
            results["horizons"][str(h)] = {
                "model": "persistence",
                "predictions": {str(a): a for a in AQI_RANGE}
            }
            continue
        
        model_path = art_dir / f"model_h{h}_{champ}.joblib"
        if not model_path.exists():
            continue
        
        bundle = joblib.load(model_path)
        model = bundle["model"]
        features = bundle["features"]
        
        # Load the latest real feature row from forecasts to get base values
        fc = pd.read_csv(art_dir / "forecasts.csv")
        fc_h = fc[fc.horizon == h].iloc[0] if len(fc[fc.horizon == h]) > 0 else None
        
        # We need a base feature vector. Load from the city's data
        src = ROOT / manifest["source_file"]
        if src.exists():
            df = pd.read_csv(src, parse_dates=["date"])
            city_data = df[df.city == city].sort_values("date")
            latest_row = city_data.iloc[-1] if len(city_data) > 0 else None
        else:
            latest_row = None
        
        # Build base feature dict from what the model expects
        base = {}
        if latest_row is not None:
            aqi_series = city_data["aqi"].values
            base["aqi_latest"] = float(aqi_series[-1]) if len(aqi_series) > 0 else 100.0
            for lag in (1, 2, 3, 7):
                key = f"aqi_lag_{lag}"
                if key in features:
                    base[key] = float(aqi_series[-(lag+1)]) if len(aqi_series) > lag else base.get("aqi_latest", 100.0)
            for window in (3, 7, 14):
                key = f"aqi_mean_{window}"
                if key in features:
                    vals = aqi_series[-window:] if len(aqi_series) >= window else aqi_series
                    base[key] = float(np.nanmean(vals))
        
        # Calendar features: use today's date + horizon
        today = pd.Timestamp.today().normalize()
        target = today + pd.Timedelta(days=h)
        cal = {
            "target_month": target.month,
            "target_season": {12:0,1:0,2:0,3:1,4:1,5:1,6:2,7:2,8:2,9:2,10:3,11:3}[target.month],
            "target_day_of_week": target.dayofweek,
            "target_diwali": 0,
            "target_day_of_year": target.dayofyear,
        }
        base.update(cal)
        
        predictions = {}
        for aqi_in in AQI_RANGE:
            row = base.copy()
            row["aqi_latest"] = float(aqi_in)
            # Also adjust lag_1 and rolling means proportionally
            if "aqi_lag_1" in features:
                row["aqi_lag_1"] = float(aqi_in) * 0.95  # slight decay
            for window in (3, 7, 14):
                key = f"aqi_mean_{window}"
                if key in features:
                    # Blend: 1/window of new value + rest of original mean
                    orig = base.get(key, aqi_in)
                    row[key] = (aqi_in + orig * (window - 1)) / window
            
            x = pd.DataFrame([{f: row.get(f, 0.0) for f in features}])
            pred = float(model.predict(x)[0])
            pred = max(0.0, min(500.0, pred))
            predictions[str(aqi_in)] = round(pred, 1)
        
        results["horizons"][str(h)] = {
            "model": champ,
            "predictions": predictions
        }
    
    return results


def main():
    out_dir = ROOT / "web" / "public" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    index = {"cities": [], "aqi_range": AQI_RANGE, "step": STEP}
    
    for art in sorted(ROOT.glob("artifacts/*/manifest.json")):
        art_dir = art.parent
        result = load_city(art_dir)
        if result:
            fname = f"whatif_{result['slug']}.json"
            (out_dir / fname).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            index["cities"].append({"city": result["city"], "slug": result["slug"], "file": fname})
            parts = [f'h{h}={d["model"]}' for h, d in result['horizons'].items()]
            print(f"  {result['city']}: {', '.join(parts)}")
    
    (out_dir / "whatif_index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(index['cities'])} what-if bundles")


if __name__ == "__main__":
    main()
