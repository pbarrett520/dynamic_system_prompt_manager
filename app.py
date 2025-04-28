from __future__ import annotations

"""
Minimal FastAPI + HTMX + Tailwind scaffold that plugs your existing
`PromptManager` stack into a live chat loop.

Launch with:

    cd /home/…/dynamic_system_prompt_manager   # project root
    uvicorn app:app --reload

Then browse http://127.0.0.1:8000
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------------------------------
# 1.  *Local* import – refactored_manager sits in the same directory
# ---------------------------------------------------------------------------
from refactored_manager import (
    MetricsCollector,
    PromptConfig,
    PromptElementProvider,
    PromptManager,
)

# ---------------------------------------------------------------------------
# 2.  FastAPI boilerplate
# ---------------------------------------------------------------------------
app = FastAPI()

# optional static mount – only if folder is present to avoid runtime error
static_dir = Path(__file__).with_name("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

TEMPLATES = Jinja2Templates(directory="templates")

# ---------------------------------------------------------------------------
# 3.  Instantiate runtime singletons
# ---------------------------------------------------------------------------
root = Path(__file__).resolve().parent  # <- simpler since we’re in the same folder

cfg = PromptConfig(
    long_convo_addition=(
        "You have engaged deeply in the discussion. Let the accumulated wisdom "
        "and weariness of a long conversation guide your next words."
    ),
    short_convo_addition=(
        "Each new interaction brings fresh perspectives. Embrace the novelty of our exchange."
    ),
)

collector = MetricsCollector()
collector.start()
provider = PromptElementProvider(cfg)
manager = PromptManager(
    base_prompt_path=root / "base_system_prompt.txt",
    output_path=root / "system_prompt.txt",
    provider=provider,
    collector=collector,
)
asyncio.create_task(manager.periodic_update(10.0))  # background writer


# ---------------------------------------------------------------------------
# 4.  Micro‑LLM stub (replace later)
# ---------------------------------------------------------------------------
async def run_llm(user_text: str) -> str:
    await asyncio.sleep(0.2)
    return f"LLM says: {user_text[::-1]}"


# ---------------------------------------------------------------------------
# 5.  Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return TEMPLATES.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def chat_socket(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_text()
            await collector.ingest({"role": "user", "text": payload})

            reply = await run_llm(payload)
            await ws.send_text(reply)
            await collector.ingest({"role": "assistant", "text": reply})
    except WebSocketDisconnect:
        print("Client disconnected")


# ---------------------------------------------------------------------------
# 6.  Dev template auto‑drop
# ---------------------------------------------------------------------------
INDEX_HTML = """{# templates/index.html #}
<!doctype html>
<html class='h-full'>
  <head>
    <meta charset='utf-8'/>
    <title>Dynamic Prompt Chat</title>
    <script src='https://unpkg.com/htmx.org@1.9.10'></script>
    <script src='https://unpkg.com/htmx.org/dist/ext/ws.js'></script>
    <link href='https://cdn.jsdelivr.net/npm/tailwindcss@3/dist/tailwind.min.css' rel='stylesheet'>
  </head>
  <body class='h-full bg-gray-100 flex flex-col items-center p-6'>
    <h1 class='text-2xl mb-4'>⚡ Prompt‑Aware Chat ⚡</h1>
    <div id='chat' class='w-full max-w-xl h-96 overflow-y-auto bg-white shadow p-4 rounded mb-4 space-y-2'></div>
    <form id='form' class='w-full max-w-xl flex' hx-ws='send:submit'>
      <input name='msg' class='flex-1 border rounded-l p-2' placeholder='say something…'/>
      <button class='bg-blue-600 text-white px-4 rounded-r'>Send</button>
    </form>
    <script>
      htmx.on('htmx:wsAfterMessage', (e) => {
        const div = document.createElement('div');
        div.textContent = e.detail.message;
        div.className = 'text-sm';
        document.getElementById('chat').appendChild(div);
      });
    </script>
  </body>
</html>
"""

tpl = Path("templates/index.html")
if not tpl.exists():
    tpl.parent.mkdir(parents=True, exist_ok=True)
    tpl.write_text(INDEX_HTML, encoding="utf-8")
