from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests


def geocode_city(city: str) -> tuple[float, float]:
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json", "countryCode": "IN"},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError(f"Open-Meteo could not geocode {city!r} in India")
    return float(results[0]["latitude"]), float(results[0]["longitude"])


def fetch_historical_daily(city: str, start: str, end: str) -> pd.DataFrame:
    """Fetch historical observed/reanalysis weather, not archived forecasts.

    These variables are valid only as issue-day history. They must not be treated
    as future weather known at an earlier forecast issue time.
    """
    lat, lon = geocode_city(city)
    variables = "temperature_2m_mean,rain_sum,wind_speed_10m_mean"
    response = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                "daily": variables, "timezone": "Asia/Kolkata"}, timeout=60,
    )
    response.raise_for_status()
    daily = response.json()["daily"]
    return pd.DataFrame(daily).rename(columns={"time": "date"})


def enrich(csv_path: str, output: str) -> None:
    source = pd.read_csv(csv_path)
    source["date"] = pd.to_datetime(source["date"]).dt.date.astype(str)
    parts = []
    for city, group in source.groupby("city"):
        weather = fetch_historical_daily(city, group.date.min(), group.date.max())
        weather["date"] = pd.to_datetime(weather["date"]).dt.date.astype(str)
        parts.append(group.merge(weather, on="date", how="left"))
    pd.concat(parts, ignore_index=True).to_csv(output, index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    enrich(args.data, args.output)
    print(f"Weather-enriched CSV written to {args.output}")


if __name__ == "__main__":
    main()
