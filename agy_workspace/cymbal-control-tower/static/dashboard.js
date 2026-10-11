// Cymbal Platform Reliability Control Tower — dashboard client.

const REFRESH_MS = 30000;
const SLOW_API_MS = 1000;
const STATUS_LABELS = {
  healthy: ["●", "Healthy"],
  at_risk: ["▲", "At risk"],
  degraded: ["◆", "Degraded"],
  critical: ["■", "Critical"],
};

const state = { overview: null, selected: null, deploys: [], team: "" };

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function compact(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "k";
  return String(Math.round(n));
}

function ms(v) {
  return v >= 1000 ? (v / 1000).toFixed(2) + " s" : Math.round(v) + " ms";
}

function clock(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function ago(iso) {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const h = Math.floor(mins / 60);
  if (h < 48) return `${h}h ${mins % 60}m ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function duration(mins) {
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

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

const SVG_NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

function statusBadge(status) {
  const [glyph, label] = STATUS_LABELS[status] || ["○", status];
  return el("span", { class: `status s-${status}` }, [el("span", { class: "glyph", text: glyph }), label]);
}

function sparkline(values, { width = 120, height = 30, accent = "var(--accent)" } = {}) {
  const root = svg("svg", { width, height, viewBox: `0 0 ${width} ${height}`, "aria-hidden": "true" });
  if (!values.length) return root;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => [
    (i / Math.max(1, values.length - 1)) * (width - 6) + 1,
    height - 4 - ((v - min) / span) * (height - 8),
  ]);
  root.append(
    svg("polyline", {
      points: pts.map((p) => p.join(",")).join(" "),
      fill: "none",
      stroke: "var(--text-muted)",
      "stroke-width": 1.5,
      "stroke-linejoin": "round",
      "stroke-linecap": "round",
    })
  );
  const [lx, ly] = pts[pts.length - 1];
  root.append(svg("circle", { cx: lx, cy: ly, r: 3.5, fill: accent, stroke: "var(--surface-1)", "stroke-width": 2 }));
  return root;
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

async function getJSON(url, options) {
  const res = await fetch(url, options);
  const body = await res.json();
  return { ok: res.ok, status: res.status, body };
}

async function loadAll() {
  document.body.classList.add("refreshing");
  try {
    const t0 = performance.now();
    const overviewUrl = state.team ? `/api/overview?team=${encodeURIComponent(state.team)}` : "/api/overview";
    const overviewReq = getJSON(overviewUrl).then((r) => ({ ...r, ms: performance.now() - t0 }));
    const [overview, health, incidents, deploys, approvals] = await Promise.all([
      overviewReq,
      getJSON("/api/health"),
      getJSON("/api/incidents"),
      getJSON("/api/deploys?limit=50"),
      getJSON("/api/approvals"),
    ]);
    state.overview = overview.body;
    state.deploys = deploys.body;
    renderBanner(health, overview.ms);
    renderHeader(overview.body);
    renderTeamSelect(overview.body.teams);
    renderKpis(computeKpis(overview.body, incidents.body, deploys.body));
    renderServiceSelect(overview.body.services);
    renderServices(overview.body.services);
    renderIncidents(incidents.body);
    renderDeploys(deploys.body.slice(0, 8));
    renderApprovals(approvals.body);
    await loadChart(state.selected);
  } catch (err) {
    renderBanner({ ok: false, body: { status: "UNREACHABLE" } }, null, err);
  } finally {
    document.body.classList.remove("refreshing");
    document.body.dataset.loaded = String(Date.now());
  }
}

// ---------------------------------------------------------------------------
// Header, banner, KPIs
// ---------------------------------------------------------------------------

function renderHeader(overview) {
  document.getElementById("ct-version").textContent = `Control Tower v${overview.version}`;
  document.getElementById("updated").textContent = `Updated ${clock(new Date().toISOString())}`;
}

function renderBanner(health, apiMs, error) {
  const banner = document.getElementById("status-banner");
  const text = document.getElementById("banner-text");
  const icon = banner.querySelector(".banner-icon");
  const status = health.body && health.body.status;
  const slow = apiMs != null && apiMs > SLOW_API_MS;
  if (error || status !== "OPERATIONAL" || slow) {
    banner.className = "banner banner-bad";
    icon.textContent = "▲";
    if (error) text.textContent = "Control Tower unreachable — the API did not respond.";
    else if (slow) text.textContent = `Control Tower degraded — overview API took ${ms(apiMs)} (budget 300 ms). Numbers below may be stale or wrong.`;
    else text.textContent = `Control Tower degraded — health check reports ${status}.`;
    return;
  }
  banner.className = "banner banner-ok";
  icon.textContent = "●";
  const checks = health.body.checks || {};
  text.textContent = `Control Tower operational — overview API ${ms(apiMs)} · telemetry from ${checks.telemetry_services} services`;
}

// KPIs are computed in the browser so they follow the team filter.
function computeKpis(overview, incidents, deploys) {
  const services = overview.services;
  const names = new Set(services.map((s) => s.service));
  const open = incidents.filter((i) => i.status !== "Resolved" && names.has(i.service));
  const deploys24h = deploys.filter((d) => d.minutes_ago <= 24 * 60 && names.has(d.service));
  const failed = deploys24h.filter((d) => d.result === "rolled_back" || d.result === "failed");
  const rpm = services.reduce((sum, s) => sum + s.requests_per_min, 0);
  const errorsPerMin = services.reduce((sum, s) => sum + (s.requests_per_min * s.error_rate_pct) / 100, 0);
  return {
    availability_30d_pct: services.reduce((sum, s) => sum + s.availability_30d_pct, 0) / services.length,
    fleet_slo_pct: overview.fleet_slo_pct,
    requests_per_min: rpm,
    requests_per_min_24h: overview.requests_per_min_24h,
    error_rate_pct: (100 * errorsPerMin) / rpm,
    error_rate_24h: overview.error_rate_24h,
    services_within_latency_slo: services.filter((s) => s.p95_ms <= s.p95_target_ms).length,
    services_total: services.length,
    open_incidents: open.length,
    open_incidents_by_severity: Object.fromEntries(
      ["SEV1", "SEV2", "SEV3"].map((sev) => [sev, open.filter((i) => i.severity === sev).length])
    ),
    deploys_24h: deploys24h.length,
    change_failure_rate_pct: deploys24h.length ? Math.round((1000 * failed.length) / deploys24h.length) / 10 : 0,
  };
}

function kpiTile({ label, value, sub, spark }) {
  return el("div", { class: "card kpi" }, [
    el("div", { class: "kpi-label", text: label }),
    el("div", { class: "kpi-value", text: value, title: value }),
    el("div", { class: "kpi-sub" }, sub),
    spark ? el("div", { class: "kpi-spark" }, spark) : null,
  ]);
}

function renderKpis(k) {
  const within = k.availability_30d_pct >= k.fleet_slo_pct;
  const sev = k.open_incidents_by_severity;
  const tiles = [
    {
      label: "Availability · 30 days",
      value: `${k.availability_30d_pct.toFixed(2)}%`,
      sub: [statusBadge(within ? "healthy" : "critical"), `SLO ${k.fleet_slo_pct.toFixed(2)}% · ${within ? "within" : "below"} target`],
    },
    {
      label: "Requests per minute",
      value: k.requests_per_min.toLocaleString(),
      sub: ["Fleet-wide, last 24h"],
      spark: sparkline(k.requests_per_min_24h),
    },
    {
      label: "Error rate",
      value: `${k.error_rate_pct.toFixed(2)}%`,
      sub: ["Failed requests, last 24h"],
      spark: sparkline(k.error_rate_24h),
    },
    {
      label: "Latency SLO",
      value: `${k.services_within_latency_slo} / ${k.services_total}`,
      sub: ["services within p95 target"],
    },
    {
      label: "Open incidents",
      value: String(k.open_incidents),
      sub: Object.entries(sev)
        .filter(([, n]) => n > 0)
        .map(([s, n]) => el("span", { class: `pill pill-${s}`, text: `${n} ${s}` })),
    },
    {
      label: "Deploys · 24h",
      value: String(k.deploys_24h),
      sub: [`Change failure rate ${k.change_failure_rate_pct}%`],
    },
  ];
  document.getElementById("kpis").replaceChildren(...tiles.map(kpiTile));
}

// ---------------------------------------------------------------------------
// Service catalog
// ---------------------------------------------------------------------------

function renderTeamSelect(teams) {
  const select = document.getElementById("team-select");
  if (select.options.length > 1) return;
  for (const t of teams) select.append(el("option", { value: t.slug, text: t.name }));
}

function renderServiceSelect(services) {
  const select = document.getElementById("service-select");
  if (!state.selected || !services.some((s) => s.service === state.selected)) {
    const worst = services.find((s) => s.status === "critical") || services.find((s) => s.status === "degraded");
    state.selected = (worst || services[0] || {}).service || null;
  }
  select.replaceChildren(
    ...services.map((s) => el("option", { value: s.service, text: s.service }))
  );
  select.value = state.selected || "";
}

function budgetMeter(pct) {
  const level = pct < 0 ? "m-critical" : pct < 25 ? "m-warning" : "";
  const width = pct < 0 ? 100 : Math.max(2, Math.min(100, pct));
  return el("div", { class: `meter ${level}` }, [
    el("div", { class: "meter-track" }, el("div", { class: "meter-fill", style: `width:${width}%` })),
    el("span", { class: "meter-label", text: pct < 0 ? `${Math.round(pct)}% · out` : `${Math.round(pct)}%` }),
  ]);
}

const STATUS_ORDER = { critical: 0, degraded: 1, at_risk: 2, healthy: 3 };

function renderServices(services) {
  const tbody = document.querySelector("#service-table tbody");
  if (!services.length) {
    tbody.replaceChildren(el("tr", {}, el("td", { colspan: "11", class: "empty", text: "No services match this filter." })));
    return;
  }
  const sorted = [...services].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || a.tier - b.tier);
  tbody.replaceChildren(
    ...sorted.map((s) => {
      const over = s.p95_ms > s.p95_target_ms;
      const row = el(
        "tr",
        {
          tabindex: "0",
          class: s.service === state.selected ? "selected" : "",
          "aria-label": `${s.service}, ${s.status}`,
          onclick: () => selectService(s.service),
          onkeydown: (e) => (e.key === "Enter" || e.key === " ") && selectService(s.service),
        },
        [
          el("td", {}, statusBadge(s.status)),
          el("td", {}, [el("span", { class: "svc-name", text: s.service }), el("span", { class: "tier", text: `T${s.tier}` })]),
          el("td", {}, [el("div", { class: "secondary", text: s.team }), el("div", { class: "small", text: s.on_call })]),
          el("td", { class: "num" }, [
            el("div", { text: `${s.availability_30d_pct.toFixed(2)}%` }),
            el("div", { class: "small", text: `SLO ${s.slo_availability_pct}%` }),
          ]),
          el("td", {}, budgetMeter(s.error_budget_remaining_pct)),
          el("td", { class: "num" }, [
            el("div", { class: over ? "over" : "", text: ms(s.p95_ms) }),
            el("div", { class: "small", text: `target ${ms(s.p95_target_ms)}` }),
          ]),
          el("td", {}, sparkline(s.p95_24h, { width: 96, height: 26, accent: over ? "var(--serious)" : "var(--accent)" })),
          el("td", { class: "num", text: `${s.error_rate_pct.toFixed(2)}%` }),
          el("td", { class: "num", text: compact(s.requests_per_min) }),
          el("td", { class: "num", text: String(s.replicas) }),
          el("td", {}, s.last_deploy
            ? [el("div", { class: "mono", text: s.last_deploy.version }), el("div", { class: "small", text: ago(s.last_deploy.at) })]
            : "—"),
        ]
      );
      return row;
    })
  );
}

function selectService(name) {
  state.selected = name;
  document.getElementById("service-select").value = name;
  document.querySelectorAll("#service-table tbody tr").forEach((tr) => {
    tr.classList.toggle("selected", tr.getAttribute("aria-label").startsWith(name + ","));
  });
  loadChart(name);
}

// ---------------------------------------------------------------------------
// Feeds
// ---------------------------------------------------------------------------

function renderIncidents(incidents) {
  const open = incidents.filter((i) => i.status !== "Resolved").length;
  document.getElementById("incident-subtitle").textContent = `${open} open · resolved incidents from the last 48 hours`;
  const list = document.getElementById("incident-list");
  if (!incidents.length) {
    list.replaceChildren(el("li", { class: "empty", text: "No incidents in the last 48 hours." }));
    return;
  }
  list.replaceChildren(
    ...incidents.map((i) =>
      el("li", {}, [
        el("span", { class: `pill pill-${i.severity}`, text: i.severity }),
        el("div", { class: "feed-main" }, [
          el("div", { class: "feed-title", text: i.title }),
          el("div", {
            class: "feed-meta",
            text: `${i.incident_id} · ${i.service} · IC ${i.commander}`,
          }),
        ]),
        el("div", { class: "feed-side" }, [
          el("div", {}, el("span", { class: i.status === "Resolved" ? "pill pill-Resolved" : "secondary", text: i.status })),
          el("div", { text: i.status === "Resolved" ? `lasted ${duration(i.duration_min)}` : `started ${ago(i.started_at)}` }),
        ]),
      ])
    )
  );
}

const DEPLOY_RESULT = { succeeded: "Succeeded", rolled_back: "Rolled back", failed: "Failed", rollback: "Rollback" };

function renderDeploys(deploys) {
  document.getElementById("deploy-list").replaceChildren(
    ...deploys.map((d) =>
      el("li", {}, [
        el("div", { class: "feed-main" }, [
          el("div", { class: "feed-title" }, [el("strong", { text: d.service }), " ", el("span", { class: "mono", text: d.version })]),
          el("div", { class: "feed-meta", text: `${d.team} · ${d.author}` }),
        ]),
        el("div", { class: "feed-side" }, [
          el("div", {}, el("span", { class: `pill pill-${d.result}`, text: DEPLOY_RESULT[d.result] || d.result })),
          el("div", { text: ago(d.at) }),
        ]),
      ])
    )
  );
}

async function decide(id, decision) {
  await getJSON(`/api/approvals/${encodeURIComponent(id)}/${decision}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  loadAll();
}

function renderApprovals(approvals) {
  const list = document.getElementById("approval-list");
  if (!approvals.length) {
    list.replaceChildren(
      el("li", { class: "empty", text: "No change requests yet. Rollbacks requested by engineers or agents appear here for the on-call engineer to approve." })
    );
    return;
  }
  list.replaceChildren(
    ...approvals.slice(0, 6).map((a) =>
      el("li", {}, [
        el("span", { class: `pill pill-${a.status}`, text: a.status === "PENDING" ? "Pending" : a.status[0] + a.status.slice(1).toLowerCase() }),
        el("div", { class: "feed-main" }, [
          el("div", { class: "feed-title" }, [
            el("strong", { text: `${a.approval_id} · ${a.action} ${a.service}` }),
            " ",
            el("span", { class: "mono", text: `${a.from_version} → ${a.to_version}` }),
          ]),
          el("div", { class: "feed-meta", text: `${a.reason} · requested by ${a.requested_by} ${ago(a.requested_at)}` }),
          a.status === "PENDING"
            ? el("div", { class: "feed-actions" }, [
                el("button", { class: "btn btn-approve", type: "button", text: "Approve as on-call", onclick: () => decide(a.approval_id, "approve") }),
                el("button", { class: "btn btn-reject", type: "button", text: "Reject", onclick: () => decide(a.approval_id, "reject") }),
              ])
            : el("div", { class: "feed-meta", text: `${a.status.toLowerCase()} by ${a.decided_by}${a.consumed ? " · executed" : ""}` }),
        ]),
      ])
    )
  );
}

// ---------------------------------------------------------------------------
// Latency chart
// ---------------------------------------------------------------------------

async function loadChart(service) {
  if (!service) return;
  const { body } = await getJSON(`/api/services/${encodeURIComponent(service)}/timeseries`);
  document.getElementById("chart-title").textContent = `Latency · ${service}`;
  renderLatencyChart(body);
  renderChartTable(body.points);
}

// Round axis: a 1/2/2.5/5 step giving about four gridlines, and a max on a step boundary.
function niceScale(v) {
  const pow = Math.pow(10, Math.floor(Math.log10(v / 4)));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * pow >= v / 4) * pow;
  return { max: Math.ceil(v / step) * step, step };
}

function renderLatencyChart(data) {
  const host = document.getElementById("latency-chart");
  const points = data.points;
  const width = Math.max(480, host.clientWidth);
  const plotH = 300;
  const m = { top: 22, right: 92, bottom: 26, left: 56 };
  const height = m.top + plotH + m.bottom;
  const innerW = width - m.left - m.right;
  const t0 = new Date(points[0].t).getTime();
  const t1 = new Date(points[points.length - 1].t).getTime();
  const x = (iso) => m.left + ((new Date(iso).getTime() - t0) / (t1 - t0)) * innerW;
  const scale = niceScale(Math.max(data.p95_target_ms, ...points.map((p) => p.p95_ms)) * 1.12);
  const yMax = scale.max;
  const y = (v) => m.top + plotH - (v / yMax) * plotH;

  const root = svg("svg", { width, height, role: "img", "aria-label": `p50 and p95 latency for ${data.service}, last 24 hours` });

  // Incident windows
  for (const inc of data.incidents) {
    const start = Math.max(t0, new Date(inc.started_at).getTime());
    const end = inc.resolved_at ? new Date(inc.resolved_at).getTime() : t1;
    if (end < t0) continue;
    const x0 = x(new Date(start).toISOString());
    const x1 = x(new Date(end).toISOString());
    const tint = inc.severity === "SEV3" ? "rgba(250, 178, 25, 0.12)" : "rgba(208, 59, 59, 0.18)";
    root.append(svg("rect", { x: x0, y: m.top, width: Math.max(2, x1 - x0), height: plotH, fill: tint, rx: 2 }));
    const label = svg("text", { x: x0 + 4, y: m.top + 12 });
    label.textContent = `${inc.incident_id} · ${inc.severity}`;
    root.append(label);
  }

  // Gridlines and y ticks
  for (let v = 0; v <= yMax + 1e-9; v += scale.step) {
    root.append(svg("line", { x1: m.left, x2: m.left + innerW, y1: y(v), y2: y(v), stroke: v === 0 ? "var(--baseline)" : "var(--grid)", "stroke-width": 1 }));
    const t = svg("text", { x: m.left - 8, y: y(v) + 4, "text-anchor": "end" });
    t.textContent = ms(v);
    root.append(t);
  }

  // x ticks every 3 hours
  const first = new Date(t0);
  first.setMinutes(0, 0, 0);
  for (let t = first.getTime() + 3600000; t <= t1; t += 3600000) {
    const d = new Date(t);
    if (d.getHours() % 3 !== 0) continue;
    const t2 = svg("text", { x: x(d.toISOString()), y: m.top + plotH + 18, "text-anchor": "middle" });
    t2.textContent = clock(d.toISOString());
    root.append(t2);
  }

  // p95 target
  root.append(svg("line", { x1: m.left, x2: m.left + innerW, y1: y(data.p95_target_ms), y2: y(data.p95_target_ms), stroke: "var(--text-muted)", "stroke-dasharray": "4 4", "stroke-width": 1 }));
  const targetLabel = svg("text", { x: m.left + innerW + 8, y: y(data.p95_target_ms) + 4 });
  targetLabel.textContent = `target ${ms(data.p95_target_ms)}`;
  root.append(targetLabel);

  // Deploy markers
  for (const d of data.deploys) {
    const dx = x(d.at);
    if (dx < m.left) continue;
    root.append(svg("line", { x1: dx, x2: dx, y1: m.top, y2: m.top + plotH, stroke: "var(--baseline)", "stroke-width": 1 }));
    const tri = svg("path", { d: `M${dx - 4},${m.top - 9} L${dx + 4},${m.top - 9} L${dx},${m.top - 2} Z`, fill: "var(--text-secondary)" });
    const title = svg("title");
    title.textContent = `Deploy ${d.version} · ${d.result} · ${clock(d.at)}`;
    tri.append(title);
    root.append(tri);
  }

  // Series
  const line = (key) =>
    points.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ");
  root.append(svg("path", { d: line("p50_ms"), fill: "none", stroke: "var(--series-p50)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
  root.append(svg("path", { d: line("p95_ms"), fill: "none", stroke: "var(--series-p95)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));

  // End labels
  const last = points[points.length - 1];
  const ends = [
    ["p95", last.p95_ms, "var(--series-p95)"],
    ["p50", last.p50_ms, "var(--series-p50)"],
  ];
  let prevY = -Infinity;
  for (const [name, v, color] of ends) {
    const ey = Math.max(y(v), prevY + 14);
    prevY = ey;
    root.append(svg("circle", { cx: x(last.t), cy: y(v), r: 4, fill: color, stroke: "var(--surface-1)", "stroke-width": 2 }));
    const label = svg("text", { x: m.left + innerW + 8, y: ey + 4, class: "end-label" });
    label.textContent = `${name} ${ms(v)}`;
    root.append(label);
  }

  // Crosshair + tooltip
  const cross = svg("line", { y1: m.top, y2: m.top + plotH, stroke: "var(--text-muted)", "stroke-width": 1, visibility: "hidden" });
  const dot50 = svg("circle", { r: 4, fill: "var(--series-p50)", stroke: "var(--surface-1)", "stroke-width": 2, visibility: "hidden" });
  const dot95 = svg("circle", { r: 4, fill: "var(--series-p95)", stroke: "var(--surface-1)", "stroke-width": 2, visibility: "hidden" });
  root.append(cross, dot50, dot95);
  const overlay = svg("rect", { x: m.left, y: m.top, width: innerW, height: plotH, class: "chart-overlay", tabindex: 0 });
  root.append(overlay);

  const tooltip = document.getElementById("tooltip");
  let index = points.length - 1;
  const show = (i, clientX, clientY) => {
    index = Math.max(0, Math.min(points.length - 1, i));
    const p = points[index];
    const px = x(p.t);
    for (const n of [cross, dot50, dot95]) n.setAttribute("visibility", "visible");
    cross.setAttribute("x1", px);
    cross.setAttribute("x2", px);
    dot50.setAttribute("cx", px);
    dot50.setAttribute("cy", y(p.p50_ms));
    dot95.setAttribute("cx", px);
    dot95.setAttribute("cy", y(p.p95_ms));
    const row = (value, label, color) =>
      el("div", { class: "tt-row" }, [
        color ? el("span", { class: "tt-key", style: `background:${color}` }) : el("span", { class: "tt-key" }),
        el("strong", { text: value }),
        label,
      ]);
    tooltip.replaceChildren(
      el("div", { class: "tt-time", text: clock(p.t) }),
      row(ms(p.p95_ms), "p95", "var(--series-p95)"),
      row(ms(p.p50_ms), "p50", "var(--series-p50)"),
      row(`${compact(p.requests_per_min)}/min`, "requests"),
      row(`${p.error_rate_pct.toFixed(2)}%`, "errors")
    );
    tooltip.hidden = false;
    const rect = root.getBoundingClientRect();
    const cx = clientX ?? rect.left + px;
    const cy = clientY ?? rect.top + m.top + 20;
    const left = cx + 16 + 180 > window.innerWidth ? cx - 196 : cx + 16;
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${cy - 10}px`;
  };
  const hide = () => {
    tooltip.hidden = true;
    for (const n of [cross, dot50, dot95]) n.setAttribute("visibility", "hidden");
  };
  overlay.addEventListener("pointermove", (e) => {
    const rect = root.getBoundingClientRect();
    const frac = (e.clientX - rect.left - m.left) / innerW;
    show(Math.round(frac * (points.length - 1)), e.clientX, e.clientY);
  });
  overlay.addEventListener("pointerleave", hide);
  overlay.addEventListener("blur", hide);
  overlay.addEventListener("focus", () => show(index));
  overlay.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") show(index - 1);
    if (e.key === "ArrowRight") show(index + 1);
  });

  host.replaceChildren(root);
}

function renderChartTable(points) {
  const table = document.getElementById("chart-table");
  const rows = [];
  for (let i = 0; i < points.length; i += 12) {
    const hour = points.slice(i, i + 12);
    rows.push(
      el("tr", {}, [
        el("td", { text: clock(hour[0].t) }),
        el("td", { class: "num", text: ms(Math.max(...hour.map((p) => p.p95_ms))) }),
        el("td", { class: "num", text: ms(hour.reduce((a, p) => a + p.p50_ms, 0) / hour.length) }),
        el("td", { class: "num", text: compact(hour.reduce((a, p) => a + p.requests_per_min, 0) / hour.length) }),
        el("td", { class: "num", text: `${(hour.reduce((a, p) => a + p.error_rate_pct, 0) / hour.length).toFixed(2)}%` }),
      ])
    );
  }
  table.replaceChildren(
    el("thead", {}, el("tr", {}, ["Hour", "Max p95", "Mean p50", "Req/min", "Errors"].map((h) => el("th", { text: h })))),
    el("tbody", {}, rows)
  );
}

// ---------------------------------------------------------------------------

document.getElementById("refresh").addEventListener("click", loadAll);
document.getElementById("service-select").addEventListener("change", (e) => selectService(e.target.value));
document.getElementById("team-select").addEventListener("change", (e) => {
  state.team = e.target.value;
  loadAll();
});
window.addEventListener("resize", () => state.selected && loadChart(state.selected));
window.addEventListener("DOMContentLoaded", loadAll);
setInterval(loadAll, REFRESH_MS);
