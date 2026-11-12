export type Forecast = {
  horizon: number; issue_date: string; forecast_date: string; aqi: number; category: string; model: string;
  range_low: number | null; range_high: number | null; holdout_n: number;
};
export type Metric = {
  horizon: number; model: string; mae: number; rmse: number; r2: number; category_accuracy: number;
  high_pollution_days: number; high_aqi_mae: number | null; high_aqi_rmse: number | null; n: number;
  mae_improvement_vs_persistence_pct: number;
};
export type ShapItem = { feature: string; label: string; value?: number; value_text?: string; shap?: number; mean_abs_shap?: number };
export type CityBundle = {
  city: string; slug: string; lat: number | null; lon: number | null; is_demo: boolean;
  experimental_short_history: boolean; data_age_days: number; is_stale: boolean;
  minimum_samples_required: number; usable_samples: Record<string, number>;
  provenance: string; source_file: string;
  issue_rule: string; selection_basis: string; champions: Record<string, string>; candidates: string[];
  latest: { date: string; aqi: number; category: string };
  forecasts: Forecast[]; history: { date: string; aqi: number }[];
  metrics_holdout: Metric[]; metrics_walk_forward: Metric[];
  holdout_sample_h1: { date: string; observed: number; predicted: number; persistence: number | null }[];
  quality: Record<string, unknown>;
  shap: Record<string, { global: ShapItem[]; local: ShapItem[] }>;
};
export type CityIndex = { city: string; slug: string; lat: number | null; lon: number | null; latest_aqi: number; latest_date: string; next_aqi: number | null; is_demo: boolean; experimental_short_history: boolean };
export type Index = { cities: CityIndex[]; any_demo: boolean };

const cache = new Map<string, Promise<unknown>>();
export function getJSON<T>(path: string): Promise<T> {
  if (!cache.has(path)) cache.set(path, fetch(`./data/${path}`).then((r) => { if (!r.ok) throw new Error(`${path}: ${r.status}`); return r.json(); }));
  return cache.get(path) as Promise<T>;
}
