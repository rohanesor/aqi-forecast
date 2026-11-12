from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import plotly.express as px
import streamlit as st

from aqi_forecast.categories import aqi_category, category_colour
from aqi_forecast.data import load_daily_aqi

st.set_page_config(page_title="India AQI Forecast", page_icon="🌫️", layout="wide")


@st.cache_data

def discover_artifacts(root: str = "artifacts") -> dict[str, dict]:
    found = {}
    for path in Path(root).glob("*/manifest.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["artifact_dir"] = str(path.parent)
        found[manifest["city"]] = manifest
    return found


@st.cache_data

def read_city_bundle(artifact_dir: str):
    p = Path(artifact_dir)
    manifest = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
    manifest["artifact_dir"] = str(p)
    forecasts = pd.read_csv(p / "forecasts.csv", parse_dates=["issue_date", "forecast_date"])
    metrics = pd.read_csv(p / "metrics_holdout.csv")
    quality = json.loads((p / "data_quality.json").read_text(encoding="utf-8"))
    source_path = Path(manifest["source_file"])
    history = pd.DataFrame()
    if source_path.exists():
        history, _ = load_daily_aqi(source_path, provenance=manifest["provenance"])
        history = history.loc[history.city == manifest["city"]].sort_values("date")
    return manifest, forecasts, metrics, quality, history


def forecast_card(row) -> str:
    value = float(row.predicted_aqi)
    category = aqi_category(value)
    colour = category_colour(value)
    text = "#111" if category in {"Good", "Satisfactory", "Moderate", "Poor"} else "#fff"
    return f"""
    <div data-testid="forecast-card-h{int(row.horizon)}" style="background:{colour};color:{text};padding:18px;
         border-radius:14px;min-height:165px;box-shadow:0 2px 8px #0002">
      <div style="font-size:15px;font-weight:700">DAY +{int(row.horizon)} · {row.forecast_date:%d %b %Y}</div>
      <div style="font-size:48px;font-weight:800;line-height:1.15">{value:.0f}</div>
      <div style="font-size:20px;font-weight:700">{category}</div>
      <div style="font-size:12px;margin-top:8px">Model: {row.model}</div>
    </div>"""


st.title("Air Quality Index Forecasting Dashboard")
st.caption("Direct day +1, +2 and +3 city forecasts · CPCB category scale")

artifacts = discover_artifacts()
if not artifacts:
    st.error("No trained artifacts found. Run the training command in README.md, then refresh.")
    st.stop()

with st.sidebar:
    st.header("Forecast controls")
    city = st.selectbox("City", sorted(artifacts))
    st.divider()
    st.subheader("Validate a CPCB-format CSV")
    uploaded = st.file_uploader("CSV with date, city, aqi", type="csv")
    if uploaded:
        try:
            _, upload_report = load_daily_aqi(uploaded, provenance="User upload", source_name=uploaded.name)
            st.success(f"{upload_report.rows_valid:,} valid rows")
            st.json(upload_report.to_dict(), expanded=False)
            st.info("To forecast this file, train versioned artifacts with the README command. Uploads are not silently passed to an incompatible model.")
        except Exception as exc:
            st.error(str(exc))

manifest, forecasts, metrics, quality, history = read_city_bundle(artifacts[city]["artifact_dir"])

if manifest.get("is_demo"):
    st.warning("DEMO MODE — synthetic data, not official CPCB observations. Metrics and predictions are for software verification only.")

latest_date = pd.Timestamp(manifest["latest_observation_date"])
latest_aqi = float(manifest["latest_observed_aqi"])
stale_days = (pd.Timestamp.today().normalize() - latest_date).days
if stale_days > 3:
    st.warning(f"Observations are stale by {stale_days} days. Treat forecasts as unavailable for operational use.")

left, right = st.columns([1, 2])
with left:
    st.metric("Latest observed AQI", f"{latest_aqi:.0f}", help=f"Observation date: {latest_date.date()}")
    st.write(f"**Observation date:** {latest_date:%d %b %Y}")
    st.write(f"**Forecast issue date:** {forecasts.issue_date.max():%d %b %Y}")
    st.write(f"**City:** {city}")
with right:
    if not history.empty:
        recent = history.tail(90)
        fig = px.line(recent, x="date", y="aqi", title="Recent daily AQI trend", markers=False)
        fig.add_hline(y=200, line_dash="dash", line_color="#E53935", annotation_text="AQI 200")
        fig.update_layout(height=310, margin=dict(l=10, r=10, t=45, b=10), yaxis_range=[0, max(250, recent.aqi.max() * 1.1)])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("The source history file is unavailable; forecast artifacts remain viewable.")

st.subheader("Three-day AQI forecast")
forecasts = forecasts.sort_values("horizon")
if set(forecasts.horizon) != {1, 2, 3}:
    st.error("Prediction bundle is incomplete. Expected day +1, +2 and +3.")
else:
    cols = st.columns(3)
    for col, row in zip(cols, forecasts.itertuples()):
        with col:
            st.markdown(forecast_card(row), unsafe_allow_html=True)

    over_200 = forecasts.loc[forecasts.predicted_aqi > 200]
    if len(over_200):
        days = ", ".join(f"day +{int(h)}" for h in over_200.horizon)
        st.error(f"⚠ HIGH AQI ALERT: predicted AQI exceeds 200 on {days}. Reduce prolonged outdoor exposure and follow local authority guidance.")
    else:
        st.success("No forecast currently exceeds AQI 200.")

performance_tab, explanation_tab, data_tab = st.tabs(["Model performance", "Explanation", "Data & provenance"])
with performance_tab:
    st.caption("Final chronological 20% holdout. Champion selection used training-only walk-forward MAE.")
    show = metrics[["horizon", "model", "mae", "rmse", "r2", "category_accuracy",
                    "high_pollution_days", "high_aqi_mae", "high_aqi_rmse",
                    "mae_improvement_vs_persistence_pct"]].copy()
    st.dataframe(show.style.format({"mae": "{:.2f}", "rmse": "{:.2f}", "r2": "{:.3f}",
                                    "category_accuracy": "{:.1%}", "high_aqi_mae": "{:.2f}",
                                    "high_aqi_rmse": "{:.2f}", "mae_improvement_vs_persistence_pct": "{:.1f}%"}),
                 use_container_width=True, hide_index=True)
    st.write("**Selected models by horizon:**", manifest["champions"])
    if manifest.get("is_demo"):
        st.info("These are synthetic demonstration metrics and are not CPCB project results.")

with explanation_tab:
    horizon = st.selectbox("Explain forecast", [1, 2, 3], format_func=lambda h: f"Day +{h}")
    p = Path(manifest["artifact_dir"])
    global_path, local_path = p / f"shap_global_h{horizon}.csv", p / f"shap_local_h{horizon}.csv"
    if global_path.exists() and local_path.exists():
        global_df = pd.read_csv(global_path).head(12).sort_values("mean_abs_shap")
        st.plotly_chart(px.bar(global_df, x="mean_abs_shap", y="feature", orientation="h",
                               title="Global mean absolute SHAP contribution"), use_container_width=True)
        local_df = pd.read_csv(local_path).head(12).sort_values("shap_value")
        local_df["direction"] = local_df.shap_value.map(lambda x: "Pushes AQI higher" if x > 0 else "Pushes AQI lower")
        st.plotly_chart(px.bar(local_df, x="shap_value", y="feature", color="direction", orientation="h",
                               title="Contributions for the current forecast",
                               color_discrete_map={"Pushes AQI higher": "#E53935", "Pushes AQI lower": "#2E7D32"}),
                        use_container_width=True)
        st.caption("SHAP describes model contributions, not causal effects. Correlated features can share attribution.")
    else:
        st.info("SHAP is unavailable because the selected horizon uses persistence/non-tree output or explanation generation failed.")

with data_tab:
    st.write(f"**Provenance:** {manifest['provenance']}")
    st.write(f"**Source file:** `{manifest['source_file']}`")
    st.write(f"**Issue-time rule:** {manifest['forecast_issue_time_definition']}")
    st.json(quality)
    st.caption("Future weather is not used in this first version. Archived issue-time forecasts are required before future-weather predictors can be backtested without leakage.")
