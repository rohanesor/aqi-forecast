"""Convert official CPCB monthly AQI Excel exports to a 4 PM daily series.

Expected filenames resemble:
AQI_Data_Station_Level_Site_301_Anand_Vihar_Delhi_DPCC_January_Daily.xlsx

Prefer placing files in a directory named with the data year (for example,
data/cpcb_downloads/2024/). Otherwise --year is required; relying on workbook
creation year is deliberately not supported because files can be regenerated later.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

MONTHS = {name: number for number, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1
)}


def month_from_name(path: Path) -> int:
    for name, number in MONTHS.items():
        if re.search(fr"(?:^|_){name}(?:_|\.)", path.name, re.IGNORECASE):
            return number
    raise ValueError(f"Month not found in filename: {path.name}")


def parse_directory(source_dir: Path, year: int, city_label: str, hour: str = "16:00") -> pd.DataFrame:
    rows = []
    files = sorted(source_dir.glob("*.xlsx"))
    if not files:
        raise ValueError(f"No .xlsx files found in {source_dir}")
    for path in files:
        month = month_from_name(path)
        frame = pd.read_excel(path, sheet_name="AQI")
        frame.columns = [str(column).strip() for column in frame.columns]
        if "Date" not in frame or hour not in frame:
            raise ValueError(f"{path.name} must contain Date and {hour} columns")
        for day, value in zip(frame["Date"], frame[hour]):
            day = pd.to_numeric(pd.Series([day]), errors="coerce").iloc[0]
            value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
            if pd.isna(day):
                continue
            try:
                observation_date = pd.Timestamp(year=year, month=month, day=int(day))
            except ValueError:
                continue
            rows.append({
                "date": observation_date.date().isoformat(),
                "city": city_label,
                "aqi": value,
                "source_file": path.name,
                "source_type": "Official CPCB station-level AQI export",
                "issue_hour_ist": hour,
            })
    result = pd.DataFrame(rows).sort_values("date").drop_duplicates(["date", "city"], keep="last")
    result = result.loc[result.aqi.between(0, 500) | result.aqi.isna()].reset_index(drop=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--city-label", default="Delhi — Anand Vihar station")
    parser.add_argument("--hour", default="16:00")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = parse_directory(args.input, args.year, args.city_label, args.hour)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(f"Wrote {len(result)} rows to {args.output}")
    print(f"Valid AQI: {result.aqi.notna().sum()}, missing AQI: {result.aqi.isna().sum()}")
    print(f"Range: {result.date.min()} to {result.date.max()}")


if __name__ == "__main__":
    main()
