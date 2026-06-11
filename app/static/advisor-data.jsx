/* advisor-data.jsx — advisor book helpers (real data from API) */

const fmtAum = (n) => {
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(2).replace(/\.?0+$/, "") + "M";
  if (n >= 1e3) return "$" + Math.round(n / 1e3) + "k";
  return "$" + Math.round(n);
};

/* ---- Claude: advisor copilot, grounded server-side (Phase 3) ----
   Context (book snapshot + drill-down tools) lives on the backend; we send
   only the conversation and a scope. handlers: { onText, onTool }. */
async function askCopilot(history, focusClient, handlers = {}) {
  // The API requires the first message to be a user turn — drop UI greetings.
  const messages = [...history];
  while (messages.length && messages[0].role !== "user") messages.shift();

  const scope = focusClient ? `client:${focusClient.id}` : "book";
  try {
    const r = await window.claude.stream({
      messages, scope,
      onText: handlers.onText,
      onTool: handlers.onTool,
    });
    return r.content || "I couldn't generate a response — please try again.";
  } catch (e) {
    const clients = window._bookClients || [];
    if (focusClient) {
      return `For ${focusClient.name}: lead with ${focusClient.action.toLowerCase()}. It has been ${focusClient.lastContact} days since last contact — a quick check-in plus the ${focusClient.opp.label.toLowerCase()} idea is the highest-value move. Want me to draft the outreach?`;
    }
    const top = [...clients].sort((a, b) => b.priority - a.priority).slice(0, 3);
    const urgent = top.map(c => `${c.name} (${c.lastContact}d, ${c.action})`).join(", ");
    return `Your top priorities today: ${urgent || "review your flagged clients"}. Want a call list with talking points?`;
  }
}

Object.assign(window, { fmtAum, askCopilot });
