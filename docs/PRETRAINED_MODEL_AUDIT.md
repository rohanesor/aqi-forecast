# Pretrained AQI Model Audit

Audit date: 2026-11-12

## Acceptance criteria

A reusable artifact must:

1. Predict CPCB city-level daily AQI at explicit day +1/+2/+3 horizons.
2. Use only information available at forecast issuance.
3. Document official CPCB provenance, feature order, preprocessing and licence.
4. Provide chronological evaluation against persistence on matching forecast dates.
5. Be compatible with our city/date distribution or pass a local CPCB holdout test.

## Repositories and models inspected

| Candidate | Evidence | Finding | Decision |
|---|---|---|---|
| [AdityaaXD/AQI-Prediction-Model-Of-India](https://huggingface.co/AdityaaXD/AQI-Prediction-Model-Of-India) and [GitHub source](https://github.com/ADITYA-tp01/AQI-Prediction-Model) | XGBoost pickle; model card claims 2015–2020 `city_day.csv`, R² 0.925, MAE 11.42, RMSE 22.90. GitHub has 0 stars/forks at audit. | Notebook target is same-row AQI and includes same-day PM2.5, PM10 and other pollutant columns plus interactions. Pollutants are interpolated in both directions and global cleaning occurs before the temporal split. It is therefore primarily same-day AQI estimation, not a day-ahead forecast. Published metrics are self-reported/unverified and no persistence comparison is provided. Dataset is a hosted `city_day.csv`, not the requested CPCB daily-bulletin archive. | **Reject for deployment.** Useful only as untrusted research reference. |
| [KISHOREAFK/AQI-Predicter-Delhi](https://huggingface.co/KISHOREAFK/AQI-Predicter-Delhi) | Delhi XGBoost JSON, scaler and encoders; model card says weather and current pollutant inputs. | Inference fetches current WAQI pollutant values and estimates current AQI. It has no explicit +1/+2/+3 target, no CPCB bulletin provenance, no documented temporal benchmark, and no persistence comparison. | **Reject.** It is a nowcast/estimator, not our forecast target. |
| [AbhishekLim17/ahmedabad-aqi-model](https://huggingface.co/AbhishekLim17/ahmedabad-aqi-model) | XGBoost pickle plus metadata; lag-only feature schema. Metadata reports MAE 35.31, 305 train rows and 60 test rows. | Ahmedabad-specific, very small history, no model card/source provenance, no licence visible in metadata, no horizon definition, no persistence result, and pickle deserialization carries supply-chain risk. | **Reject for direct loading.** Could be compared only in an isolated environment after provenance is supplied. |
| [lavenhub/Air_Quality_Forecasting_RanForReg](https://huggingface.co/lavenhub/Air_Quality_Forecasting_RanForReg) | Random-forest pickle and Streamlit app. | Predicts next-day PM2.5 from manually entered pollutants; not CPCB AQI and no India/CPCB validation. | **Reject.** Wrong target. |
| [Microsoft Aurora / “A foundation model for the Earth system”](https://doi.org/10.1038/s41586-025-09005-y) | Published global 5-day atmospheric-composition model at 0.4° resolution. | Predicts atmospheric species/particulate variables, not CPCB city daily AQI. Converting gridded concentrations to a CPCB bulletin target requires downscaling, pollutant breakpoint calculation and local validation. | **Do not use as a drop-in model.** Potential future exogenous forecast source. |

## GitHub search result

GitHub searches found many AQI notebooks/apps but no versioned, documented pretrained artifact satisfying all acceptance criteria. Common problems were synthetic data, China/US AQI scales, current-pollutant AQI estimation, absent issue-time definitions, and no persistence benchmark.

## Hugging Face search result

The most relevant India-tagged artifact was `AdityaaXD/AQI-Prediction-Model-Of-India`. It cannot safely support this product’s day +1/+2/+3 forecasts for the reasons above. Other results had zero or negligible downloads, sparse/absent model cards, incompatible targets, or unknown provenance.

## Security note

Do not deserialize third-party `.pkl`/`.joblib` files in the application process. Python pickle can execute code. Any future candidate must be downloaded with a pinned revision and checksum, scanned, and tested in an isolated environment. Prefer XGBoost JSON/UBJSON or ONNX plus a separately validated feature contract.

## Decision

Keep **persistence + locally fitted XGBoost** for v1. The pipeline may load our own versioned artifacts. A third-party pretrained model can be added only as a challenger after it passes the same official-CPCB chronological holdout and persistence benchmark; it must never be promoted solely from self-reported repository metrics.
