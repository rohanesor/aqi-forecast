import { AnimatePresence, motion } from 'framer-motion';
import { useMemo, useState } from 'react';
import { Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { CATS, cat, fmtDate } from '../aqi';
import { CityBundle } from '../data';
import { Chip, Counter, Glyph, Reveal, Section } from './ui';

const MODEL_NAME: Record<string, string> = { persistence: 'Persistence (tomorrow = today)', xgboost: 'XGBoost', linear_regression: 'Linear regression', random_forest: 'Random forest', lightgbm: 'LightGBM' };
const mname = (m: string) => MODEL_NAME[m] ?? m;
const tip = { contentStyle: { background: '#0f1526', border: '1px solid #26304d', borderRadius: 10, color: '#e9edf7' }, labelStyle: { color: '#9aa6c4' } };

// ------------------------------------------------------------------------------------------------ 3-day forecast
export function ForecastCards({ b, day, setDay, reduced }: { b: CityBundle; day: number; setDay: (d: number) => void; reduced: boolean }) {
  return (
    <Section id="forecast" kicker="Next three days" title={`${b.city}: what the air will look like`}
      intro={<>Each day has its own model. The range shows where 80% of this model's past errors fell on held-out days. It is an honest spread, not a guarantee.</>}>
      <div className="cards">
        {b.forecasts.map((f, i) => {
          const c = cat(f.aqi); const d = f.aqi - b.latest.aqi; const lo = f.range_low ?? f.aqi, hi = f.range_high ?? f.aqi;
          return (
            <Reveal key={f.horizon} delay={i * 0.08}>
              <motion.button className={`card ${day === f.horizon ? 'sel' : ''}`} onClick={() => setDay(f.horizon)} whileHover={reduced ? {} : { y: -6 }} whileTap={{ scale: 0.98 }}
                style={{ ['--c' as string]: c.colour }} aria-pressed={day === f.horizon}>
                <div className="card-top"><span>Day +{f.horizon}</span><span>{fmtDate(f.forecast_date)}</span></div>
                <div className="card-aqi"><Counter value={f.aqi} reduced={reduced} /></div>
                <Chip aqi={f.aqi} />
                <div className={`delta ${d > 0 ? 'up' : 'down'}`}>{d > 0 ? '▲' : '▼'} {Math.abs(d).toFixed(0)} vs today ({Math.round(b.latest.aqi)})</div>
                <div className="range" aria-label={`Likely range ${Math.round(lo)} to ${Math.round(hi)}`}>
                  <div className="range-track">
                    {CATS.map((k) => <i key={k.label} style={{ background: k.colour, width: `${((Math.min(k.high, 500) - k.low + 1) / 501) * 100}%` }} />)}
                    <motion.b initial={false} animate={{ left: `${(lo / 500) * 100}%`, width: `${Math.max(0.6, ((hi - lo) / 500) * 100)}%` }} />
                    <motion.em initial={false} animate={{ left: `${(f.aqi / 500) * 100}%` }} />
                  </div>
                  <div className="range-txt">Likely {Math.round(lo)}–{Math.round(hi)}</div>
                </div>
                <div className="card-advice">{c.advice}</div>
                <div className="card-model">Model: {mname(f.model)}</div>
              </motion.button>
            </Reveal>
          );
        })}
      </div>
      {b.forecasts.some((f) => f.aqi > 200) && (
        <Reveal><div className="alert" role="alert"><Glyph name="Severe" /> <b>High AQI alert:</b>&nbsp;AQI above 200 is forecast on {b.forecasts.filter((f) => f.aqi > 200).map((f) => fmtDate(f.forecast_date)).join(', ')}. Reduce prolonged outdoor exertion and follow local advisories.</div></Reveal>
      )}
    </Section>
  );
}

// ------------------------------------------------------------------------------------------------ trend
export function Trend({ b }: { b: CityBundle }) {
  const data = useMemo(() => {
    const h = b.history.slice(-90).map((r) => ({ date: r.date, observed: r.aqi } as Record<string, number | string | null>));
    const last = h[h.length - 1];
    if (last) { last.forecast = last.observed as number; last.band = [last.observed as number, last.observed as number] as unknown as number; }
    for (const f of b.forecasts) h.push({ date: f.forecast_date, forecast: f.aqi, band: [f.range_low ?? f.aqi, f.range_high ?? f.aqi] as unknown as number });
    return h;
  }, [b]);
  const max = Math.max(250, ...data.map((d) => Number(d.observed ?? d.forecast ?? 0))) * 1.08;
  return (
    <Section id="trend" kicker="Trend" title="Last 90 days and the next 3"
      intro="Solid line: observed daily AQI. Dashed line: forecast, with the likely range shaded. Background bands are the CPCB categories.">
      <Reveal className="panel chart-tall">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 16, left: -10, bottom: 0 }}>
            {CATS.map((k) => <ReferenceArea key={k.label} y1={k.low} y2={Math.min(k.high, max)} fill={k.colour} fillOpacity={0.11} ifOverflow="hidden" />)}
            <CartesianGrid stroke="#1e2742" vertical={false} />
            <XAxis dataKey="date" tickFormatter={(d) => fmtDate(d, { day: 'numeric', month: 'short' })} stroke="#6f7c9e" fontSize={12} minTickGap={40} />
            <YAxis domain={[0, Math.round(max)]} stroke="#6f7c9e" fontSize={12} />
            <Tooltip {...tip} labelFormatter={(d) => fmtDate(String(d), { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
              formatter={(v: unknown, n: string) => Array.isArray(v) ? [`${Math.round(v[0])}–${Math.round(v[1])}`, 'Likely range'] : [Math.round(Number(v)), n === 'observed' ? 'Observed' : 'Forecast']} />
            <ReferenceLine y={200} stroke="#FF9900" strokeDasharray="5 5" label={{ value: 'AQI 200', fill: '#FF9900', fontSize: 11, position: 'insideTopLeft' }} />
            <Area dataKey="band" stroke="none" fill="#8fb3ff" fillOpacity={0.25} isAnimationActive />
            <Line dataKey="observed" stroke="#e9edf7" strokeWidth={2} dot={false} isAnimationActive animationDuration={1400} />
            <Line dataKey="forecast" stroke="#8fb3ff" strokeWidth={2.5} strokeDasharray="6 5" dot={{ r: 4, fill: '#8fb3ff' }} isAnimationActive animationBegin={900} />
          </ComposedChart>
        </ResponsiveContainer>
      </Reveal>
    </Section>
  );
}

// ------------------------------------------------------------------------------------------------ explanation
export function Explain({ b, day, setDay }: { b: CityBundle; day: number; setDay: (d: number) => void }) {
  const s = b.shap[String(day)];
  const f = b.forecasts.find((x) => x.horizon === day);
  const local = s ? [...s.local].sort((a, c) => Math.abs(c.shap ?? 0) - Math.abs(a.shap ?? 0)) : [];
  const maxAbs = Math.max(1, ...local.map((x) => Math.abs(x.shap ?? 0)));
  return (
    <Section id="why" kicker="Why this forecast" title="What pushed the number up or down"
      intro="SHAP breaks the model's prediction into contributions from each input. It describes how the model reasons, not what causes pollution. Inputs that move together can share credit.">
      <Tabs day={day} setDay={setDay} />
      {!s ? <div className="panel muted">No explanation for this day: the selected model is not a tree model.</div> : (
        <div className="explain">
          <Reveal className="panel">
            <h3>Day +{day} forecast: <b>{Math.round(f?.aqi ?? 0)}</b></h3>
            <ul className="shap">
              <AnimatePresence mode="popLayout">
                {local.map((x, i) => {
                  const v = x.shap ?? 0; const up = v > 0;
                  return (
                    <motion.li key={day + x.feature} layout initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ delay: i * 0.05 }}>
                      <div className="shap-txt"><b>{x.label}</b> was <b>{x.value_text}</b> <span className={up ? 'up' : 'down'}>{up ? 'pushed it up' : 'pulled it down'} by {Math.abs(v).toFixed(1)}</span></div>
                      <div className="shap-bar"><motion.i className={up ? 'up' : 'down'} initial={{ width: 0 }} animate={{ width: `${(Math.abs(v) / maxAbs) * 100}%` }} transition={{ duration: 0.8, delay: 0.1 + i * 0.05 }} /></div>
                    </motion.li>
                  );
                })}
              </AnimatePresence>
            </ul>
          </Reveal>
          <Reveal className="panel" delay={0.1}>
            <h3>What this model relies on overall</h3>
            <div className="chart-mid">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={s.global.slice(0, 7)} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <XAxis type="number" stroke="#6f7c9e" fontSize={11} />
                  <YAxis type="category" dataKey="label" width={190} stroke="#9aa6c4" fontSize={12} />
                  <Tooltip {...tip} formatter={(v: number) => [v.toFixed(1), 'Average effect (AQI points)']} />
                  <Bar dataKey="mean_abs_shap" fill="#8fb3ff" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Reveal>
        </div>
      )}
    </Section>
  );
}

function Tabs({ day, setDay }: { day: number; setDay: (d: number) => void }) {
  return (
    <div className="tabs" role="tablist">
      {[1, 2, 3].map((d) => (
        <button key={d} role="tab" aria-selected={day === d} className={day === d ? 'on' : ''} onClick={() => setDay(d)}>
          Day +{d}{day === d && <motion.span layoutId="tabpill" className="pill" />}
        </button>
      ))}
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ model report
export function ModelReport({ b }: { b: CityBundle }) {
  const [day, setDay] = useState(1);
  const rows = b.metrics_holdout.filter((m) => m.horizon === day);
  const champ = b.champions[String(day)]; const pers = rows.find((r) => r.model === 'persistence'); const best = rows.find((r) => r.model === champ);
  const bars = [1, 2, 3].map((h) => {
    const o: Record<string, number | string> = { day: `Day +${h}` };
    b.metrics_holdout.filter((m) => m.horizon === h).forEach((m) => { o[m.model] = m.mae; });
    return o;
  });
  const models = Array.from(new Set(b.metrics_holdout.map((m) => m.model)));
  const colours = ['#6f7c9e', '#8fb3ff', '#66CC66', '#F2D600', '#FF9900'];
  const worseHigh = best && pers && best.high_aqi_mae != null && pers.high_aqi_mae != null && best.high_aqi_mae > pers.high_aqi_mae;
  return (
    <Section id="model" kicker="Model report" title="How accurate is it?"
      intro={<>Measured on the last 20% of days, which no model saw during training or selection. Lower error is better. Every model is compared with <b>persistence</b> (tomorrow = today), a strong baseline for air quality.</>}>
      <div className="explain">
        <Reveal className="panel">
          <h3>Average error (MAE, AQI points) by day</h3>
          <div className="chart-mid">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={bars} margin={{ left: -10, right: 10 }}>
                <CartesianGrid stroke="#1e2742" vertical={false} />
                <XAxis dataKey="day" stroke="#9aa6c4" fontSize={12} /><YAxis stroke="#6f7c9e" fontSize={11} />
                <Tooltip {...tip} formatter={(v: number, n: string) => [v.toFixed(2), mname(n)]} />
                <Legend formatter={(v) => <span style={{ color: '#c8d0e4' }}>{mname(v)}</span>} />
                {models.map((m, i) => <Bar key={m} dataKey={m} fill={colours[i % colours.length]} radius={[6, 6, 0, 0]} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Reveal>
        <Reveal className="panel" delay={0.1}>
          <Tabs day={day} setDay={setDay} />
          {best && pers && (
            <div className="stats">
              <Stat k="Selected model" v={mname(champ)} />
              <Stat k="Average error" v={`${best.mae.toFixed(1)}`} sub={`persistence ${pers.mae.toFixed(1)}`} />
              <Stat k="Better than persistence" v={`${best.mae_improvement_vs_persistence_pct.toFixed(0)}%`} />
              <Stat k="Right category" v={`${(best.category_accuracy * 100).toFixed(0)}%`} sub={`persistence ${(pers.category_accuracy * 100).toFixed(0)}%`} />
              <Stat k="R²" v={best.r2.toFixed(3)} />
              <Stat k="High-AQI days tested" v={`${best.high_pollution_days}`} sub="observed AQI > 200" />
            </div>
          )}
          {worseHigh && (
            <div className="note"><Glyph name="Poor" /><span>On days above AQI 200 the selected model's error is <b>{best!.high_aqi_mae!.toFixed(1)}</b> vs <b>{pers!.high_aqi_mae!.toFixed(1)}</b> for persistence. It is better on average but weaker on the most polluted days, which matter most for alerts.{best!.high_pollution_days < 10 && <> Only {best!.high_pollution_days} such days were tested, so this comparison is uncertain.</>}</span></div>
          )}
        </Reveal>
      </div>
      <Reveal className="panel chart-tall" delay={0.05}>
        <h3>Day +1 on held-out days: forecast vs what happened (last 120)</h3>
        <ResponsiveContainer width="100%" height="88%">
          <LineChart data={b.holdout_sample_h1} margin={{ left: -10, right: 16 }}>
            <CartesianGrid stroke="#1e2742" vertical={false} />
            <XAxis dataKey="date" tickFormatter={(d) => fmtDate(d, { day: 'numeric', month: 'short', year: '2-digit' })} stroke="#6f7c9e" fontSize={11} minTickGap={40} />
            <YAxis stroke="#6f7c9e" fontSize={11} />
            <Tooltip {...tip} formatter={(v: number, n: string) => [Math.round(v), n === 'observed' ? 'Observed' : n === 'predicted' ? mname(b.champions['1']) : 'Persistence']} />
            <Legend formatter={(v) => <span style={{ color: '#c8d0e4' }}>{v === 'observed' ? 'Observed' : v === 'predicted' ? mname(b.champions['1']) : 'Persistence'}</span>} />
            <Line dataKey="observed" stroke="#e9edf7" dot={false} strokeWidth={2} />
            <Line dataKey="predicted" stroke="#8fb3ff" dot={false} strokeWidth={2} />
            <Line dataKey="persistence" stroke="#6f7c9e" dot={false} strokeDasharray="4 4" />
          </LineChart>
        </ResponsiveContainer>
      </Reveal>
    </Section>
  );
}
const Stat = ({ k, v, sub }: { k: string; v: string; sub?: string }) => (
  <div className="stat"><div className="stat-k">{k}</div><div className="stat-v">{v}</div>{sub && <div className="stat-s">{sub}</div>}</div>
);

// ------------------------------------------------------------------------------------------------ health guide
export function HealthGuide({ current }: { current: number }) {
  const now = cat(current).label;
  return (
    <Section id="health" kicker="Health guide" title="What each AQI level means"
      intro="Health impacts follow CPCB's National AQI categories. The suggested actions are general guidance; follow local authority advisories.">
      <div className="guide">
        {CATS.map((c, i) => (
          <Reveal key={c.label} delay={i * 0.05}>
            <div className={`guide-row ${c.label === now ? 'now' : ''}`} style={{ ['--c' as string]: c.colour }}>
              <div className="guide-band" style={{ background: c.colour, color: c.ink }}><Glyph name={c.label} /><b>{c.label}</b><span>{c.low}–{c.high === 500 ? '500' : c.high}</span></div>
              <div className="guide-txt"><p>{c.impact}</p><p><b>Everyone:</b> {c.advice}</p><p><b>Sensitive groups:</b> {c.sensitive}</p></div>
              {c.label === now && <div className="guide-now">Next 3 days</div>}
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

// ------------------------------------------------------------------------------------------------ provenance
export function Provenance({ b }: { b: CityBundle }) {
  const q = b.quality as Record<string, unknown>;
  const items: [string, unknown][] = [['Rows read', q.rows_read], ['Valid rows', q.rows_valid], ['Duplicate city-days', q.duplicate_city_dates], ['Invalid dates', q.invalid_dates], ['Invalid AQI values', q.invalid_aqi], ['Missing dates (not filled in)', q.missing_dates], ['Period', `${q.min_date} → ${q.max_date}`]];
  return (
    <Section id="data" kicker="Data & method" title="Where the numbers come from">
      <div className="explain">
        <Reveal className="panel">
          <h3>Source</h3>
          <p className={b.is_demo ? 'warn-txt' : ''}>{b.provenance}</p>
          <h3>When a forecast is issued</h3><p>{b.issue_rule}</p>
          <h3>How the model is chosen</h3><p>{b.selection_basis} Candidates: {b.candidates.map(mname).join(', ')}.</p>
          <h3>What the model does not use</h3><p>Future weather is not used yet. Weather forecasts archived at the time each forecast was issued are needed before they can be tested without leaking information.</p>
        </Reveal>
        <Reveal className="panel" delay={0.1}>
          <h3>Data quality checks</h3>
          <dl className="dq">{items.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{String(v ?? '—')}</dd></div>)}</dl>
        </Reveal>
      </div>
    </Section>
  );
}
