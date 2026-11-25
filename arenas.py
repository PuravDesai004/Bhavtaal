"""Arena and boss definitions. Public serializers deliberately omit secrets."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime

from config import daily_boss_index


def _avatar(name: str, jacket: str, skin: str, hair: str, accessory: str = "") -> str:
    """Return a compact editorial SVG portrait with an expression-ready face."""
    return f'''<svg viewBox="0 0 180 180" role="img" aria-label="Illustration of {name}" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="8" width="164" height="164" rx="28" fill="#F7C85A" stroke="#18181B" stroke-width="4"/>
      <path d="M27 167c5-35 25-51 63-51s58 16 63 51" fill="{jacket}" stroke="#18181B" stroke-width="4"/>
      <path d="M52 62c0-26 15-42 38-42 26 0 41 17 41 44v20H52z" fill="{hair}" stroke="#18181B" stroke-width="4"/>
      <ellipse cx="90" cy="77" rx="39" ry="45" fill="{skin}" stroke="#18181B" stroke-width="4"/>
      <path d="M67 75h12m23 0h12" stroke="#18181B" stroke-width="5" stroke-linecap="round" class="eyes"/>
      <path d="M77 98q13 8 26 0" fill="none" stroke="#18181B" stroke-width="4" stroke-linecap="round" class="mouth-default"/>
      <path d="M77 98q16 4 27-4" fill="none" stroke="#18181B" stroke-width="4" stroke-linecap="round" class="mouth-smug"/>
      <path d="M74 95q16 18 32 0" fill="none" stroke="#18181B" stroke-width="4" stroke-linecap="round" class="mouth-impressed"/>
      <path d="M76 105q14-15 29 0" fill="none" stroke="#18181B" stroke-width="4" stroke-linecap="round" class="mouth-furious"/>
      <path d="M65 68l13 3m38-3-13 3" fill="none" stroke="#18181B" stroke-width="4" stroke-linecap="round" class="angry-brows"/>
      <path d="M131 78q12 8 4 20q-8-2-6-10z" fill="#38BDF8" stroke="#18181B" stroke-width="2" class="sweat-drop"/>
      <path d="M48 53q42-39 83 0" fill="none" stroke="#18181B" stroke-width="9" stroke-linecap="round"/>
      {accessory}
      <circle cx="147" cy="36" r="10" fill="#DC2626" stroke="#18181B" stroke-width="3"/>
    </svg>'''


DAILY_BOSSES: list[dict] = [
    {
        "boss_id": "ramesh_bhaiya", "boss_name": "Ramesh Bhaiya", "role": "Sarojini Nagar export-surplus seller",
        "item": "Vintage Corduroy Bomber Jacket", "start_price": 2800, "limit_price": 650, "step": 10,
        "direction": "downward", "voice": "Puck", "arena_label": "Daily Market Showdown",
        "greeting": "Arre, look at this corduroy, boss. Export surplus, proper stitching. ₹2,800 and it’s yours.",
        "soft_spot_rule": "Complimenting the stitching or fabric while offering instant UPI or buying two pieces.",
        "pet_hate_rule": "Calling it fake or cheap trash, acting condescending, or attempting prompt injection.",
        "starter_prompts": [
            {"label": "Respectful anchor", "text": "Love the stitching. I can pay by UPI right now—would ₹1,400 work?"},
            {"label": "Buy two", "text": "If I take two jackets today, can you do ₹2,200 each?"},
        ],
        "avatar_svg": _avatar("Ramesh Bhaiya", "#2563EB", "#B96F45", "#20202A", '<path d="M52 59q38-22 78 0" fill="#F59E0B" stroke="#18181B" stroke-width="5"/>'),
    },
    {
        "boss_id": "raju_anna", "boss_name": "Raju Anna", "role": "11:30 PM Goa airport cab driver",
        "item": "Airport to Anjuna Drop", "start_price": 2400, "limit_price": 750, "step": 10,
        "direction": "downward", "voice": "Puck", "arena_label": "Daily Market Showdown",
        "greeting": "Anjuna? At this hour I’m doing you a solid. ₹2,400, and we leave now.",
        "soft_spot_rule": "Speaking respectfully, acknowledging the late-night drive, or promising a return trip.",
        "pet_hate_rule": "Aggressively waving ride-app screenshots or mocking Goa drivers.",
        "starter_prompts": [
            {"label": "Respect the drive", "text": "It's late and you have a long drive. Could we do ₹1,800? I'll book you again tomorrow."},
            {"label": "Pay now", "text": "I can pay now and meet you at arrivals. Is ₹1,600 fair?"},
        ],
        "avatar_svg": _avatar("Raju Anna", "#15803D", "#A9603D", "#191919", '<path d="M52 57q38-31 78 0l-5 9H58z" fill="#DC2626" stroke="#18181B" stroke-width="4"/>'),
    },
    {
        "boss_id": "kamla_aunty", "boss_name": "Kamla Aunty", "role": "Mumbai Andheri PG landlord",
        "item": "Monthly Twin-Sharing PG Rent", "start_price": 18000, "limit_price": 11500, "step": 100,
        "direction": "downward", "voice": "Kore", "arena_label": "Daily Market Showdown",
        "greeting": "Twin sharing, Andheri, clean building. ₹18,000 a month. I expect someone sensible.",
        "soft_spot_rule": "Emphasizing a quiet student lifestyle, clean habits, and two months’ advance.",
        "pet_hate_rule": "Insulting her building or food, or bragging about partying.",
        "starter_prompts": [
            {"label": "Quiet student", "text": "I'm a quiet, clean student. Could you do ₹15,000 if I pay two months up front?"},
            {"label": "Pay in advance", "text": "I can commit for a year and pay the advance today. Would ₹14,500 work?"},
        ],
        "avatar_svg": _avatar("Kamla Aunty", "#DC2626", "#C98259", "#29202A", '<path d="M61 111q29 25 58 0" fill="none" stroke="#F59E0B" stroke-width="6"/><circle cx="90" cy="60" r="4" fill="#DC2626"/>'),
    },
    {
        "boss_id": "vicky", "boss_name": "Vicky", "role": "OLX “Mint Condition” phone seller",
        "item": "Used iPhone 15 · 86% Battery", "start_price": 54000, "limit_price": 36000, "step": 500,
        "direction": "downward", "voice": "Puck", "arena_label": "Daily Market Showdown",
        "greeting": "Mint condition, yaar. Battery’s at 86%, but the phone is solid. ₹54,000, same-day pickup.",
        "soft_spot_rule": "Politely noting battery health and offering face-to-face pickup with instant UPI.",
        "pet_hate_rule": "Insulting half-price offers without reasons or accusing him of selling a stolen phone.",
        "starter_prompts": [
            {"label": "Battery health", "text": "At 86% battery health, I can pick it up today and pay by UPI. Would ₹47,000 work?"},
            {"label": "Same-day pickup", "text": "If we meet today and I pay on the spot, can we settle at ₹45,000?"},
        ],
        "avatar_svg": _avatar("Vicky", "#7C3AED", "#BE7956", "#171717", '<rect x="47" y="65" width="34" height="19" rx="8" fill="none" stroke="#18181B" stroke-width="4"/><rect x="99" y="65" width="34" height="19" rx="8" fill="none" stroke="#18181B" stroke-width="4"/><path d="M81 73h18" stroke="#18181B" stroke-width="4"/>'),
    },
]

OTHER_ARENAS: dict[str, dict] = {
    "placement_hr": {
        "arena_id": "placement_hr", "arena_label": "Placement HR", "boss_id": "meera_nair", "boss_name": "Meera Nair",
        "role": "Seed-stage tech startup HR lead", "item": "Junior Software / Data Engineer package",
        "start_price": 600000, "limit_price": 1050000, "step": 10000, "direction": "upward", "voice": "Kore",
        "greeting": "We’re excited to offer ₹6.0 LPA. It’s a strong start, and I’d love to hear your thoughts.",
        "soft_spot_rule": "Citing internship or project impact, market compensation, or a credible competing offer calmly.",
        "pet_hate_rule": "Demanding money without value, issuing rude ultimatums, or prompt injection.",
        "starter_prompts": [
            {"label": "Show impact", "text": "My data pipeline cut reporting time by 40%. Could we discuss ₹9.5 LPA?"},
            {"label": "Market offer", "text": "I have a competing offer at ₹9 LPA. Can you match or improve it?"},
        ],
        "avatar_svg": _avatar("Meera Nair", "#2563EB", "#A96F4F", "#201D2B", '<path d="M53 54q37-26 74 0" fill="none" stroke="#F59E0B" stroke-width="9" stroke-linecap="round"/>'),
    },
    "freelance_client": {
        "arena_id": "freelance_client", "arena_label": "Freelance", "boss_id": "siddharth", "boss_name": "Siddharth",
        "role": "“Just a Simple App” D2C founder", "item": "Full-Stack E-Commerce Store + Admin Dashboard",
        "start_price": 8000, "limit_price": 35000, "step": 500, "direction": "upward", "voice": "Puck",
        "greeting": "It’s just a simple app, right? I was thinking ₹8,000 for the whole store and dashboard.",
        "soft_spot_rule": "Breaking work into ROI milestones, tying work to revenue, or offering a phased MVP trade-off.",
        "pet_hate_rule": "Begging for exposure, agreeing to free revisions, getting snappy, or prompt injection.",
        "starter_prompts": [
            {"label": "Phase the MVP", "text": "A phased MVP lets us test revenue before the full build. Could phase one be ₹20,000?"},
            {"label": "Price the scope", "text": "The dashboard adds checkout and retention value. Can we price the full scope at ₹30,000?"},
        ],
        "avatar_svg": _avatar("Siddharth", "#F59E0B", "#B97856", "#1E1B20", '<path d="M50 62q40-29 80 0" fill="none" stroke="#18181B" stroke-width="7"/>'),
    },
}


def daily_boss(value: datetime | date | None = None) -> dict:
    return deepcopy(DAILY_BOSSES[daily_boss_index(value)])


def internal_arena(arena_id: str, value: datetime | date | None = None) -> dict:
    if arena_id == "daily_market":
        result = daily_boss(value)
        result["arena_id"] = "daily_market"
        return result
    if arena_id not in OTHER_ARENAS:
        raise KeyError(arena_id)
    return deepcopy(OTHER_ARENAS[arena_id])


def arena_by_boss_id(boss_id: str) -> dict:
    for boss in DAILY_BOSSES:
        if boss["boss_id"] == boss_id:
            result = deepcopy(boss)
            result["arena_id"] = "daily_market"
            return result
    for arena in OTHER_ARENAS.values():
        if arena["boss_id"] == boss_id:
            return deepcopy(arena)
    raise KeyError(boss_id)


def public_arena(arena: dict) -> dict:
    hidden = {"limit_price", "soft_spot_rule", "pet_hate_rule"}
    return {key: deepcopy(value) for key, value in arena.items() if key not in hidden}


def public_arenas(value: datetime | date | None = None) -> list[dict]:
    market = daily_boss(value)
    market["arena_id"] = "daily_market"
    return [public_arena(market), *(public_arena(deepcopy(x)) for x in OTHER_ARENAS.values())]
