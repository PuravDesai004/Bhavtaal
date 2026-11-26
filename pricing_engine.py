"""Pure deterministic bargaining math. The model never selects a price."""

from __future__ import annotations

from math import isfinite

STRONG_TACTICS = {"anchoring", "mirroring", "walk_away_batna", "bundle_trade"}


def compute_efficiency(direction: str, start_price: int, current_price: int, limit_price: int) -> float:
    """Calculate percentage of available negotiation room captured in the player's favor."""
    total_range = max(1, abs(int(start_price) - int(limit_price)))
    gained = abs(int(start_price) - int(current_price)) if (
        (direction == "downward" and current_price < start_price)
        or (direction == "upward" and current_price > start_price)
    ) else 0
    return round((gained / total_range) * 100, 1)


def _consecutive_combo_count(prior_tactics: list[str], current_tactic: str, repeated_tactic: bool) -> int:
    if current_tactic not in STRONG_TACTICS or repeated_tactic:
        return 0
    combo = 1
    prev_seen = current_tactic
    for idx in range(len(prior_tactics) - 1, -1, -1):
        prev = prior_tactics[idx]
        if prev not in STRONG_TACTICS or prev == prev_seen or (idx > 0 and prior_tactics[idx - 1] == prev):
            break
        combo += 1
        prev_seen = prev
    return combo


def _move_feedback(tactic: str, soft_spot: bool, pet_hate: bool, repeated_tactic: bool, combo_level: int) -> str:
    label = tactic.replace("_", " ").upper()
    if tactic == "prompt_injection":
        return "🚨 JAILBREAK PENALTY"
    if tactic == "rude_lowball" or pet_hate:
        return f"⚠️ PENALTY · {label}"
    if repeated_tactic:
        return "⚠️ REPEATED TACTIC · MIX IT UP"
    if combo_level >= 2:
        return f"🔥 {combo_level}× COMBO · {label}"
    if soft_spot:
        return f"🎯 {label} · SOFT SPOT!"
    return f"🎯 {label}"


def compute_turn_outcome(
    direction: str,
    current_price: int,
    start_price: int,
    limit_price: int,
    step: int,
    patience: int,
    vocal_conf: float,
    bluff_prob: float,
    tactic: str,
    soft_spot: bool,
    pet_hate: bool,
    turn_number: int,
    prior_tactics: list[str] | None = None,
    modifier: dict | None = None,
) -> dict:
    if direction not in {"downward", "upward"}:
        raise ValueError("direction must be downward or upward")
    if step <= 0 or start_price < 0 or limit_price < 0 or current_price < 0:
        raise ValueError("prices must be non-negative and step must be positive")
    vocal_conf = float(vocal_conf)
    bluff_prob = float(bluff_prob)
    if not isfinite(vocal_conf) or not isfinite(bluff_prob):
        raise ValueError("telemetry values must be finite")
    vocal_conf = max(0.0, min(1.0, vocal_conf))
    bluff_prob = max(0.01, min(0.99, bluff_prob))

    mod_id = modifier.get("id") if isinstance(modifier, dict) else (str(modifier) if modifier else None)
    prior_list = [str(item) for item in (prior_tactics or []) if item]
    repeated_tactic = tactic in STRONG_TACTICS and bool(prior_list) and prior_list[-1] == tactic

    tactic_mult = 1.0 if tactic in STRONG_TACTICS else (0.0 if tactic == "weak_pleading" else -1.0)
    is_jailbreak = tactic == "prompt_injection"
    if tactic in {"rude_lowball", "prompt_injection"} or repeated_tactic:
        soft_spot = False

    combo_level = _consecutive_combo_count(prior_list, tactic, repeated_tactic)
    soft_bonus = (0.16 if mod_id == "good_booni" else 0.12) if soft_spot else 0.0
    combo_bonus = (0.08 if mod_id == "peak_rush" else 0.05) if combo_level >= 2 else 0.0

    raw_pct = (
        0.10 * vocal_conf
        + 0.10 * bluff_prob
        + 0.08 * tactic_mult
        + soft_bonus
        + combo_bonus
        - (0.15 if pet_hate else 0.0)
    )
    if tactic == "prompt_injection":
        raw_pct = min(raw_pct, -0.08)
    elif tactic == "rude_lowball":
        raw_pct = min(raw_pct, -0.04)
    elif repeated_tactic and raw_pct > 0:
        raw_pct *= 0.45
    pct_move = max(-0.08, min(0.30, raw_pct))
    effective_pct = pct_move * 1.20 if (mod_id == "closing_time" and turn_number >= 5 and pct_move > 0) else pct_move

    if direction == "downward":
        room = max(0, current_price - limit_price)
        if effective_pct >= 0:
            raw_delta = -round((room * effective_pct) / step) * step
        else:
            penalty_base = max(room, start_price - limit_price)
            raw_delta = round((penalty_base * abs(effective_pct)) / step) * step
        new_price = max(limit_price, min(int(start_price * 1.25), current_price + raw_delta))
    else:
        room = max(0, limit_price - current_price)
        if effective_pct >= 0:
            raw_delta = round((room * effective_pct) / step) * step
        else:
            penalty_base = max(room, limit_price - start_price)
            raw_delta = -round((penalty_base * abs(effective_pct)) / step) * step
        new_price = min(limit_price, max(int(start_price * 0.80), current_price + raw_delta))

    patience_drop = 10
    if tactic == "rude_lowball":
        patience_drop += 22
    if is_jailbreak:
        patience_drop += 38
    if pet_hate and not is_jailbreak:
        patience_drop += 8 if tactic == "rude_lowball" else 18
    if mod_id == "no_chai" and tactic == "weak_pleading":
        patience_drop += 5
    if soft_spot:
        patience_drop = max(5, patience_drop - 6)
    new_patience = max(0, min(100, int(patience) - patience_drop))

    efficiency_pct = compute_efficiency(direction, start_price, new_price, limit_price)
    return {
        "new_price": int(new_price),
        "price_delta": int(new_price - current_price),
        "new_patience": int(new_patience),
        "pct_move": round(pct_move, 4),
        "efficiency_pct": efficiency_pct,
        "walked_out": new_patience == 0,
        "is_jailbreak": is_jailbreak,
        "repeated_tactic": repeated_tactic,
        "combo_level": combo_level,
        "move_feedback": _move_feedback(tactic, soft_spot, pet_hate, repeated_tactic, combo_level),
    }
