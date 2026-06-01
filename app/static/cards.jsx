/* cards.jsx — dashboard card components for GenAdvisorIQ */

const pct = (cur, tar) => Math.min(100, Math.round((cur / tar) * 100));

/* ---- small KPI stat ---- */
function KPIStat({ label, value, delta, deltaUp, spark, ico }) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="row between">
        <span className="eyebrow">{label}</span>
        {ico && <span className="lrow-ico" style={{ width: 26, height: 26 }}><Icon name={ico} size={15} /></span>}
      </div>
      <div className="row between" style={{ alignItems: "flex-end" }}>
        <div>
          <div className="metric metric-md tnum">{value}</div>
          {delta != null && (
            <div className={"delta " + (deltaUp ? "up" : "down")} style={{ marginTop: 4 }}>
              <Icon name={deltaUp ? "arrowUp" : "arrowDn"} size={13} sw={2.2} />{delta}
            </div>
          )}
        </div>
        {spark && <Sparkline data={spark} color={deltaUp === false ? "var(--neg)" : "var(--accent)"} />}
      </div>
    </div>
  );
}

/* ---- Health score ---- */
function HealthScoreCard({ p, onExplain }) {
  // Use p.hsFactors if provided (from real API), otherwise fall back to empty
  const factors = (p.hsFactors && p.hsFactors.length > 0) ? p.hsFactors : [];
  return (
    <div className="card">
      <div className="card-hd">
        <h3><Icon name="heart" size={16} />Financial health</h3>
        {p.scoreDelta != null && p.scoreDelta !== 0 && (
          <div className="right"><span className={"delta-pill " + (p.scoreDelta >= 0 ? "up" : "down")}>{p.scoreDelta >= 0 ? "+" : ""}{p.scoreDelta} this mo</span></div>
        )}
      </div>
      <div className="row" style={{ gap: 18, alignItems: "center" }}>
        <ScoreRing value={p.healthScore} size={126} />
        <div className="stack" style={{ flex: 1, gap: 9 }}>
          {factors.length === 0 && (
            <div style={{ color: "var(--ink-3)", fontSize: 12.5 }}>Score factors not available.</div>
          )}
          {factors.filter(f => f.v != null).map(f => (
            <div key={f.k}>
              <div className="row between" style={{ marginBottom: 4 }}>
                <span className="label-sm">{f.k}</span>
                <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{f.v}</span>
              </div>
              <div className="bar"><i style={{ width: f.v + "%", background: f.v < 60 ? "var(--warn)" : "var(--accent)" }} /></div>
            </div>
          ))}
        </div>
      </div>
      <button className="btn btn-quiet" style={{ marginTop: 14, paddingLeft: 0 }} onClick={onExplain}>
        <Icon name="sparkle" size={14} /> Why this score?
      </button>
    </div>
  );
}

/* ---- Net worth ---- */
function NetWorthCard({ p }) {
  const t = personaTotals(p);
  const hasHistory = p.netWorthSeries && p.netWorthSeries.length > 1;
  return (
    <div className="card">
      <div className="card-hd">
        <h3><Icon name="trend" size={16} />Net worth</h3>
        {hasHistory && <div className="right hide-narrow"><span className="chip">12-month</span></div>}
      </div>
      <div className="row between" style={{ alignItems: "flex-end", marginBottom: 6 }}>
        <div>
          <div className="metric metric-xl tnum">{fmt$(t.net)}</div>
          {p.netWorthDelta !== 0 && (
            <div className="row" style={{ gap: 10, marginTop: 6 }}>
              <span className={"delta " + (p.netWorthDelta >= 0 ? "up" : "down")}>
                <Icon name={p.netWorthDelta >= 0 ? "arrowUp" : "arrowDn"} size={14} sw={2.2} />{Math.abs(p.netWorthDelta)}% MoM
              </span>
              {hasHistory && <span className="muted" style={{ fontSize: 12.5 }}>+{fmtK(p.netWorthSeries.at(-1).value - p.netWorthSeries[0].value)} this year</span>}
            </div>
          )}
        </div>
        <div className="hide-narrow" style={{ textAlign: "right" }}>
          <div className="label-sm">Assets <b className="mono" style={{ color: "var(--pos)" }}>{fmtK(t.assets)}</b></div>
          <div className="label-sm" style={{ marginTop: 4 }}>Debts <b className="mono" style={{ color: "var(--neg)" }}>{fmtK(t.liab)}</b></div>
        </div>
      </div>
      {hasHistory
        ? <AreaTrend data={p.netWorthSeries} height={150} />
        : (
          <div className="grid" style={{ gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginTop: 8 }}>
            <div className="card" style={{ padding: 12, background: "var(--panel-2)" }}>
              <div className="eyebrow" style={{ fontSize: 10 }}>Total assets</div>
              <div className="metric tnum" style={{ fontSize: 18, color: "var(--pos)", marginTop: 4 }}>{fmtK(t.assets)}</div>
            </div>
            <div className="card" style={{ padding: 12, background: "var(--panel-2)" }}>
              <div className="eyebrow" style={{ fontSize: 10 }}>Total liabilities</div>
              <div className="metric tnum" style={{ fontSize: 18, color: "var(--neg)", marginTop: 4 }}>{fmtK(t.liab)}</div>
            </div>
            <div className="card" style={{ padding: 12, background: "var(--panel-2)" }}>
              <div className="eyebrow" style={{ fontSize: 10 }}>Net worth</div>
              <div className="metric tnum" style={{ fontSize: 18, marginTop: 4 }}>{fmtK(t.net)}</div>
            </div>
          </div>
        )
      }
    </div>
  );
}

/* ---- Cashflow ---- */
function CashflowCard({ p }) {
  const net = p.monthlyIncome - p.monthlyExpenses;
  const hasCashflow = p.cashflow && p.cashflow.length > 0;
  return (
    <div className="card">
      <div className="card-hd">
        <h3><Icon name="bolt" size={16} />Income vs. expenses</h3>
        {hasCashflow && (
          <div className="right">
            <span className="row" style={{ gap: 5, fontSize: 11, color: "var(--ink-2)" }}><i style={{ width: 9, height: 9, borderRadius: 3, background: "var(--accent)", display: "inline-block" }} />Income</span>
            <span className="row" style={{ gap: 5, fontSize: 11, color: "var(--ink-2)" }}><i style={{ width: 9, height: 9, borderRadius: 3, background: "var(--ink-3)", opacity: .5, display: "inline-block" }} />Spend</span>
          </div>
        )}
      </div>
      <div className="row" style={{ gap: 22, marginBottom: 8 }}>
        <div><div className="eyebrow">Net / mo</div><div className="metric metric-md tnum" style={{ color: net >= 0 ? "var(--pos)" : "var(--neg)" }}>{net >= 0 ? "+" : ""}{fmt$(net)}</div></div>
        <div><div className="eyebrow">Savings rate</div><div className="metric metric-md tnum">{p.savingsRate}%</div></div>
      </div>
      {hasCashflow
        ? <CashflowChart data={p.cashflow} height={150} />
        : (
          <div className="stack" style={{ gap: 10, marginTop: 4 }}>
            <div className="row between" style={{ padding: "10px 0", borderTop: "1px solid var(--line-2)" }}>
              <span className="label-sm">Monthly income</span>
              <span className="mono" style={{ fontWeight: 600, color: "var(--pos)" }}>{fmt$(p.monthlyIncome)}</span>
            </div>
            <div className="row between" style={{ padding: "10px 0", borderTop: "1px solid var(--line-2)" }}>
              <span className="label-sm">Monthly expenses</span>
              <span className="mono" style={{ fontWeight: 600, color: "var(--neg)" }}>{fmt$(p.monthlyExpenses)}</span>
            </div>
            <div className="row between" style={{ padding: "10px 0", borderTop: "1px solid var(--line-2)" }}>
              <span className="label-sm">Monthly savings</span>
              <span className="mono" style={{ fontWeight: 600, color: net >= 0 ? "var(--pos)" : "var(--neg)" }}>{net >= 0 ? "+" : ""}{fmt$(net)}</span>
            </div>
          </div>
        )
      }
    </div>
  );
}

/* ---- Allocation ---- */
function AllocationCard({ p }) {
  const total = p.allocation.reduce((s, a) => s + a.value, 0);
  return (
    <div className="card">
      <div className="card-hd"><h3><Icon name="pie" size={16} />Asset allocation</h3></div>
      <div className="row" style={{ gap: 16, alignItems: "center" }}>
        <Donut data={p.allocation} size={128} />
        <div className="stack" style={{ flex: 1, gap: 8 }}>
          {p.allocation.map(a => (
            <div key={a.label} className="row between">
              <span className="row" style={{ gap: 8 }}>
                <i style={{ width: 9, height: 9, borderRadius: 3, background: a.color }} />
                <span className="label-sm">{a.label}</span>
              </span>
              <span className="mono" style={{ fontSize: 12 }}>{Math.round(a.value / total * 100)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---- Goals ---- */
function GoalsCard({ p, compact }) {
  const list = compact ? p.goals.slice(0, 3) : p.goals;
  return (
    <div className="card">
      <div className="card-hd">
        <h3><Icon name="target" size={16} />Goal progress</h3>
        <div className="right"><button className="btn btn-quiet" style={{ height: 28, padding: "0 8px" }}><Icon name="plus" size={14} />New</button></div>
      </div>
      <div className="stack" style={{ gap: 16 }}>
        {list.map(g => {
          const p2 = pct(g.current, g.target);
          return (
            <div key={g.name}>
              <div className="row between" style={{ marginBottom: 7, alignItems: "flex-start", gap: 10 }}>
                <span className="row" style={{ gap: 9, minWidth: 0, flex: 1, alignItems: "flex-start" }}>
                  <span className="lrow-ico" style={{ width: 28, height: 28, flex: "none", background: "color-mix(in oklab," + g.color + " 16%, transparent)", color: g.color }}><Icon name={g.icon} size={15} /></span>
                  <span style={{ minWidth: 0, flex: 1, display: "flex", flexDirection: "column" }}>
                    <span className="t" style={{ fontSize: 13, lineHeight: 1.3 }}>{g.name}</span>
                    <span className="meta" style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 2, display: "block" }}>{fmtK(g.current)} of {fmtK(g.target)} · {fmt$(g.monthly)}/mo</span>
                  </span>
                </span>
                <span style={{ textAlign: "right", flex: "none" }}>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{p2}%</span>
                  <span className="meta" style={{ display: "block", fontSize: 10.5, color: "var(--ink-3)" }}>{g.eta}</span>
                </span>
              </div>
              <div className="bar"><i style={{ width: p2 + "%", background: g.color, transition: "width 1s cubic-bezier(.2,.8,.2,1)" }} /></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- Recommendations (with explainability) ---- */
function RecommendationsCard({ p, onAsk }) {
  const [open, setOpen] = React.useState(null);
  const uColor = { high: "var(--neg)", med: "var(--warn)", low: "var(--ink-3)" };
  return (
    <div className="card">
      <div className="card-hd">
        <h3><Icon name="sparkle" size={16} style={{ color: "var(--accent)" }} />AI recommendations</h3>
        <div className="right"><span className="chip accent">{p.recommendations.length} actions</span></div>
      </div>
      <div className="stack" style={{ gap: 0 }}>
        {p.recommendations.map(r => (
          <div key={r.id} className="lrow" style={{ flexDirection: "column", gap: 0 }}>
            <div className="row" style={{ gap: 12, alignItems: "flex-start" }}>
              <span className="lrow-ico accent"><Icon name="bolt" size={16} /></span>
              <div style={{ flex: 1 }}>
                <div className="row between" style={{ gap: 10, alignItems: "flex-start" }}>
                  <span className="t" style={{ flex: 1, minWidth: 0 }}>{r.title}</span>
                  <span className="delta-pill up" style={{ marginLeft: 8, flex: "none" }}>{r.impact}</span>
                </div>
                <div className="d">{r.body}</div>
                <div className="meta">
                  <span className="chip" style={{ padding: "2px 7px" }}>{r.category}</span>
                  <span className="row" style={{ gap: 4 }}><i style={{ width: 6, height: 6, borderRadius: 99, background: uColor[r.urgency] }} />{r.urgency} priority</span>
                  <button className="btn btn-quiet" style={{ height: 24, padding: "0 6px", fontSize: 11.5 }} onClick={() => setOpen(open === r.id ? null : r.id)}>
                    <Icon name="info" size={13} /> Explain
                  </button>
                  <button className="btn btn-quiet" style={{ height: 24, padding: "0 6px", fontSize: 11.5 }} onClick={() => onAsk && onAsk("Walk me through: " + r.title)}>
                    <Icon name="chat" size={13} /> Ask
                  </button>
                </div>
                {open === r.id && <div className="explain rise">{r.why}</div>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Risk indicators ---- */
function RiskCard({ p }) {
  return (
    <div className="card">
      <div className="card-hd"><h3><Icon name="shield" size={16} />Risk indicators</h3></div>
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {p.risk.map(r => (
          <div key={r.label}>
            <div className="row between" style={{ marginBottom: 6 }}>
              <span className="label-sm">{r.label}</span>
              <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: r.tone }}>{r.value}</span>
            </div>
            <RiskMeter value={r.level} max={r.max} segments={r.max} tone={r.tone} />
            <div className="meta" style={{ marginTop: 5, fontSize: 10.5, color: "var(--ink-3)" }}>{r.note}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Recent insights ---- */
function InsightsCard({ p }) {
  return (
    <div className="card">
      <div className="card-hd">
        <h3><Icon name="spark" size={16} />Recent insights</h3>
        <div className="right"><button className="btn btn-quiet" style={{ height: 28, padding: "0 8px" }}>History<Icon name="arrowR" size={13} /></button></div>
      </div>
      <div className="stack" style={{ gap: 0 }}>
        {p.insights.map(i => (
          <div key={i.id} className="lrow">
            <span className="lrow-ico"><Icon name="spark" size={15} /></span>
            <div style={{ flex: 1 }}>
              <div className="row between" style={{ gap: 8, alignItems: "baseline" }}><span className="t" style={{ fontSize: 12.5, flex: 1, minWidth: 0 }}>{i.title}</span><span className="meta" style={{ fontSize: 10.5, flex: "none" }}>{i.when}</span></div>
              <div className="d" style={{ fontSize: 11.5 }}>{i.body}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Upcoming actions ---- */
function ActionsCard({ p }) {
  const ico = { transfer: "coins", bill: "wallet", review: "check" };
  return (
    <div className="card">
      <div className="card-hd"><h3><Icon name="cal" size={16} />Upcoming actions</h3></div>
      <div className="stack" style={{ gap: 0 }}>
        {p.actions.map(a => (
          <div key={a.id} className="lrow" style={{ alignItems: "center" }}>
            <span className="lrow-ico"><Icon name={ico[a.type]} size={15} /></span>
            <div style={{ flex: 1 }}>
              <div className="t" style={{ fontSize: 12.5 }}>{a.title}</div>
              <div className="meta" style={{ fontSize: 10.5 }}><Icon name="clock" size={11} />{a.due}{a.amount ? " · " + fmt$(a.amount) : ""}</div>
            </div>
            <button className="icon-btn" style={{ width: 28, height: 28 }}><Icon name="check" size={14} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, {
  KPIStat, HealthScoreCard, NetWorthCard, CashflowCard, AllocationCard,
  GoalsCard, RecommendationsCard, RiskCard, InsightsCard, ActionsCard, pct,
});
