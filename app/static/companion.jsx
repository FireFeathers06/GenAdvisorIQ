/* companion.jsx — central AI companion chat, briefing band, explain modal */

const SUGGESTIONS = [
  "Can I afford a $1,800/mo apartment?",
  "How do I hit my house fund faster?",
  "Am I saving enough for retirement?",
  "What should I do with my next $1,000?",
];

function AICompanion({ p, pendingAsk, onConsumeAsk, variant = "rail" }) {
  const [msgs, setMsgs] = React.useState([
    { role: "assistant", content: `Hi ${p.name.split(" ")[0]} 👋 I've reviewed your finances this morning. Net worth is up ${p.netWorthDelta}% and your health score climbed to ${p.healthScore}. The one thing I'd jump on: that 22.9% credit card. Ask me anything.` },
  ]);
  const [input, setInput] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const streamRef = React.useRef(null);
  const taRef = React.useRef(null);

  const scrollDown = () => requestAnimationFrame(() => {
    if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight;
  });

  const send = async (text) => {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    if (taRef.current) taRef.current.style.height = "auto";
    const next = [...msgs, { role: "user", content: q }];
    setMsgs(next);
    setBusy(true);
    scrollDown();
    const reply = await askAdvisor(next.map(m => ({ role: m.role === "assistant" ? "assistant" : "user", content: m.content })), p);
    setMsgs(m => [...m, { role: "assistant", content: reply }]);
    setBusy(false);
    scrollDown();
  };

  React.useEffect(() => {
    if (pendingAsk && pendingAsk.text) { send(pendingAsk.text); onConsumeAsk && onConsumeAsk(); }
    // eslint-disable-next-line
  }, [pendingAsk && pendingAsk.n]);

  React.useEffect(() => { scrollDown(); }, [busy]);

  const onKey = (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } };
  const grow = (e) => { e.target.style.height = "auto"; e.target.style.height = Math.min(120, e.target.scrollHeight) + "px"; setInput(e.target.value); };

  return (
    <div className="ai-rail" style={{ height: "100%" }}>
      <div className="ai-hd">
        <span className="ai-orb"><Icon name="sparkle" size={17} /></span>
        <div style={{ flex: 1 }}>
          <div className="t">GenAdvisor</div>
          <div className="s"><span className="live-dot" /> Always-on · powered by Claude</div>
        </div>
        <button className="icon-btn" style={{ width: 30, height: 30 }} title="New conversation"
                onClick={() => setMsgs(m => m.slice(0, 1))}><Icon name="plus" size={15} /></button>
      </div>

      <div className="ai-stream" ref={streamRef}>
        {msgs.map((m, i) => (
          <div key={i} className={"msg " + (m.role === "user" ? "user" : "ai") + " rise"}>
            {m.role !== "user" && <span className="m-ava"><Icon name="sparkle" size={14} /></span>}
            <div className="bub">
              {m.role === "user" ? m.content : <Markdown content={m.content} />}
            </div>
          </div>
        ))}
        {busy && (
          <div className="msg ai">
            <span className="m-ava"><Icon name="sparkle" size={14} /></span>
            <div className="bub"><span className="typing"><i /><i /><i /></span></div>
          </div>
        )}
        {msgs.length <= 1 && !busy && (
          <div className="ai-suggest" style={{ marginTop: 4 }}>
            {SUGGESTIONS.map(s => <button key={s} onClick={() => send(s)}>{s}</button>)}
          </div>
        )}
      </div>

      <div className="ai-input">
        <textarea ref={taRef} rows={1} placeholder="Ask about your money…" value={input}
                  onChange={grow} onKeyDown={onKey} />
        <button className="send-btn" disabled={!input.trim() || busy} onClick={() => send()}>
          <Icon name="send" size={16} />
        </button>
      </div>
    </div>
  );
}

/* ---- AI daily briefing band ---- */
function AIBriefing({ p, onAsk }) {
  const t = personaTotals(p);
  const fallback = `You're in a strong position, ${p.name.split(" ")[0]}. Net worth rose ${p.netWorthDelta}% to ${fmtK(t.net)} and you're saving ${p.savingsRate}% of income. The single highest-return move this month is clearing your 22.9% APR card — about $490/yr back in your pocket.`;
  const [text, setText] = React.useState(fallback);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const prompt = `Write a 2-sentence upbeat-but-honest morning financial briefing for ${p.name.split(" ")[0]}. Net worth ${fmtK(t.net)} (+${p.netWorthDelta}% MoM), health score ${p.healthScore}/100, savings rate ${p.savingsRate}%, top issue: a 22.9% APR credit card with $${p.liabilities.find(l => l.apr > 20)?.value || 2150}. Plain language, no greeting, no markdown. End with the single most valuable action.`;
        const r = await window.claude.complete({ messages: [{ role: "user", content: prompt }] });
        if (alive && r && r.length > 20) setText(r.trim());
      } catch (e) { /* keep fallback */ }
      if (alive) setLoading(false);
    })();
    return () => { alive = false; };
  }, [p.name]);

  return (
    <div className="briefing rise">
      <div className="row between" style={{ marginBottom: 12 }}>
        <span className="row" style={{ gap: 9 }}>
          <span className="ai-orb" style={{ width: 28, height: 28 }}><Icon name="sparkle" size={15} /></span>
          <span>
            <div style={{ fontSize: 13.5, fontWeight: 650, whiteSpace: "nowrap" }}>Your morning briefing</div>
            <div className="s" style={{ fontSize: 11, color: "var(--ink-3)", display: "flex", alignItems: "center", gap: 5 }}>
              {loading ? <><span className="typing" style={{ transform: "scale(.8)" }}><i /><i /><i /></span> drafting…</> : <>{new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}</>}
            </div>
          </span>
        </span>
        <span className="chip accent hide-narrow"><Icon name="sparkle" size={12} /> AI generated</span>
      </div>
      <Markdown content={text} style={{ fontSize: 15.5, lineHeight: 1.5, fontWeight: 500, letterSpacing: "-.01em", maxWidth: 760 }} />
      <div className="row" style={{ gap: 8, marginTop: 16 }}>
        <button className="btn btn-accent" onClick={() => onAsk("Build me a 90-day plan to improve my finances")}>
          <Icon name="bolt" size={15} /> Build my 90-day plan
        </button>
        <button className="btn btn-ghost" onClick={() => onAsk("Explain my biggest financial risk right now")}>
          Explain my top risk
        </button>
      </div>
    </div>
  );
}

/* ---- Explainability modal (why this score) ---- */
function ExplainModal({ p, onClose, onAsk }) {
  // Use real hsFactors from persona if available; fall back to empty
  const hsFactors = (p.hsFactors && p.hsFactors.length > 0) ? p.hsFactors : [];

  // Convert hsFactors (0-100 per factor) to driver objects for display
  // A factor above 60 is positive, below 60 is a drag
  const drivers = hsFactors.map(f => {
    const good = f.v >= 60;
    const note = f.note || (good ? `${f.k} is in good shape.` : `${f.k} is below target and dragging the score.`);
    return { k: f.k, v: f.v, good, note };
  });

  const estimatedImproved = Math.min(100, p.healthScore + 12);

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="slideover">
        <div className="ai-hd" style={{ borderBottom: "1px solid var(--line)" }}>
          <span className="ai-orb" style={{ width: 30, height: 30 }}><Icon name="heart" size={16} /></span>
          <div style={{ flex: 1 }}>
            <div className="t">How this score is calculated</div>
            <div className="s">{p.healthScore}/100</div>
          </div>
          <button className="icon-btn" onClick={onClose}><Icon name="x" size={16} /></button>
        </div>
        <div className="scroll" style={{ padding: 18 }}>
          <div className="row" style={{ gap: 16, marginBottom: 18 }}>
            <ScoreRing value={p.healthScore} size={104} />
            <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.5, color: "var(--ink-2)", textWrap: "pretty" }}>
              The score blends five weighted factors — savings rate, debt load, goal progress, insurance coverage, and emergency fund adequacy. Every point is traceable to real numbers.
            </p>
          </div>
          {drivers.length === 0 ? (
            <div style={{ color: "var(--ink-3)", fontSize: 13, padding: "12px 0" }}>Factor breakdown not available for this profile.</div>
          ) : (
            <div className="stack" style={{ gap: 0 }}>
              {drivers.map(d => (
                <div key={d.k} className="lrow" style={{ alignItems: "flex-start" }}>
                  <span className="lrow-ico" style={{
                    color: d.good ? "var(--pos)" : "var(--neg)",
                    background: d.good ? "color-mix(in oklab, var(--pos) 12%, transparent)" : "color-mix(in oklab, var(--neg) 12%, transparent)"
                  }}>
                    <Icon name={d.good ? "arrowUp" : "arrowDn"} size={15} />
                  </span>
                  <div style={{ flex: 1 }}>
                    <div className="row between">
                      <span className="t" style={{ fontSize: 13 }}>{d.k}</span>
                      <span className="mono" style={{ fontWeight: 600, color: d.good ? "var(--pos)" : "var(--warn)" }}>{d.v}/100</span>
                    </div>
                    <div className="d">{d.note}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="explain" style={{ marginTop: 16 }}>
            Addressing the weakest factors could lift the score to an estimated <b style={{ color: "var(--ink)" }}>{estimatedImproved} or higher</b> within 6 months.
          </div>
          <button className="btn btn-accent" style={{ width: "100%", marginTop: 18, justifyContent: "center" }}
                  onClick={() => { onClose(); onAsk("How do I raise my financial health score to " + estimatedImproved + "?"); }}>
            <Icon name="sparkle" size={15} /> Ask how to improve
          </button>
        </div>
      </div>
    </>
  );
}

Object.assign(window, { AICompanion, AIBriefing, ExplainModal, SUGGESTIONS });
