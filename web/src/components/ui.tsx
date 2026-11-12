import { animate, motion, useInView, useMotionValue, useTransform } from 'framer-motion';
import { ReactNode, useEffect, useRef } from 'react';
import { cat } from '../aqi';

export function Counter({ value, decimals = 0, reduced }: { value: number; decimals?: number; reduced?: boolean }) {
  const mv = useMotionValue(reduced ? value : 0); const text = useTransform(mv, (v) => v.toFixed(decimals));
  useEffect(() => { const c = animate(mv, value, { duration: reduced ? 0 : 1.1, ease: [0.16, 1, 0.3, 1] }); return c.stop; }, [value, reduced]);
  return <motion.span>{text}</motion.span>;
}

export function Reveal({ children, delay = 0, className }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef(null); const seen = useInView(ref, { once: true, margin: '-12% 0px' });
  return (
    <motion.div ref={ref} className={className} initial={{ opacity: 0, y: 28 }} animate={seen ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: [0.16, 1, 0.3, 1] }}>{children}</motion.div>
  );
}

export function Section({ id, kicker, title, intro, children }: { id: string; kicker: string; title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className="section">
      <Reveal>
        <div className="kicker">{kicker}</div>
        <h2>{title}</h2>
        {intro && <p className="intro">{intro}</p>}
      </Reveal>
      {children}
    </section>
  );
}

/** Category chip: colour + text label + shape icon (never colour alone). */
export function Chip({ aqi, label }: { aqi: number; label?: string }) {
  const c = cat(aqi);
  return <span className="chip" style={{ background: c.colour, color: c.ink }}><Glyph name={c.label} />{label ?? c.label}</span>;
}
export function Glyph({ name }: { name: string }) {
  const d: Record<string, string> = {
    Good: 'M4 8.5l2.5 2.5L12 5.5', Satisfactory: 'M4 8h8', Moderate: 'M8 4v5M8 11.5v.5',
    Poor: 'M8 3.5v6M8 12v.5', 'Very Poor': 'M5 5l6 6M11 5l-6 6', Severe: 'M8 2l6.5 11h-13z',
  };
  return <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden><path d={d[name] ?? 'M4 8h8'} fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}
