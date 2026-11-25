"""Single-process FastAPI server for MolBhaav."""
from __future__ import annotations

import base64
import binascii
import html
import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import db
import gemini_pipeline
import storage
from arenas import arena_by_boss_id, internal_arena, public_arena, public_arenas
from config import (
    STATIC_DIR,
    UTC,
    format_indian_rupees,
    ist_date,
    ist_timestamp,
    now_ist,
    port,
    utc_timestamp,
)
from pricing_engine import compute_turn_outcome

MAX_AUDIO_BYTES = 750 * 1024
RATE_MESSAGE = "Bhaiya needs a chai break—try again in a few seconds!"
ARENA_IDS = ("daily_market", "placement_hr", "freelance_client")


class SlidingWindowLimiter:
    def __init__(self, per_minute: int = 18, per_hour: int = 120):
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self.per_minute = per_minute
        self.per_hour = per_hour

    def allow(self, ip: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        with self._lock:
            for stale in [key for key, q in self.events.items() if not q or q[-1] < current - 3600]:
                self.events.pop(stale, None)
            if ip not in self.events and len(self.events) >= 5000:
                oldest = min(self.events, key=lambda key: self.events[key][-1] if self.events[key] else float("-inf"))
                self.events.pop(oldest, None)
            queue = self.events[ip]
            while queue and queue[0] <= current - 3600:
                queue.popleft()
            if sum(stamp > current - 60 for stamp in queue) >= self.per_minute or len(queue) >= self.per_hour:
                return False
            queue.append(current)
            return True

    def reset(self):
        with self._lock:
            self.events.clear()


class SessionLockPool:
    """Serialize turns and receipt creation for each session without retaining finished locks."""
    def __init__(self):
        self._guard = threading.Lock()
        self._entries: dict[str, dict[str, Any]] = {}

    @contextmanager
    def hold(self, session_id: str):
        with self._guard:
            entry = self._entries.get(session_id)
            if entry is None:
                entry = {"lock": threading.Lock(), "users": 0}
                self._entries[session_id] = entry
            entry["users"] += 1
        entry["lock"].acquire()
        try:
            yield
        finally:
            entry["lock"].release()
            with self._guard:
                entry["users"] -= 1
                if entry["users"] == 0:
                    self._entries.pop(session_id, None)


turn_limiter = SlidingWindowLimiter(per_minute=18, per_hour=120)
session_limiter = SlidingWindowLimiter(per_minute=45, per_hour=300)
session_lock_pool = SessionLockPool()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="MolBhaav", version="1.0.0", debug=False, lifespan=lifespan)


class StartBody(BaseModel):
    arena_id: str = "daily_market"
    player_name: str | None = Field(None, max_length=32)


class SampleBody(BaseModel):
    arena_id: str = "daily_market"


class TurnBody(BaseModel):
    session_id: str
    audio_b64: str | None = Field(None, max_length=1_024_008)
    text: str | None = Field(None, max_length=4000)


class FinishBody(BaseModel):
    session_id: str
    player_name: str | None = Field(None, max_length=32)


def _name(value: str | None, fallback: str) -> str:
    return " ".join((value or "").split()).strip(" ._-")[:24] or fallback


def _decode_wav(value: str | None) -> bytes | None:
    if not value:
        return None
    if len(value) > ((MAX_AUDIO_BYTES + 2) // 3) * 4 + 8:
        raise HTTPException(413, "Audio is too large. Keep each turn under 750 KB.")
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(400, "Audio must be valid base64 WAV data.") from None
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio is too large. Keep each turn under 750 KB.")
    if not data.startswith(b"RIFF") or b"WAVE" not in data[:16]:
        raise HTTPException(400, "Audio must be a WAV recording.")
    return data


def _ip(request: Request) -> str:
    for header in ("cf-connecting-ip", "x-real-ip"):
        value = request.headers.get(header, "").strip()
        if value:
            return value
    forwarded = request.headers.get("x-forwarded-for", "")
    first_hop = forwarded.split(",", 1)[0].strip()
    if first_hop:
        return first_hop
    return request.client.host if request.client else "unknown"


def _rate_limited_response(request: Request, rate_limiter: SlidingWindowLimiter) -> JSONResponse | None:
    if rate_limiter.allow(_ip(request)):
        return None
    return JSONResponse(status_code=429, content={"detail": RATE_MESSAGE})


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html; charset=utf-8")


@app.get("/api/health")
def health():
    daily = internal_arena("daily_market")
    storage_mode = "embarko" if os.environ.get("STORAGE_URL") and os.environ.get("STORAGE_TOKEN") else "local"
    return {"status": "ok", "daily_boss_id": daily["boss_id"], "ist_date": ist_date().isoformat(),
            "gemini_configured": gemini_pipeline.gemini_configured(), "storage_mode": storage_mode}


@app.get("/api/arenas")
def get_arenas():
    return {"ist_date": ist_date().isoformat(), "arenas": public_arenas()}


@app.post("/api/session/start")
def start_session(body: StartBody, request: Request):
    limited = _rate_limited_response(request, session_limiter)
    if limited:
        return limited
    try:
        arena = internal_arena(body.arena_id)
    except KeyError:
        raise HTTPException(404, "That arena is not on the board.") from None
    session_id = uuid.uuid4().hex
    now = utc_timestamp()
    player_name = _name(body.player_name, f"JugaadKing_{int(session_id[:8], 16) % 90 + 10}")
    db.create_session({"session_id": session_id, "arena_id": body.arena_id, "boss_id": arena["boss_id"],
        "player_name": player_name, "date_ist": ist_date().isoformat(), "current_price": arena["start_price"],
        "start_price": arena["start_price"], "created_at": now, "updated_at": now})
    return {"session_id": session_id, "arena": public_arena(arena), "player_name": player_name,
            "opening_greeting": arena["greeting"], "sample_audio_b64": None}


@app.post("/api/session/sample-audio")
def sample_audio(body: SampleBody, request: Request):
    limited = _rate_limited_response(request, session_limiter)
    if limited:
        return limited
    try:
        arena = internal_arena(body.arena_id)
    except KeyError:
        raise HTTPException(404, "That arena is not on the board.") from None
    audio = gemini_pipeline.sample_audio(arena)
    return {"audio_b64": base64.b64encode(audio).decode("ascii") if audio else None,
            "tts_fallback": audio is None, "fallback_text": arena["greeting"]}


@app.post("/api/turn")
def submit_turn(body: TurnBody, request: Request):
    limited = _rate_limited_response(request, turn_limiter)
    if limited:
        return limited
    with session_lock_pool.hold(body.session_id):
        return _submit_turn(body, request)


def _submit_turn(body: TurnBody, request: Request):
    audio_bytes = _decode_wav(body.audio_b64)
    text = (body.text or "").strip()
    if not text and audio_bytes is None:
        raise HTTPException(422, "Say something or type your counter-offer.")
    session = db.get_session(body.session_id)
    if not session:
        raise HTTPException(404, "Negotiation session not found.")
    if session["status"] != "active":
        raise HTTPException(409, "This negotiation has ended.")
    if session["turn_number"] >= 4:
        raise HTTPException(409, "This was your fourth turn. Lock in the result.")

    arena = arena_by_boss_id(session["boss_id"])
    arena["current_price"] = session["current_price"]
    move = gemini_pipeline.analyze_turn(text or None, audio_bytes, arena)
    turn = session["turn_number"] + 1
    outcome = compute_turn_outcome(arena["direction"], session["current_price"], session["start_price"],
        arena["limit_price"], arena["step"], session["patience"], move["vocal_conf"], move["bluff_prob"],
        move["tactic"], move["soft_spot"], move["pet_hate"], turn)
    accepting = (
        bool(move.get("accept_deal"))
        and session["turn_number"] >= 1
        and move.get("tactic") not in {"prompt_injection", "rude_lowball"}
        and not move.get("pet_hate")
    )
    move["accept_deal"] = accepting
    if accepting:
        outcome.update({
            "new_price": session["current_price"], "price_delta": 0,
            "new_patience": session["patience"], "efficiency_pct": session["efficiency"],
            "walked_out": False, "pct_move": 0.0,
        })
    prior_turns = db.list_turns(body.session_id, include_audio=False)
    dialogue = gemini_pipeline.generate_dialogue(arena, move, outcome, text or None, audio_bytes, history=prior_turns)
    audio = gemini_pipeline.synthesize_speech(arena, dialogue["reply_text"], dialogue["delivery_style"])
    status = "walked_out" if outcome["walked_out"] else ("accepted" if accepting else ("finished" if turn == 4 else "active"))
    now = utc_timestamp()
    new_session = {**session, "current_price": outcome["new_price"], "patience": outcome["new_patience"],
        "turn_number": turn, "efficiency": outcome["efficiency_pct"], "status": status, "updated_at": now}
    mood = "furious" if outcome["walked_out"] or outcome["is_jailbreak"] else (
        "sweating" if outcome["new_patience"] < 40 else ("impressed" if move["soft_spot"] else "smug"))
    record = {"turn_number": turn, "player_transcript": str(dialogue.get("player_transcript") or move.get("player_transcript") or text)[:360],
        "player_text": text[:1000], "reply_text": dialogue["reply_text"], "coach_tip": dialogue["coach_tip"],
        "delivery_style": dialogue["delivery_style"], "audio_b64": base64.b64encode(audio).decode("ascii") if audio else None,
        "tactic": move["tactic"], "tactic_badge": move["tactic"].replace("_", " ").title(),
        "soft_spot": bool(move["soft_spot"]), "pet_hate": bool(move["pet_hate"]), "accept_deal": accepting,
        "vocal_conf": round(float(move["vocal_conf"]), 4), "bluff_prob": round(float(move["bluff_prob"]), 4),
        "new_price": outcome["new_price"], "price_delta": outcome["price_delta"], "patience": outcome["new_patience"],
        "efficiency_pct": outcome["efficiency_pct"], "pct_move": outcome["pct_move"], "mood": mood,
        "walked_out": outcome["walked_out"], "is_jailbreak": outcome["is_jailbreak"], "created_at": now}
    try:
        db.record_turn(body.session_id, record, new_session)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "This move was already submitted. Refresh the negotiation and try again.") from None
    del audio_bytes
    return {"session_id": body.session_id, "turn": turn, "turn_limit": 4, "current_price": outcome["new_price"],
        "price_delta": outcome["price_delta"], "patience": outcome["new_patience"],
        "vocal_confidence": round(float(move["vocal_conf"]) * 100), "bluff_credibility": round(float(move["bluff_prob"]) * 100),
        "opponent_patience": outcome["new_patience"], "tactic": move["tactic"], "tactic_badge": record["tactic_badge"],
        "boss_mood": mood, "player_transcript": record["player_transcript"], "reply_text": dialogue["reply_text"],
        "coach_tip": dialogue["coach_tip"], "audio_b64": record["audio_b64"], "tts_fallback": audio is None,
        "walked_out": outcome["walked_out"], "accepted": accepting, "ended": status != "active",
        "efficiency_pct": outcome["efficiency_pct"]}


def _final_audio(turns: list[dict]) -> bytes | None:
    if not turns or not turns[-1].get("audio_b64"):
        return None
    try:
        return base64.b64decode(turns[-1]["audio_b64"], validate=True)
    except (ValueError, binascii.Error):
        return None


def _deal_payload(row: dict) -> dict:
    arena = arena_by_boss_id(row["boss_id"])
    debrief = json.loads(row["debrief_json"])
    movement = row["start_price"] - row["final_price"] if row["direction"] == "downward" else row["final_price"] - row["start_price"]
    left = row["final_price"] - row["limit_price"] if row["direction"] == "downward" else row["limit_price"] - row["final_price"]
    payload = {"deal_id": row["deal_id"], "arena_id": row["arena_id"], "arena_label": arena["arena_label"],
        "boss": public_arena(arena), "player_name": row["player_name"], "date_ist": row["date_ist"],
        "created_at": row["created_at"], "starting_price": row["start_price"], "final_price": row["final_price"],
        "secret_limit_price": row["limit_price"], "direction": row["direction"], "savings_or_gain": movement,
        "left_on_table": max(0, left), "efficiency_pct": row["efficiency"], "patience": row["patience"],
        "status": row["status"], "rank": row["rank"], "percentile": row["percentile"], "audio_url": row["audio_url"]}
    allowed_debrief = {"tactics_summary", "missed_opportunity", "better_line", "badges", "deal_timestamp_ist"}
    payload.update({key: value for key, value in debrief.items() if key in allowed_debrief})
    return payload


def _rank(deal_id: str, arena_id: str, date_text: str) -> tuple[int, float]:
    return db.compute_rank(deal_id, arena_id, date_text)


@app.post("/api/session/finish")
def finish_session(body: FinishBody):
    with session_lock_pool.hold(body.session_id):
        return _finish_session(body)


def _finish_session(body: FinishBody):
    existing = db.find_deal_by_session(body.session_id)
    if existing:
        return _deal_payload(existing)
    session = db.get_session(body.session_id)
    if not session:
        raise HTTPException(404, "Negotiation session not found.")
    if session["turn_number"] < 1:
        raise HTTPException(409, "Make at least one counter before locking a deal.")
    arena = arena_by_boss_id(session["boss_id"])
    turns = db.list_turns(body.session_id)
    final_price = session["current_price"]
    debrief = gemini_pipeline.generate_debrief(arena, turns, final_price, session["efficiency"], history=turns)
    tactics = {item.get("tactic") for item in turns}
    badges = [item.replace("_", " ").title() for item in sorted(tactics) if item]
    if any(item.get("soft_spot") for item in turns):
        badges.append("Soft Spot Unlocked")
    if any(item.get("is_jailbreak") for item in turns):
        badges.append("Jailbreak Roast")
    debrief["badges"] = badges
    debrief["secret_limit_price"] = arena["limit_price"]
    remaining = final_price - arena["limit_price"] if arena["direction"] == "downward" else arena["limit_price"] - final_price
    debrief["left_on_table"] = max(0, remaining)
    debrief["deal_timestamp_ist"] = ist_timestamp()
    deal_id, created = uuid.uuid4().hex, utc_timestamp()
    try:
        audio_url = storage.persist_ai_audio(deal_id, _final_audio(turns))
    except Exception as exc:
        logger.warning("Could not save boss reaction audio (%s)", type(exc).__name__)
        audio_url = None
    status = "walked_out" if session["status"] == "walked_out" else (
        session["status"] if session["status"] in {"finished", "accepted"} else "locked"
    )
    deal = {"deal_id": deal_id, "session_id": body.session_id, "arena_id": session["arena_id"], "boss_id": session["boss_id"],
        "player_name": _name(body.player_name, session["player_name"]), "date_ist": session["date_ist"],
        "start_price": session["start_price"], "final_price": final_price, "limit_price": arena["limit_price"],
        "direction": arena["direction"], "efficiency": session["efficiency"], "patience": session["patience"],
        "status": status, "debrief_json": json.dumps(debrief, ensure_ascii=False), "audio_url": audio_url,
        "rank": 0, "percentile": 0.0, "created_at": created, "boss_name": arena["boss_name"]}
    try:
        db.save_deal(deal)
    except sqlite3.IntegrityError:
        existing = db.find_deal_by_session(body.session_id)
        if existing:
            return _deal_payload(existing)
        raise
    rank, percentile = (0, 0.0) if status == "walked_out" else _rank(deal_id, session["arena_id"], session["date_ist"])
    db.update_deal_rank(deal_id, rank, percentile)
    db.close_session(body.session_id, "walked_out" if status == "walked_out" else "locked", utc_timestamp())
    db.clear_session_audio(body.session_id)
    saved = db.find_deal(deal_id)
    return _deal_payload(saved)


@app.get("/api/leaderboard")
def leaderboard(arena_id: str = "daily_market"):
    if arena_id not in ARENA_IDS:
        raise HTTPException(404, "That arena is not on the board.")
    date_text = ist_date().isoformat()
    rows = db.leaderboard_rows(arena_id, date_text, 20)
    entries = [{"rank": i, "player_name": row["player_name"], "boss_name": row["boss_name"],
        "final_price": row["final_price"], "efficiency_pct": row["efficiency"], "deal_id": row["deal_id"]}
        for i, row in enumerate(rows, 1)]
    return {"arena_id": arena_id, "date_ist": date_text, "entries": entries}


@app.get("/api/deal/{deal_id}")
def get_deal(deal_id: str):
    row = db.find_deal(deal_id)
    if not row:
        raise HTTPException(404, "Receipt not found.")
    return _deal_payload(row)


@app.get("/api/local-audio/{deal_id}")
def local_audio(deal_id: str):
    path = storage.local_audio_path(deal_id)
    if not path:
        raise HTTPException(404, "Audio clip not found.")
    return FileResponse(path, media_type="audio/wav")


@app.get("/deal/{deal_id}", response_class=HTMLResponse)
def share_deal(deal_id: str):
    row = db.find_deal(deal_id)
    if not row:
        raise HTTPException(404, "Receipt not found.")
    arena = arena_by_boss_id(row["boss_id"])
    start_price = format_indian_rupees(row["start_price"])
    final_price = format_indian_rupees(row["final_price"])
    penalized = (row["final_price"] > row["start_price"] if arena["direction"] == "downward"
                 else row["final_price"] < row["start_price"])
    verb = "talked" if arena["direction"] == "downward" else "pushed"
    direction_word = "down" if arena["direction"] == "downward" else "up"
    title = (f"{arena['boss_name']} slammed the shutter on me on MolBhaav!" if row["status"] == "walked_out"
             else f"I locked {final_price} with {arena['boss_name']} on MolBhaav" if row["final_price"] == row["start_price"]
             else f"{arena['boss_name']} pushed my price up from {start_price} to {final_price} on MolBhaav" if penalized and arena["direction"] == "downward"
             else f"{arena['boss_name']} lowered my offer from {start_price} to {final_price} on MolBhaav" if penalized
             else f"I {verb} {arena['boss_name']} {direction_word} from {start_price} to {final_price} on MolBhaav")
    description = (f"{arena['boss_name']} slammed the shutter on me in {arena['arena_label']}."
                   if row["status"] == "walked_out" else f"Hear the boss's reaction and try to beat this {arena['arena_label']} deal.")
    safe_title, safe_description = html.escape(title, quote=True), html.escape(description, quote=True)
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{safe_title}</title>
<meta name="description" content="{safe_description}"><meta property="og:title" content="{safe_title}"><meta property="og:description" content="{safe_description}"><meta property="og:type" content="website"><meta name="twitter:card" content="summary">
<link rel="icon" href="data:,"><link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="/static/styles.css?v=5"><script defer src="/static/receipt_canvas.js?v=5"></script><script defer src="/static/app.js?v=5"></script></head>
<body data-deal-id="{html.escape(deal_id, quote=True)}"><div class="phone-shell share-shell"><header class="topbar"><a class="wordmark" href="/">Mol<span>Bhaav</span></a><a class="nav-pill" href="/">Enter the arena ↗</a></header><main id="receipt-root" class="receipt-root" aria-live="polite"><p class="eyebrow">THERMAL DEAL RECEIPT</p><h1>{safe_title}</h1><p>Loading your receipt…</p></main></div><div class="toast" id="toast" role="status" aria-live="polite"></div></body></html>''')


def _rotate_daily():
    yesterday = (now_ist().date() - timedelta(days=1)).isoformat()
    archived = db.archive_day(yesterday, list(ARENA_IDS), utc_timestamp())
    audio_cutoff = (datetime.now(UTC) - timedelta(hours=2)).isoformat(timespec="seconds")
    db.prune_stale_session_audio(audio_cutoff)
    return {"status": "ok", "archived_date": yesterday, "new_archives": archived, "idempotent": archived == 0}


def _require_schedule_auth(request: Request) -> None:
    expected = os.environ.get("CRON_SECRET")
    if not expected or request.headers.get("authorization") != f"Bearer {expected}":
        raise HTTPException(401, "Unauthorized schedule request.")


@app.get("/api/internal/rotate-daily")
def rotate_daily_scheduled(request: Request):
    _require_schedule_auth(request)
    return _rotate_daily()


@app.post("/api/internal/rotate-daily")
def rotate_daily_manual(request: Request):
    _require_schedule_auth(request)
    return _rotate_daily()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port(), workers=1, reload=False, log_level="info")
