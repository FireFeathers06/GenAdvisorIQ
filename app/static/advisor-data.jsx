/* advisor-data.jsx — advisor book helpers (real data from API) */

const fmtAum = (n) => {
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
  if (n >= 1e3) return "$" + Math.round(n / 1e3) + "k";
  return "$" + Math.round(n);
};

/* ---- Claude: advisor copilot grounded in the live book ---- */
async function askCopilot(history, focusClient) {
  const clients = window._bookClients || [];
  const advisor = window._advisorInfo || { name: "Advisor", title: "Wealth Advisor" };
  const kpis    = window._bookKpis   || {};

  const top = [...clients].sort((a, b) => b.priority - a.priority).slice(0, 6);
  const aumTotal = kpis.total_aum || clients.reduce((s, c) => s + (c.aum || 0), 0);
  const clientCount = kpis.client_count || clients.length;
  const atRisk = kpis.at_risk_count || clients.filter(c => c.flag).length;

  const bookCtx = `You are Copilot, the AI assistant inside GenAdvisorIQ for ${advisor.name}, a ${advisor.title}. You help the advisor GROW and RETAIN their book of business.
Book: ${fmtAum(aumTotal)} AUM across ${clientCount} clients, ${atRisk} at-risk clients.
Priority clients: ${top.map(c =>
    `${c.name} (${c.segment}, ${fmtAum(c.aum)} AUM, health score ${c.score}, last contact ${c.lastContact}d ago${c.summary ? " — " + c.summary.slice(0, 120) : ""}. Opportunity: ${c.opp.label}${c.opp.value ? " ~" + fmtAum(c.opp.value) : ""}).`
  ).join(" ")}`;

  const clientCtx = focusClient
    ? `\nThe advisor is currently viewing client ${focusClient.name}: ${focusClient.who}, ${focusClient.segment}, ${fmtAum(focusClient.aum)} AUM, health score ${focusClient.score}, last contacted ${focusClient.lastContact} days ago. Suggested action: ${focusClient.action}.${focusClient.summary ? " Summary: " + focusClient.summary : ""}`
    : "";

  const rules = `\nRules: Be concise and action-oriented (2-4 sentences unless asked to draft). Talk like a sharp practice-management coach. Reference SPECIFIC client names and dollar figures from above. If asked to draft an email or call script, write it ready-to-send. Never invent compliance-sensitive claims.`;

  try {
    const msgs = [
      { role: "user", content: bookCtx + clientCtx + rules + "\n\nRespond to the latest advisor turn below." },
      ...history
    ];
    return await window.claude.complete({ messages: msgs });
  } catch (e) {
    if (focusClient) {
      return `For ${focusClient.name}: lead with ${focusClient.action.toLowerCase()}. It has been ${focusClient.lastContact} days since last contact — a quick check-in plus the ${focusClient.opp.label.toLowerCase()} idea is the highest-value move. Want me to draft the outreach?`;
    }
    const urgent = top.slice(0, 3).map(c => `${c.name} (${c.lastContact}d, ${c.action})`).join(", ");
    return `Your top priorities today: ${urgent || "review your flagged clients"}. Want a call list with talking points?`;
  }
}

Object.assign(window, { fmtAum, askCopilot });
