/* reports.jsx — AI usage & budget dashboard (Reports nav item) */

const fmtTok = (n) => {
  if (n >= 1e6) return (n / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
  return String(Math.round(n || 0));
};
const fmtCost = (n) => "$" + (n || 0).toFixed(n >= 1 ? 2 : 4);
const ENDPOINT_LABELS = {
  "/api/v1/copilot/ask": "Copilot (grounded chat)",
  "/api/v1/chat/complete": "Chat proxy (legacy)",
};

function BudgetBar({ used, limit }) {
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0;
  const tone = pct >= 90 ? "var(--neg)" : pct >= 70 ? "var(--warn)" : "var(--accent)";
  return (
    <div>
      <div className="row between" style={{ marginBottom: 6 }}>
        <span className="label-sm">Daily token budget</span>
        <span className="mono" style={{ fontSize: 12, color: "var(--ink-2)" }}>
          {fmtTok(used)} / {fmtTok(limit)} · {Math.round(pct)}%
        </span>
      </div>
      <div style={{ height: 8, borderRadius: 99, background: "var(--line)", overflow: "hidden" }}>
        <div style={{ width: pct + "%", height: "100%", borderRadius: 99, background: tone, transition: "width .4s ease" }} />
      </div>
      <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 6 }}>Resets at midnight UTC</div>
    </div>
  );
}

function UsageBars({ daily }) {
  const max = Math.max(1, ...daily.map(d => d.tokens));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 120 }}>
      {daily.map(d => (
        <div key={d.date} title={`${d.date} · ${fmtTok(d.tokens)} tokens · ${fmtCost(d.cost_usd)} · ${d.requests} req`}
             style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 5, minWidth: 0 }}>
          <div style={{
            width: "100%", maxWidth: 34, borderRadius: 4,
            height: Math.max(2, (d.tokens / max) * 96),
            background: d.tokens > 0 ? "var(--accent)" : "var(--line)",
            opacity: d.tokens > 0 ? 0.9 : 1,
          }} />
          <span className="mono" style={{ fontSize: 9, color: "var(--ink-3)", whiteSpace: "nowrap" }}>
            {d.date.slice(5).replace("-", "/")}
          </span>
        </div>
      ))}
    </div>
  );
}

function ReportsView() {
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await window.authFetch("/api/v1/admin/usage");
        const json = await res.json();
        if (alive) {
          if (json.success && json.data) setData(json.data);
          else setError("Could not load usage data.");
        }
      } catch (e) {
        if (alive) setError("Network error: " + e.message);
      }
    })();
    return () => { alive = false; };
  }, []);

  if (error) {
    return <div className="empty"><div style={{ color: "var(--ink-3)" }}>{error}</div></div>;
  }
  if (!data) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--ink-3)", fontSize: 13, gap: 10 }}>
        <span className="typing"><i /><i /><i /></span> Loading usage…
      </div>
    );
  }

  const a = data.advisor || {};
  const today = a.today || { requests: 0, tokens: 0, cost_usd: 0 };
  const total = a.total || { requests: 0, tokens: 0, cost_usd: 0 };
  const budget = a.budget || { daily_limit: 0, used_today: 0 };
  const daily = a.daily || [];
  const endpoints = a.endpoints || [];

  const stats = [
    { label: "AI requests today", value: today.requests,        sub: total.requests + " all time" },
    { label: "Tokens today",      value: fmtTok(today.tokens),  sub: fmtTok(total.tokens) + " all time" },
    { label: "Spend today",       value: fmtCost(today.cost_usd), sub: fmtCost(total.cost_usd) + " all time" },
  ];

  return (
    <div className="scroll" style={{ height: "100%" }}>
      <div className="stack" style={{ maxWidth: 920, margin: "0 auto" }}>
        <div className="briefing rise">
          <div className="row between" style={{ marginBottom: 14 }}>
            <span className="row" style={{ gap: 9 }}>
              <span className="ai-orb" style={{ width: 28, height: 28 }}><Icon name="chart" size={15} /></span>
              <span>
                <div style={{ fontSize: 13.5, fontWeight: 650 }}>Your AI usage</div>
                <div className="s" style={{ fontSize: 11, color: "var(--ink-3)" }}>Copilot &amp; briefing consumption · just you, not the firm</div>
              </span>
            </span>
            <span className="chip accent hide-narrow"><Icon name="sparkle" size={12} /> {data.model || "Claude"}</span>
          </div>
          <BudgetBar used={budget.used_today} limit={budget.daily_limit} />
        </div>

        <div className="grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          {stats.map(s => (
            <div key={s.label} className="card" style={{ padding: 14 }}>
              <div className="eyebrow" style={{ fontSize: 10, marginBottom: 10 }}>{s.label}</div>
              <div className="metric tnum" style={{ fontSize: 23 }}>{s.value}</div>
              <div style={{ marginTop: 6, fontSize: 11.5, color: "var(--ink-3)" }}>{s.sub}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-hd">
            <h3><Icon name="chart" size={16} style={{ color: "var(--accent)" }} />Tokens per day</h3>
            <div className="right"><span className="chip">last {daily.length} days</span></div>
          </div>
          <UsageBars daily={daily} />
        </div>

        <div className="card flush">
          <div className="row between" style={{ padding: "15px 18px 13px" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600, display: "flex", gap: 8, alignItems: "center" }}>
              <Icon name="bolt" size={16} /> By feature
            </h3>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderTop: "1px solid var(--line)", borderBottom: "1px solid var(--line)" }}>
                {["Feature", "Requests", "Tokens", "Cost"].map((h, i) => (
                  <th key={h} style={{ textAlign: i === 0 ? "left" : "right", padding: "9px 18px", fontSize: 10.5, fontWeight: 600, letterSpacing: ".05em", textTransform: "uppercase", color: "var(--ink-3)" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {endpoints.length === 0 && (
                <tr><td colSpan={4} style={{ padding: 22, textAlign: "center", color: "var(--ink-3)" }}>No AI usage recorded yet — ask the copilot something.</td></tr>
              )}
              {endpoints.map(e => (
                <tr key={e.endpoint} style={{ borderBottom: "1px solid var(--line-2)" }}>
                  <td style={{ padding: "11px 18px" }}>
                    <b style={{ fontWeight: 600 }}>{ENDPOINT_LABELS[e.endpoint] || e.endpoint}</b>
                    <span className="meta" style={{ display: "block", fontSize: 11, color: "var(--ink-3)" }}>{e.endpoint}</span>
                  </td>
                  <td className="mono" style={{ padding: "11px 18px", textAlign: "right" }}>{e.requests}</td>
                  <td className="mono" style={{ padding: "11px 18px", textAlign: "right" }}>{fmtTok(e.tokens)}</td>
                  <td className="mono" style={{ padding: "11px 18px", textAlign: "right" }}>{fmtCost(e.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {data.platform && (
          <div style={{ fontSize: 11.5, color: "var(--ink-3)", padding: "0 4px 8px" }}>
            Platform-wide (all advisors &amp; system jobs): {data.platform.total.requests} requests · {fmtTok(data.platform.total.tokens)} tokens · {fmtCost(data.platform.total.cost_usd)} all time.
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ReportsView });
