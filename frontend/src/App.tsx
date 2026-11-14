import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { Icon, Logo } from "./components/ui";
import { fmtWhen, Json, snapshot } from "./lib/data";
import Alerts from "./screens/Alerts";
import Brief from "./screens/Brief";
import Research from "./screens/Research";
import Settings from "./screens/Settings";

type Tab = "brief" | "research" | "alerts" | "settings";
const TABS: { key: Tab; label: string }[] = [
  { key: "brief", label: "Brief" }, { key: "research", label: "Research" },
  { key: "alerts", label: "Alerts" }, { key: "settings", label: "Settings" },
];

function parseHash(): { tab: Tab; ticker: string | null } {
  const [tab, ticker] = window.location.hash.replace(/^#\/?/, "").split("/");
  const t = (TABS.find((x) => x.key === tab)?.key || "brief") as Tab;
  return { tab: t, ticker: ticker ? decodeURIComponent(ticker).toUpperCase() : null };
}

export default function App() {
  const reduce = useReducedMotion();
  const [{ tab, ticker }, setRoute] = useState(parseHash);
  const [meta, setMeta] = useState<Json | null>(null);

  useEffect(() => {
    const on = () => setRoute(parseHash());
    window.addEventListener("hashchange", on);
    snapshot("meta.json").then(setMeta).catch(() => setMeta(null));
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [tab]);

  const go = (t: Tab, tk?: string | null) => { window.location.hash = tk ? `${t}/${tk}` : t; };

  return (
    <>
      <div className="bg-glow" aria-hidden />
      <div className="app">
        <header className="topbar">
          <Logo />
          <div className="asof">snapshot {meta ? fmtWhen(meta.generated_at) : "…"}<br />NSE · BSE · primary sources</div>
        </header>
        <main>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={tab} initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={reduce ? undefined : { opacity: 0, y: -6 }}
              transition={{ duration: 0.18, ease: [0.2, 0.8, 0.2, 1] }}>
              {tab === "brief" && <Brief onOpenResearch={(t) => go("research", t)} />}
              {tab === "research" && <Research ticker={ticker} setTicker={(t) => go("research", t)} />}
              {tab === "alerts" && <Alerts onOpenResearch={(t) => go("research", t)} />}
              {tab === "settings" && <Settings />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
      <nav className="nav" aria-label="Main">
        <LayoutGroup>
          {TABS.map((t) => (
            <button key={t.key} aria-current={tab === t.key ? "page" : undefined} onClick={() => go(t.key, t.key === "research" ? ticker : null)} aria-label={t.label}>
              {tab === t.key && <motion.span layoutId="pill" className="pill-bg" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              {Icon[t.key]}<span className="label">{t.label}</span>
            </button>
          ))}
        </LayoutGroup>
      </nav>
    </>
  );
}
