/* Texas Hold'em frontend */

let gameId = null;

// ── Card rendering ──────────────────────────────────────────────

const RANK_LABEL = { T: "10", J: "J", Q: "Q", K: "K", A: "A" };
const SUIT_SYMBOL = { H: "♥", D: "♦", C: "♣", S: "♠" };

function renderCard(code) {
  if (code === "??") {
    return `<div class="card card-back" title="Hidden"></div>`;
  }

  const rankChar = code[0];
  const suitChar = code[1];
  const rank = RANK_LABEL[rankChar] ?? rankChar;
  const suit = SUIT_SYMBOL[suitChar] ?? suitChar;
  const color = (suitChar === "H" || suitChar === "D") ? "red" : "black";

  return `
    <div class="card ${color}" title="${rank}${suit}">
      <div class="card-top"><span class="card-rank">${rank}</span><span class="card-suit">${suit}</span></div>
      <div class="card-center">${suit}</div>
      <div class="card-bottom"><span class="card-rank">${rank}</span><span class="card-suit">${suit}</span></div>
    </div>`;
}

function renderCards(codes) {
  if (!codes || codes.length === 0) {
    return `<span class="no-cards-msg">—</span>`;
  }
  return codes.map(renderCard).join("");
}

// ── State rendering ─────────────────────────────────────────────

function render(state) {
  // Phase label
  const phaseNames = {
    idle: "—", pre_flop: "Pre-Flop", flop: "Flop",
    turn: "Turn", river: "River",
    showdown: "Showdown", hand_complete: "Hand Complete",
    game_over: "Game Over",
  };
  document.getElementById("phase-label").textContent = phaseNames[state.phase] ?? state.phase;

  // Community cards
  document.getElementById("community-cards").innerHTML =
    state.community_cards.length > 0
      ? renderCards(state.community_cards)
      : `<span class="no-cards-msg">No community cards yet</span>`;

  // Pot
  document.getElementById("pot-display").textContent = `Pot: ${state.pot}`;

  // Opponents
  const opponentsDiv = document.getElementById("opponents");
  opponentsDiv.innerHTML = "";
  for (const p of state.players) {
    if (p.is_human) continue;
    const el = document.createElement("div");
    el.className = [
      "player-seat",
      p.folded ? "folded" : "",
      p.is_current_actor ? "acting" : "",
    ].filter(Boolean).join(" ");
    el.innerHTML = `
      <div class="seat-name">${p.name}</div>
      <div class="seat-chips">${p.chips} chips</div>
      <div class="card-row">${renderCards(p.hole_cards)}</div>`;
    opponentsDiv.appendChild(el);
  }

  // Human player
  const human = state.players.find(p => p.is_human);
  if (human) {
    document.getElementById("human-cards").innerHTML = renderCards(human.hole_cards);
    document.getElementById("human-info").textContent = `${human.name} — ${human.chips} chips`;
  }

  // Action buttons
  const waiting = state.awaiting_action;
  const foldBtn  = document.getElementById("fold-btn");
  const callBtn  = document.getElementById("call-btn");
  const raiseBtn = document.getElementById("raise-btn");
  const nextBtn  = document.getElementById("next-btn");

  foldBtn.disabled  = !waiting;
  callBtn.disabled  = !waiting;
  raiseBtn.disabled = !waiting;

  if (waiting) {
    const ca = state.call_amount;
    callBtn.textContent = ca > 0 ? `Call ${ca}` : "Check";
    raiseBtn.textContent = `Raise +${10}`;
  } else {
    callBtn.textContent = "Call";
    raiseBtn.textContent = "Raise";
  }

  const isTerminal = ["hand_complete", "game_over"].includes(state.phase);
  nextBtn.style.display = isTerminal ? "inline-block" : "none";

  if (state.phase === "game_over") {
    nextBtn.textContent = "New Game";
    nextBtn.onclick = newGame;
  } else {
    nextBtn.textContent = "Next Hand ▶";
    nextBtn.onclick = nextHand;
  }

  // Log
  const logDiv = document.getElementById("log-messages");
  logDiv.innerHTML = state.messages
    .map(m => {
      const isSep = m.startsWith("--");
      return `<div class="log-entry${isSep ? " separator" : ""}">${escHtml(m)}</div>`;
    })
    .join("");
  logDiv.scrollTop = logDiv.scrollHeight;
}

function escHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ── API calls ───────────────────────────────────────────────────

async function apiPost(url, body) {
  const opts = { method: "POST" };
  if (body !== undefined) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

async function newGame() {
  try {
    const state = await apiPost("/api/game/new");
    gameId = state.game_id;
    render(state);
  } catch (e) {
    alert("Failed to start game: " + e.message);
  }
}

async function doAction(action) {
  if (!gameId) return;
  try {
    const state = await apiPost(`/api/game/${gameId}/action`, { action });
    render(state);
  } catch (e) {
    alert("Action failed: " + e.message);
  }
}

async function nextHand() {
  if (!gameId) return;
  try {
    const state = await apiPost(`/api/game/${gameId}/next-hand`);
    render(state);
  } catch (e) {
    alert("Failed to start next hand: " + e.message);
  }
}

// ── Server log overlay ──────────────────────────────────────────

const TAG_LABELS = {
  new:    "NEW",
  action: "ACTION",
  result: "RESULT",
  server: "SERVER",
  error:  "ERROR",
};

let _srvLogOpen = true;

function toggleSrvLog() {
  _srvLogOpen = !_srvLogOpen;
  document.getElementById("srv-log-body").classList.toggle("collapsed", !_srvLogOpen);
  document.getElementById("srv-log-btn").textContent = _srvLogOpen ? "▼" : "▲";
}

function appendSrvEntry(data) {
  // data: { ts, type, msg }
  const body = document.getElementById("srv-log-body");
  if (!body) return;

  const row = document.createElement("div");
  row.className = `srv-entry srv-type-${data.type ?? "server"}`;
  row.innerHTML =
    `<span class="srv-ts">${escHtml(data.ts ?? "")}</span>` +
    `<span class="srv-tag">${escHtml(TAG_LABELS[data.type] ?? data.type ?? "")}</span>` +
    `<span class="srv-msg" title="${escHtml(data.msg ?? "")}">${escHtml(data.msg ?? "")}</span>`;

  body.appendChild(row);

  // Keep memory bounded
  while (body.children.length > 120) body.removeChild(body.firstChild);

  // Auto-scroll only when already at bottom
  if (body.scrollHeight - body.scrollTop - body.clientHeight < 40) {
    body.scrollTop = body.scrollHeight;
  }

  // Flash the live dot
  const dot = document.getElementById("srv-dot");
  if (dot) {
    dot.classList.add("blink");
    setTimeout(() => dot.classList.remove("blink"), 350);
  }
}

function connectServerLog() {
  const es = new EventSource("/api/logs/stream");

  es.onmessage = (event) => {
    if (!event.data || event.data.startsWith(":")) return; // SSE keepalive comment
    try {
      const data = JSON.parse(event.data);
      appendSrvEntry(data);
    } catch {
      // Fallback: render raw text as a server entry
      appendSrvEntry({ ts: "", type: "server", msg: event.data });
    }
  };

  // EventSource reconnects automatically on error — no extra handling needed
}

// ── Boot ────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  connectServerLog();
  newGame();
});
