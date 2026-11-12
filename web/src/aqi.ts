// CPCB AQI scale, colours and health information. Health-impact text follows CPCB's National AQI category table;
// the "what to do" lines are general guidance only.
export type Category = 'Good' | 'Satisfactory' | 'Moderate' | 'Poor' | 'Very Poor' | 'Severe' | 'Unavailable';

export const CATS: { label: Category; low: number; high: number; colour: string; ink: string; impact: string; advice: string; sensitive: string }[] = [
  { label: 'Good', low: 0, high: 50, colour: '#009966', ink: '#ffffff', impact: 'Minimal impact.',
    advice: 'A good day to be outdoors.', sensitive: 'No special precautions needed.' },
  { label: 'Satisfactory', low: 51, high: 100, colour: '#66CC66', ink: '#0b1a0b', impact: 'Minor breathing discomfort to sensitive people.',
    advice: 'Outdoor activity is fine for most people.', sensitive: 'Watch for coughing or shortness of breath.' },
  { label: 'Moderate', low: 101, high: 200, colour: '#F2D600', ink: '#1d1a00', impact: 'Breathing discomfort to people with lung disease such as asthma, and discomfort to people with heart disease, children and older adults.',
    advice: 'Most people can stay active; take breaks if you notice irritation.', sensitive: 'Reduce long or heavy outdoor exertion.' },
  { label: 'Poor', low: 201, high: 300, colour: '#FF9900', ink: '#1f1200', impact: 'Breathing discomfort to most people on prolonged exposure.',
    advice: 'Cut down prolonged or heavy outdoor exertion.', sensitive: 'Avoid outdoor exertion; keep relief medication handy.' },
  { label: 'Very Poor', low: 301, high: 400, colour: '#E53935', ink: '#ffffff', impact: 'Respiratory illness on prolonged exposure.',
    advice: 'Avoid prolonged outdoor activity; consider a well-fitted mask outdoors.', sensitive: 'Stay indoors as much as possible.' },
  { label: 'Severe', low: 401, high: 500, colour: '#990000', ink: '#ffffff', impact: 'Affects healthy people and seriously impacts those with existing diseases.',
    advice: 'Avoid outdoor activity. Follow local authority advisories.', sensitive: 'Remain indoors and keep activity low.' },
];

export function cat(aqi: number | null | undefined) {
  if (aqi == null || !isFinite(aqi)) return { label: 'Unavailable' as Category, low: 0, high: 0, colour: '#808080', ink: '#fff', impact: '', advice: '', sensitive: '' };
  const v = Math.max(0, aqi);
  return CATS.find((c) => v <= c.high + 0.999) ?? CATS[CATS.length - 1];
}
/** 0 (clean) .. 1 (severe) — drives the smog density in 3D. */
export const smogLevel = (aqi: number) => Math.min(1, Math.max(0, aqi / 450));

export const fmtDate = (iso: string, opts: Intl.DateTimeFormatOptions = { weekday: 'short', day: 'numeric', month: 'short' }) =>
  new Date(iso + 'T00:00:00').toLocaleDateString('en-IN', opts);
