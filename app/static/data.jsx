/* data.jsx — palette, helpers, and real-data persona builder for GenAdvisorIQ */

const PALETTE = ["var(--accent)", "#2fa46a", "#3a7d8c", "#9a8cff", "#d9a23a", "#c98b7a"];

/* totals helpers */
function personaTotals(p) {
  const assets = (p.assets || []).reduce((s, a) => s + a.value, 0);
  const liab   = (p.liabilities || []).reduce((s, l) => s + l.value, 0);
  return { assets, liab, net: assets - liab };
}

/* ---- Map asset type from DB string to UI category ---- */
function _assetCategory(type) {
  const t = (type || "").toLowerCase();
  if (/savings|cash|liquid|fd|bank|checking|current/.test(t)) return "cash";
  if (/mutual|equity|stock|brokerage|invest|sip/.test(t)) return "invest";
  if (/retirement|pension|pf|epf|nps|401|ira/.test(t)) return "retirement";
  if (/property|real estate|land|house|flat|plot/.test(t)) return "property";
  return "other";
}

const _GOAL_ICONS = {
  retirement: "coins", house: "layers", home: "layers", car: "layers",
  education: "target", emergency: "shield", travel: "flag", health: "heart",
  wedding: "sparkle", default: "target",
};

function _goalIcon(goalType) {
  const t = (goalType || "").toLowerCase();
  for (const [k, v] of Object.entries(_GOAL_ICONS)) {
    if (t.includes(k)) return v;
  }
  return _GOAL_ICONS.default;
}

function _goalEta(goalYear) {
  if (!goalYear) return "–";
  return "Dec " + goalYear;
}

/* ---- Health score factors from raw hs_factors array ---- */
function _extractHsFactors(bookClient) {
  if (bookClient && bookClient.hs_factors && bookClient.hs_factors.length) {
    return bookClient.hs_factors;
  }
  return [];
}

/* ---- Build 4 risk indicators from the context data ---- */
function _buildRisk(customer, financialSummary, assets) {
  const income     = financialSummary.monthly_income || 0;
  const expenses   = financialSummary.monthly_expenses || 0;
  const totalLiab  = financialSummary.total_liabilities || 0;
  const totalAssets = financialSummary.total_assets || 0;

  const savingsRate  = income > 0 ? Math.round((income - expenses) / income * 100) : 0;
  const dti          = income > 0 ? Math.round(totalLiab / (income * 12) * 100) : 0;

  // Liquid months
  const _LIQUID_RE = /savings|cash|liquid|fd|bank/i;
  const liquid = (assets || []).filter(a => _LIQUID_RE.test(a.type) || _LIQUID_RE.test(a.header || ""))
                               .reduce((s, a) => s + a.value, 0);
  const liquidMonths = expenses > 0 ? +(liquid / expenses).toFixed(1) : 0;

  return [
    { label: "Emergency runway", value: liquidMonths + " mo", level: Math.min(5, Math.round(liquidMonths / 6 * 5)), max: 5, note: "Target 6 months",   tone: liquidMonths >= 6 ? "var(--pos)" : "var(--warn)" },
    { label: "Debt-to-income",   value: dti + "%",            level: dti < 36 ? 4 : dti < 50 ? 2 : 1,              max: 5, note: dti < 36 ? "Healthy, under 36%" : "Consider reducing debt", tone: dti < 36 ? "var(--pos)" : "var(--warn)" },
    { label: "Savings rate",     value: savingsRate + "%",    level: Math.min(5, Math.round(savingsRate / 20)),      max: 5, note: savingsRate >= 20 ? "Excellent" : "Target 20%+",           tone: savingsRate >= 20 ? "var(--pos)" : "var(--warn)" },
    { label: "Asset coverage",   value: totalLiab > 0 ? (+(totalAssets / totalLiab).toFixed(1)) + "x" : "No debt", level: totalLiab > 0 ? Math.min(5, Math.round(totalAssets / totalLiab)) : 5, max: 5, note: "Assets vs total liabilities", tone: totalAssets > totalLiab ? "var(--pos)" : "var(--warn)" },
  ];
}

/* ---- Build allocation from asset list ---- */
function _buildAllocation(assets) {
  const groups = {};
  for (const a of assets) {
    const cat = _assetCategory(a.type);
    const label = { cash: "Cash & savings", invest: "Investments", retirement: "Retirement", property: "Property", other: "Other" }[cat];
    if (!groups[label]) groups[label] = { label, value: 0, color: PALETTE[Object.keys(groups).length % PALETTE.length] };
    groups[label].value += a.value;
  }
  return Object.values(groups);
}

/**
 * buildPersonaFromContext(ctx)
 *
 * ctx is the `data` field from GET /api/v1/admin/customers/{id}
 * Returns a persona object compatible with cards.jsx and companion.jsx.
 */
function buildPersonaFromContext(ctx) {
  const customer   = ctx.customer   || {};
  const fin        = ctx.financial_summary || {};
  const rawAssets  = ctx.assets     || [];
  const rawLiab    = ctx.liabilities || [];
  const rawGoals   = ctx.goals      || [];
  const rawInsurance = ctx.insurance || [];
  const rawCallLogs  = ctx.recent_call_logs || [];

  const name     = `${customer.first_name || ""} ${customer.last_name || ""}`.trim();
  const initials = ((customer.first_name || " ")[0] + (customer.last_name || " ")[0]).toUpperCase();

  // Assets
  const assets = rawAssets.map(a => ({
    name:  a.header || a.type,
    inst:  a.firm   || "",
    value: a.amount || 0,
    type:  _assetCategory(a.type),
  }));

  // Liabilities
  const liabilities = rawLiab.map(l => ({
    name:  l.header || l.type,
    inst:  l.firm   || "",
    value: l.outstanding_balance || 0,
    apr:   l.interest_rate || 0,
  }));

  // Goals
  const goals = rawGoals.map((g, i) => ({
    name:    g.name,
    icon:    _goalIcon(g.goal_type),
    target:  g.goal_amount   || 0,
    current: g.current_amount || 0,
    monthly: 0,   // not stored
    eta:     _goalEta(g.goal_year),
    color:   PALETTE[i % PALETTE.length],
  }));

  // Allocation
  const allocation = _buildAllocation(assets);

  // Health score — prefer pre-computed from book client if we have it
  const healthScore = fin.health_score || 0;

  // hs_factors — read from ctx if present (the advisor book endpoint injects it)
  const hsFactors = (ctx.hs_factors && ctx.hs_factors.length)
    ? ctx.hs_factors
    : [];

  // Risk
  const risk = _buildRisk(customer, fin, rawAssets);

  // Last sentiment from most recent call log
  const lastLog = rawCallLogs[0];
  const lastSentimentRaw = lastLog ? (lastLog.customer_sentiment || "").trim().toLowerCase() : "";
  const sentimentMap = { "very positive": "champion", "positive": "warm", "neutral": "warm", "negative": "cooling", "very negative": "cooling" };
  const sentiment = sentimentMap[lastSentimentRaw] || "warm";

  const income   = fin.monthly_income   || customer.earning   || 0;
  const expenses = fin.monthly_expenses || customer.expenses  || 0;
  const netWorth = fin.net_worth != null ? fin.net_worth : (fin.total_assets || 0) - (fin.total_liabilities || 0);

  return {
    name,
    initials,
    occupation: customer.occupation || "",
    netWorth,
    netWorthDelta: 0,
    healthScore,
    scoreDelta: 0,
    monthlyIncome:    income,
    monthlyExpenses:  expenses,
    get savingsRate() {
      return this.monthlyIncome > 0
        ? Math.round((this.monthlyIncome - this.monthlyExpenses) / this.monthlyIncome * 100)
        : 0;
    },
    // No historical series available
    netWorthSeries: null,
    cashflow:       null,
    assets,
    liabilities,
    allocation,
    goals,
    recommendations: [],
    insights: [],
    actions: [],
    risk,
    hsFactors,
    summary: customer.summary || null,
    debtRatio: fin.total_assets > 0
      ? Math.round(fin.total_liabilities / fin.total_assets * 100)
      : 0,
    _raw: ctx,
  };
}

/* ---- Claude: advisor chat grounded in persona ---- */
async function askAdvisor(history, p) {
  const t = personaTotals(p);
  const ctx = `You are GenAdvisor, the warm, sharp AI financial companion inside GenAdvisorIQ. You advise ${p.name}, a ${p.occupation}.
Snapshot: net worth ${fmtK(t.net)}, health score ${p.healthScore}/100, income ${fmt$(p.monthlyIncome)}/mo, expenses ${fmt$(p.monthlyExpenses)}/mo, savings rate ${p.savingsRate}%.
Assets: ${p.assets.map(a => a.name + " " + fmtK(a.value)).join(", ")}.
Debts: ${p.liabilities.map(l => l.name + " " + fmtK(l.value) + (l.apr ? " @" + l.apr + "%" : "")).join(", ")}.
Goals: ${p.goals.map(g => g.name + " (" + Math.round(g.current / g.target * 100) + "%)").join(", ")}.
Rules: be concise (2-4 sentences max unless asked to elaborate), specific to THEIR numbers, encouraging but honest. Use plain language, no jargon dumps. Never invent products. You may reference exact dollar figures above.`;
  try {
    const msgs = [
      { role: "user", content: ctx + "\n\nConversation so far is below; respond to the latest user turn." },
      ...history
    ];
    return await window.claude.complete({ messages: msgs });
  } catch (e) {
    return "I'm having trouble reaching my models right now — but based on your snapshot, the highest-leverage move is addressing your biggest financial gap. Want me to sketch a 90-day plan?";
  }
}

/* ---- Markdown renderer — converts Claude/DB markdown to formatted HTML ---- */
function Markdown({ content, className, style }) {
  if (!content) return null;
  const html = (typeof marked !== "undefined")
    ? marked.parse(content, { breaks: true, gfm: true })
    : content.replace(/\n/g, "<br>");
  return (
    <div
      className={"md-body" + (className ? " " + className : "")}
      style={style}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

Object.assign(window, { PALETTE, personaTotals, askAdvisor, buildPersonaFromContext, Markdown });
