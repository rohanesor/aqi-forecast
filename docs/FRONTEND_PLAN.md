# AQI Forecast — Frontend audit & plan (v1 draft)

## Audit summary
- Backend is solid and stays as is: leakage-aware direct day +1/+2/+3 models, persistence benchmark, walk-forward selection,
  20 % holdout, SHAP, data-quality reports, tests (unit/integration/e2e). All results land in `artifacts/<city>/`.
- Data: only synthetic demo data for Delhi + Chennai (2019-01-01 → 2026-11-12). Official CPCB history still missing —
  every screen must keep the DEMO label until it is replaced.
- Current frontend = default Streamlit page (app.py, ~170 lines): plain coloured cards, default Plotly charts,
  raw feature names in SHAP (`aqi_lag_1`), no health guidance, no map, no uncertainty, colour-only category cue,
  history and forecast on separate visuals, desktop-only layout.
- Slide deck promises station / state visuals and a "real-time dashboard" — the app has neither.
- Model note worth showing honestly: on Delhi demo data XGBoost beats persistence overall (h1 MAE 6.86 vs 7.86) but
  is worse on AQI > 200 days (8.74 vs 7.33).

## Architecture
artifacts/ --(scripts/export_web.py)--> web/public/data/*.json --> React app (Vite + TypeScript)
- No server needed for viewing: static site, deployable to Vercel / GitHub Pages / S3+CloudFront.
- Streamlit stays as the analyst/validation tool (CSV upload checks).
- Optional later: FastAPI `/forecast/{city}` for live retraining.

## Stack (our tools)
- React + Vite + TypeScript, Tailwind tokens for the CPCB colour scale.
- Motion: Framer Motion (page/scroll), GSAP for number roll-ups and timeline scrubbing.
- 3D: Three.js / react-three-fiber — smog particle field whose density, colour and drift follow the AQI;
  India map with extruded city pillars (height = AQI, colour = category).
- Charts: visx / Recharts restyled (history + forecast on one line, uncertainty band, AQI 200 threshold).
- Blender: low-poly city skyline / India relief asset exported to GLB for the hero.
- Remotion: 30–45 s product promo of the dashboard for the review / LinkedIn.

## Screens
1. Hero — 3D city in smog that clears or thickens with the selected city's forecast; big animated AQI number, category,
   one-line health advice; DEMO badge.
2. 3-day forecast strip — cards with category, change vs today, honest range from holdout residuals (p10–p90).
3. Trend — last 90 days + 3 forecast days on one chart, threshold lines, hover details.
4. India map — 3D pillars per trained city; click to switch city.
5. Why this forecast — SHAP in plain words ("Yesterday's AQI 267 pushed the forecast up by +68").
6. Model report — persistence vs XGBoost per horizon, high-AQI performance, walk-forward vs holdout.
7. Data & provenance — source, quality checks, issue-time rule, demo warning.
8. Health guide — CPCB category table with advice for general public and sensitive groups.

## Phases
1. Export script + JSON schema + tests (backend untouched).
2. Design system + layout + mobile.
3. Motion pass (load sequence, scroll reveals, number roll-ups, card transitions).
4. 3D pass (smog field, India map, Blender skyline) with low-power fallback and prefers-reduced-motion.
5. QA: Playwright screenshots desktop + mobile, Lighthouse, accessibility (category text + icon, not colour only).
6. Deploy + Remotion promo.
