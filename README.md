# Indian City AQI Forecasting Dashboard

A runnable Streamlit product for direct **day +1, +2 and +3** daily AQI forecasts. It validates CPCB-format data, uses leakage-aware direct-horizon features, compares a no-training persistence baseline with XGBoost, selects a model separately for each horizon using training-only walk-forward validation, evaluates on a final chronological holdout, and generates SHAP explanations for selected tree models.

> **Current data status:** no CPCB data or existing code/model was present in the supplied workspace; only the presentation was found. The checked-in `data/demo_cpcb_format_NOT_OFFICIAL.csv` and generated demo artifacts are synthetic and visibly labelled. They verify the software flow only. Do not cite their metrics as project results.

## Model decision

**Initial primary candidate: XGBoost. Mandatory benchmark: persistence.**

There is no trustworthy, generally transferable pretrained model that directly predicts CPCB city-level daily AQI. Microsoft Aurora forecasts global atmospheric composition, not CPCB's city bulletin AQI target, and cannot be substituted without a validated conversion/evaluation. This project can load already fitted `joblib` artifacts, but a city-specific fit is required for defensible CPCB forecasts.

A GitHub and Hugging Face search was completed. The evidence and rejection reasons are documented in [`docs/PRETRAINED_MODEL_AUDIT.md`](docs/PRETRAINED_MODEL_AUDIT.md). The closest hosted India model uses same-day pollutant inputs to estimate same-day AQI and therefore does not meet the forecast-time contract.

| Candidate | What it tests | Initial status |
|---|---|---|
| Persistence | Strong autocorrelation baseline; day +1/+2/+3 = latest AQI | Implemented; no training |
| XGBoost | Nonlinear lag, rolling and seasonal relationships | Implemented; initial primary candidate |
| Linear Regression | Whether a simple linear relationship is sufficient | Implemented; optional benchmark |
| Random Forest | Bagged nonlinear trees and robust interactions | Implemented; optional benchmark |
| LightGBM | Efficient boosted-tree alternative | Implemented; optional benchmark |
| LSTM | Sequence learning with longer histories | Experiment pending; not selected for v1 because no official history is attached and a deep model is not justified before tree baselines |
| Microsoft Aurora | Pretrained global atmospheric-composition forecast | Not a drop-in CPCB AQI model; excluded from v1 |

The deployed model is **not hard-coded as the winner**. For each horizon, the pipeline selects the candidate with the lowest nested walk-forward MAE using only the training period. The final 20% chronological holdout is report-only.

## Exact setup

Python **3.11 is recommended** (3.10–3.13 supported). Python 3.14 may compile scientific packages from source and take substantially longer.

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

## Run the included end-to-end demo

```bash
python scripts/generate_demo_data.py
python -m aqi_forecast.train \
  --data data/demo_cpcb_format_NOT_OFFICIAL.csv \
  --city Delhi \
  --models persistence,xgboost \
  --provenance "SYNTHETIC DEMO — NOT OFFICIAL CPCB DATA"

python -m aqi_forecast.train \
  --data data/demo_cpcb_format_NOT_OFFICIAL.csv \
  --city Chennai \
  --models persistence,xgboost \
  --provenance "SYNTHETIC DEMO — NOT OFFICIAL CPCB DATA"

streamlit run app.py
```

Open the URL printed by Streamlit (normally <http://localhost:8501>).

## Train with official CPCB daily bulletin history

Prepare a CSV derived from official CPCB daily bulletins with at least:

```csv
date,city,aqi
2021-01-01,Delhi,441
2021-01-02,Delhi,443
```

Use one row per city/day, ISO dates, and numeric AQI in the CPCB 0–500 range. Keep the raw bulletins and record their URLs/download dates. Then run:

```bash
python -m aqi_forecast.train \
  --data data/cpcb_daily_official.csv \
  --city Delhi \
  --models persistence,xgboost \
  --provenance "CPCB Daily AQI Bulletin archive; downloaded YYYY-MM-DD; SOURCE_URL"
streamlit run app.py
```

After the first official end-to-end run, compare every implemented classical candidate:

```bash
python -m aqi_forecast.train \
  --data data/cpcb_daily_official.csv \
  --city Delhi \
  --models persistence,linear_regression,random_forest,xgboost,lightgbm \
  --provenance "CPCB Daily AQI Bulletin archive; downloaded YYYY-MM-DD; SOURCE_URL"
```

Train every city with at least 450 valid observations:

```bash
python scripts/train_all_cities.py \
  --data data/cpcb_daily_official.csv \
  --models persistence,xgboost \
  --provenance "CPCB Daily AQI Bulletin archive; downloaded YYYY-MM-DD; SOURCE_URL"
```

## Optional historical weather

Open-Meteo observed/reanalysis daily temperature, wind and rain can be joined by city/date:

```bash
python -m aqi_forecast.weather \
  --data data/cpcb_daily_official.csv \
  --output data/cpcb_daily_with_weather.csv
```

The v1 pipeline treats these as **issue-day historical weather only**. It does not claim future weather was known. Future weather must come from archived forecasts generated at the historical issue time during backtesting; using today's reanalysis for a past forecast would leak information. Humidity, boundary-layer height, and optional NASA FIRMS fire counts are accepted as CSV columns but are only activated when sufficiently populated. Their collection pipelines remain pending.

## Forecast issue-time definition and leakage controls

- Issue time: immediately after the latest daily CPCB AQI observation is available.
- `aqi_latest`, lags 1/2/3/7 and rolling means use only observations on or before issue date.
- Calendar features describe each target date.
- Day +1/+2/+3 are separate direct models.
- No AQI interpolation or backward fill is performed.
- Hyperparameter search occurs within each outer training fold.
- Every candidate predicts the same chronological dates.
- The final 20% is held out from tuning and model selection.

## Outputs

For each city, `artifacts/<city>/` contains:

- `manifest.json` — source, issue rule, candidate list and selected models
- `data_quality.json` — duplicates, invalid values and missing-date report
- `metrics_walk_forward.csv` — training-period walk-forward metrics
- `metrics_holdout.csv` — final chronological holdout metrics
- `holdout_predictions.csv` — date-level measured test predictions
- `forecasts.csv` — current day +1/+2/+3 forecasts
- `model_h{1,2,3}_<candidate>.joblib` — fitted model and feature schema
- `shap_global_h*.csv`, `shap_local_h*.csv` — explanations when a tree model is selected

Metrics include MAE, RMSE, R², CPCB category accuracy, high-AQI (`observed > 200`) MAE/RMSE and event count, plus MAE improvement over persistence.

## Test and verification

```bash
# Full suite
pytest -q

# Individually
pytest -q -m unit
pytest -q -m integration
pytest -q -m e2e
```

For a standalone automated Streamlit smoke check after artifacts exist:

```bash
python scripts/verify_app.py
```

The verified demo run produced: 3 unit tests passed, 1 integration test passed, and 1 end-to-end test passed. The E2E test changes Delhi to Chennai, verifies all three forecast dates, verifies Delhi's >200 alert, and verifies the alert clears for Chennai. Streamlit's health endpoint also returned `ok` and the home page returned HTTP 200.

## Data-quality behavior

- Duplicate city/date rows are reported; the last row is retained.
- Invalid dates, blank cities, nonnumeric AQI and AQI outside 0–500 are rejected/reported.
- Missing dates are reported and remain missing; they are not silently imputed.
- The app warns on observations older than three days.
- An upload is validated but is never passed silently into an incompatible trained model.
- Unsupported cities require training before they appear in the selector.

## Current limitations

1. The attached official CPCB export covers only Anand Vihar station (January–October 2026), not Delhi city-wide AQI. It produces 177–183 usable samples by horizon, below the production requirement of 450. Its output is therefore shown only as a stale, short-history experimental run; persistence won training-only walk-forward selection for all three horizons.
2. Historical CPCB city-level data remains incomplete, so production performance and final city-model selection are blocked.
3. Automated extraction from changing CPCB PDF bulletin layouts is not included; v1 accepts auditable official CSV/Excel exports.
4. Archived forecast weather is not yet integrated, so future-weather predictors are intentionally excluded.
5. NASA FIRMS and boundary-layer-height collection are pending. LSTM is deferred until an official city series is long enough for a fair comparison.

Parse the supplied monthly station exports with:

```bash
python scripts/parse_cpcb_4pm_excel.py --input "data/New folder" --year 2026 \
  --city-label "Delhi — Anand Vihar station" \
  --output data/official/cpcb_anand_vihar_4pm_2026.csv
```

`--min-samples` exists for explicitly labelled research runs only. The production default remains 450.

## Web frontend (React + 3D)

A static single-page site in `web/` presents the same forecasts with motion and 3D: an AQI-driven smog skyline, 3-day forecast cards with empirical ranges, a 90-day trend, a 3D India map (Natural Earth India-view boundary), SHAP explanations in plain words, the model report (including the high-AQI caveat), the CPCB health guide, and data provenance. Demo data is labelled on every view. The Streamlit app stays the place to upload and validate CSVs.

```bat
run_web.bat
```

or step by step:

```bash
python scripts/export_web.py        # artifacts/<city>/ -> web/public/data/*.json
cd web && npm install && npm run build && npm run preview
```

`web/dist/` is fully static (relative paths), so it can be hosted on any static host (GitHub Pages, Netlify, an S3 bucket). Re-run `export_web.py` and `npm run build` after retraining. Likely range = 10th–90th percentile of the selected model's signed holdout errors for that horizon. `tests/test_export_web.py` checks the export. The 3D views fall back to plain layouts without WebGL and honour reduced-motion settings.
