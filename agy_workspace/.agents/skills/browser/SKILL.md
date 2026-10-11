---
name: browser
description: >-
  Browser verification and UI actuation for this workspace. Use when the user invokes /browser or asks to
  open, look at, click through, screenshot or visually verify a web app — the Cymbal Control Tower dashboard
  (http://localhost:3000), the Company Twin & Decision Inbox (http://localhost:8090), or the Play 2 agent
  Playground (http://localhost:8080). Starts the app if needed, drives a real browser, captures a screenshot,
  and reports exactly what the page shows.
---

# Browser verification & UI actuation (`/browser`)

Goal: show the user what a real browser renders — not what the code or API suggests it should render.

## 1. Make sure the app is running

| App | URL | Start it (from the workspace root) if nothing is listening |
| --- | --- | --- |
| Control Tower | http://localhost:3000 | `cd cymbal-control-tower && ../.venv/bin/uvicorn app:app --port 3000` (run in the background) |
| Company Twin & Decision Inbox | http://localhost:8090 | `.venv/bin/uvicorn inbox_app:app --app-dir company-twin --port 8090` (run in the background) |
| Agent Playground | http://localhost:8080 | `cd twin-agent && agents-cli playground` (run in the background) |

Check with `curl -s -o /dev/null -w '%{http_code}' <url>`. Wait until it answers before continuing.

## 2. Drive a real browser — pick the first option that is available

1. **Built-in browser agent** (Antigravity's browser subagent) or **Chrome DevTools MCP tools**
   (`navigate_page`, `click`, `fill`, `wait_for`, `take_screenshot`): open the URL, wait for the data to load
   (the Control Tower sets `document.body.dataset.loaded` when it has finished rendering), perform the
   requested clicks or filter changes, then take a screenshot.
2. **Headless Chrome fallback** — the bundled script drives real Chrome over the DevTools protocol, waits for
   rendering to finish, can select options and click, saves a full-page screenshot, and prints what the page
   shows (banner, KPI values, table rows, chart labels, `NaN`/`undefined` counts, console errors):

   ```bash
   .venv/bin/python .agents/skills/browser/scripts/browser_check.py --url http://localhost:3000
   .venv/bin/python .agents/skills/browser/scripts/browser_check.py --url http://localhost:3000 --select "#team-select=search-discovery"
   .venv/bin/python .agents/skills/browser/scripts/browser_check.py --url http://localhost:3000 --click "#approval-list .btn-approve"
   .venv/bin/python .agents/skills/browser/scripts/browser_check.py --url http://localhost:8090 --summary generic --wait "document.body.dataset.loaded === '1'"
   .venv/bin/python .agents/skills/browser/scripts/browser_check.py --url http://localhost:8080 --summary generic --wait "document.readyState === 'complete'"
   ```

   Screenshots go to `artifacts/browser/`. Set `CHROME_PATH` if Chrome is installed somewhere unusual.

## 3. Report honestly

- Show the screenshot (open or embed it) and quote what the page displays: banner text, KPI values, anything
  that looks wrong.
- Treat `NaN`, `undefined`, `Infinity`, empty tables, flat charts and console errors as failures, even if the
  banner is green.
- **Never claim visual verification without a screenshot.** If no browser option worked, say so plainly and
  fall back to API checks, labelled as API checks — not as "verified in the browser".
