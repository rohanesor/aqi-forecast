import { AnimatePresence, MotionConfig, motion, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { Component, ReactNode, Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { cat, fmtDate, smogLevel } from './aqi';
import { Chip, Counter, Reveal, Section } from './components/ui';
import { Explain, ForecastCards, HealthGuide, ModelReport, Provenance, Trend } from './components/Sections';
import { CityBundle, Index, getJSON } from './data';

const Smog = lazy(() => import('./components/Smog'));
const IndiaMap = lazy(() => import('./components/IndiaMap'));
const Simulator = lazy(() => import('./components/Simulator'));

function hasWebGL() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch { return false; }
}
class Safe extends Component<{ fallback: ReactNode; children: ReactNode }, { err: boolean }> {
  state = { err: false };
  static getDerivedStateFromError() { return { err: true }; }
  render() { return this.state.err ? this.props.fallback : this.props.children; }
}

export default function App() {
  const reduced = !!useReducedMotion();
  const gl = useMemo(hasWebGL, []);
  const [index, setIndex] = useState<Index | null>(null);
  const [slug, setSlug] = useState<string>(() => new URLSearchParams(location.search).get('city') ?? '');
  const [bundle, setBundle] = useState<CityBundle | null>(null);
  const [all, setAll] = useState<Record<string, CityBundle>>({});
  const [day, setDay] = useState(1);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { getJSON<Index>('index.json').then((i) => { setIndex(i); setSlug((s) => s || [...i.cities].sort((a, b) => (b.next_aqi ?? b.latest_aqi) - (a.next_aqi ?? a.latest_aqi))[0]?.slug || ''); }).catch((e) => setErr(String(e))); }, []);
  useEffect(() => {
    if (!index) return;
    Promise.all(index.cities.map((c) => getJSON<CityBundle>(`${c.slug}.json`))).then((bs) => setAll(Object.fromEntries(bs.map((b) => [b.slug, b])))).catch(() => {});
  }, [index]);
  useEffect(() => {
    if (!slug) return;
    getJSON<CityBundle>(`${slug}.json`).then(setBundle).catch((e) => setErr(String(e)));
    const u = new URL(location.href); u.searchParams.set('city', slug); history.replaceState(null, '', u);
  }, [slug]);

  const { scrollY } = useScroll();
  const heroFade = useTransform(scrollY, [0, 500], [1, 0.25]);
  const heroLift = useTransform(scrollY, [0, 500], [0, -60]);

  if (err) return <div className="fatal"><h1>Could not load forecast data</h1><p>{err}</p><p>Run <code>python scripts/export_web.py</code> and rebuild.</p></div>;
  if (!index || !bundle) return <div className="loading"><div className="spinner" /><span>Loading forecasts…</span></div>;

  const f = bundle.forecasts.find((x) => x.horizon === day) ?? bundle.forecasts[0];
  const c = cat(f.aqi);
  const mapValues = Object.fromEntries(index.cities.map((ci) => [ci.slug, all[ci.slug]?.forecasts.find((x) => x.horizon === day)?.aqi ?? ci.next_aqi ?? ci.latest_aqi]));

  return (
    <MotionConfig reducedMotion="user">
      {bundle.is_demo && <div className="demo-bar" role="note"><b>DEMO DATA</b>&nbsp;· These numbers come from a synthetic dataset for demonstration. They are not real air-quality readings.</div>}
      {!bundle.is_demo && bundle.experimental_short_history && <div className="demo-bar" role="note"><b>OFFICIAL CPCB — STATION · INSUFFICIENT HISTORY{bundle.is_stale ? ' · STALE DATA' : ''}</b>&nbsp;· Historical experimental run, not Delhi city-wide AQI. Only {Math.min(...Object.values(bundle.usable_samples))} usable samples are available; 450 are required for production.{bundle.is_stale ? ` Latest observation is ${bundle.data_age_days} days old.` : ''}</div>}
      <header className="top">
        <a className="brand" href="#top"><span className="logo" style={{ background: c.colour }} />India AQI Forecast</a>
        <nav className="links">{[['forecast', 'Forecast'], ['trend', 'Trend'], ['map', 'Map'], ['simulator', 'Try It'], ['why', 'Why'], ['model', 'Accuracy'], ['health', 'Health'], ['data', 'Data']].map(([id, t]) => <a key={id} href={`#${id}`}>{t}</a>)}</nav>
        <div className="pills" role="radiogroup" aria-label="City">
          {index.cities.map((ci) => (
            <button key={ci.slug} role="radio" aria-checked={ci.slug === slug} className={ci.slug === slug ? 'on' : ''} onClick={() => setSlug(ci.slug)}>
              {ci.city}{ci.slug === slug && <motion.span layoutId="citypill" className="pill" />}
            </button>
          ))}
        </div>
      </header>

      <section id="top" className="hero">
        <div className="hero-3d" aria-hidden>
          {gl ? <Safe fallback={<div className="hero-flat" style={{ ['--c' as string]: c.colour }} />}><Suspense fallback={<div className="hero-flat" style={{ ['--c' as string]: c.colour }} />}><Smog level={smogLevel(f.aqi)} tint={c.colour} reduced={reduced} /></Suspense></Safe>
            : <div className="hero-flat" style={{ ['--c' as string]: c.colour }} />}
        </div>
        <div className="hero-shade" />
        <motion.div className="hero-copy" style={reduced ? {} : { opacity: heroFade, y: heroLift }}>
          <AnimatePresence mode="wait">
            <motion.div key={bundle.slug + day} initial={{ opacity: 0, y: 18, filter: 'blur(6px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} exit={{ opacity: 0, y: -12, filter: 'blur(6px)' }} transition={{ duration: 0.5 }}>
              <div className="hero-k">{bundle.city} · {day === 1 ? 'Tomorrow' : `In ${day} days`}, {fmtDate(f.forecast_date, { weekday: 'long', day: 'numeric', month: 'long' })}</div>
              <div className="hero-n" style={{ color: c.colour }}><Counter value={f.aqi} reduced={reduced} /></div>
              <div className="hero-row"><Chip aqi={f.aqi} /><span className="hero-range">Likely {Math.round(f.range_low ?? f.aqi)}–{Math.round(f.range_high ?? f.aqi)}</span></div>
              <p className="hero-adv">{c.advice}</p>
              <p className="hero-sub">Latest observed: <b>{Math.round(bundle.latest.aqi)}</b> on {fmtDate(bundle.latest.date)} · forecast issued from data up to that day</p>
            </motion.div>
          </AnimatePresence>
          <div className="day-switch" role="tablist" aria-label="Forecast day">
            {bundle.forecasts.map((x) => (
              <button key={x.horizon} role="tab" aria-selected={day === x.horizon} className={day === x.horizon ? 'on' : ''} onClick={() => setDay(x.horizon)}>
                <span>{fmtDate(x.forecast_date, { weekday: 'short' })}</span><b style={{ color: cat(x.aqi).colour }}>{Math.round(x.aqi)}</b>
                {day === x.horizon && <motion.span layoutId="daypill" className="pill" />}
              </button>
            ))}
          </div>
        </motion.div>
        <a className="scroll-cue" href="#forecast" aria-label="Scroll to forecast"><span /></a>
      </section>

      <main>
        <ForecastCards b={bundle} day={day} setDay={setDay} reduced={reduced} />
        <Trend b={bundle} />
        <Section id="map" kicker="Across India" title="Forecast by city"
          intro={<>Pillar height is the Day +{day} forecast; colour is its CPCB category. Drag to rotate, click a city to open it. Only cities with trained models are shown. Boundary: Natural Earth, India's view.</>}>
          <Reveal className="map-wrap">
            {gl ? <Safe fallback={<MapList index={index} values={mapValues} slug={slug} setSlug={setSlug} />}><Suspense fallback={<div className="map-load">Loading 3D map…</div>}>
              <IndiaMap cities={index.cities} values={mapValues} active={slug} onPick={setSlug} reduced={reduced} />
            </Suspense></Safe> : <MapList index={index} values={mapValues} slug={slug} setSlug={setSlug} />}
          </Reveal>
          <MapList index={index} values={mapValues} slug={slug} setSlug={setSlug} compact />
        </Section>
        <Suspense fallback={null}><Simulator slug={bundle.slug} reduced={reduced} /></Suspense>
        <Explain b={bundle} day={day} setDay={setDay} />
        <ModelReport b={bundle} />
        <HealthGuide current={f.aqi} />
        <Provenance b={bundle} />
      </main>
      <footer className="foot">
        <p>Built by <b>ANBU CHELVAN K R</b> and <b>B. HARIHARAN</b>. Categories and health impacts follow CPCB's National AQI. Forecasts are statistical estimates; follow official advisories.</p>
        {bundle.is_demo && <p className="warn-txt">This view shows synthetic demo data.</p>}
        {!bundle.is_demo && bundle.experimental_short_history && <p className="warn-txt">This view uses official but incomplete station-level history and is not production-ready.</p>}
      </footer>
    </MotionConfig>
  );
}

function MapList({ index, values, slug, setSlug, compact }: { index: Index; values: Record<string, number>; slug: string; setSlug: (s: string) => void; compact?: boolean }) {
  return (
    <ul className={`map-list ${compact ? 'compact' : ''}`}>
      {index.cities.map((ci) => (
        <li key={ci.slug}><button className={ci.slug === slug ? 'on' : ''} onClick={() => setSlug(ci.slug)}>
          <b>{ci.city}</b><span>{Math.round(values[ci.slug])}</span><Chip aqi={values[ci.slug]} />
        </button></li>
      ))}
    </ul>
  );
}
