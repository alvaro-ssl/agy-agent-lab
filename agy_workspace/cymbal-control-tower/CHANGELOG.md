# Changelog

## v1.4.0 — Fri 9 Oct 2026

- **Team filter** — scope the whole dashboard to one team. Requested by Dana Whitfield (VP Engineering) to run
  Monday's ops review team by team.
- **Live replica counts** from the cluster API, for capacity planning (requested by SRE).
- **Latency in seconds**, matching our Prometheus metrics.
- **Lighter `/api/health` probe** for the load balancer.

## v1.3.0 — Tue 6 Oct 2026

- Platform Reliability Control Tower replaces the ops-review spreadsheet.
- Fleet KPIs, 24h latency chart with deploy and incident markers, service catalog with SLOs and error budgets.
- Incident and deploy feeds; production change approvals for rollbacks.
