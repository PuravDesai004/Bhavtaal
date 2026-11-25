/* Mobile-first arena state, interactions, receipt sharing and speech fallback. */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = { arenas: [], session: null, arena: null, turns: [], busy: false, ended: false, audioUrl: null, recorder: null, timer: null, muted: false, currentTtsFallback: true, pointerHeld: false, activePointerId: null, recordingToken: 0, playerName: "" };
  const HANDLE_KEY = "molbhaav-player-name";
  const cash = (amount) => {
    const num = Number(amount || 0);
    const sign = num < 0 ? "-" : "";
    return `${sign}₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(Math.abs(num))}`;
  };
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  const stripVoiceTags = (value) => String(value ?? "").replace(/<\/?\s*(?:laugh|sigh|short[\s_-]*pause|gasp)\s*\/?>/gi, "").replace(/ {2,}/g, " ");
  const api = async (path, body) => {
    const response = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((item) => item?.msg || String(item)).join("; ")
        : data.detail;
      throw new Error(detail || "That move did not go through.");
    }
    return data;
  };
  function toast(message) {
    const el = $("toast"); if (!el) return;
    el.textContent = message; el.classList.add("show");
    clearTimeout(toast.timer); toast.timer = setTimeout(() => el.classList.remove("show"), 2600);
  }
  function playText(text) {
    if (state.muted || !window.speechSynthesis || !text) return;
    const clean = stripVoiceTags(text);
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(clean);
    const voices = window.speechSynthesis.getVoices();
    utterance.voice = voices.find((voice) => /en-IN|hi-IN/i.test(voice.lang)) || null;
    utterance.lang = utterance.voice?.lang || "en-IN"; utterance.rate = 1.02;
    window.speechSynthesis.speak(utterance);
  }
  function setAudio(base64, url, text, ttsFallback = false) {
    document.querySelector(".equalizer")?.classList.remove("playing");
    const audio = $("voice-audio");
    audio.pause();
    audio.muted = state.muted;
    window.speechSynthesis?.cancel();
    state.currentTtsFallback = Boolean(ttsFallback);
    $("voice-play").classList.remove("play-blocked");
    if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
    state.audioUrl = null;
    if (url) audio.src = url;
    else if (base64) {
      try {
        const raw = atob(base64); const bytes = new Uint8Array(raw.length);
        for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
        state.audioUrl = URL.createObjectURL(new Blob([bytes], { type: "audio/wav" })); audio.src = state.audioUrl;
      } catch (_) { audio.removeAttribute("src"); audio.load(); state.currentTtsFallback = true; }
    } else { audio.removeAttribute("src"); audio.load(); }
    $("voice-play").disabled = !base64 && !url && !text;
    $("voice-caption").textContent = audio.getAttribute("src") ? "BOSS AUDIO" : "SPEAK REPLY";
    audio.onplay = () => document.querySelector(".equalizer")?.classList.add("playing");
    audio.onpause = () => document.querySelector(".equalizer")?.classList.remove("playing");
    audio.onended = () => document.querySelector(".equalizer")?.classList.remove("playing");
    audio.onerror = () => {
      document.querySelector(".equalizer")?.classList.remove("playing");
      if (audio.getAttribute("src")) {
        audio.removeAttribute("src");
        audio.load();
        state.currentTtsFallback = true;
        $("voice-caption").textContent = "SPEAK REPLY";
      }
    };
  }
  async function playCurrentVoice() {
    if (state.muted) { toast("Audio is muted — tap the speaker icon to hear the boss."); return; }
    const audio = $("voice-audio");
    if (audio.getAttribute("src")) {
      try { await audio.play(); $("voice-play").classList.remove("play-blocked"); }
      catch (error) {
        if (error?.name === "NotAllowedError") $("voice-play").classList.add("play-blocked");
        else {
          audio.removeAttribute("src");
          audio.load();
          state.currentTtsFallback = true;
          $("voice-caption").textContent = "SPEAK REPLY";
          playText(stripVoiceTags($("boss-line").textContent));
        }
      }
    } else if (state.currentTtsFallback && !state.muted) playText(stripVoiceTags($("boss-line").textContent));
  }
  function updateArenaCard(arena, greeting) {
    state.arena = arena;
    $("arena-kicker").textContent = arena.arena_label === "Daily Market Showdown" ? "TODAY'S SHOWDOWN" : arena.arena_label.toUpperCase();
    $("price-label").textContent = arena.direction === "downward" ? "ASKING" : "OPENING OFFER";
    $("boss-name").textContent = arena.boss_name;
    $("boss-role").textContent = arena.role.toUpperCase();
    $("boss-line").textContent = greeting || arena.greeting || "All right, make your move.";
    $("boss-portrait").innerHTML = arena.avatar_svg || "";
    $("price-value").textContent = cash(arena.start_price);
    $("price-value").classList.toggle("compact", Number(arena.start_price) >= 100000);
    $("price-delta").textContent = "READY"; $("price-delta").className = "delta-pill";
    $("turn-count").textContent = "TURN 1 / 4";
    $("confidence-value").textContent = "—"; $("bluff-value").textContent = "—";
    $("confidence-bar").style.width = "0%"; $("bluff-bar").style.width = "0%";
    $("patience-value").textContent = "100%"; $("patience-bar").style.width = "100%";
    $("transcript-count").textContent = "0 MOVES";
    $("transcript-list").innerHTML = '<p class="empty-transcript">Your first move goes here. Keep it respectful, specific, and a little clever.</p>';
    $("coach-tip").textContent = "Make one clear ask. A reason beats a random lowball.";
    state.ended = false;
    document.querySelector(".patience-meter").classList.remove("low");
    $("mic-button").disabled = false; $("type-toggle").disabled = false; $("typed-move").disabled = false;
    $("type-form").querySelector('button[type="submit"]').disabled = false; $("sample-audio").disabled = false;
    $("lock-deal").disabled = true; $("lock-deal").classList.remove("ready", "receipt-ready");
    $("lock-deal").querySelector(".lock-stamp").textContent = "LOCK";
    $("lock-deal").querySelector("small").textContent = "DEAL";
    $("lock-deal").setAttribute("aria-label", "Lock deal");
    document.querySelector(".boss-card").dataset.mood = "smug";
    const promptButtons = (arena.starter_prompts || []).slice(0, 2).map((prompt, index) =>
      `<button class="prompt-chip ${index === 1 ? "cheeky" : ""}" data-prompt="${escapeHtml(prompt.text)}">${escapeHtml(prompt.label)}</button>`
    ).join("");
    $("quick-prompts").innerHTML = `<span class="quick-label">TRY A MOVE</span>${promptButtons}`;
    $("quick-prompts").hidden = false;
    setAudio(null, null, greeting || arena.greeting, true);
  }

  function currentPlayerName() {
    return $("player-handle")?.value.trim().slice(0, 24) || state.playerName || null;
  }

  function initializePlayerHandle() {
    const input = $("player-handle");
    if (!input) return;
    const generated = () => {
      const handles = ["ChaiChampion", "DealDost", "JugaadKing", "BargainBoss"];
      return `${handles[Math.floor(Math.random() * handles.length)]}_${Math.floor(10 + Math.random() * 90)}`;
    };
    try { state.playerName = localStorage.getItem(HANDLE_KEY) || ""; } catch (_) { state.playerName = ""; }
    state.playerName = state.playerName.trim().slice(0, 24) || generated();
    input.value = state.playerName;
    try { localStorage.setItem(HANDLE_KEY, state.playerName); } catch (_) { /* storage may be disabled */ }
    input.addEventListener("input", () => {
      const value = input.value.trim().replace(/\s+/g, " ").slice(0, 24);
      state.playerName = value || state.playerName;
      try { localStorage.setItem(HANDLE_KEY, state.playerName); } catch (_) { /* storage may be disabled */ }
    });
  }
  async function startArena(arenaId) {
    if (state.busy) return;
    if (state.pointerHeld || state.recorder?.recording || state.recorder?.starting) {
      state.pointerHeld = false; state.activePointerId = null; state.recordingToken += 1;
      clearInterval(state.timer); $("mic-button").classList.remove("recording"); $("record-time").textContent = "HOLD";
      await state.recorder?.cleanup();
    }
    state.busy = true;
    try {
      const session = await api("/api/session/start", { arena_id: arenaId, player_name: currentPlayerName() });
      state.session = session; state.turns = [];
      updateArenaCard(session.arena, session.opening_greeting);
      document.querySelectorAll(".arena-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.arena === arenaId));
      $("typed-move").value = ""; $("type-panel").hidden = true;
      $("dock-hint").textContent = "HOLD TO SPEAK · 1.5–10 SEC";
      if (state.arena.arena_id === "daily_market") {
        const date = new Date();
        $("arena-kicker").textContent = `TODAY'S SHOWDOWN · ${new Intl.DateTimeFormat("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short" }).format(date).toUpperCase()}`;
      }
    } catch (error) { toast(error.message); }
    finally { state.busy = false; }
  }
  function addTurn(result, originalText) {
    state.turns.push(result);
    const list = $("transcript-list");
    if (state.turns.length === 1) list.innerHTML = "";
    const row = document.createElement("article"); row.className = "transcript-item";
    const tag = document.createElement("span"); tag.className = "turn-tag"; tag.textContent = `T${result.turn}`;
    const copy = document.createElement("div");
    const you = document.createElement("p"); you.className = "you-line"; you.textContent = `YOU · ${result.player_transcript || originalText || "Voice move"}`;
    const boss = document.createElement("p"); boss.className = "boss-line"; boss.textContent = `${state.arena.boss_name} · ${stripVoiceTags(result.reply_text)}`;
    copy.append(you, boss); row.append(tag, copy); list.append(row); list.scrollTop = list.scrollHeight;
    $("transcript-count").textContent = `${state.turns.length} ${state.turns.length === 1 ? "MOVE" : "MOVES"}`;
  }
  async function submitMove({ text, audio_b64 }) {
    if (state.ended) return;
    if (!state.session || state.busy) return;
    state.busy = true; $("mic-button").classList.add("processing");
    $("dock-hint").textContent = "READING THE ROOM…";
    try {
      const result = await api("/api/turn", { session_id: state.session.session_id, text: text || null, audio_b64: audio_b64 || null });
      addTurn(result, text);
      $("price-value").textContent = cash(result.current_price);
      $("price-value").classList.toggle("compact", Number(result.current_price) >= 100000);
      const goodDirection = state.arena.direction === "downward" ? result.price_delta < 0 : result.price_delta > 0;
      const delta = result.price_delta;
      const deltaEl = $("price-delta");
      deltaEl.textContent = `${delta > 0 ? "+" : delta < 0 ? "−" : ""}${cash(Math.abs(delta)).replace("₹", "₹")}`;
      deltaEl.className = `delta-pill ${goodDirection ? "good" : delta === 0 ? "" : "bad"}`;
      $("turn-count").textContent = result.ended
        ? `FINAL · TURN ${result.turn} / 4`
        : `TURN ${Math.min(result.turn + 1, 4)} / 4`;
      $("confidence-value").textContent = `${result.vocal_confidence}%`; $("confidence-bar").style.width = `${result.vocal_confidence}%`;
      $("bluff-value").textContent = `${result.bluff_credibility}%`; $("bluff-bar").style.width = `${result.bluff_credibility}%`;
      $("patience-value").textContent = `${result.opponent_patience}%`; $("patience-bar").style.width = `${result.opponent_patience}%`;
      document.querySelector(".patience-meter").classList.toggle("low", result.opponent_patience < 30);
      document.querySelector(".boss-card").dataset.mood = result.boss_mood;
      $("boss-line").textContent = stripVoiceTags(result.reply_text);
      $("coach-tip").textContent = result.coach_tip;
      setAudio(result.audio_b64, null, result.reply_text, result.tts_fallback);
      const lockButton = $("lock-deal");
      lockButton.disabled = false; lockButton.classList.toggle("ready", goodDirection);
      $("quick-prompts").hidden = true;
      if (result.ended) {
        state.ended = true;
        $("mic-button").disabled = true; $("type-toggle").disabled = true; $("typed-move").disabled = true;
        $("type-form").querySelector('button[type="submit"]').disabled = true;
        $("sample-audio").disabled = true; $("type-panel").hidden = true;
        lockButton.querySelector(".lock-stamp").textContent = "VIEW";
        lockButton.querySelector("small").textContent = "RECEIPT →";
        lockButton.setAttribute("aria-label", "View receipt");
        lockButton.classList.add("receipt-ready");
        $("dock-hint").textContent = result.walked_out ? "SHUTTER DOWN · FINAL REACTION" : "FINAL MOVE · HEAR THE REACTION";
      } else $("dock-hint").textContent = "HOLD TO SPEAK · 1.5–10 SEC";
      if (result.walked_out || result.tactic === "prompt_injection") window.playBazaarSound?.("buzzer");
      else if (goodDirection) window.playBazaarSound?.("price");
      if (!state.muted) await playCurrentVoice();
    } catch (error) {
      toast(error.message);
      $("dock-hint").textContent = "HOLD TO SPEAK · 1.5–10 SEC";
    } finally {
      state.busy = false; $("mic-button").classList.remove("processing");
      if (!$("type-panel").hidden) $("typed-move").focus();
    }
  }
  async function finishDeal() {
    if (!state.session || state.busy || !state.turns.length) return;
    const button = $("lock-deal");
    state.busy = true; button.disabled = true;
    try {
      const deal = await api("/api/session/finish", { session_id: state.session.session_id, player_name: currentPlayerName() });
      window.playBazaarSound?.("lock");
      window.location.assign(`/deal/${encodeURIComponent(deal.deal_id)}`);
    } catch (error) {
      toast(error.message); button.disabled = false;
    } finally { state.busy = false; }
  }
  async function openLeaderboard(arenaId = "daily_market") {
    $("leaderboard-panel").hidden = false;
    $("leaderboard-eyebrow").textContent = arenaId === "daily_market" ? "TODAY'S TOP HAGGLERS" : "ALL-TIME TOP HAGGLERS";
    document.querySelectorAll("[data-board]").forEach((button) => button.classList.toggle("selected", button.dataset.board === arenaId));
    const list = $("leaderboard-list");
    list.innerHTML = arenaId === "daily_market" ? "<li>Counting today's wins…</li>" : "<li>Counting all-time wins…</li>";
    try {
      const result = await api(`/api/leaderboard?arena_id=${encodeURIComponent(arenaId)}`);
      if (!result.entries.length) { list.innerHTML = "<li>No receipts yet. Set the first number.</li>"; return; }
      list.innerHTML = result.entries.map((entry) => `<li><span class="leader-rank">#${entry.rank}</span><span><span class="leader-player">${escapeHtml(entry.player_name)}</span><br><small>${escapeHtml(entry.boss_name)}</small></span><span class="leader-price">${cash(entry.final_price)}</span></li>`).join("");
    } catch (error) { list.innerHTML = `<li>${escapeHtml(error.message)}</li>`; }
  }
  async function sampleMood() {
    if (state.muted) { toast("Audio is muted — tap the speaker icon to hear the boss."); return; }
    if (!state.arena || state.busy) return;
    const button = $("sample-audio"); button.disabled = true;
    try {
      const result = await api("/api/session/sample-audio", { arena_id: state.arena.arena_id });
      setAudio(result.audio_b64, null, result.fallback_text, result.tts_fallback);
      await playCurrentVoice();
    } catch (error) { toast(error.message); }
    finally { button.disabled = false; }
  }
  async function stopRecording() {
    state.pointerHeld = false; state.activePointerId = null; state.recordingToken += 1;
    if (!state.recorder?.recording) return;
    clearInterval(state.timer); $("mic-button").classList.remove("recording");
    $("record-time").textContent = "HOLD"; $("dock-hint").textContent = "ENCODING CLEAN WAV…";
    try {
      const result = await state.recorder.stop();
      if (!result) { toast("Hold for at least 1.5 seconds to make your case."); $("dock-hint").textContent = "HOLD TO SPEAK · 1.5–10 SEC"; return; }
      const audio_b64 = result.audio_b64;
      await submitMove({ audio_b64 });
      // The browser drops the player's WAV after the request; it is never written to storage.
    } catch (error) { toast(error.message || "Microphone recording stopped."); $("dock-hint").textContent = "HOLD TO SPEAK · 1.5–10 SEC"; }
  }
  async function startRecording(event, token = state.recordingToken) {
    if (event) { event.preventDefault(); }
    if (state.busy || !state.session || !state.recorder) return;
    try {
      const started = await state.recorder.start();
      if (!started) return;
      if (!state.pointerHeld || token !== state.recordingToken) {
        await state.recorder.cleanup();
        return;
      }
      $("mic-button").classList.add("recording"); $("dock-hint").textContent = "RECORDING · RELEASE TO SEND";
      state.timer = setInterval(() => {
        const elapsed = Math.min(10, (performance.now() - state.recorder.startedAt) / 1000);
        $("record-time").textContent = `0:${String(Math.floor(elapsed)).padStart(2, "0")}`;
      }, 100);
    } catch (error) {
      const isDeviceError = error && ["NotAllowedError", "PermissionDeniedError", "NotFoundError", "NotReadableError"].includes(error.name);
      if (isDeviceError || (state.pointerHeld && token === state.recordingToken)) {
        state.pointerHeld = false; state.activePointerId = null;
        toast(error?.message || "Allow microphone access to speak.");
      }
    }
  }
  async function initializeArena() {
    try {
      const payload = await api("/api/arenas"); state.arenas = payload.arenas;
      await startArena("daily_market");
    } catch (error) { toast(error.message); }
  }
  function initReceipt(dealId) {
    api(`/api/deal/${encodeURIComponent(dealId)}`).then((deal) => {
      const root = $("receipt-root");
      const walkedOut = deal.status === "walked_out";
      const upward = deal.direction === "upward";
      const gain = Number(deal.savings_or_gain ?? 0);
      const penalty = !walkedOut && gain < 0;
      const neutral = !walkedOut && gain === 0;
      const title = walkedOut
        ? "Shutter slammed. No deal."
        : penalty
          ? (upward ? "Offer slipped. Tough room." : "Price jumped. Tough room.")
          : neutral
            ? "Locked at opening price."
            : (upward ? "Offer raised. Respect earned." : "Deal locked. Shutter rattled.");
      const movementLabel = walkedOut
        ? "NO DEAL"
        : penalty
          ? (upward ? `DROPPED ${cash(Math.abs(gain))}` : `PENALTY +${cash(Math.abs(gain))}`)
          : neutral ? "OPENING PRICE" : `${upward ? "GAINED" : "SAVED"} ${cash(gain)}`;
      const movementClass = `receipt-savings${penalty || walkedOut ? " penalty" : neutral ? " neutral" : ""}`;
      const openingLabel = upward ? "OPENING OFFER" : "OPENING ASK";
      const arrowLabel = walkedOut
        ? "✕ &nbsp; SHUTTER DOWN &nbsp; ✕"
        : penalty
          ? (upward ? "↓ &nbsp; PENALTY &nbsp; ↓" : "↑ &nbsp; PENALTY &nbsp; ↑")
          : neutral
            ? "→ &nbsp; LOCKED AT &nbsp; →"
            : (upward ? "↑ &nbsp; LOCKED AT &nbsp; ↑" : "↓ &nbsp; LOCKED AT &nbsp; ↓");
      const tactics = (deal.tactics_summary || []).map((item) => `<li><b>${escapeHtml(item.tag)}</b> · ${escapeHtml(item.verdict)} — ${escapeHtml(item.note)}</li>`).join("");
      const badges = (deal.badges || []).map((item) => `<span class="prompt-chip">${escapeHtml(item)}</span>`).join(" ");
      const audio = deal.audio_url ? `<audio class="share-audio" controls preload="none" src="${escapeHtml(deal.audio_url)}"></audio>` : '<p class="receipt-coach">Audio reaction is unavailable for this receipt.</p>';
      const percentile = Math.max(0, Math.min(100, Number(deal.percentile ?? 0)));
      const rank = Number(deal.rank ?? 0);
      const rankMarkup = walkedOut
        ? '<p class="receipt-rank walkout">WALKOUT — NO RANK</p>'
        : rank <= 0
          ? '<p class="receipt-rank">UNRANKED</p>'
          : `<p class="receipt-rank">RANK #${rank}</p><p class="receipt-rank-caption">TOP ${Math.max(1, Math.round(100 - percentile))}% OF ${deal.arena_id === "daily_market" ? "TODAY'S" : "ALL-TIME"} HAGGLERS</p>`;
      root.innerHTML = `<p class="eyebrow">THERMAL DEAL RECEIPT</p><h1>${escapeHtml(title)}</h1>
        <article class="receipt-card" id="receipt-card"><div class="receipt-brand">Mol<span>Bhaav</span></div><hr class="receipt-rule"><div class="receipt-meta"><span>${escapeHtml(deal.arena_label)}</span><span>${escapeHtml(deal.date_ist)}</span></div>
        <h2 class="receipt-boss">${escapeHtml(deal.boss.boss_name)}</h2><p class="receipt-item">${escapeHtml(deal.boss.item)}</p><p class="receipt-price-label">${openingLabel}</p><div class="receipt-price">${cash(deal.starting_price)}</div><div class="receipt-arrow${upward && !neutral ? " upward" : ""}${penalty || walkedOut ? " penalty" : ""}${neutral ? " neutral" : ""}">${arrowLabel}</div><div class="receipt-price">${cash(deal.final_price)}</div>
        <div class="${movementClass}">${movementLabel}</div>${rankMarkup}<p class="receipt-dots">· · · · · · · · · · · · · · · · · · · ·</p><p class="receipt-item">${escapeHtml(deal.player_name)} · ${Number(deal.efficiency_pct).toFixed(0)}% efficiency</p></article>
        <div class="receipt-actions"><button class="primary" id="share-deal">CHALLENGE A FRIEND ↗</button><button id="download-receipt">SAVE 9:16 RECEIPT</button></div>
        <section class="receipt-debrief"><h2>What moved the room</h2><p class="receipt-coach">Secret ${upward ? "ceiling" : "floor"}: <b>${cash(deal.secret_limit_price)}</b> · ${cash(deal.left_on_table)} left on the table</p><p>${badges}</p><ul>${tactics}</ul><p><b>Missed opportunity</b><br>${escapeHtml(deal.missed_opportunity)}</p><p class="receipt-coach"><b>One killer line you could have used</b><br>“${escapeHtml(deal.better_line)}”</p></section>
        ${audio}<a class="cta-wide" href="/">TRY TO BEAT THIS DEAL →</a>`;
      $("share-deal").addEventListener("click", async () => {
        const shareUrl = new URL(`/deal/${deal.deal_id}`, window.location.origin).href;
        const message = walkedOut
          ? `I walked away from ${deal.boss.boss_name} on MolBhaav. The shutter came down at ${cash(deal.final_price)}. Think you can do better?`
          : `I got ${cash(deal.final_price)} with ${deal.boss.boss_name} on MolBhaav. Think you can beat my deal?`;
        try {
          if (navigator.share) await navigator.share({ title: walkedOut ? "I walked away on MolBhaav" : "Beat my MolBhaav deal", text: message, url: shareUrl });
          else { await navigator.clipboard.writeText(`${message} ${shareUrl}`); toast("Challenge copied. Send it to your bargaining rival."); }
        } catch (error) { if (error.name !== "AbortError") { try { await navigator.clipboard.writeText(`${message} ${shareUrl}`); toast("Challenge copied to clipboard."); } catch (_) { toast(shareUrl); } } }
      });
      $("download-receipt").addEventListener("click", () => window.ReceiptCanvas?.download(deal));
    }).catch((error) => { $("receipt-root").innerHTML = `<p class="eyebrow">RECEIPT NOT FOUND</p><h1>${escapeHtml(error.message)}</h1><a class="cta-wide" href="/">START A NEW SHOWDOWN</a>`; });
  }
  function bind() {
    state.recorder = new window.MolAudioRecorder($("wave-ring"), () => {});
    initializePlayerHandle();
    document.querySelectorAll(".arena-tab").forEach((tab) => tab.addEventListener("click", () => startArena(tab.dataset.arena)));
    $("quick-prompts").addEventListener("click", (event) => {
      const chip = event.target.closest(".prompt-chip[data-prompt]");
      if (!chip || state.ended) return;
      $("type-panel").hidden = false; $("typed-move").value = chip.dataset.prompt; $("typed-move").focus();
    });
    $("sample-audio").addEventListener("click", sampleMood);
    $("voice-play").addEventListener("click", playCurrentVoice);
    $("type-toggle").addEventListener("click", () => { $("type-panel").hidden = !$("type-panel").hidden; if (!$("type-panel").hidden) $("typed-move").focus(); });
    $("type-form").addEventListener("submit", (event) => { event.preventDefault(); const input = $("typed-move"); const text = input.value.trim(); if (!text) return; input.value = ""; submitMove({ text }); });
    $("mic-button").addEventListener("pointerdown", (event) => {
      if (event.currentTarget.disabled) return;
      if (state.busy || state.pointerHeld || state.recorder?.recording || state.recorder?.starting) return;
      const target = event.currentTarget; const pointerId = event.pointerId;
      state.pointerHeld = true;
      state.activePointerId = pointerId;
      const token = ++state.recordingToken;
      try { target.setPointerCapture(pointerId); } catch (_) { /* capture may be unsupported */ }
      startRecording(event, token);
    });
    ["pointerup", "pointercancel", "lostpointercapture"].forEach((name) => $("mic-button").addEventListener(name, (event) => {
      if (state.activePointerId !== null && event.pointerId !== state.activePointerId) return;
      stopRecording();
    }));
    window.addEventListener("molbhaav-recording-limit", stopRecording);
    $("lock-deal").addEventListener("click", finishDeal);
    $("leaderboard-open").addEventListener("click", () => openLeaderboard("daily_market"));
    document.querySelectorAll("[data-board]").forEach((button) => button.addEventListener("click", () => openLeaderboard(button.dataset.board)));
    document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => { $(button.dataset.close).hidden = true; }));
    $("leaderboard-panel").addEventListener("click", (event) => { if (event.target.id === "leaderboard-panel") event.currentTarget.hidden = true; });
    $("mute-toggle").addEventListener("click", (event) => {
      state.muted = !state.muted; window.setBazaarMuted?.(state.muted);
      $("voice-audio").muted = state.muted;
      if (state.muted) { $("voice-audio").pause(); window.speechSynthesis?.cancel(); }
      const audioStatus = state.muted ? "Audio muted." : "Audio on.";
      event.currentTarget.setAttribute("aria-label", audioStatus);
      event.currentTarget.title = audioStatus;
      toast(audioStatus);
    });
  }
  document.addEventListener("DOMContentLoaded", () => {
    const dealId = document.body.dataset.dealId;
    if (dealId) initReceipt(dealId);
    else { bind(); initializeArena(); }
  });
})();
