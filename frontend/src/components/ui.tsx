import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";
import { useEffect, useState } from "react";

export const Icon = {
  brief: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <path d="M4 6h16M4 12h10M4 18h7" />
    </svg>
  ),
  research: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <circle cx="11" cy="11" r="6.5" /><path d="m20 20-4-4" />
    </svg>
  ),
  alerts: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <path d="M5 7h9M18 7h1M5 17h1M10 17h9" /><circle cx="16" cy="7" r="2" /><circle cx="8" cy="17" r="2" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="m3.5 8.5 3 3 6-7" />
    </svg>
  ),
  cross: (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden>
      <path d="m4 4 8 8M12 4l-8 8" />
    </svg>
  ),
  doc: (
    <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" aria-hidden>
      <path d="M4 2h5l3 3v9H4z" /><path d="M9 2v3h3" />
    </svg>
  ),
  speaker: (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 10v4h4l5 4V6L8 10z" /><path d="M16.5 9a4 4 0 0 1 0 6" />
    </svg>
  ),
  search: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <circle cx="11" cy="11" r="6.5" /><path d="m20 20-4-4" />
    </svg>
  ),
};

export function Logo() {
  return (
    <div className="brand">
      <img src="/icons/finn-f.svg" alt="" width={30} height={30} />
      <span>FINN</span>
    </div>
  );
}

export function Ring({ done, total }: { done: number; total: number }) {
  const r = 31;
  const c = 2 * Math.PI * r;
  const frac = total ? done / total : 1;
  return (
    <div className="ring" role="img" aria-label={`${done} of ${total} cleared`}>
      <svg width="74" height="74" viewBox="0 0 74 74">
        <circle cx="37" cy="37" r={r} stroke="rgba(255,255,255,0.08)" strokeWidth="6" fill="none" />
        <motion.circle
          cx="37" cy="37" r={r} stroke="var(--mint)" strokeWidth="6" fill="none" strokeLinecap="round"
          strokeDasharray={c} transform="rotate(-90 37 37)"
          initial={false} animate={{ strokeDashoffset: c * (1 - frac) }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          style={{ filter: "drop-shadow(0 0 6px rgba(102, 209, 158,0.55))" }}
        />
      </svg>
      <div className="ring-label">
        <div>{total - done}<small>LEFT</small></div>
      </div>
    </div>
  );
}

export function CountUp({ value, format }: { value: number; format: (v: number) => string }) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(reduce ? value : 0);
  const text = useTransform(mv, (v) => format(v));
  const [, force] = useState(0);
  useEffect(() => {
    if (reduce) { mv.set(value); force((x) => x + 1); return; }
    const c = animate(mv, value, { duration: 0.7, ease: [0.2, 0.8, 0.2, 1] });
    return () => c.stop();
  }, [value, reduce, mv]);
  return <motion.span className="tnum">{text}</motion.span>;
}

/** Small bar chart (annual values) with an optional line overlay (margin %). */
/** Short rupee label for chart tops: 1,83,341 -> "1.83L", 44,465 -> "44.5K". */
const short = (v?: number | null) => v == null ? "–" : Math.abs(v) >= 1e5 ? `${(v / 1e5).toFixed(2)}L` : Math.abs(v) >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : `${Math.round(v)}`;

/** Smooth line through points (Catmull-Rom as cubic Béziers). */
function smooth(pts: [number, number][]) {
  if (pts.length < 2) return "";
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 8, p1[1] + (p2[1] - p0[1]) / 8];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 8, p2[1] - (p3[1] - p1[1]) / 8];
    d += ` C${c1[0]},${c1[1]} ${c2[0]},${c2[1]} ${p2[0]},${p2[1]}`;
  }
  return d;
}

export function Bars({ data, label, metric, fmt, lineName }: {
  data: { x: string; y: number | null; line?: number | null }[]; label: string;
  metric?: string; fmt?: (v: number | null | undefined) => string; lineName?: string;
}) {
  const reduce = useReducedMotion();
  const [sel, setSel] = useState(data.length - 1);
  const cur = data[Math.min(sel, data.length - 1)];
  const W = 340, H = 168, top = 26, base = 140, left = 6, right = 6;
  const plotH = base - top;
  const max = Math.max(...data.map((d) => d.y ?? 0), 1) * 1.05;
  const bw = (W - left - right) / data.length;
  const yOf = (v: number) => base - (v / max) * plotH;
  const lines = data.map((d) => d.line).filter((v): v is number => v != null);
  const lmin = Math.min(...lines), lmax = Math.max(...lines);
  const ly = (v: number) => top + 2 + (1 - (v - lmin) / (lmax - lmin || 1)) * plotH * 0.4;
  const marks = data.map((d, i) => (d.line == null ? null : { i, x: left + i * bw + bw / 2, y: ly(d.line) }))
    .filter((p): p is { i: number; x: number; y: number } => p != null);
  const pts = marks.map((m) => [m.x, m.y] as [number, number]);
  const linePath = smooth(pts);
  return (
    <div>
      {metric && (
        <div className="bars-head tnum">
          <span className="faint small">{metric}</span>
          <span className="small"><b>{cur?.x}</b> · {fmt ? fmt(cur?.y) : cur?.y}{lineName && cur?.line != null ? ` · ${lineName} ${cur.line.toFixed(1)}%` : ""}</span>
        </div>
      )}
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={label} className="chart">
        <defs>
          <linearGradient id="bar-on" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#9fe6c3" /><stop offset="1" stopColor="var(--mint)" stopOpacity="0.55" />
          </linearGradient>
          <linearGradient id="bar-off" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--mint)" stopOpacity="0.42" /><stop offset="1" stopColor="var(--mint)" stopOpacity="0.06" />
          </linearGradient>
          <linearGradient id="bar-mid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--mint)" stopOpacity="0.75" /><stop offset="1" stopColor="var(--mint)" stopOpacity="0.25" />
          </linearGradient>
          <linearGradient id="bar-grey" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#ffffff" stopOpacity="0.16" /><stop offset="1" stopColor="#ffffff" stopOpacity="0.04" />
          </linearGradient>
          <linearGradient id="line-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#f5c86b" stopOpacity="0.22" /><stop offset="1" stopColor="#f5c86b" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="mtn-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--mint)" stopOpacity="0.42" /><stop offset="1" stopColor="var(--mint)" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.33, 0.66, 1].map((f) => (
          <line key={f} x1={left} x2={W - right} y1={base - f * plotH} y2={base - f * plotH} stroke="rgba(255,255,255,0.05)" strokeWidth="0.6" />
        ))}
        <line x1={left} x2={W - right} y1={base} y2={base} stroke="rgba(255,255,255,0.14)" />
        {(() => {
          // The main series as a mountain: a smooth line with a soft filled area under it.
          const vp = data.map((d, i) => (d.y == null ? null : { i, x: left + i * bw + bw / 2, y: yOf(d.y) }))
            .filter((p): p is { i: number; x: number; y: number } => p != null);
          if (vp.length < 2) return null;
          const top_ = smooth(vp.map((p) => [p.x, p.y] as [number, number]));
          const fill = `${top_} L${vp[vp.length - 1].x},${base} L${vp[0].x},${base} Z`;
          const selP = vp.find((p) => p.i === sel);
          return (
            <g>
              <motion.path d={fill} fill="url(#mtn-fill)" initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, delay: 0.35 }} />
              <motion.path d={top_} fill="none" stroke="var(--mint)" strokeWidth="2.2" strokeLinecap="round"
                initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.0, ease: [0.2, 0.8, 0.2, 1] }} />
              {selP && <line x1={selP.x} x2={selP.x} y1={selP.y} y2={base} stroke="rgba(255,255,255,0.18)" strokeDasharray="2 3" />}
              {vp.map((p) => {
                const hot = p.i >= data.length - 2;
                return <circle key={p.i} cx={p.x} cy={p.y} r={p.i === sel ? 5 : hot ? 3.6 : 2.6}
                  fill={p.i === sel || p.i === data.length - 1 ? "var(--mint)" : "#0b0c0c"} stroke="var(--mint)" strokeWidth="1.6"
                  opacity={hot || p.i === sel ? 1 : 0.6} />;
              })}
            </g>
          );
        })()}
        {linePath && (
          <motion.path d={linePath} fill="none" stroke="#f5c86b" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="4 3" pointerEvents="none" opacity="0.85"
            initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 0.85 }} transition={{ duration: 0.8, delay: 0.6 }} />
        )}
        {marks.filter((m) => m.i === sel).map((m) => (
          <circle key={m.i} cx={m.x} cy={m.y} r="3.5" fill="#f5c86b" pointerEvents="none" />
        ))}
        {[0, data.length - 1].filter((i, k, a) => a.indexOf(i) === k && data[i]?.y != null).map((i) => (
          <text key={i} x={left + i * bw + bw / 2} y={Math.max(12, yOf(data[i].y as number) - 10)} textAnchor="middle" fontSize="10.5"
            fontWeight="700" fill={i === data.length - 1 ? "#e9f7ef" : "rgba(236,239,237,0.55)"}>{short(data[i].y)}</text>
        ))}
        {data.map((_, i) => <rect key={`hit${i}`} x={left + i * bw} y={0} width={bw} height={H} fill="transparent" style={{ cursor: "pointer" }} onClick={() => setSel(i)} />)}
        {data.map((d, i) => (
          <text key={d.x} x={left + i * bw + bw / 2} y={base + 18} textAnchor="middle" fontSize="10"
            fontWeight={i === sel ? 700 : 500} fill={i === sel ? "rgba(236,239,237,0.95)" : "rgba(236,239,237,0.42)"}>{d.x}</text>
        ))}
      </svg>
      {metric && <div className="faint small" style={{ textAlign: "center", marginTop: 2 }}>Tap the chart to see each year</div>}
    </div>
  );
}

/** Target band vs actual: where the actual landed relative to the promised range. */
export function BandChart({ low, high, actual, unit }: { low: number | null; high: number | null; actual: number | null; unit: string }) {
  const reduce = useReducedMotion();
  const lo = low ?? high ?? 0, hi = high ?? low ?? 0;
  const vals = [lo, hi, actual ?? lo];
  const min = Math.min(...vals) - Math.max(2, Math.abs(hi - lo)), max = Math.max(...vals) + Math.max(2, Math.abs(hi - lo));
  const x = (v: number) => 14 + ((v - min) / (max - min)) * 292;
  const hit = actual != null && actual >= Math.min(lo, hi) - 0.5;
  const col = actual == null ? "#ecefed" : hit ? "var(--up)" : "#f29a9a";
  return (
    <svg viewBox="0 0 320 60" width="100%" role="img" aria-label={`target ${lo} to ${hi}${unit}, actual ${actual ?? "not yet"}${unit}`} className="chart">
      <defs>
        <linearGradient id="band-fill" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="var(--mint)" stopOpacity="0.18" /><stop offset="1" stopColor="var(--mint)" stopOpacity="0.38" />
        </linearGradient>
      </defs>
      <rect x="14" y="27" width="292" height="6" rx="3" fill="rgba(255,255,255,0.07)" />
      <rect x={x(lo)} y="20" width={Math.max(x(hi) - x(lo), 6)} height="20" rx="10" fill="url(#band-fill)" stroke="rgba(102, 209, 158,0.55)" />
      <text x={(x(lo) + x(hi)) / 2} y="13" textAnchor="middle" fontSize="10" fill="rgba(236,239,237,0.62)">target {lo === hi ? lo : `${lo}–${hi}`}{unit}</text>
      {actual != null && (
        <motion.g initial={reduce ? false : { x: x(min) - x(actual), opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.7, ease: [0.2, 0.8, 0.2, 1] }}>
          <circle cx={x(actual)} cy="30" r="10" fill={col} opacity="0.18" />
          <circle cx={x(actual)} cy="30" r="5.5" fill={col} stroke="#0b0c0c" strokeWidth="2" />
          <text x={x(actual)} y="55" textAnchor="middle" fontSize="10.5" fontWeight="700" fill={col}>actual {actual}{unit}</text>
        </motion.g>
      )}
    </svg>
  );
}

export function Cite({ href, children }: { href?: string; children: React.ReactNode }) {
  if (!href) return <span className="cite">{Icon.doc}{children}</span>;
  return (
    <a className="cite" href={href} target="_blank" rel="noopener noreferrer">
      {Icon.doc}{children}
    </a>
  );
}


/** Mountain chart: the stock's % change as a filled area, the Nifty as a thin line, end values labelled. */
export function Mountain({ points, name }: { points: { d: string; s: number; n: number }[]; name: string }) {
  const reduce = useReducedMotion();
  const W = 340, H = 150, top = 14, base = 120, left = 4, right = 64;
  const all = points.flatMap((p) => [p.s, p.n]);
  const lo = Math.min(...all, 0), hi = Math.max(...all, 0);
  const pad = (hi - lo) * 0.08 || 1;
  const y = (v: number) => top + (1 - (v - (lo - pad)) / (hi + pad - (lo - pad))) * (base - top);
  const x = (i: number) => left + (i / (points.length - 1)) * (W - left - right);
  const sPts = points.map((p, i) => [x(i), y(p.s)] as [number, number]);
  const nPts = points.map((p, i) => [x(i), y(p.n)] as [number, number]);
  const line = (pts: [number, number][]) => pts.map(([a, b], i) => `${i ? "L" : "M"}${a.toFixed(1)},${b.toFixed(1)}`).join(" ");
  const sLine = line(sPts);
  const area = `${sLine} L${sPts[sPts.length - 1][0]},${base} L${sPts[0][0]},${base} Z`;
  const last = points[points.length - 1];
  const lab = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
  const fmt = (d: string) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  const sy = y(last.s), ny = y(last.n);
  const gap = Math.abs(sy - ny) < 14 ? (sy < ny ? -7 : 7) : 0;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" className="chart"
      aria-label={`${name} ${lab(last.s)} vs Nifty ${lab(last.n)} over the period`}>
      <defs>
        <linearGradient id="mtn" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--mint)" stopOpacity="0.38" /><stop offset="1" stopColor="var(--mint)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((f) => <line key={f} x1={left} x2={W - right} y1={top + f * (base - top)} y2={top + f * (base - top)} stroke="rgba(255,255,255,0.05)" strokeWidth="0.6" />)}
      <line x1={left} x2={W - right} y1={y(0)} y2={y(0)} stroke="rgba(255,255,255,0.18)" strokeDasharray="2 4" />
      <motion.path d={area} fill="url(#mtn)" initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, delay: 0.4 }} />
      <motion.path d={line(nPts)} fill="none" stroke="rgba(236,239,237,0.45)" strokeWidth="1.2"
        initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.1 }} />
      <motion.path d={sLine} fill="none" stroke="var(--mint)" strokeWidth="2" strokeLinejoin="round"
        initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.1 }} />
      <circle cx={sPts[sPts.length - 1][0]} cy={sy} r="3.5" fill="var(--mint)" />
      <text x={W - right + 6} y={sy + 4 + gap} fontSize="11" fontWeight="700" fill={last.s >= 0 ? "var(--up)" : "#f29a9a"}>{lab(last.s)}</text>
      <text x={W - right + 6} y={ny + 4 - gap} fontSize="10" fill="rgba(236,239,237,0.55)">Nifty {lab(last.n)}</text>
      <text x={left} y={H - 8} fontSize="10" fill="rgba(236,239,237,0.45)">{fmt(points[0].d)}</text>
      <text x={W - right} y={H - 8} fontSize="10" textAnchor="end" fill="rgba(236,239,237,0.45)">{fmt(last.d)}</text>
    </svg>
  );
}
