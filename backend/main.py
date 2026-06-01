"""FastAPI entry point for the Texas Hold'em web app."""
import asyncio
import json
import logging
import os
import uuid
from collections import deque
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Flat imports — Docker WORKDIR /app puts all .py files at the same level.
# Do NOT let an IDE rewrite these as absolute package paths.
from game_session import GameSession

app = FastAPI(title="Texas Hold'em Poker API")

sessions: dict[str, GameSession] = {}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# ------------------------------------------------------------------
# Server log system — broadcasts structured entries to SSE clients
# ------------------------------------------------------------------

_log_history: deque[str] = deque(maxlen=200)
_log_subscribers: list[asyncio.Queue] = []

PHASE_NAMES = {
    "pre_flop": "Pre-Flop", "flop": "Flop", "turn": "Turn",
    "river": "River", "hand_complete": "Hand Complete",
    "showdown": "Showdown", "game_over": "Game Over", "idle": "Idle",
}


def _log(log_type: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    entry = json.dumps({"ts": ts, "type": log_type, "msg": msg})
    _log_history.append(entry)
    for q in _log_subscribers:
        try:
            q.put_nowait(entry)
        except asyncio.QueueFull:
            pass


class _UvicornLogHandler(logging.Handler):
    """Captures uvicorn startup / shutdown / error messages."""
    def emit(self, record: logging.LogRecord) -> None:
        text = record.getMessage()
        # Skip the noisy per-request access lines (handled by API wrappers)
        if record.name == "uvicorn.access":
            return
        _log("server", text)


_uvicorn_handler = _UvicornLogHandler()
# Attach only to uvicorn.error — propagation to the root uvicorn logger
# would double-fire the handler, causing duplicate entries.
logging.getLogger("uvicorn.error").addHandler(_uvicorn_handler)


# ------------------------------------------------------------------
# API routes  (must be registered BEFORE the static mount)
# ------------------------------------------------------------------

class ActionRequest(BaseModel):
    action: str  # "fold" | "call" | "raise"


@app.post("/api/game/new")
async def new_game():
    game_id = str(uuid.uuid4())
    session = GameSession(game_id)
    sessions[game_id] = session
    session.start_hand()
    state = session.get_state()

    chips = "  |  ".join(f"{p['name']}: {p['chips']}" for p in state["players"])
    _log("new", f"New game [{game_id[:8]}]   {chips}")
    return state


@app.get("/api/game/{game_id}")
async def get_game(game_id: str):
    session = sessions.get(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")
    return session.get_state()


@app.post("/api/game/{game_id}/action")
async def submit_action(game_id: str, body: ActionRequest):
    session = sessions.get(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")
    if body.action not in ("fold", "call", "raise"):
        raise HTTPException(status_code=400, detail="action must be fold, call, or raise")
    if not session.awaiting_action:
        raise HTTPException(status_code=409, detail="Not awaiting player action")

    call_amount_before = session.current_call_amount
    phase_before = session.phase

    session.submit_action(body.action)
    state = session.get_state()

    # Build human-readable action description
    if body.action == "fold":
        action_desc = "You folded"
    elif body.action == "call":
        action_desc = "You checked" if call_amount_before == 0 else f"You called {call_amount_before}"
    else:
        action_desc = f"You raised +{session.big_blind}"

    # Show phase transition if it changed
    p_before = PHASE_NAMES.get(phase_before, phase_before)
    p_after  = PHASE_NAMES.get(state["phase"], state["phase"])
    phase_info = f"{p_before} → {p_after}" if state["phase"] != phase_before else p_before

    _log("action", f"{action_desc}   {phase_info}   Pot: {state['pot']}")

    # Log the result if the hand just ended
    if state["phase"] == "hand_complete":
        winner_msg = next((m for m in reversed(state["messages"]) if "wins" in m), None)
        if winner_msg:
            chips = "  |  ".join(f"{p['name']}: {p['chips']}" for p in state["players"])
            _log("result", f"{winner_msg}   —   {chips}")

    return state


@app.post("/api/game/{game_id}/next-hand")
async def next_hand(game_id: str):
    session = sessions.get(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game not found")
    if session.phase not in ("hand_complete", "game_over"):
        raise HTTPException(status_code=409, detail="Current hand is not complete")
    session.messages = []
    session.start_hand()
    state = session.get_state()

    chips = "  |  ".join(f"{p['name']}: {p['chips']}" for p in state["players"])
    _log("new", f"Next hand [{game_id[:8]}]   {chips}")
    return state


# ------------------------------------------------------------------
# Server-Sent Events — real-time log stream
# ------------------------------------------------------------------

@app.get("/api/logs/stream")
async def log_stream():
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    _log_subscribers.append(queue)

    async def generate():
        try:
            # Replay recent history for the new client
            for entry in list(_log_history):
                yield f"data: {entry}\n\n"
            # Stream live events
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {entry}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # prevents proxy / browser timeout
        finally:
            try:
                _log_subscribers.remove(queue)
            except ValueError:
                pass

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ------------------------------------------------------------------
# Static file serving (catch-all — must come last)
# ------------------------------------------------------------------

if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
