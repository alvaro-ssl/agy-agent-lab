#!/usr/bin/env python3
"""Fast A2UI check: ask the agent one question in-process and confirm the reply carries A2UI cards.

One model call (~10-40 s) instead of starting servers, curling endpoints or taking screenshots.
Run from the agent project (the folder with app/agent.py):

    uv run python <workspace>/.agents/skills/enable-a2ui/scripts/check_a2ui.py ["optional question"]

Exit code 0 = at least one renderable A2UI message came back; 1 = none (prints what came back instead).
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path.cwd()))

QUESTION = sys.argv[1] if len(sys.argv) > 1 else "Give me a three-line status of our biggest issue as a card."
MARKER = b"application/json+a2ui"


async def main() -> int:
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from app.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="app")
    session = await runner.session_service.create_session(app_name="app", user_id="a2ui-check")
    started = time.time()
    cards, text = [], []
    message = types.Content(role="user", parts=[types.Part(text=QUESTION)])
    async for event in runner.run_async(user_id="a2ui-check", session_id=session.id, new_message=message):
        for part in (event.content.parts if event.content else None) or []:
            blob = part.inline_data.data if part.inline_data and part.inline_data.data else b""
            if MARKER in blob:
                payload = blob.split(b"<a2a_datapart_json>")[-1].split(b"</a2a_datapart_json>")[0]
                cards.append(json.loads(payload)["data"])
            elif part.text:
                text.append(part.text)
    seconds = time.time() - started
    try:
        await runner.close()  # closes the model client cleanly
    except Exception:
        pass
    if cards:
        kinds = sorted({k for c in cards for k in c})
        print(f"PASS: {len(cards)} A2UI message(s) in {seconds:.0f}s ({', '.join(kinds)}). "
              "Restart the Playground and ask in a New Session (Token Streaming OFF).")
        return 0
    print(f"FAIL: no A2UI message in {seconds:.0f}s. Reply started with: {' '.join(text)[:300]!r}")
    print("Check that after_model_callback=a2ui_callback is set and the A2UI instruction (version 0.8) is in the prompt.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
