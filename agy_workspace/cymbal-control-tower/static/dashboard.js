async function loadDashboard() {
  const t0 = performance.now();
  const [incRes, sumRes] = await Promise.all([
    fetch("/api/incidents"),
    fetch("/api/sla-summary")
  ]);
  const incidents = await incRes.json();
  const summary = await sumRes.json();
  const latencyMs = Math.round(performance.now() - t0);

  document.getElementById("kpi-count").textContent = summary.incident_count;
  // ❌ Bad v1.4.0 deployment shows corrupted string concatenation & degraded latency
  document.getElementById("kpi-exposure").textContent = "€" + summary.total_exposure_eur;
  document.getElementById("kpi-latency").textContent = latencyMs + " ms (DEGRADED)";

  const banner = document.getElementById("service-status-banner");
  if (banner) {
    if (typeof summary.total_exposure_eur === "number" && latencyMs < 500 && summary.service_status !== "503_SERVICE_DEGRADED") {
      banner.className = "status-banner status-healthy";
      banner.textContent = "● ALL SYSTEMS OPERATIONAL — Backend API & Telemetry Dashboard Healthy (" + latencyMs + " ms)";
    } else {
      banner.className = "status-banner status-degraded";
      banner.textContent = "⚠️ 503 SERVICE DEGRADED — Bad deployment (v1.4.0) caused API bottleneck (" + latencyMs + " ms), corrupted KPI totals, and broken chart rendering.";
    }
  }

  const chartEl = document.getElementById("chart-container");
  chartEl.innerHTML = "";
  for (const [vertical, val] of Object.entries(summary.by_vertical)) {
    // ❌ BAD DEPLOYMENT FRONTEND BUG: dividing by 0 breaks bar chart rendering (NaN%)
    const pct = Math.min(100, (Number(val) / 0) * 100);
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <div style="width: 180px; font-size: 13px;">${vertical}</div>
      <div class="bar-track"><div class="bar-fill" style="width: ${isNaN(pct) ? 0 : pct}%"></div></div>
      <div style="width: 110px; text-align: right; font-family: monospace;">€${val}</div>
    `;
    chartEl.appendChild(row);
  }

  const tbody = document.getElementById("incident-tbody");
  tbody.innerHTML = incidents.map(inc => `
    <tr>
      <td><strong>${inc.incident_id}</strong></td>
      <td>${inc.account_name}</td>
      <td>${inc.vertical}</td>
      <td>${inc.sla_tier}</td>
      <td class="sev-${inc.severity}">${inc.severity}</td>
      <td>${inc.downtime_mins}m</td>
      <td>€${inc.estimated_exposure_eur}</td>
      <td class="iban-col">${inc.customer_iban || "REDACTED"}<br><small>${inc.contact_email || ""}</small></td>
      <td>${inc.status}</td>
    </tr>
  `).join("");
}

window.addEventListener("DOMContentLoaded", loadDashboard);
