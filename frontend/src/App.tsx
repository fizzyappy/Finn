import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import Splash, { splashWanted } from "./components/Splash";
import { Icon, Logo } from "./components/ui";
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
  const [dir, setDir] = useState(1);
  const [prevTab, setPrevTab] = useState(tab);
  if (tab !== prevTab) {           // slide left when moving right along the nav, and back
    setDir(TABS.findIndex((x) => x.key === tab) >= TABS.findIndex((x) => x.key === prevTab) ? 1 : -1);
    setPrevTab(tab);
  }

  useEffect(() => {
    const on = () => setRoute(parseHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [tab, ticker]);

  const go = (t: Tab, tk?: string | null) => { window.location.hash = tk ? `${t}/${tk}` : t; };
  const [splash, setSplash] = useState(splashWanted);
  const done = useCallback(() => setSplash(false), []);

  return (
    <>
      <div className="bg-glow" aria-hidden />
      <AnimatePresence mode="wait">
      {splash ? <Splash key="splash" onDone={done} /> : (
      <motion.div key="app" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.45 }}>
      <div className="app">
        <header className="topbar">
          <Logo />
          <div className="asof">NSE · BSE<br />primary sources</div>
        </header>
        <main>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={tab} initial={reduce ? false : { opacity: 0, x: 28 * dir }} animate={{ opacity: 1, x: 0 }}
              exit={reduce ? undefined : { opacity: 0, x: -20 * dir }}
              transition={{ duration: 0.24, ease: [0.2, 0.8, 0.2, 1] }}>
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
            <motion.button key={t.key} whileTap={{ scale: 0.92 }} aria-current={tab === t.key ? "page" : undefined}
              onClick={() => go(t.key, t.key === "research" && tab !== "research" ? ticker : null)} aria-label={t.label}>
              {tab === t.key && <motion.span layoutId="pill" className="pill-bg" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              {Icon[t.key]}<span className="label">{t.label}</span>
            </motion.button>
          ))}
        </LayoutGroup>
      </nav>
      </motion.div>
      )}
      </AnimatePresence>
    </>
  );
}
