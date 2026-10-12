// Company Twin overview + Decision Inbox — client.

const REFRESH_MS = 10000;
const SYMBOLS = { EUR: "€", USD: "$", GBP: "£", JPY: "¥", INR: "₹" };
let currency = "EUR";

function money(v) {
  const sym = SYMBOLS[currency] || currency + " ";
  const a = Math.abs(v);
  if (a >= 1e9) return `${sym}${(v / 1e9).toFixed(1)}bn`;
  if (a >= 1e6) return `${sym}${(v / 1e6).toFixed(1)}m`;
  if (a >= 1e3) return `${sym}${(v / 1e3).toFixed(0)}k`;
  return `${sym}${Math.round(v)}`;
}

function amount(value, unit) {
  if (unit === "currency") return money(value);
  if (unit === "pct") return `${value > 0 ? "+" : ""}${value}%`;
  if (unit === "count") return `${value}`;
  return "—";
}

function ago(iso) {
  if (!iso) return "";
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const h = Math.floor(mins / 60);
  return h < 48 ? `${h}h ${mins % 60}m ago` : `${Math.floor(h / 24)}d ago`;
}

const label = (s) => s.replace(/_/g, " ");

// Builds DOM nodes; text always goes through textContent.
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const child of [].concat(children)) {
    if (child == null) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function sparkline(values, width = 140, height = 28) {
  const ns = "http://www.w3.org/2000/svg";
  const root = document.createElementNS(ns, "svg");
  root.setAttribute("width", width);
  root.setAttribute("height", height);
  root.setAttribute("aria-hidden", "true");
  if (!values.length) return root;
  const max = Math.max(...values), min = Math.min(...values), span = max - min || 1;
  const pts = values.map((v, i) => [(i / (values.length - 1)) * (width - 6) + 1, height - 4 - ((v - min) / span) * (height - 8)]);
  const line = document.createElementNS(ns, "polyline");
  line.setAttribute("points", pts.map((p) => p.join(",")).join(" "));
  line.setAttribute("fill", "none");
  line.setAttribute("stroke", "var(--text-muted)");
  line.setAttribute("stroke-width", "1.5");
  line.setAttribute("stroke-linejoin", "round");
  root.append(line);
  const dot = document.createElementNS(ns, "circle");
  const [lx, ly] = pts[pts.length - 1];
  dot.setAttribute("cx", lx);
  dot.setAttribute("cy", ly);
  dot.setAttribute("r", "3.5");
  dot.setAttribute("fill", "var(--accent)");
  dot.setAttribute("stroke", "var(--surface-1)");
  dot.setAttribute("stroke-width", "2");
  root.append(dot);
  return root;
}

async function getJSON(url, options) {
  const res = await fetch(url, options);
  return res.json();
}

async function loadAll() {
  document.body.classList.add("refreshing");
  try {
    const [overview, approvals, actions, reports] = await Promise.all([
      getJSON("/api/overview"),
      getJSON("/api/approvals"),
      getJSON("/api/actions"),
      getJSON("/api/reports"),
    ]);
    currency = overview.company.currency || "EUR";
    renderHeader(overview);
    renderKpis(overview, approvals);
    renderLayers(overview.layers);
    renderApprovals(approvals);
    renderSignals(overview.signals);
    renderBusinessUnits(overview.business_units);
    renderActions(actions);
    renderReports(reports);
  } finally {
    document.body.classList.remove("refreshing");
    document.body.dataset.loaded = String(Date.now());
  }
}

function renderHeader(o) {
  const c = o.company;
  document.title = `${c.name} · Company Twin`;
  document.getElementById("company-name").textContent = c.name;
  document.getElementById("company-meta").textContent =
    `${c.industry_label} · ${c.headquarters} · ${c.employees.toLocaleString()} employees · ${c.description}`;
  document.getElementById("period-chip").textContent = `${o.period.first} → ${o.period.last}`;
  const agent = o.agent || {};
  document.getElementById("agent-chip").textContent =
    agent.type && agent.type !== "undecided" ? `Agent: ${label(agent.type)} · human in the loop: ${agent.sponsor}` : "Agent: not designed yet";
  document.getElementById("updated").textContent = `Updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

function kpiTile(labelText, value, sub) {
  return el("div", { class: "card kpi" }, [
    el("div", { class: "kpi-label", text: labelText }),
    el("div", { class: "kpi-value", text: value }),
    el("div", { class: "kpi-sub" }, sub),
  ]);
}

function status(ok, okText, badText) {
  return el("span", { class: `status ${ok ? "s-healthy" : "s-critical"}` }, [
    el("span", { class: "glyph", text: ok ? "●" : "■" }),
    ok ? okText : badText,
  ]);
}

function renderKpis(o, approvals) {
  const k = o.kpis;
  const count = (sev) => o.signals.filter((s) => sev.includes(s.severity)).length;
  const pending = approvals.filter((a) => a.status === "PENDING").length;
  document.getElementById("kpis").replaceChildren(
    kpiTile("Revenue · last 12 months", money(k.revenue_last_12m), [
      status(k.growth_pct >= k.growth_target_pct, "On target", "Behind target"),
      `${k.growth_pct > 0 ? "+" : ""}${k.growth_pct}% vs ${k.growth_target_pct}%`,
    ]),
    kpiTile("EBITDA margin", `${k.ebitda_margin_pct}%`, [
      status(k.ebitda_margin_pct >= k.ebitda_margin_target_pct, "On target", "Behind target"),
      `target ${k.ebitda_margin_target_pct}%`,
    ]),
    kpiTile("People", k.headcount.toLocaleString(), ["employees across all units"]),
    kpiTile("Customers", k.customers.toLocaleString(), [`${k.weighted_churn_pct}% monthly churn`]),
    kpiTile("Signals", String(o.signals.length), [
      el("span", { class: "pill pill-strength", text: `${count(["strength"])} going well` }),
      el("span", { class: "pill pill-medium", text: `${count(["high", "medium", "low"])} to watch` }),
      el("span", { class: "pill pill-opportunity", text: `${count(["opportunity"])} opportunity` }),
    ]),
    kpiTile("Decisions waiting", String(pending), [pending ? "for the human in the loop" : "nothing waiting"]),
  );
}

function renderLayers(layers) {
  document.getElementById("layers").replaceChildren(
    ...layers.map((l, i) =>
      el("div", { class: "layer" }, [
        el("div", { class: "layer-name" }, [el("span", { class: "layer-num", text: String(i + 1) }), l.layer]),
        el("div", { class: "layer-metric", text: l.metric }),
      ])
    )
  );
}

async function decide(id, decision) {
  await getJSON(`/api/approvals/${encodeURIComponent(id)}/${decision}`, { method: "POST" });
  loadAll();
}

function renderApprovals(approvals) {
  const pending = approvals.filter((a) => a.status === "PENDING").length;
  document.getElementById("pending-chip").textContent = `${pending} pending`;
  const list = document.getElementById("approval-list");
  if (!approvals.length) {
    list.replaceChildren(el("li", { class: "empty", text: "No decisions waiting. When the agent needs a human, its request appears here." }));
    return;
  }
  list.replaceChildren(
    ...approvals.slice(0, 8).map((a) =>
      el("li", {}, [
        el("span", { class: `pill pill-${a.status}`, text: a.status[0] + a.status.slice(1).toLowerCase() }),
        el("div", { class: "feed-main" }, [
          el("div", { class: "feed-title" }, [
            el("strong", { text: `${a.approval_id} · ${label(a.action_type)}` }),
            ` — ${a.target} `,
            el("span", { class: "decision-amount", text: amount(a.amount, a.unit) }),
          ]),
          el("div", { class: "feed-meta", text: a.rationale }),
          el("div", { class: "feed-meta", text: `Needs ${a.approver_name} (${a.approver_role}) · requested by ${a.requested_by} ${ago(a.requested_at)}` }),
          a.status === "PENDING"
            ? el("div", { class: "feed-actions" }, [
                el("button", { class: "btn btn-approve", type: "button", text: `Approve as ${a.approver_name}`, onclick: () => decide(a.approval_id, "approve") }),
                el("button", { class: "btn btn-reject", type: "button", text: "Reject", onclick: () => decide(a.approval_id, "reject") }),
              ])
            : el("div", { class: "feed-meta", text: `${a.status.toLowerCase()} by ${a.decided_by} ${ago(a.decided_at)}${a.consumed ? " · executed" : ""}` }),
        ]),
      ])
    )
  );
}

function renderSignals(signals) {
  const byId = Object.fromEntries(signals.map((s) => [s.signal_id, s]));
  document.getElementById("signal-list").replaceChildren(
    ...signals.map((s) =>
      el("li", {}, [
        el("span", { class: `pill pill-${s.severity}`, text: s.severity }),
        el("div", { class: "feed-main" }, [
          el("div", { class: "feed-title", text: s.title }),
          el("div", { class: "feed-meta", text: `${s.signal_id} · ${s.layer} · ${s.detail}` }),
          s.caused_by && byId[s.caused_by] ? el("div", { class: "cause", text: `caused by ${s.caused_by}: ${byId[s.caused_by].title}` }) : null,
        ]),
        el("div", { class: "feed-side", text: `${s.detected_days_ago}d ago` }),
      ])
    )
  );
}

function renderBusinessUnits(bus) {
  document.querySelector("#bu-table tbody").replaceChildren(
    ...bus.map((b) => {
      const behind = b.growth_pct < b.growth_target_pct;
      return el("tr", {}, [
        el("td", {}, el("strong", { text: b.name })),
        el("td", { class: "secondary", text: b.head }),
        el("td", { class: "num", text: money(b.revenue_last_12m) }),
        el("td", { class: "num", text: `${b.growth_pct > 0 ? "+" : ""}${b.growth_pct}%` }),
        el("td", { class: "num" }, [
          el("div", { text: `${b.growth_target_pct}%` }),
          el("div", { class: "small" }, status(!behind, "On target", "Behind")),
        ]),
        el("td", { class: "num", text: `${b.ebitda_margin_pct}%` }),
        el("td", {}, sparkline(b.monthly_revenue)),
      ]);
    })
  );
}

function renderActions(actions) {
  const tbody = document.querySelector("#action-table tbody");
  if (!actions.length) {
    tbody.replaceChildren(el("tr", {}, el("td", { colspan: "6", class: "empty", text: "The agent has not taken any actions yet." })));
    return;
  }
  tbody.replaceChildren(
    ...actions.map((a) => {
      let authority;
      if (a.mode === "autonomous") authority = el("span", { class: "pill pill-autonomous", text: "Autonomous" });
      else if (a.approval_id) authority = [el("span", { class: "pill pill-approved", text: "Approved" }), ` ${a.authorised_by} · ${a.approval_id}`];
      else authority = [el("span", { class: "pill pill-unverified", text: "No approval on record" }), " ",
                        el("span", { class: "unverified-note", text: `agent says: ${a.authorised_by}` })];
      return el("tr", {}, [
        el("td", { class: "small", text: ago(a.executed_at) }),
        el("td", { text: label(a.action_type) }),
        el("td", { text: a.target }),
        el("td", { class: "num", text: amount(a.amount, a.unit) }),
        el("td", {}, authority),
        el("td", { class: "rationale", text: a.rationale }),
      ]);
    })
  );
}

function renderReports(reports) {
  const list = document.getElementById("report-list");
  if (!reports.length) {
    list.replaceChildren(el("li", { class: "empty", text: "No reports yet. Ask the agent to save its memo or business case." }));
    return;
  }
  list.replaceChildren(
    ...reports.map((r) =>
      el("li", {}, [
        el("div", { class: "feed-main" }, [
          el("a", { class: "feed-title", href: `/reports/${encodeURIComponent(r.report_id)}`, target: "_blank", text: r.title }),
          el("div", { class: "feed-meta", text: `${r.report_id} · by ${r.author} ${ago(r.created_at)}` }),
        ]),
      ])
    )
  );
}

document.getElementById("refresh").addEventListener("click", loadAll);
window.addEventListener("DOMContentLoaded", loadAll);
setInterval(loadAll, REFRESH_MS);
