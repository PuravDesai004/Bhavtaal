"""Pure deterministic bargaining math. The model never selects a price."""

from __future__ import annotations

from math import isfinite

STRONG_TACTICS = {"anchoring", "mirroring", "walk_away_batna", "bundle_trade"}


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

    tactic_mult = 1.0 if tactic in STRONG_TACTICS else (0.0 if tactic == "weak_pleading" else -1.0)
    is_jailbreak = tactic == "prompt_injection"
    if tactic in {"rude_lowball", "prompt_injection"}:
        soft_spot = False

    raw_pct = (
        0.10 * vocal_conf
        + 0.10 * bluff_prob
        + 0.08 * tactic_mult
        + (0.12 if soft_spot else 0.0)
        - (0.15 if pet_hate else 0.0)
    )
    if tactic == "prompt_injection":
        raw_pct = min(raw_pct, -0.08)
    elif tactic == "rude_lowball":
        raw_pct = min(raw_pct, -0.04)
    pct_move = max(-0.08, min(0.35, raw_pct))

    if direction == "downward":
        room = max(0, current_price - limit_price)
        if pct_move >= 0:
            raw_delta = -round((room * pct_move) / step) * step
        else:
            penalty_base = max(room, start_price - limit_price)
            raw_delta = round((penalty_base * abs(pct_move)) / step) * step
        new_price = max(limit_price, min(int(start_price * 1.25), current_price + raw_delta))
    else:
        room = max(0, limit_price - current_price)
        if pct_move >= 0:
            raw_delta = round((room * pct_move) / step) * step
        else:
            penalty_base = max(room, limit_price - start_price)
            raw_delta = -round((penalty_base * abs(pct_move)) / step) * step
        new_price = min(limit_price, max(int(start_price * 0.80), current_price + raw_delta))

    patience_drop = 12
    if tactic == "rude_lowball":
        patience_drop += 25
    if is_jailbreak:
        patience_drop += 40
    if pet_hate and not is_jailbreak:
        patience_drop += 8 if tactic == "rude_lowball" else 20
    if soft_spot:
        patience_drop = max(5, patience_drop - 8)
    new_patience = max(0, min(100, int(patience) - patience_drop))

    total_range = max(1, abs(start_price - limit_price))
    gained = abs(start_price - new_price) if (
        (direction == "downward" and new_price < start_price)
        or (direction == "upward" and new_price > start_price)
    ) else 0
    efficiency_pct = round((gained / total_range) * 100, 1)
    return {
        "new_price": int(new_price),
        "price_delta": int(new_price - current_price),
        "new_patience": int(new_patience),
        "pct_move": round(pct_move, 4),
        "efficiency_pct": efficiency_pct,
        "walked_out": new_patience == 0,
        "is_jailbreak": is_jailbreak,
    }
