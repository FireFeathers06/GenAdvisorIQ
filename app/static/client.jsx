/* client.jsx — customer self-serve shell for GenAdvisorIQ */

const CLIENT_NAV = [
  { group: "Overview", items: [
    { id: "home",     label: "Home",           icon: "grid"    },
    { id: "ask",      label: "Ask GenAdvisor", icon: "sparkle" },
  ]},
  { group: "Finances", items: [
    { id: "goals",    label: "Goals & plan",      icon: "target" },
    { id: "accounts", label: "Accounts",           icon: "wallet" },
    { id: "insights", label: "Insights",           icon: "spark"  },
  ]},
];

const ASSET_TYPE_ICON = { cash: "wallet", retirement: "coins", invest: "trend", property: "layers" };

/* ---- Asset grid ---- */
function AssetGrid({ p }) {
  const total = p.assets.reduce((s, a) => s + a.value, 0);
  return (
    <div className="card flush">
      <div className="row between" style={{ padding: "14px 18px 12px" }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600, display: "flex", gap: 8, alignItems: "center" }}>
          <Icon name="wallet" size={16} /> Assets
          <span style={{ color: "var(--ink-3)", fontWeight: 500 }}>· {fmtK(total)}</span>
        </h3>
      </div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(176px, 1fr))", padding: "0 16px 16px", gap: 12 }}>
        {p.assets.map(a => (
          <div key={a.name} className="card" style={{ display: "flex", flexDirection: "column", gap: 8, padding: 14 }}>
            <div className="row between">
              <span className="lrow-ico" style={{ width: 28, height: 28 }}>
                <Icon name={ASSET_TYPE_ICON[a.type] || "wallet"} size={14} />
              </span>
              <span className="chip" style={{ fontSize: 10, padding: "1px 6px" }}>{a.type}</span>
            </div>
            <div>
              <div className="eyebrow" style={{ fontSize: 9.5 }}>{a.name}</div>
              <div className="metric tnum" style={{ fontSize: 20, fontWeight: 680, marginTop: 4 }}>{fmtK(a.value)}</div>
              <div className="label-sm" style={{ marginTop: 3, fontSize: 11 }}>{a.inst}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Liabilities list (flex: 1 on name to prevent wrapping overlap) ---- */
function LiabilitiesList({ p }) {
  const total = p.liabilities.reduce((s, l) => s + l.value, 0);
  return (
    <div className="card flush">
      <div className="row between" style={{ padding: "14px 18px 12px" }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600, display: "flex", gap: 8, alignItems: "center" }}>
          <Icon name="scale" size={16} /> Liabilities
          <span style={{ color: "var(--ink-3)", fontWeight: 500 }}>· {fmtK(total)} total</span>
        </h3>
      </div>
      {p.liabilities.map(l => (
        <div key={l.name} style={{ padding: "12px 18px", borderTop: "1px solid var(--line-2)" }}>
          <div className="row between" style={{ marginBottom: 7, gap: 12 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 13, display: "flex", alignItems: "center", gap: 7, minWidth: 0 }}>
                <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{l.name} · {l.inst}</span>
                {l.apr > 15 && <span className="chip" style={{ color: "var(--neg)", borderColor: "color-mix(in oklab,var(--neg) 30%,transparent)", fontSize: 10, padding: "1px 6px", flex: "none" }}>High rate</span>}
              </div>
              <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 2 }}>{l.apr}% APR</div>
            </div>
            <div style={{ textAlign: "right", flex: "none" }}>
              <div className="mono" style={{ fontWeight: 600, fontSize: 14 }}>{fmtK(l.value)}</div>
            </div>
          </div>
          <div className="bar" style={{ height: 5 }}>
            <i style={{ width: Math.round(l.value / total * 100) + "%", background: l.apr > 15 ? "var(--neg)" : "var(--accent)" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- Home quick-action cards ---- */
const QUICK_ACTIONS = [
  { id: "ask",      label: "Ask a question",  icon: "sparkle", desc: "Get instant AI financial advice"   },
  { id: "goals",    label: "View goals",       icon: "target",  desc: "Track your financial goals"        },
  { id: "accounts", label: "My accounts",      icon: "wallet",  desc: "Net worth & all accounts"          },
  { id: "insights", label: "Insights history", icon: "spark",   desc: "Past AI insights & advice"         },
];

/* ---- Home view ---- */
function HomeView({ p, onNav, onAsk, onExplain }) {
  return (
    <div className="scroll" style={{ height: "100%" }}>
      <div className="stack" style={{ maxWidth: 1040, margin: "0 auto" }}>
        <AIBriefing p={p} onAsk={onAsk} />

        <div className="grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          {QUICK_ACTIONS.map(a => (
            <div key={a.id} className="card" style={{ cursor: "pointer", display: "flex", flexDirection: "column", gap: 10 }}
                 onClick={() => a.id === "ask" ? onAsk("What should I focus on financially right now?") : onNav(a.id)}>
              <span className="lrow-ico accent" style={{ width: 34, height: 34 }}><Icon name={a.icon} size={17} /></span>
              <div>
                <div style={{ fontWeight: 650, fontSize: 13.5, lineHeight: 1.2 }}>{a.label}</div>
                <div className="muted" style={{ fontSize: 11.5, marginTop: 3 }}>{a.desc}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid" style={{ gridTemplateColumns: "1fr 1.6fr" }}>
          <HealthScoreCard p={p} onExplain={onExplain} />
          <NetWorthCard p={p} />
        </div>

        <GoalsCard p={p} />
        <RecommendationsCard p={p} onAsk={onAsk} />

        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <InsightsCard p={p} />
          <RiskCard p={p} />
        </div>
      </div>
    </div>
  );
}

/* ---- Ask view (full-width chat) ---- */
function AskView({ p, pendingAsk, onConsumeAsk }) {
  return (
    <div style={{ height: "100%", maxWidth: 880, margin: "0 auto" }}>
      <AICompanion p={p} pendingAsk={pendingAsk} onConsumeAsk={onConsumeAsk} />
    </div>
  );
}

/* ---- Goals view ---- */
function GoalsView({ p, onAsk }) {
  return (
    <div className="scroll" style={{ height: "100%" }}>
      <div className="stack" style={{ maxWidth: 1040, margin: "0 auto" }}>
        <GoalsCard p={p} />
        <RecommendationsCard p={p} onAsk={onAsk} />
        <ActionsCard p={p} />
      </div>
    </div>
  );
}

/* ---- Accounts view ---- */
function AccountsView({ p }) {
  const t = personaTotals(p);
  return (
    <div className="scroll" style={{ height: "100%" }}>
      <div className="stack" style={{ maxWidth: 1040, margin: "0 auto" }}>
        <div className="card">
          <div className="card-hd"><h3><Icon name="trend" size={16} />Net worth</h3></div>
          <div className="row" style={{ gap: 32, marginBottom: 16 }}>
            <div><div className="eyebrow">Total assets</div><div className="metric metric-lg tnum" style={{ color: "var(--pos)", marginTop: 4 }}>{fmtK(t.assets)}</div></div>
            <div><div className="eyebrow">Total liabilities</div><div className="metric metric-lg tnum" style={{ color: "var(--neg)", marginTop: 4 }}>{fmtK(t.liab)}</div></div>
            <div><div className="eyebrow">Net worth</div><div className="metric metric-lg tnum" style={{ marginTop: 4 }}>{fmtK(t.net)}</div></div>
          </div>
          <AreaTrend data={p.netWorthSeries} height={120} />
        </div>
        <AssetGrid p={p} />
        <LiabilitiesList p={p} />
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <AllocationCard p={p} />
          <CashflowCard p={p} />
        </div>
        <RiskCard p={p} />
      </div>
    </div>
  );
}

/* ---- Insights view ---- */
function InsightsView({ p }) {
  return (
    <div className="scroll" style={{ height: "100%" }}>
      <div className="stack" style={{ maxWidth: 860, margin: "0 auto" }}>
        <InsightsCard p={p} />
        <ActionsCard p={p} />
      </div>
    </div>
  );
}

/* ---- Client Rail ---- */
function ClientRail({ active, setActive, setRole }) {
  const p = BASE_PERSONA;
  return (
    <nav className="rail">
      <div className="brand">
        <div className="brand-mark">G</div>
        <div className="brand-name"><b>GenAdvisor</b><span>IQ</span></div>
      </div>
      <div className="role-switch">
        <button className="role-btn" onClick={() => setRole("advisor")}>Advisor</button>
        <button className="role-btn on">Client</button>
      </div>
      {CLIENT_NAV.map(g => (
        <div key={g.group}>
          <div className="nav-group-label">{g.group}</div>
          {g.items.map(it => (
            <div key={it.id} className={"nav-item" + (active === it.id ? " active" : "")} onClick={() => setActive(it.id)}>
              <Icon name={it.icon} size={17} className="nav-ico" /><span className="txt">{it.label}</span>
            </div>
          ))}
        </div>
      ))}
      <div className="rail-foot">
        <div className="user-chip">
          <div className="avatar">{p.initials}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="u-name">{p.name}</div>
            <div className="u-sub">{p.occupation.split("·")[0].trim()}</div>
          </div>
          <Icon name="gear" size={16} style={{ color: "var(--ink-3)" }} className="label-hide" />
        </div>
      </div>
    </nav>
  );
}

/* ---- Client Shell (renders as Fragment so App's .app grid handles layout) ---- */
function ClientShell({ setRole }) {
  const p = BASE_PERSONA;
  const [active, setActive] = React.useState("home");
  const [explainOpen, setExplainOpen] = React.useState(false);
  const [cpending, setCPending] = React.useState({ text: "", n: 0 });

  const cpilotAsk = (text) => setCPending(prev => ({ text, n: prev.n + 1 }));
  cpilotAsk._pending = cpending;
  cpilotAsk._consume = () => setCPending(prev => ({ ...prev, text: "" }));

  const onAsk = (text) => {
    if (text) cpilotAsk(text);
    setActive("ask");
  };

  const TITLES = {
    home:     "Good morning, " + p.name.split(" ")[0],
    ask:      "Ask GenAdvisor",
    goals:    "Goals & plan",
    accounts: "Accounts & net worth",
    insights: "Insights",
  };

  return (
    <>
      <ClientRail active={active} setActive={setActive} setRole={setRole} />
      <div className="main">
        <header className="topbar">
          <div>
            <h1>{TITLES[active] || active}</h1>
            {active === "home" && <span className="sub">{p.occupation}</span>}
          </div>
          <div className="spacer" />
          <div className="search hide-narrow"><Icon name="search" size={15} /> Search…<kbd>⌘K</kbd></div>
          <button className="icon-btn has-dot"><Icon name="bell" size={17} /></button>
          <button className="btn btn-accent" onClick={() => onAsk("What should I focus on financially right now?")}>
            <Icon name="sparkle" size={15} /> Ask GenAdvisor
          </button>
        </header>

        <div style={{ flex: 1, minHeight: 0, padding: "20px 26px 24px" }}>
          {active === "home"     && <HomeView p={p} onNav={setActive} onAsk={onAsk} onExplain={() => setExplainOpen(true)} />}
          {active === "ask"      && <AskView p={p} pendingAsk={cpilotAsk._pending} onConsumeAsk={cpilotAsk._consume} />}
          {active === "goals"    && <GoalsView p={p} onAsk={onAsk} />}
          {active === "accounts" && <AccountsView p={p} />}
          {active === "insights" && <InsightsView p={p} />}
        </div>
      </div>

      {explainOpen && (
        <ExplainModal p={p} onClose={() => setExplainOpen(false)} onAsk={onAsk} />
      )}
    </>
  );
}

Object.assign(window, {
  ClientShell, ClientRail,
  HomeView, AskView, GoalsView, AccountsView, InsightsView,
  AssetGrid, LiabilitiesList,
});
