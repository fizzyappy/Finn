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
export function Bars({ data, label, metric, fmt, lineName }: {
  data: { x: string; y: number | null; line?: number | null }[]; label: string;
  metric?: string; fmt?: (v: number | null | undefined) => string; lineName?: string;
}) {
  const [sel, setSel] = useState(data.length - 1);
  const W = 340, H = 120, pad = 18;
  const cur = data[Math.min(sel, data.length - 1)];
  const vals = data.map((d) => d.y ?? 0);
  const max = Math.max(...vals, 1);
  const lines = data.map((d) => d.line).filter((v): v is number => v != null);
  const lmin = Math.min(...lines, 0), lmax = Math.max(...lines, 1);
  const bw = (W - pad * 2) / data.length;
  return (
    <div>
    {metric && (
      <div className="bars-head tnum">
        <span className="faint small">{metric}</span>
        <span className="small"><b>{cur?.x}</b> · {fmt ? fmt(cur?.y) : cur?.y}{lineName && cur?.line != null ? ` · ${lineName} ${cur.line.toFixed(1)}%` : ""}</span>
      </div>
    )}
    <svg viewBox={`0 0 ${W} ${H + 18}`} width="100%" role="img" aria-label={label}>
      {data.map((d, i) => {
        const h = ((d.y ?? 0) / max) * H * 0.85;
        return (
          <g key={d.x} onClick={() => setSel(i)} style={{ cursor: "pointer" }}>
            <rect x={pad + i * bw} y={0} width={bw} height={H + 18} fill="transparent" />
            <rect x={pad + i * bw + bw * 0.18} y={H - h} width={bw * 0.64} height={Math.max(h, 1)} rx="4"
              fill={i === sel ? "var(--mint)" : "rgba(102, 209, 158,0.28)"} />
            <text x={pad + i * bw + bw / 2} y={H + 14} textAnchor="middle" fontSize="10"
              fill={i === sel ? "rgba(236,239,237,0.9)" : "rgba(236,239,237,0.42)"}>{d.x}</text>
          </g>
        );
      })}
      {lines.length > 1 && (
        <polyline fill="none" stroke="#f5c86b" strokeWidth="2" strokeLinejoin="round"
          points={data.map((d, i) => d.line == null ? "" : `${pad + i * bw + bw / 2},${H - ((d.line - lmin) / (lmax - lmin || 1)) * H * 0.8 - 8}`).filter(Boolean).join(" ")} />
      )}
    </svg>
    {metric && <div className="faint small" style={{ textAlign: "center", marginTop: 2 }}>Tap a bar to see its numbers</div>}
    </div>
  );
}

/** Target band vs actual: where the actual landed relative to the promised range. */
export function BandChart({ low, high, actual, unit }: { low: number | null; high: number | null; actual: number | null; unit: string }) {
  const lo = low ?? high ?? 0, hi = high ?? low ?? 0;
  const vals = [lo, hi, actual ?? lo];
  const min = Math.min(...vals) - Math.max(2, Math.abs(hi - lo)), max = Math.max(...vals) + Math.max(2, Math.abs(hi - lo));
  const x = (v: number) => 12 + ((v - min) / (max - min)) * 296;
  return (
    <svg viewBox="0 0 320 52" width="100%" role="img" aria-label={`target ${lo} to ${hi}${unit}, actual ${actual ?? "not yet"}${unit}`}>
      <line x1="12" x2="308" y1="26" y2="26" stroke="rgba(255,255,255,0.12)" strokeWidth="2" />
      <rect x={x(lo)} y="18" width={Math.max(x(hi) - x(lo), 4)} height="16" rx="8" fill="rgba(102, 209, 158,0.22)" stroke="rgba(102, 209, 158,0.6)" />
      <text x={(x(lo) + x(hi)) / 2} y="13" textAnchor="middle" fontSize="10" fill="rgba(234,245,238,0.6)">target {lo === hi ? lo : `${lo}–${hi}`}{unit}</text>
      {actual != null && (
        <g>
          <circle cx={x(actual)} cy="26" r="6" fill="#eaf5ee" />
          <text x={x(actual)} y="48" textAnchor="middle" fontSize="10.5" fontWeight="600" fill="#eaf5ee">actual {actual}{unit}</text>
        </g>
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
