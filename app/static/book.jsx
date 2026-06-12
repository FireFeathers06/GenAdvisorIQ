/* book.jsx — advisor book-of-business views, copilot, client detail */

/* ---------------- Advisor AI Copilot ---------------- */
const COPILOT_SUGGEST_BOOK = [
  "Who should I call this week?",
  "Where's my biggest revenue opportunity?",
  "Which clients are at risk of leaving?",
  "Draft a re-engagement email for my top at-risk client",
];

const COPILOT_SUGGEST_CLIENT = (c) => [
  `What should I discuss with ${c.name.split(" ")[0]}?`,
  `Draft an outreach email`,
  `How do I grow this relationship?`,
  `Prep me for the review call`,
];


function AdvisorCopilot({ focusClient, pendingAsk, onConsumeAsk }) {
  const advisor  = window._advisorInfo || { name: "Jordan" };
  const firstName = (advisor.name || "Jordan").split(" ")[0];
  const atRisk   = (window._bookKpis || {}).at_risk_count || 0;

  const greeting = focusClient
    ? `Looking at ${focusClient.name}. Last contact was ${focusClient.lastContact} days ago. I can draft outreach or prep your call — just ask.`
    : `Good morning, ${firstName}. I scanned your book: ${atRisk} client${atRisk !== 1 ? "s" : ""} need${atRisk === 1 ? "s" : ""} attention. Want today's call list?`;

  const [msgs, setMsgs] = React.useState([{ role: "assistant", content: greeting }]);
  const [input, setInput] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [toolNote, setToolNote] = React.useState(null);
  const [budget, setBudget] = React.useState(window._aiBudget || null);
  const [clientSuggestions, setClientSuggestions] = React.useState(null);
  const streamRef = React.useRef(null);
  const taRef = React.useRef(null);

  // Signal-driven suggestions for the focused client (birthday coming up,
  // uncovered spend, premium due, …) — static chips are the fallback.
  React.useEffect(() => {
    setClientSuggestions(null);
    if (!focusClient) return;
    let alive = true;
    (async () => {
      try {
        const r = await window.authFetch(`/api/v1/copilot/suggestions/${focusClient.id}`);
        if (!r.ok) return;
        const j = await r.json();
        if (alive && j.suggestions && j.suggestions.length) setClientSuggestions(j.suggestions);
      } catch (e) {}
    })();
    return () => { alive = false; };
  }, [focusClient && focusClient.id]);

  const suggestions = focusClient
    ? (clientSuggestions || COPILOT_SUGGEST_CLIENT(focusClient).map(s => ({ label: s, ask: s })))
    : COPILOT_SUGGEST_BOOK.map(s => ({ label: s, ask: s }));

  React.useEffect(() => {
    setMsgs([{ role: "assistant", content: greeting }]);
  }, [focusClient && focusClient.id]);

  const scrollDown = () => requestAnimationFrame(() => {
    if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight;
  });

  const send = async (text, display) => {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    if (taRef.current) taRef.current.style.height = "auto";
    // display: short chip label shown in the bubble; content: full prompt sent
    const next = [...msgs, { role: "user", content: q, display }];
    setMsgs(next);
    setBusy(true);
    setToolNote(null);
    scrollDown();

    // Stream the reply: append an assistant bubble on the first token, then
    // grow it in place. Tool events surface as a status line while we wait.
    let streaming = false;
    const reply = await askCopilot(
      next.map((m) => ({ role: m.role === "assistant" ? "assistant" : "user", content: m.content })),
      focusClient,
      {
        onText: (delta, full) => {
          setToolNote(null);
          if (!streaming) {
            streaming = true;
            setMsgs((m) => [...m, { role: "assistant", content: full }]);
          } else {
            setMsgs((m) => {
              const copy = [...m];
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: full };
              return copy;
            });
          }
          scrollDown();
        },
        onTool: (ev) => { setToolNote(ev.label || "Fetching data…"); scrollDown(); },
      }
    );
    setMsgs((m) => {
      const copy = [...m];
      if (streaming) copy[copy.length - 1] = { role: "assistant", content: reply };
      else copy.push({ role: "assistant", content: reply });
      return copy;
    });
    setBudget(window._aiBudget || null);
    setBusy(false);
    setToolNote(null);
    scrollDown();
  };

  React.useEffect(() => {
    if (pendingAsk && pendingAsk.text) { send(pendingAsk.text); onConsumeAsk && onConsumeAsk(); }
  }, [pendingAsk && pendingAsk.n]);
  React.useEffect(() => { scrollDown(); }, [busy]);

  const onKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } };
  const grow  = (e) => { e.target.style.height = "auto"; e.target.style.height = Math.min(120, e.target.scrollHeight) + "px"; setInput(e.target.value); };

  return (
    <div className="ai-rail" style={{ height: "100%" }}>
      <div className="ai-hd">
        <span className="ai-orb"><Icon name="sparkle" size={17} /></span>
        <div style={{ flex: 1 }}>
          <div className="t">Copilot{focusClient ? " · " + focusClient.name.split(" ")[0] : ""}</div>
          <div className="s">
            <span className="live-dot" /> Book-aware · powered by Claude
            {budget && budget.daily_limit ? ` · ${Math.min(100, Math.round(budget.used_today / budget.daily_limit * 100))}% budget used` : ""}
          </div>
        </div>
        <button className="icon-btn" style={{ width: 30, height: 30 }}
                onClick={() => setMsgs([{ role: "assistant", content: greeting }])} title="Reset">
          <Icon name="plus" size={15} />
        </button>
      </div>
      <div className="ai-stream" ref={streamRef}>
        {msgs.map((m, i) => (
          <div key={i} className={"msg " + (m.role === "user" ? "user" : "ai") + " rise"}>
            {m.role !== "user" && <span className="m-ava"><Icon name="sparkle" size={14} /></span>}
            <div className="bub">
              {m.role === "user" ? (m.display || m.content) : <Markdown content={m.content} />}
            </div>
          </div>
        ))}
        {busy && (toolNote || msgs[msgs.length - 1].role === "user") && (
          <div className="msg ai">
            <span className="m-ava"><Icon name="sparkle" size={14} /></span>
            <div className="bub">
              {toolNote
                ? <span className="row" style={{ gap: 8, fontSize: 12, color: "var(--ink-2)" }}>
                    <span className="typing" style={{ transform: "scale(.85)" }}><i /><i /><i /></span> {toolNote}
                  </span>
                : <span className="typing"><i /><i /><i /></span>}
            </div>
          </div>
        )}
        {msgs.length <= 1 && !busy && (
          <div className="ai-suggest" style={{ marginTop: 4 }}>
            {suggestions.map((s) => <button key={s.label} onClick={() => send(s.ask, s.label)}>{s.label}</button>)}
          </div>
        )}
      </div>
      <div className="ai-input">
        <textarea ref={taRef} rows={1} placeholder={focusClient ? "Ask about this client…" : "Ask about your book…"}
                  value={input} onChange={grow} onKeyDown={onKey} />
        <button className="send-btn" disabled={!input.trim() || busy} onClick={() => send()}>
          <Icon name="send" size={16} />
        </button>
      </div>
    </div>
  );
}

/* ---------------- Book briefing band ---------------- */
function BookBriefing({ clients, ask }) {
  const top = [...(clients || [])].sort((a, b) => b.priority - a.priority).slice(0, 3);
  const clientCount = (window._bookKpis || {}).client_count || (clients || []).length;

  const fallback = top.length > 0
    ? `${top.length} relationship${top.length !== 1 ? "s" : ""} need${top.length === 1 ? "s" : ""} your attention today. ${top.map(c => `${c.name} — ${c.action} (${c.lastContact}d since last contact)`).join("; ")}.`
    : "Your book is looking healthy today. No urgent follow-ups flagged.";

  const [text, setText] = React.useState(fallback);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let alive = true;
    (async () => {
      try {
        if (top.length > 0) {
          // Server-side grounding: the backend already has the full book
          // snapshot, so the prompt carries only the instruction.
          const prompt = "Write a 2-3 sentence punchy morning briefing about my book. Lead with the relationships that need attention today and end with the single highest-value action. Plain text, no greeting line, no markdown headers.";
          const r = await window.claude.stream({
            messages: [{ role: "user", content: prompt }],
            scope: "book",
            onText: (delta, full) => { if (alive && full.length > 20) { setText(full.trim()); setLoading(false); } },
          });
          if (alive && r.content && r.content.length > 20) setText(r.content.trim());
        }
      } catch (e) {}
      if (alive) setLoading(false);
    })();
    return () => { alive = false; };
  }, []);

  return (
    <div className="briefing rise">
      <div className="row between" style={{ marginBottom: 12 }}>
        <span className="row" style={{ gap: 9 }}>
          <span className="ai-orb" style={{ width: 28, height: 28 }}><Icon name="sparkle" size={15} /></span>
          <span>
            <div style={{ fontSize: 13.5, fontWeight: 650, whiteSpace: "nowrap" }}>Your book this morning</div>
            <div className="s" style={{ fontSize: 11, color: "var(--ink-3)", display: "flex", alignItems: "center", gap: 5 }}>
              {loading
                ? <><span className="typing" style={{ transform: "scale(.8)" }}><i /><i /><i /></span> scanning {clientCount} clients…</>
                : "Updated just now"}
            </div>
          </span>
        </span>
        <span className="chip accent hide-narrow"><Icon name="sparkle" size={12} /> AI generated</span>
      </div>
      <Markdown content={text} style={{ fontSize: 15.5, lineHeight: 1.5, fontWeight: 500, letterSpacing: "-.01em", maxWidth: 820 }} />
      <div className="row" style={{ gap: 8, marginTop: 16 }}>
        <button className="btn btn-accent" onClick={() => ask("Build my prioritized call list for today with talking points")}>
          <Icon name="bolt" size={15} /> Build my call list
        </button>
        <button className="btn btn-ghost" onClick={() => ask("Where is my biggest revenue opportunity this quarter?")}>
          Find revenue
        </button>
      </div>
    </div>
  );
}

/* ---------------- Book KPIs ---------------- */
function BookKPIs({ kpis, cols = 6 }) {
  const k = kpis || {};
  const stats = [
    { label: "Assets under mgmt", value: fmtAum(k.total_aum || 0),    delta: k.client_count + " clients",   up: true,  ico: "coins" },
    { label: "Clients",            value: k.client_count || 0,         delta: "active relationships",         up: true,  ico: "user"  },
    { label: "At-risk",            value: k.at_risk_count || 0,        delta: "needs attention",              up: false, ico: "shield"},
    { label: "Goals tracked",      value: k.goal_count || 0,           delta: "across all clients",           up: true,  ico: "target"},
  ];

  const displayCols = Math.min(cols, stats.length);
  return (
    <div className="grid" style={{ gridTemplateColumns: `repeat(${displayCols}, 1fr)` }}>
      {stats.slice(0, displayCols).map((s) => (
        <div key={s.label} className="card" style={{ padding: 14 }}>
          <div className="row between" style={{ marginBottom: 10 }}>
            <span className="eyebrow" style={{ fontSize: 10 }}>{s.label}</span>
          </div>
          <div className="metric tnum" style={{ fontSize: 23 }}>{s.value}</div>
          <div className={"delta " + (s.up ? "up" : "down")} style={{ marginTop: 6, fontSize: 11.5, color: s.up ? "var(--pos)" : "var(--warn)" }}>
            {s.label === "At-risk" ? <Icon name="info" size={12} /> : <Icon name={s.up ? "arrowUp" : "arrowDn"} size={12} sw={2.2} />}{s.delta}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---- shared bits ---- */
function ScorePill({ v }) {
  const tone = v >= 80 ? "var(--pos)" : v >= 65 ? "var(--accent)" : "var(--warn)";
  return (
    <span className="mono" style={{ fontWeight: 600, fontSize: 12.5, color: v >= 65 ? "var(--ink)" : "var(--warn)", display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 7, height: 7, borderRadius: 99, background: tone }} />{v}
    </span>
  );
}
function SentimentDot({ s }) {
  const c = { champion: "var(--pos)", warm: "var(--accent)", cooling: "var(--warn)" }[s] || "var(--ink-3)";
  return <span title={s} style={{ width: 8, height: 8, borderRadius: 99, background: c, display: "inline-block" }} />;
}
function OppChip({ opp }) {
  return <span className="chip accent" style={{ fontWeight: 600 }}>{opp.label}{opp.value ? " · " + fmtAum(opp.value) : ""}</span>;
}
function Contact({ d }) {
  const never = !d || d >= 999;
  const warn = never || d > 60;
  const label = never ? "Never" : d + "d ago";
  return <span className="mono" style={{ fontSize: 12, color: warn ? "var(--neg)" : "var(--ink-2)" }}>{label}</span>;
}

/* ---------------- Client TABLE ---------------- */
function ClientTable({ clients, onOpen }) {
  const [sort, setSort] = React.useState({ key: "priority", dir: -1 });
  const cols = [
    { key: "name",        label: "Client",          align: "left"  },
    { key: "aum",         label: "AUM",             align: "right" },
    { key: "score",       label: "Health",          align: "right" },
    { key: "opp",         label: "Top opportunity", align: "left"  },
    { key: "lastContact", label: "Last contact",    align: "right" },
    { key: "action",      label: "Next action",     align: "left"  },
  ];

  const list = clients || [];
  const sorted = [...list].sort((a, b) => {
    let av = a[sort.key], bv = b[sort.key];
    if (sort.key === "opp") { av = a.opp.value; bv = b.opp.value; }
    if (typeof av === "string") return av.localeCompare(bv) * sort.dir;
    return (av - bv) * sort.dir;
  });
  const setS = (key) => setSort((s) => s.key === key ? { key, dir: -s.dir } : { key, dir: key === "name" || key === "action" ? 1 : -1 });

  return (
    <div className="card flush">
      <div className="row between" style={{ padding: "15px 18px 13px" }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600, display: "flex", gap: 8, alignItems: "center" }}>
          <Icon name="user" size={16} /> Priority clients <span className="hint" style={{ color: "var(--ink-3)", fontWeight: 500 }}>· {list.length} total</span>
        </h3>
        <div className="row" style={{ gap: 6 }}>
          <button className="btn btn-quiet" style={{ height: 30 }}><Icon name="filter" size={14} /> Filter</button>
          <button className="btn btn-quiet" style={{ height: 30 }}><Icon name="download" size={14} /> Export</button>
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 820 }}>
          <thead>
            <tr style={{ borderTop: "1px solid var(--line)", borderBottom: "1px solid var(--line)" }}>
              {cols.map((c) => (
                <th key={c.key} onClick={() => setS(c.key)}
                    style={{ textAlign: c.align, padding: "9px 18px", fontSize: 10.5, fontWeight: 600, letterSpacing: ".05em", textTransform: "uppercase", color: "var(--ink-3)", cursor: "pointer", whiteSpace: "nowrap", userSelect: "none" }}>
                  {c.label}{sort.key === c.key ? sort.dir === -1 ? " ↓" : " ↑" : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((c) => (
              <tr key={c.id} onClick={() => onOpen(c)}
                  style={{ borderBottom: "1px solid var(--line-2)", cursor: "pointer", background: c.flag ? "color-mix(in oklab, var(--warn) 5%, transparent)" : "transparent" }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "var(--hover)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = c.flag ? "color-mix(in oklab, var(--warn) 5%, transparent)" : "transparent"}>
                <td style={{ padding: "11px 18px" }}>
                  <span className="row" style={{ gap: 10 }}>
                    <span className="avatar" style={{ width: 30, height: 30, fontSize: 11 }}>{c.initials}</span>
                    <span>
                      <span className="row" style={{ gap: 6 }}>
                        <SentimentDot s={c.sentiment} />
                        <b style={{ fontWeight: 600, whiteSpace: "nowrap" }}>{c.name}</b>
                        {c.flag && <Icon name="info" size={13} style={{ color: "var(--warn)" }} />}
                      </span>
                      <span className="meta" style={{ display: "block", fontSize: 11, color: "var(--ink-3)" }}>{c.who} · {c.segment}</span>
                    </span>
                  </span>
                </td>
                <td style={{ padding: "11px 18px", textAlign: "right" }}><b className="mono" style={{ fontWeight: 600 }}>{fmtAum(c.aum)}</b></td>
                <td style={{ padding: "11px 18px", textAlign: "right" }}><ScorePill v={c.score} /></td>
                <td style={{ padding: "11px 18px" }}><OppChip opp={c.opp} /></td>
                <td style={{ padding: "11px 18px", textAlign: "right" }}><Contact d={c.lastContact} /></td>
                <td style={{ padding: "11px 18px" }}><span className="row" style={{ gap: 6, color: "var(--ink-2)" }}><Icon name="arrowR" size={13} style={{ color: "var(--accent)" }} />{c.action}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ---------------- Client CARDS ---------------- */
function ClientCards({ clients, onOpen }) {
  const list = clients || [];
  return (
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}>
      {[...list].sort((a, b) => b.aum - a.aum).map((c) => (
        <div key={c.id} className="card" style={{ cursor: "pointer", display: "flex", flexDirection: "column", gap: 12 }} onClick={() => onOpen(c)}>
          <div className="row between">
            <span className="row" style={{ gap: 10 }}>
              <span className="avatar" style={{ width: 36, height: 36 }}>{c.initials}</span>
              <span>
                <b style={{ fontWeight: 600, fontSize: 13.5, whiteSpace: "nowrap" }}>{c.name}</b>
                <span className="meta" style={{ display: "block", fontSize: 11, color: "var(--ink-3)" }}>{c.segment}</span>
              </span>
            </span>
            {c.flag ? <span className="chip" style={{ color: "var(--warn)", borderColor: "color-mix(in oklab,var(--warn) 30%,transparent)" }}>Attention</span> : <SentimentDot s={c.sentiment} />}
          </div>
          <div className="row between" style={{ alignItems: "flex-end" }}>
            <div>
              <div className="eyebrow">AUM</div>
              <div className="metric tnum" style={{ fontSize: 24 }}>{fmtAum(c.aum)}</div>
            </div>
          </div>
          <div className="divider" style={{ margin: "2px 0" }} />
          <div className="row between"><span className="label-sm">Health</span><ScorePill v={c.score} /></div>
          <OppChip opp={c.opp} />
          <div className="row" style={{ gap: 6, color: "var(--ink-2)", fontSize: 12 }}>
            <Icon name="arrowR" size={13} style={{ color: "var(--accent)" }} />{c.action}
            <span style={{ marginLeft: "auto" }}><Contact d={c.lastContact} /></span>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---------------- WORKLIST (AI prioritized) ---------------- */
function Worklist({ clients, onOpen, ask }) {
  const list = clients || [];
  const ranked = [...list].filter((c) => c.flag || c.priority >= 50).sort((a, b) => b.priority - a.priority);
  return (
    <div className="card">
      <div className="card-hd">
        <h3><Icon name="bolt" size={16} style={{ color: "var(--accent)" }} />Today's priorities</h3>
        <div className="right"><span className="chip accent">AI ranked</span></div>
      </div>
      <div className="stack" style={{ gap: 0 }}>
        {ranked.length === 0 && (
          <div style={{ padding: 24, color: "var(--ink-3)", textAlign: "center", fontSize: 13 }}>No flagged clients today. Great shape!</div>
        )}
        {ranked.map((c, i) => (
          <div key={c.id} className="lrow" style={{ alignItems: "flex-start", gap: 12 }}>
            <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--ink-3)", width: 18, fontSize: 13, paddingTop: 6 }}>{i + 1}</span>
            <span className="avatar" style={{ width: 36, height: 36, marginTop: 2 }}>{c.initials}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="row between">
                <span className="row" style={{ gap: 7 }}>
                  <b style={{ fontWeight: 600, fontSize: 13.5, whiteSpace: "nowrap" }}>{c.name}</b>
                  <span className="chip" style={{ padding: "1px 7px" }}>{c.segment}</span>
                  <span className="mono muted" style={{ fontSize: 11.5 }}>{fmtAum(c.aum)}</span>
                </span>
                {c.flag && (
                  <span className="chip" style={{ color: "var(--warn)", borderColor: "color-mix(in oklab,var(--warn) 30%,transparent)" }}>
                    <Icon name="info" size={12} /> {c.lastContact >= 999 ? "No contact" : c.lastContact + "d dark"}
                  </span>
                )}
              </div>
              {c.summary && (() => {
                const plain = c.summary.replace(/\*{1,3}|_{1,2}|`|#{1,6}\s?/g, "");
                return <div className="d" style={{ fontSize: 12.5, marginTop: 5 }}>{plain.length > 180 ? plain.slice(0, 180) + "…" : plain}</div>;
              })()}
              <div className="row" style={{ gap: 7, marginTop: 9 }}>
                <button className="btn btn-accent" style={{ height: 28, fontSize: 12 }}
                        onClick={(e) => { e.stopPropagation(); ask(`Draft outreach to ${c.name} about: ${c.opp.label}. They haven't been contacted in ${c.lastContact} days.`); }}>
                  <Icon name="send" size={13} /> Draft outreach
                </button>
                <button className="btn btn-ghost" style={{ height: 28, fontSize: 12 }} onClick={() => onOpen(c)}>Open client</button>
                <span className="row" style={{ gap: 5, marginLeft: "auto", color: "var(--ink-2)", fontSize: 12 }}>
                  <Icon name="target" size={13} style={{ color: "var(--accent)" }} />{c.opp.label}{c.opp.value ? " · " + fmtAum(c.opp.value) : ""}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------- BOOK VIEW (3 layouts) ---------------- */
function BookView({ layout, onOpen, ask, copilotAsk, clients, kpis }) {
  const rail = (
    <div style={{ height: "100%", minHeight: 0, overflow: "hidden" }}>
      <AdvisorCopilot pendingAsk={copilotAsk._pending} onConsumeAsk={copilotAsk._consume} />
    </div>
  );

  if (layout === "table") {
    return (
      <div className="scroll" style={{ height: "100%" }}>
        <div className="stack">
          <BookBriefing clients={clients} ask={ask} />
          <BookKPIs kpis={kpis} />
          <ClientTable clients={clients} onOpen={onOpen} />
        </div>
      </div>
    );
  }
  if (layout === "cards") {
    return (
      <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) 384px", gridTemplateRows: "minmax(0,1fr)", height: "100%", minHeight: 0 }}>
        <div className="scroll" style={{ minHeight: 0, height: "100%", paddingRight: 4 }}>
          <div className="stack">
            <BookKPIs kpis={kpis} cols={3} />
            <ClientCards clients={clients} onOpen={onOpen} />
          </div>
        </div>
        {rail}
      </div>
    );
  }
  // worklist (default)
  return (
    <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) 384px", gridTemplateRows: "minmax(0,1fr)", height: "100%", minHeight: 0 }}>
      <div className="scroll" style={{ minHeight: 0, height: "100%", paddingRight: 4 }}>
        <div className="stack">
          <BookKPIs kpis={kpis} cols={3} />
          <Worklist clients={clients} onOpen={onOpen} ask={copilotAsk} />
        </div>
      </div>
      {rail}
    </div>
  );
}

/* ---------------- CLIENT DETAIL ---------------- */
function ClientDetail({ bookClient, context, onBack, explain, copilotAsk }) {
  // Build persona from the full context returned by admin/customers/{id}
  const persona = React.useMemo(() => {
    if (!context) return null;
    // Inject hs_factors from bookClient into the context before building
    const enrichedCtx = context;
    if (bookClient && bookClient.hs_factors) {
      enrichedCtx.hs_factors = bookClient.hs_factors;
    }
    if (bookClient && bookClient.health_score != null) {
      if (!enrichedCtx.financial_summary) enrichedCtx.financial_summary = {};
      enrichedCtx.financial_summary.health_score = bookClient.health_score;
    }
    return buildPersonaFromContext(enrichedCtx);
  }, [context, bookClient && bookClient.id]);

  const c = bookClient;

  if (!persona) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--ink-3)", fontSize: 14 }}>
        Loading client profile…
      </div>
    );
  }

  return (
    <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) 384px", gridTemplateRows: "minmax(0,1fr)", height: "100%", minHeight: 0 }}>
      <div className="scroll" style={{ minHeight: 0, height: "100%", paddingRight: 4 }}>
        <div className="stack">
          {/* advisor action header */}
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="row between">
              <button className="btn btn-quiet" style={{ paddingLeft: 0 }} onClick={onBack}>
                <Icon name="arrowLeft" size={15} /> Book
              </button>
              <div className="row" style={{ gap: 6 }}>
                <button className="btn btn-ghost"><Icon name="chat" size={15} /> Log note</button>
                <button className="btn btn-ghost"><Icon name="cal" size={15} /> Schedule</button>
                <button className="btn btn-accent" onClick={() => copilotAsk("Draft an outreach email for " + c.name + " about " + c.opp.label)}>
                  <Icon name="send" size={15} /> Outreach
                </button>
              </div>
            </div>
            <div className="row" style={{ gap: 16 }}>
              <span className="avatar" style={{ width: 56, height: 56, fontSize: 19 }}>{c.initials}</span>
              <div style={{ flex: 1 }}>
                <div className="row" style={{ gap: 9 }}>
                  <h1 style={{ margin: 0, fontSize: 22, letterSpacing: "-.02em" }}>{c.name}</h1>
                  <SentimentDot s={c.sentiment} />
                  <span className="chip">{c.segment}</span>
                </div>
                <div className="sub" style={{ color: "var(--ink-3)", fontSize: 13, marginTop: 3 }}>
                  {c.who} · Last contact {c.lastContact} days ago
                </div>
              </div>
              <div className="row hide-narrow" style={{ gap: 26 }}>
                <div><div className="eyebrow">AUM</div><div className="metric tnum" style={{ fontSize: 22 }}>{fmtAum(c.aum)}</div></div>
                <div><div className="eyebrow">Health</div><div style={{ marginTop: 4 }}><ScorePill v={c.score} /></div></div>
              </div>
            </div>
            {c.flag && (
              <div className="explain" style={{ borderLeftColor: "var(--warn)" }}>
                <b style={{ color: "var(--ink)" }}>Needs attention.</b> Last contact was {c.lastContact} days ago.
                {c.health_score < 60 ? " Financial health score is below target." : ""}
              </div>
            )}
          </div>

          {/* AI summary card if available */}
          {persona.summary && (
            <div className="card" style={{ borderLeft: "3px solid var(--accent)" }}>
              <div className="card-hd">
                <h3><Icon name="sparkle" size={16} style={{ color: "var(--accent)" }} />AI advisor summary</h3>
                <span className="chip accent">Generated by Claude</span>
              </div>
              <Markdown content={persona.summary} style={{ fontSize: 13.5, lineHeight: 1.6, color: "var(--ink-2)" }} />
            </div>
          )}

          <NetWorthCard p={persona} />
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <HealthScoreCard p={persona} onExplain={explain} />
            <AllocationCard p={persona} />
          </div>
          {persona.recommendations && persona.recommendations.length > 0 && (
            <RecommendationsCard p={persona} onAsk={copilotAsk} />
          )}
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <CashflowCard p={persona} />
            <RiskCard p={persona} />
          </div>
          {persona.goals && persona.goals.length > 0 && <GoalsCard p={persona} />}
        </div>
      </div>
      <div style={{ height: "100%", minHeight: 0, overflow: "hidden" }}>
        <AdvisorCopilot focusClient={c} pendingAsk={copilotAsk._pending} onConsumeAsk={copilotAsk._consume} />
      </div>
    </div>
  );
}

Object.assign(window, {
  AdvisorCopilot, BookBriefing, BookKPIs, ClientTable, ClientCards,
  Worklist, BookView, ClientDetail,
  ScorePill, SentimentDot, OppChip, Contact,
});
