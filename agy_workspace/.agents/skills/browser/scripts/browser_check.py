#!/usr/bin/env python3
"""Drive a real headless Chrome over the DevTools protocol: open a page, wait for it to finish
rendering, optionally click / pick options, then save a screenshot and print what the page shows.

Standard library only (no Playwright, no Node) so it works on any workshop laptop with Chrome.

Examples:
  python3 browser_check.py --url http://localhost:3000
  python3 browser_check.py --url http://localhost:3000 --select "#team-select=search-discovery"
  python3 browser_check.py --url http://localhost:3000 --click "#approval-list .btn-approve"
  python3 browser_check.py --url http://localhost:8080 --summary generic --wait "document.readyState === 'complete'"
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

# What the Control Tower dashboard is showing, read from the rendered DOM.
CONTROL_TOWER_SUMMARY = r"""
(() => {
  const text = (sel) => { const n = document.querySelector(sel); return n ? n.textContent.trim() : null; };
  const kpis = [...document.querySelectorAll('#kpis .kpi')].map((k) => ({
    label: k.querySelector('.kpi-label')?.textContent.trim(),
    value: k.querySelector('.kpi-value')?.textContent.trim(),
    detail: k.querySelector('.kpi-sub')?.textContent.trim(),
  }));
  const rows = [...document.querySelectorAll('#service-table tbody tr')].map((tr) =>
    [...tr.querySelectorAll('td')].map((td) => td.textContent.trim().replace(/\s+/g, ' ')));
  const chartText = [...document.querySelectorAll('#latency-chart text')].map((t) => t.textContent);
  const body = document.body.innerText;
  return {
    title: document.title,
    version: text('#ct-version'),
    banner: text('#banner-text'),
    banner_state: document.getElementById('status-banner')?.className,
    kpis,
    service_rows: rows.length,
    first_rows: rows.slice(0, 4),
    chart_title: text('#chart-title'),
    chart_labels: chartText,
    chart_paths: document.querySelectorAll('#latency-chart path').length,
    incidents: document.querySelectorAll('#incident-list li').length,
    approvals: [...document.querySelectorAll('#approval-list li')].map((li) => li.textContent.trim().replace(/\s+/g, ' ')),
    suspicious_values: {
      NaN: (body.match(/\bNaN\b/g) || []).length,
      undefined: (body.match(/\bundefined\b/g) || []).length,
      Infinity: (body.match(/\bInfinity\b/g) || []).length,
    },
  };
})()
"""

GENERIC_SUMMARY = r"""
(() => ({
  title: document.title,
  url: location.href,
  headings: [...document.querySelectorAll('h1, h2, h3')].slice(0, 15).map((h) => h.textContent.trim()),
  text_excerpt: document.body.innerText.slice(0, 2500),
}))()
"""


def find_chrome() -> str:
    for candidate in CHROME_CANDIDATES:
        if not candidate:
            continue
        path = candidate if os.path.isabs(candidate) else shutil.which(candidate)
        if path and os.path.exists(path):
            return path
    sys.exit("No Chrome/Chromium/Edge found. Set CHROME_PATH to the browser executable.")


class DevToolsSocket:
    """Minimal WebSocket client (RFC 6455) — enough for the Chrome DevTools protocol."""

    def __init__(self, ws_url: str):
        host_port, path = ws_url.removeprefix("ws://").split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(
            (f"GET /{path} HTTP/1.1\r\nHost: {host_port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
             f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode()
        )
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.sock.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"WebSocket handshake failed: {response[:200]!r}")
        self.buffer = response.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0
        self.events: list[dict] = []

    def _recv_exact(self, n: int) -> bytes:
        while len(self.buffer) < n:
            chunk = self.sock.recv(1 << 16)
            if not chunk:
                raise ConnectionError("DevTools socket closed")
            self.buffer += chunk
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def _send(self, payload: dict) -> None:
        data = json.dumps(payload).encode()
        header = bytearray([0x81])
        if len(data) < 126:
            header.append(0x80 | len(data))
        elif len(data) < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", len(data))
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", len(data))
        mask = os.urandom(4)
        self.sock.sendall(bytes(header) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _recv(self) -> dict:
        message = b""
        while True:
            b0, b1 = self._recv_exact(2)
            length = b1 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exact(8))[0]
            message += self._recv_exact(length)
            if b0 & 0x80:
                return json.loads(message)

    def call(self, method: str, **params) -> dict:
        self.next_id += 1
        self._send({"id": self.next_id, "method": method, "params": params})
        while True:
            msg = self._recv()
            if msg.get("id") == self.next_id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self.events.append(msg)

    def evaluate(self, expression: str):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"].get("text", "evaluation failed"))
        return result["result"].get("value")


def wait_for(ws: DevToolsSocket, expression: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if ws.evaluate(f"Boolean({expression})"):
                return True
        except RuntimeError:
            pass
        time.sleep(0.25)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:3000")
    parser.add_argument("--out", default="", help="Screenshot path (default: artifacts/browser/<host>-<time>.png)")
    parser.add_argument("--wait", default="document.body && document.body.dataset.loaded",
                        help="JS expression that becomes truthy when the page has finished loading")
    parser.add_argument("--timeout", type=float, default=30.0, help="Seconds to wait for --wait")
    parser.add_argument("--click", action="append", default=[], help="CSS selector to click (repeatable)")
    parser.add_argument("--select", action="append", default=[], help="'<css>=<value>' to choose in a <select>")
    parser.add_argument("--summary", choices=["control-tower", "generic"], default="control-tower")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()

    out = Path(args.out or f"artifacts/browser/{args.url.split('//')[-1].replace(':', '-').strip('/').replace('/', '_')}"
                            f"-{datetime.now():%Y%m%d-%H%M%S}.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    profile = tempfile.mkdtemp(prefix="agy-browser-")
    chrome = subprocess.Popen(
        [find_chrome(), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
         "--hide-scrollbars", "--remote-debugging-port=0", f"--user-data-dir={profile}",
         f"--window-size={args.width},{args.height}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    report: dict = {"url": args.url, "screenshot": None}
    try:
        port_file = Path(profile) / "DevToolsActivePort"
        for _ in range(100):
            if port_file.exists() and port_file.read_text().strip():
                break
            time.sleep(0.1)
        port = port_file.read_text().split()[0]
        targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list"))
        page = next(t for t in targets if t["type"] == "page")
        ws = DevToolsSocket(page["webSocketDebuggerUrl"])
        ws.call("Page.enable")
        ws.call("Runtime.enable")

        started = time.time()
        ws.call("Page.navigate", url=args.url)
        loaded = wait_for(ws, args.wait, args.timeout)
        report["load_seconds"] = round(time.time() - started, 2)
        report["loaded"] = loaded

        for item in args.select:
            selector, value = item.rsplit("=", 1)
            ws.evaluate(
                f"(() => {{ const s = document.querySelector({json.dumps(selector)}); s.value = {json.dumps(value)};"
                f" s.dispatchEvent(new Event('change', {{bubbles: true}})); }})()"
            )
            time.sleep(0.3)
            wait_for(ws, args.wait, args.timeout)
        for selector in args.click:
            clicked = ws.evaluate(
                f"(() => {{ const n = document.querySelector({json.dumps(selector)}); if (!n) return false; n.click(); return true; }})()"
            )
            report.setdefault("clicked", []).append({selector: clicked})
            time.sleep(0.5)
            wait_for(ws, args.wait, args.timeout)
        if args.select or args.click:
            time.sleep(0.5)

        report["page"] = ws.evaluate(CONTROL_TOWER_SUMMARY if args.summary == "control-tower" else GENERIC_SUMMARY)
        height = ws.evaluate("Math.ceil(document.documentElement.scrollHeight)") or args.height
        ws.call("Emulation.setDeviceMetricsOverride", width=args.width, height=min(int(height), 6000),
                deviceScaleFactor=1, mobile=False)
        shot = ws.call("Page.captureScreenshot", format="png", captureBeyondViewport=True)
        out.write_bytes(base64.b64decode(shot["data"]))
        report["screenshot"] = str(out.resolve())
        report["console_errors"] = [
            e["params"].get("exceptionDetails", {}).get("exception", {}).get("description")
            or e["params"].get("exceptionDetails", {}).get("text")
            for e in ws.events if e.get("method") == "Runtime.exceptionThrown"
        ] + [
            " ".join(str(a.get("value", a.get("description", ""))) for a in e["params"].get("args", []))
            for e in ws.events if e.get("method") == "Runtime.consoleAPICalled" and e["params"].get("type") == "error"
        ]
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome.kill()
        shutil.rmtree(profile, ignore_errors=True)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
