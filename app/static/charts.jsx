/* charts.jsx — SVG chart primitives + icon set for GenAdvisorIQ */

/* ---------------- Icons (stroke, 24-grid) ---------------- */
const ICONS = {
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  spark: "M12 3v4M12 17v4M5 12H3M21 12h-2M6 6l1.5 1.5M16.5 16.5L18 18M18 6l-1.5 1.5M7.5 16.5L6 18",
  chat: "M21 15a4 4 0 0 1-4 4H8l-4 3V7a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4z",
  target: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
  heart: "M12 20s-7-4.5-9.5-9C1 8 2.5 4.5 6 4.5c2 0 3.2 1.2 4 2.3.8-1.1 2-2.3 4-2.3 3.5 0 5 3.5 3.5 6.5C19 15.5 12 20 12 20z",
  wallet: "M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v0H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2V9M16 13h2",
  layers: "M12 3 2 8l10 5 10-5-10-5zM2 13l10 5 10-5M2 18l10 5 10-5",
  scale: "M12 4v16M5 8h14M7 8l-3 6a3 3 0 0 0 6 0zM17 8l-3 6a3 3 0 0 0 6 0z",
  history: "M3 12a9 9 0 1 0 3-6.7M3 5v3h3M12 8v4l3 2",
  chart: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  gear: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 13.5a7.9 7.9 0 0 0 0-3l1.8-1.4-2-3.4-2.1.9a7.6 7.6 0 0 0-2.6-1.5L12 2h-4l-.5 2.6a7.6 7.6 0 0 0-2.6 1.5l-2.1-.9-2 3.4 1.8 1.4a7.9 7.9 0 0 0 0 3L.8 14.9l2 3.4 2.1-.9a7.6 7.6 0 0 0 2.6 1.5L8 22h4l.5-2.6a7.6 7.6 0 0 0 2.6-1.5l2.1.9 2-3.4z",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 3.6-6 8-6s8 2 8 6",
  bell: "M18 8a6 6 0 1 0-12 0c0 7-3 8-3 8h18s-3-1-3-8M13.7 21a2 2 0 0 1-3.4 0",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-4-4",
  arrowUp: "M12 19V5M6 11l6-6 6 6",
  arrowDn: "M12 5v14M6 13l6 6 6-6",
  arrowR: "M5 12h14M13 6l6 6-6 6",
  plus: "M12 5v14M5 12h14",
  send: "M22 2 11 13M22 2l-7 20-4-9-9-4z",
  check: "M20 6 9 17l-5-5",
  sparkle: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 15l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z",
  shield: "M12 3 5 6v5c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3z",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7l1-8z",
  flag: "M5 21V4M5 4c3-2 7 2 10 0v9c-3 2-7-2-10 0",
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
  trend: "M3 17l6-6 4 4 8-8M21 7v5h-5",
  coins: "M9 13a6 3 0 1 0 0-6 6 3 0 0 0 0 6zM3 10v4c0 1.7 2.7 3 6 3M3 14v3c0 1.7 2.7 3 6 3M15 10c3.3 0 6 1.3 6 3v4c0 1.7-2.7 3-6 3-1.2 0-2.3-.2-3.2-.5",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v5M12 8h.01",
  arrowLeft: "M19 12H5M11 18l-6-6 6-6",
  x: "M18 6 6 18M6 6l12 12",
  dots: "M5 12h.01M12 12h.01M19 12h.01",
  download: "M12 3v12M7 10l5 5 5-5M5 21h14",
  filter: "M3 5h18l-7 8v6l-4-2v-4z",
  pie: "M12 3v9h9a9 9 0 1 1-9-9zM14 3a7 7 0 0 1 7 7h-7z",
  cal: "M5 5h14v15H5zM5 9h14M9 3v4M15 3v4",
};

function Icon({ name, size = 18, sw = 1.7, fill = "none", style, className }) {
  const d = ICONS[name] || ICONS.info;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}
         stroke="currentColor" strokeWidth={sw} strokeLinecap="round"
         strokeLinejoin="round" style={style} className={className} aria-hidden="true">
      {d.split("M").filter(Boolean).map((seg, i) => <path key={i} d={"M" + seg} />)}
    </svg>
  );
}

/* ---------------- shared tooltip hook ---------------- */
function useTip() {
  const [tip, setTip] = React.useState(null);
  const node = tip ? <div className="tip" style={{ left: tip.x, top: tip.y }}>{tip.label}</div> : null;
  const show = (e, label) => setTip({ x: e.clientX, y: e.clientY, label });
  const hide = () => setTip(null);
  return { node, show, hide };
}

const fmt$ = (n, d = 0) => "$" + Math.round(n).toLocaleString("en-US", { maximumFractionDigits: d });
const fmtK = (n) => {
  const a = Math.abs(n);
  if (a >= 1e6) return "$" + (n / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
  if (a >= 1e3) return "$" + (n / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
  return "$" + Math.round(n);
};

/* ---------------- Score ring (health score) ---------------- */
function ScoreRing({ value = 0, size = 132, stroke = 13, label }) {
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const start = 135, sweep = 270; // open-bottom gauge
  const polar = (ang) => {
    const a = (ang - 90) * Math.PI / 180;
    return [cx + r * Math.cos(a), cx + r * Math.sin(a)];
  };
  const arc = (from, to) => {
    const [x1, y1] = polar(from), [x2, y2] = polar(to);
    const large = to - from > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  };
  const pct = Math.max(0, Math.min(100, value)) / 100;
  const grade = value >= 80 ? "Excellent" : value >= 65 ? "Strong" : value >= 50 ? "Fair" : "Needs work";
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size}>
        <path d={arc(start, start + sweep)} fill="none" stroke="var(--chart-grid)" strokeWidth={stroke} strokeLinecap="round" />
        <path d={arc(start, start + sweep * pct)} fill="none" stroke="var(--accent)" strokeWidth={stroke}
              strokeLinecap="round" style={{ transition: "all 1s cubic-bezier(.2,.8,.2,1)" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
        <div>
          <div className="metric metric-lg tnum" style={{ fontSize: size * .29 }}>{Math.round(value)}</div>
          <div className="eyebrow" style={{ marginTop: 2 }}>{label || grade}</div>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Area trend (net worth) ---------------- */
function AreaTrend({ data, height = 150, accent = "var(--accent)", showAxis = true }) {
  const ref = React.useRef(null);
  const [w, setW] = React.useState(560);
  const tip = useTip();
  React.useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  const pad = { l: 6, r: 6, t: 12, b: showAxis ? 22 : 8 };
  const vals = data.map(d => d.value);
  const min = Math.min(...vals) * .985, max = Math.max(...vals) * 1.01;
  const X = i => pad.l + (i / (data.length - 1)) * (w - pad.l - pad.r);
  const Y = v => pad.t + (1 - (v - min) / (max - min)) * (height - pad.t - pad.b);
  const line = data.map((d, i) => `${i ? "L" : "M"} ${X(i)} ${Y(d.value)}`).join(" ");
  const area = `${line} L ${X(data.length - 1)} ${height - pad.b} L ${X(0)} ${height - pad.b} Z`;
  const gid = React.useId();
  const [hi, setHi] = React.useState(null);
  const onMove = (e) => {
    const rect = ref.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    let idx = Math.round(((x - pad.l) / (w - pad.l - pad.r)) * (data.length - 1));
    idx = Math.max(0, Math.min(data.length - 1, idx));
    setHi(idx);
    tip.show(e, `${data[idx].label} · ${fmtK(data[idx].value)}`);
  };
  return (
    <div ref={ref} style={{ width: "100%" }} onMouseMove={onMove} onMouseLeave={() => { setHi(null); tip.hide(); }}>
      <svg width={w} height={height} style={{ display: "block" }}>
        <defs>
          <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity=".26" />
            <stop offset="100%" stopColor={accent} stopOpacity="0" />
          </linearGradient>
        </defs>
        {showAxis && [0, .5, 1].map(f => {
          const y = pad.t + f * (height - pad.t - pad.b);
          return <line key={f} x1={pad.l} x2={w - pad.r} y1={y} y2={y} stroke="var(--chart-grid)" strokeWidth="1" />;
        })}
        <path d={area} fill={`url(#${gid})`} />
        <path d={line} fill="none" stroke={accent} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        {hi != null && (
          <g>
            <line x1={X(hi)} x2={X(hi)} y1={pad.t} y2={height - pad.b} stroke="var(--ink-3)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx={X(hi)} cy={Y(data[hi].value)} r="4.5" fill="var(--panel)" stroke={accent} strokeWidth="2.4" />
          </g>
        )}
        {showAxis && data.filter((_, i) => i % Math.ceil(data.length / 6) === 0).map((d) => {
          const i = data.indexOf(d);
          return <text key={i} x={X(i)} y={height - 6} fontSize="10" fill="var(--ink-3)" textAnchor="middle" fontFamily="var(--font-mono)">{d.label}</text>;
        })}
      </svg>
      {tip.node}
    </div>
  );
}

/* ---------------- Income vs Expense bars ---------------- */
function CashflowChart({ data, height = 170 }) {
  const ref = React.useRef(null);
  const [w, setW] = React.useState(560);
  const tip = useTip();
  React.useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  const pad = { l: 6, r: 6, t: 14, b: 22 };
  const max = Math.max(...data.flatMap(d => [d.income, d.expenses])) * 1.12;
  const n = data.length;
  const slot = (w - pad.l - pad.r) / n;
  const bw = Math.min(13, slot * .28);
  const Y = v => pad.t + (1 - v / max) * (height - pad.t - pad.b);
  return (
    <div ref={ref} style={{ width: "100%" }} onMouseLeave={tip.hide}>
      <svg width={w} height={height} style={{ display: "block" }}>
        {[0, .5, 1].map(f => {
          const y = pad.t + f * (height - pad.t - pad.b);
          return <line key={f} x1={pad.l} x2={w - pad.r} y1={y} y2={y} stroke="var(--chart-grid)" strokeWidth="1" />;
        })}
        {data.map((d, i) => {
          const cx = pad.l + slot * (i + .5);
          return (
            <g key={i}>
              <rect x={cx - bw - 2} y={Y(d.income)} width={bw} height={height - pad.b - Y(d.income)} rx="3"
                    fill="var(--accent)" onMouseMove={(e) => tip.show(e, `${d.label} income · ${fmtK(d.income)}`)} />
              <rect x={cx + 2} y={Y(d.expenses)} width={bw} height={height - pad.b - Y(d.expenses)} rx="3"
                    fill="var(--ink-3)" opacity=".5" onMouseMove={(e) => tip.show(e, `${d.label} spend · ${fmtK(d.expenses)}`)} />
              <text x={cx} y={height - 6} fontSize="10" fill="var(--ink-3)" textAnchor="middle" fontFamily="var(--font-mono)">{d.label}</text>
            </g>
          );
        })}
      </svg>
      {tip.node}
    </div>
  );
}

/* ---------------- Donut (allocation) ---------------- */
function Donut({ data, size = 132, thickness = 20 }) {
  const tip = useTip();
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = (size - thickness) / 2, cx = size / 2;
  let acc = 0;
  const seg = (frac) => {
    const a0 = acc * 2 * Math.PI - Math.PI / 2;
    acc += frac;
    const a1 = acc * 2 * Math.PI - Math.PI / 2;
    const p = (a) => [cx + r * Math.cos(a), cx + r * Math.sin(a)];
    const [x0, y0] = p(a0), [x1, y1] = p(a1);
    const large = frac > .5 ? 1 : 0;
    return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
  };
  return (
    <div style={{ position: "relative", width: size, height: size }} onMouseLeave={tip.hide}>
      <svg width={size} height={size} style={{ transform: "rotate(0deg)" }}>
        {data.map((d, i) => (
          <path key={i} d={seg(d.value / total)} fill="none" stroke={d.color} strokeWidth={thickness}
                strokeLinecap="butt"
                onMouseMove={(e) => tip.show(e, `${d.label} · ${Math.round(d.value / total * 100)}%`)} />
        ))}
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div className="metric metric-md tnum">{fmtK(total)}</div>
          <div className="eyebrow">Total</div>
        </div>
      </div>
      {tip.node}
    </div>
  );
}

/* ---------------- Sparkline ---------------- */
function Sparkline({ data, width = 90, height = 30, color = "var(--accent)" }) {
  const min = Math.min(...data), max = Math.max(...data);
  const X = i => (i / (data.length - 1)) * width;
  const Y = v => height - 3 - ((v - min) / (max - min || 1)) * (height - 6);
  const d = data.map((v, i) => `${i ? "L" : "M"} ${X(i)} ${Y(v)}`).join(" ");
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ---------------- Segmented risk meter ---------------- */
function RiskMeter({ value, max = 100, segments = 5, tone = "var(--accent)" }) {
  const on = Math.round((value / max) * segments);
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {Array.from({ length: segments }).map((_, i) => (
        <div key={i} style={{ flex: 1, height: 7, borderRadius: 3, background: i < on ? tone : "var(--panel-3)" }} />
      ))}
    </div>
  );
}

Object.assign(window, { Icon, ICONS, ScoreRing, AreaTrend, CashflowChart, Donut, Sparkline, RiskMeter, useTip, fmt$, fmtK });
