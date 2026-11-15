import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

const TOP = "M 130.8 270.0 C 144.1 194.4, 175.3 126.5, 237.7 126.5 L 414.7 126.5 L 396.0 174.9 C 387.4 195.9, 370.3 209.2, 349.2 209.2 L 214.3 209.2 C 175.3 209.2, 140.2 233.4, 130.8 270.0 Z";
const LOW = "M 97.3 385.5 L 128.5 276.3 C 136.3 258.3, 159.7 247.4, 187.0 247.4 L 340.6 247.4 L 327.4 280.2 C 318.8 302.0, 304.0 316.1, 284.5 316.1 L 198.7 316.1 L 176.1 385.5 Z";
const ease = [0.2, 0.8, 0.2, 1] as const;

/** Show the opening animation once per visit (not in automated test browsers). */
export function splashWanted(): boolean {
  try {
    if (navigator.webdriver || sessionStorage.getItem("finn.splash")) return false;
    sessionStorage.setItem("finn.splash", "1");
  } catch { /* private mode: show it */ }
  return true;
}

/** Opening animation: the two bars of the F slide in, the wordmark fades up, then onDone. Tap to skip.
 *  The app is not mounted underneath while it plays (iPhone Safari flickers when an animated overlay sits
 *  above blurred layers), and it starts only once the fonts are ready, so text never swaps mid-animation. */
export default function Splash({ onDone }: { onDone: () => void }) {
  const reduce = useReducedMotion();
  const [go, setGo] = useState(false);
  useEffect(() => {
    let alive = true;
    const start = () => alive && setGo(true);
    const fallback = setTimeout(start, 500);
    (document as Document & { fonts?: { ready: Promise<unknown> } }).fonts?.ready.then(start).catch(start);
    return () => { alive = false; clearTimeout(fallback); };
  }, []);
  useEffect(() => {
    if (!go) return;
    const t = setTimeout(onDone, reduce ? 1000 : 2800);
    return () => clearTimeout(t);
  }, [go, reduce, onDone]);

  const bar = (delay: number) => ({
    initial: reduce ? { opacity: 0 } : { opacity: 0, x: -60, y: 18 },
    animate: go ? { opacity: 1, x: 0, y: 0 } : undefined,
    transition: { duration: 0.85, delay, ease },
  });
  return (
    <motion.div className="splash" onClick={onDone} role="presentation"
      exit={{ opacity: 0 }} transition={{ duration: 0.5, ease }}>
      <div className="splash-mark" aria-hidden>
        <motion.svg viewBox="0 0 512 512" className="splash-bar" {...bar(0.15)}>
          <defs><linearGradient id="sp-t" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#B2FAD0" /><stop offset="1" stopColor="#8BEFB4" /></linearGradient></defs>
          <path d={TOP} fill="url(#sp-t)" />
        </motion.svg>
        <motion.svg viewBox="0 0 512 512" className="splash-bar" {...bar(0.5)}>
          <defs><linearGradient id="sp-l" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#86EDB0" /><stop offset="1" stopColor="#5FD992" /></linearGradient></defs>
          <path d={LOW} fill="url(#sp-l)" />
        </motion.svg>
      </div>
      <motion.div className="splash-word" initial={{ opacity: 0, y: 8 }} animate={go ? { opacity: 1, y: 0 } : undefined}
        transition={{ duration: 0.7, delay: reduce ? 0.1 : 1.1, ease }}>
        FINN
      </motion.div>
      <motion.div className="splash-line" initial={{ opacity: 0 }} animate={go ? { opacity: 1 } : undefined}
        transition={{ duration: 0.6, delay: reduce ? 0.2 : 1.5 }}>
        what matters in your holdings
      </motion.div>
    </motion.div>
  );
}
