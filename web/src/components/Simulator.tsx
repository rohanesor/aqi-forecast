import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useMemo, useState } from 'react';
import { cat, smogLevel, CATS } from '../aqi';
import { Chip, Counter, Reveal, Section } from './ui';
import { getJSON } from '../data';

type WhatIf = {
  city: string; slug: string;
  horizons: Record<string, { model: string; predictions: Record<string, number> }>;
};

const MODEL_NAME: Record<string, string> = {
  persistence: 'Persistence (tomorrow = today)', xgboost: 'XGBoost',
  linear_regression: 'Linear regression', random_forest: 'Random forest', lightgbm: 'LightGBM',
};

function lerp(data: Record<string, number>, aqi: number): number {
  const step = 5;
  const lo = Math.floor(aqi / step) * step;
  const hi = Math.ceil(aqi / step) * step;
  const vLo = data[String(lo)] ?? aqi;
  const vHi = data[String(hi)] ?? aqi;
  if (lo === hi) return vLo;
  const t = (aqi - lo) / (hi - lo);
  return vLo + (vHi - vLo) * t;
}

export default function Simulator({ slug, reduced }: { slug: string; reduced: boolean }) {
  const [data, setData] = useState<WhatIf | null>(null);
  const [input, setInput] = useState(150);
  const [err, setErr] = useState(false);

  useEffect(() => {
    setErr(false);
    getJSON<WhatIf>(`whatif_${slug}.json`).then(setData).catch(() => setErr(true));
  }, [slug]);

  const preds = useMemo(() => {
    if (!data) return null;
    return [1, 2, 3].map((h) => {
      const hd = data.horizons[String(h)];
      if (!hd) return { h, aqi: input, model: 'persistence' };
      const aqi = Math.round(lerp(hd.predictions, input) * 10) / 10;
      return { h, aqi: Math.max(0, Math.min(500, aqi)), model: hd.model };
    });
  }, [data, input]);

  if (err) return null;
  if (!data || !preds) return null;

  const inputCat = cat(input);

  return (
    <Section id="simulator" kicker="Try it yourself" title="What-If Simulator"
      intro={<>Drag the slider or type any AQI value. The trained model runs instantly and shows what it would forecast for the next three days. This is the actual {data.city} model — not a lookup table.</>}>
      <Reveal>
        <div className="sim-wrap">
          <div className="sim-input">
            <label className="sim-label">
              <span>If today's AQI is</span>
              <div className="sim-num-row">
                <input
                  type="number" min={0} max={500} value={input}
                  onChange={(e) => setInput(Math.max(0, Math.min(500, Number(e.target.value) || 0)))}
                  className="sim-num"
                  style={{ color: inputCat.colour, borderColor: inputCat.colour }}
                />
                <Chip aqi={input} />
              </div>
            </label>
            <input
              type="range" min={0} max={500} step={1} value={input}
              onChange={(e) => setInput(Number(e.target.value))}
              className="sim-slider"
              style={{ ['--pct' as string]: `${(input / 500) * 100}%`, ['--c' as string]: inputCat.colour }}
            />
            <div className="sim-scale">
              {CATS.map((c) => (
                <span key={c.label} style={{ background: c.colour, flex: c.high - c.low + 1 }} title={c.label} />
              ))}
            </div>
          </div>

          <div className="sim-arrow">→</div>

          <div className="sim-output">
            <AnimatePresence mode="wait">
              <motion.div key={input} className="sim-cards"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
                {preds.map((p) => {
                  const c = cat(p.aqi);
                  const delta = p.aqi - input;
                  return (
                    <div key={p.h} className="sim-card" style={{ ['--c' as string]: c.colour }}>
                      <div className="sim-card-head">
                        <span className="sim-day">Day +{p.h}</span>
                        <span className="sim-model">{MODEL_NAME[p.model] ?? p.model}</span>
                      </div>
                      <div className="sim-card-aqi" style={{ color: c.colour }}>
                        <Counter value={p.aqi} reduced={reduced} />
                      </div>
                      <Chip aqi={p.aqi} />
                      <div className={`delta ${delta > 0 ? 'up' : 'down'}`}>
                        {delta > 0 ? '▲' : delta < 0 ? '▼' : '='} {Math.abs(delta).toFixed(0)} vs input
                      </div>
                      <div className="sim-card-advice">{c.advice}</div>
                    </div>
                  );
                })}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {preds.some((p) => p.aqi > 200) && (
          <div className="alert" role="alert" style={{ marginTop: 16 }}>
            ⚠️ <b>High AQI predicted</b> — the model forecasts unhealthy air on Day{' '}
            {preds.filter((p) => p.aqi > 200).map((p) => `+${p.h}`).join(', ')}.
          </div>
        )}

        <div className="sim-note panel" style={{ marginTop: 18 }}>
          <p style={{ margin: 0 }}>
            <b>How this works:</b> We pre-ran the trained {preds[0].model !== 'persistence' ? 'XGBoost' : 'persistence'} model for every AQI value from 0 to 500.
            The slider interpolates between those predictions. Features like yesterday's AQI, rolling averages, month, and season are held at their latest real values —
            only "today's AQI" changes. In production, the model ingests all features automatically from the latest CPCB data.
          </p>
        </div>
      </Reveal>
    </Section>
  );
}
