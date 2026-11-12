import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aqi_forecast.data import load_daily_aqi
from aqi_forecast.train import train_city

parser = argparse.ArgumentParser()
parser.add_argument("--data", required=True)
parser.add_argument("--output", default="artifacts")
parser.add_argument("--provenance", required=True)
parser.add_argument("--models", default="persistence,xgboost")
args = parser.parse_args()

df, report = load_daily_aqi(args.data, provenance=args.provenance)
models = [x.strip() for x in args.models.split(",") if x.strip()]
for city in report.cities:
    if (df.city == city).sum() >= 450:
        print(f"Training {city}...")
        train_city(args.data, city, args.output, args.provenance, models)
    else:
        print(f"Skipping {city}: fewer than 450 valid observations")
