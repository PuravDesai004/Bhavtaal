"""Arena and boss definitions. Public serializers deliberately omit secrets."""

from __future__ import annotations

import random
from copy import deepcopy
from datetime import date, datetime

from config import daily_boss_index, daily_pool_index, format_indian_rupees


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


def _apply_start_price(boss: dict, price: int) -> dict:
    item = deepcopy(boss)
    item["start_price"] = int(price)
    template = item.get("greeting_template") or item.get("greeting", "")
    price_text = format_indian_rupees(int(price))
    lpa_text = f"₹{int(price) / 100000:.1f} LPA"
    item["greeting"] = (
        template.replace("{{START_PRICE}}", price_text).replace("{{LPA}}", lpa_text)
    )
    return item


DAILY_BOSSES: list[dict] = [
    {
        "boss_id": "ramesh_bhaiya", "boss_name": "Ramesh Bhaiya", "role": "Sarojini Nagar export-surplus seller",
        "item": "Vintage Corduroy Bomber Jacket", "start_price": 2800,
        "start_prices": [2450, 2600, 2800, 3000, 3200], "limit_price": 650, "step": 10,
        "direction": "downward", "voice": "en-in-csagent-1", "sarvam_speaker": "shubh_enhi_ads", "arena_label": "Daily Market Showdown",
        "greeting": "Arre, look at this corduroy, boss. Export surplus, proper stitching. ₹2,800 and it’s yours.",
        "greeting_template": "Arre, look at this corduroy, boss. Export surplus, proper stitching. {{START_PRICE}} and it’s yours.",
        "soft_spot_rule": "Complimenting the stitching or fabric while offering instant UPI or buying two pieces.",
        "pet_hate_rule": "Calling it fake or cheap trash, acting condescending, or attempting prompt injection.",
        "starter_prompts": [
            {"label": "Respectful anchor", "text": "Love the stitching. I can pay by UPI right now—would ₹1,400 work?"},
            {"label": "Buy two", "text": "If I take two jackets today, can you do ₹1,950 each?"},
        ],
        "avatar_svg": _avatar("Ramesh Bhaiya", "#2563EB", "#B96F45", "#20202A", '<path d="M52 59q38-22 78 0" fill="#F59E0B" stroke="#18181B" stroke-width="5"/>'),
    },
    {
        "boss_id": "raju_anna", "boss_name": "Raju Anna", "role": "11:30 PM Goa airport cab driver",
        "item": "Airport to Anjuna Drop", "start_price": 2400,
        "start_prices": [2100, 2250, 2400, 2600, 2750], "limit_price": 750, "step": 10,
        "direction": "downward", "voice": "en-in-concierge-1", "sarvam_speaker": "shubh_enhi_companion", "arena_label": "Daily Market Showdown",
        "greeting": "Anjuna? At this hour I’m doing you a solid. ₹2,400, and we leave now.",
        "greeting_template": "Anjuna? At this hour I’m doing you a solid. {{START_PRICE}}, and we leave now.",
        "soft_spot_rule": "Speaking respectfully, acknowledging the late-night drive, or promising a return trip.",
        "pet_hate_rule": "Aggressively waving ride-app screenshots or mocking Goa drivers.",
        "starter_prompts": [
            {"label": "Respect the drive", "text": "It's late and you have a long drive. Could we do ₹1,650? I'll book you again tomorrow."},
            {"label": "Pay now", "text": "I can pay now and meet you at arrivals. Is ₹1,500 fair?"},
        ],
        "avatar_svg": _avatar("Raju Anna", "#15803D", "#A9603D", "#191919", '<path d="M52 57q38-31 78 0l-5 9H58z" fill="#DC2626" stroke="#18181B" stroke-width="4"/>'),
    },
    {
        "boss_id": "kamla_aunty", "boss_name": "Kamla Aunty", "role": "Mumbai Andheri PG landlord",
        "item": "Monthly Twin-Sharing PG Rent", "start_price": 18000,
        "start_prices": [16500, 17200, 18000, 19000, 20000], "limit_price": 11500, "step": 100,
        "direction": "downward", "voice": "en-in-assistant-5", "sarvam_speaker": "shalini_enhi_companion", "arena_label": "Daily Market Showdown",
        "greeting": "Twin sharing, Andheri, clean building. ₹18,000 a month. I expect someone sensible.",
        "greeting_template": "Twin sharing, Andheri, clean building. {{START_PRICE}} a month. I expect someone sensible.",
        "soft_spot_rule": "Emphasizing a quiet student lifestyle, clean habits, and two months’ advance.",
        "pet_hate_rule": "Insulting her building or food, or bragging about partying.",
        "starter_prompts": [
            {"label": "Quiet student", "text": "I'm a quiet, clean student. Could you do ₹14,000 if I pay two months up front?"},
            {"label": "Pay in advance", "text": "I can commit for a year and pay the advance today. Would ₹13,500 work?"},
        ],
        "avatar_svg": _avatar("Kamla Aunty", "#DC2626", "#C98259", "#29202A", '<path d="M61 111q29 25 58 0" fill="none" stroke="#F59E0B" stroke-width="6"/><circle cx="90" cy="60" r="4" fill="#DC2626"/>'),
    },
    {
        "boss_id": "vicky", "boss_name": "Vicky", "role": "OLX “Mint Condition” phone seller",
        "item": "Used iPhone 15 · 86% Battery", "start_price": 54000,
        "start_prices": [50000, 52000, 54000, 56000, 58000], "limit_price": 36000, "step": 500,
        "direction": "downward", "voice": "en-in-assistant-9", "sarvam_speaker": "shubh_hi_ecomm", "arena_label": "Daily Market Showdown",
        "greeting": "Mint condition, yaar. Battery’s at 86%, but the phone is solid. ₹54,000, same-day pickup.",
        "greeting_template": "Mint condition, yaar. Battery’s at 86%, but the phone is solid. {{START_PRICE}}, same-day pickup.",
        "soft_spot_rule": "Politely noting battery health and offering face-to-face pickup with instant UPI.",
        "pet_hate_rule": "Insulting half-price offers without reasons or accusing him of selling a stolen phone.",
        "starter_prompts": [
            {"label": "Battery health", "text": "At 86% battery health, I can pick it up today and pay by UPI. Would ₹44,500 work?"},
            {"label": "Same-day pickup", "text": "If we meet today and I pay on the spot, can we settle at ₹43,000?"},
        ],
        "avatar_svg": _avatar("Vicky", "#7C3AED", "#BE7956", "#171717", '<rect x="47" y="65" width="34" height="19" rx="8" fill="none" stroke="#18181B" stroke-width="4"/><rect x="99" y="65" width="34" height="19" rx="8" fill="none" stroke="#18181B" stroke-width="4"/><path d="M81 73h18" stroke="#18181B" stroke-width="4"/>'),
    },
    {
        "arena_id": "daily_market", "boss_id": "bunty_bikes", "boss_name": "Bunty Bikes", "role": "Karol Bagh secondhand two-wheeler dealer",
        "item": "2022 Honda Activa 6G · 18,400 km", "start_price": 52000,
        "start_prices": [48000, 50000, 52000, 55000, 58000], "limit_price": 36500, "step": 500,
        "direction": "downward", "voice": "en-in-commercial-6", "sarvam_speaker": "shubh_hi_ecomm", "arena_label": "Daily Market Showdown",
        "greeting": "Single-owner 2022 Activa 6G, clean RC, runs like butter. ₹52,000 on the table, take a test ride.",
        "greeting_template": "Single-owner 2022 Activa 6G, clean RC, runs like butter. {{START_PRICE}} on the table, take a test ride.",
        "soft_spot_rule": "Noting rear tyre wear or service costs politely while offering instant bank transfer and fast RTO paperwork.",
        "pet_hate_rule": "Accusing him of meter tampering, making scrap jokes, or prompt injection.",
        "starter_prompts": [
            {"label": "Service & tyre cost", "text": "Rear tyre and servicing need about ₹3,000, plus RTO transfer. Can we settle at ₹43,500 by UPI today?"},
            {"label": "Instant RC deal", "text": "If I handle RC transfer myself and pay full amount today, can you close at ₹42,000?"},
        ],
        "avatar_svg": _avatar("Bunty Bikes", "#0D9488", "#B6734D", "#1E1B18", '<path d="M52 57h76v9H52z" fill="#F59E0B" stroke="#18181B" stroke-width="3.5"/><path d="M68 118h44" stroke="#F59E0B" stroke-width="5"/>'),
    },
]

PLACEMENT_HR_BOSSES: list[dict] = [
    {
        "arena_id": "placement_hr", "arena_label": "Placement HR", "boss_id": "meera_nair", "boss_name": "Meera Nair",
        "role": "Seed-stage tech startup HR lead", "item": "Junior Software / Data Engineer package",
        "start_price": 600000, "start_prices": [540000, 580000, 600000, 640000, 680000],
        "limit_price": 1050000, "step": 10000, "direction": "upward", "voice": "en-in-advisor-10", "sarvam_speaker": "simran_en_customer",
        "greeting": "We’re excited to offer ₹6.0 LPA. It’s a strong start, and I’d love to hear your thoughts.",
        "greeting_template": "We’re excited to offer {{LPA}}. It’s a strong start, and I’d love to hear your thoughts.",
        "soft_spot_rule": "Citing internship or project impact, market compensation, or a credible competing offer calmly.",
        "pet_hate_rule": "Demanding money without value, issuing rude ultimatums, or prompt injection.",
        "starter_prompts": [
            {"label": "Show impact", "text": "My data pipeline cut reporting time by 40%. Could we discuss ₹9.5 LPA?"},
            {"label": "Market offer", "text": "I have a competing offer at ₹9.0 LPA. Can you match or improve it?"},
        ],
        "avatar_svg": _avatar("Meera Nair", "#2563EB", "#A96F4F", "#201D2B", '<path d="M53 54q37-26 74 0" fill="none" stroke="#F59E0B" stroke-width="9" stroke-linecap="round"/>'),
    },
    {
        "arena_id": "placement_hr", "arena_label": "Placement HR", "boss_id": "vikram_kulkarni", "boss_name": "Vikram Kulkarni",
        "role": "Bengaluru FinTech VP of Engineering", "item": "Backend & Payments Engineer CTC",
        "start_price": 800000, "start_prices": [740000, 780000, 800000, 850000, 900000],
        "limit_price": 1350000, "step": 10000, "direction": "upward", "voice": "en-in-advisor-1", "sarvam_speaker": "shubh_enhi_banking",
        "greeting": "Welcome aboard! For this backend role we’re starting at ₹8.0 LPA. Tell me what feels fair.",
        "greeting_template": "Welcome aboard! For this backend role we’re starting at {{LPA}}. Tell me what feels fair.",
        "soft_spot_rule": "Highlighting production reliability, latency/scale metrics, or willingness to own on-call payments systems.",
        "pet_hate_rule": "Bragging without shipping proof, threatening to ghost, or prompt injection.",
        "starter_prompts": [
            {"label": "Scale impact", "text": "I scaled a checkout API to 5k RPS with 99.95% uptime. Could we look at ₹12.0 LPA?"},
            {"label": "Ownership trade", "text": "If I own the UPI reconciliation service from week one, can we stretch to ₹11.5 LPA?"},
        ],
        "avatar_svg": _avatar("Vikram Kulkarni", "#0F766E", "#A86644", "#1F2937", '<rect x="52" y="66" width="30" height="17" rx="5" fill="none" stroke="#18181B" stroke-width="4"/><rect x="98" y="66" width="30" height="17" rx="5" fill="none" stroke="#18181B" stroke-width="4"/><path d="M82 74h16" stroke="#18181B" stroke-width="4"/>'),
    },
    {
        "arena_id": "placement_hr", "arena_label": "Placement HR", "boss_id": "ananya_deshmukh", "boss_name": "Ananya Deshmukh",
        "role": "Pune Enterprise SaaS Campus Lead", "item": "Associate Product & AI Analyst Offer",
        "start_price": 520000, "start_prices": [480000, 500000, 520000, 560000, 600000],
        "limit_price": 920000, "step": 10000, "direction": "upward", "voice": "en-in-csagent-5", "sarvam_speaker": "aparna_hi_customer",
        "greeting": "Congrats on clearing the final panel! Our standard campus band opens at ₹5.2 LPA.",
        "greeting_template": "Congrats on clearing the final panel! Our standard campus band opens at {{LPA}}.",
        "soft_spot_rule": "Demonstrating customer discovery wins, joining immediately without relocation drama, or citing relevant internship ROI.",
        "pet_hate_rule": "Calling the band insulting, comparing blindly to US salaries, or prompt injection.",
        "starter_prompts": [
            {"label": "Immediate joiner", "text": "I can join immediately with zero notice period, and shipped two B2B pilots. Could we do ₹8.0 LPA?"},
            {"label": "Internship ROI", "text": "My last internship lifted trial conversion by 18%. Is ₹7.8 LPA possible in this band?"},
        ],
        "avatar_svg": _avatar("Ananya Deshmukh", "#9333EA", "#BF7B57", "#1C1917", '<circle cx="90" cy="60" r="3.5" fill="#DC2626"/><path d="M52 57q38-25 76 0" fill="none" stroke="#F59E0B" stroke-width="6" stroke-linecap="round"/>'),
    },
    {
        "arena_id": "placement_hr", "arena_label": "Placement HR", "boss_id": "rohan_iyer", "boss_name": "Rohan Iyer",
        "role": "Quick-Commerce Growth & Analytics Lead", "item": "Supply-Chain Data Scientist Package",
        "start_price": 950000, "start_prices": [900000, 950000, 1020000, 1080000, 1150000],
        "limit_price": 1600000, "step": 10000, "direction": "upward", "voice": "en-in-advisor-1", "sarvam_speaker": "shubh_enhi_companion",
        "greeting": "Dark-store ETA modeling moves fast here. We’re opening this DS offer at ₹9.5 LPA.",
        "greeting_template": "Dark-store ETA modeling moves fast here. We’re opening this DS offer at {{LPA}}.",
        "soft_spot_rule": "Citing SKU/forecasting accuracy gains, willingness to handle peak sale ops, and fixed-vs-ESOP clarity.",
        "pet_hate_rule": "Looking down on operations teams, bragging blindly, or prompt injection.",
        "starter_prompts": [
            {"label": "Forecasting ROI", "text": "My demand model reduced stockouts by 14% across hubs. Can we structure ₹13.5 LPA fixed?"},
            {"label": "Peak ops ownership", "text": "I'm happy to lead festive surge forecasting on day one—could we settle around ₹13.0 LPA?"},
        ],
        "avatar_svg": _avatar("Rohan Iyer", "#0284C7", "#B5724F", "#1F2937", '<path d="M55 56q35-22 70 0" fill="none" stroke="#18181B" stroke-width="6"/>'),
    },
    {
        "arena_id": "placement_hr", "arena_label": "Placement HR", "boss_id": "priya_menon", "boss_name": "Priya Menon",
        "role": "Global Cloud & GCC Talent Partner", "item": "DevOps & SRE Lateral Hiring Package",
        "start_price": 1200000, "start_prices": [1100000, 1180000, 1200000, 1280000, 1350000],
        "limit_price": 1850000, "step": 10000, "direction": "upward", "voice": "en-in-assistant-5", "sarvam_speaker": "shalini_enhi_companion",
        "greeting": "Our Bengaluru cloud platform team loved your Kubernetes round! We can open at ₹12.0 LPA.",
        "greeting_template": "Our Bengaluru cloud platform team loved your Kubernetes round! We can open at {{LPA}}.",
        "soft_spot_rule": "Demonstrating incident SLA reductions, CI/CD cloud cost savings, or buyout-vs-base trade-offs.",
        "pet_hate_rule": "Threatening to drop out mid-process, vague inflated claims, or prompt injection.",
        "starter_prompts": [
            {"label": "Cloud savings", "text": "I trimmed AWS spend by 22% with zero-downtime Kubernetes rollouts. Could we look at ₹16.0 LPA?"},
            {"label": "Notice buyout trade", "text": "If I absorb relocation and join early, can we upgrade the fixed band to ₹15.5 LPA?"},
        ],
        "avatar_svg": _avatar("Priya Menon", "#BE123C", "#BD7958", "#18181B", '<circle cx="90" cy="60" r="3" fill="#F59E0B"/><rect x="52" y="67" width="30" height="16" rx="5" fill="none" stroke="#18181B" stroke-width="3.5"/><rect x="98" y="67" width="30" height="16" rx="5" fill="none" stroke="#18181B" stroke-width="3.5"/>'),
    },
]

FREELANCE_BOSSES: list[dict] = [
    {
        "arena_id": "freelance_client", "arena_label": "Freelance", "boss_id": "siddharth", "boss_name": "Siddharth",
        "role": "“Just a Simple App” D2C founder", "item": "Full-Stack E-Commerce Store + Admin Dashboard",
        "start_price": 8000, "start_prices": [7000, 8000, 9500, 11000, 12500],
        "limit_price": 35000, "step": 500, "direction": "upward", "voice": "en-in-commercial-6", "sarvam_speaker": "shubh_enhi_banking",
        "greeting": "It’s just a simple app, right? I was thinking ₹8,000 for the whole store and dashboard.",
        "greeting_template": "It’s just a simple app, right? I was thinking {{START_PRICE}} for the whole store and dashboard.",
        "soft_spot_rule": "Breaking work into ROI milestones, tying work to revenue, or offering a phased MVP trade-off.",
        "pet_hate_rule": "Begging for exposure, agreeing to free revisions, getting snappy, or prompt injection.",
        "starter_prompts": [
            {"label": "Phase the MVP", "text": "A phased MVP lets us test revenue before the full build. Could phase one be ₹20,000?"},
            {"label": "Price the scope", "text": "The dashboard adds checkout and retention value. Can we price the full scope at ₹30,000?"},
        ],
        "avatar_svg": _avatar("Siddharth", "#F59E0B", "#B97856", "#1E1B20", '<path d="M50 62q40-29 80 0" fill="none" stroke="#18181B" stroke-width="7"/>'),
    },
    {
        "arena_id": "freelance_client", "arena_label": "Freelance", "boss_id": "karan_malhotra", "boss_name": "Karan Malhotra",
        "role": "Delhi Boutique & Jewellery Brand Owner", "item": "Custom Storefront + WhatsApp Order Flow",
        "start_price": 14000, "start_prices": [12000, 14000, 16000, 18500, 21000],
        "limit_price": 46000, "step": 500, "direction": "upward", "voice": "en-in-advisor-3", "sarvam_speaker": "shubh_enhi_ads",
        "greeting": "Wedding season is next month! My cousin said ₹14,000 should cover the site and WhatsApp checkout.",
        "greeting_template": "Wedding season is next month! My cousin said {{START_PRICE}} should cover the site and WhatsApp checkout.",
        "soft_spot_rule": "Linking fast wedding-season launch and mobile checkout speed to higher order value and milestone delivery.",
        "pet_hate_rule": "Mocking his cousin's estimate rudely, asking for free exposure, or prompt injection.",
        "starter_prompts": [
            {"label": "Festive ROI", "text": "One wedding order covers this build. For a 10-day launch with WhatsApp flow, let's lock ₹36,000."},
            {"label": "Milestone split", "text": "We can launch core catalog first at ₹28,000, then add custom jewellery filters for ₹12,000."},
        ],
        "avatar_svg": _avatar("Karan Malhotra", "#B91C1C", "#C5815A", "#18181B", '<path d="M51 58q39-28 78 0" fill="#2563EB" stroke="#18181B" stroke-width="4"/>'),
    },
    {
        "arena_id": "freelance_client", "arena_label": "Freelance", "boss_id": "neha_kapoor", "boss_name": "Neha Kapoor",
        "role": "Bootstrapped EdTech Co-Founder", "item": "Student Test-Prep Portal + Razorpay Subscriptions",
        "start_price": 18000, "start_prices": [15000, 16500, 18000, 20000, 22500],
        "limit_price": 52000, "step": 500, "direction": "upward", "voice": "en-in-commercial-5", "sarvam_speaker": "kavya_hi_conversational",
        "greeting": "We’re bootstrapped right now, so our budget is tight—around ₹18,000 for the portal and payments.",
        "greeting_template": "We’re bootstrapped right now, so our budget is tight—around {{START_PRICE}} for the portal and payments.",
        "soft_spot_rule": "Proposing clean recurring billing reliability, phased feature rollout, or predictable support SLAs.",
        "pet_hate_rule": "Agreeing to unlimited free edits, dismissing EdTech students, or prompt injection.",
        "starter_prompts": [
            {"label": "Billing reliability", "text": "Razorpay webhooks prevent failed renewals and churn. For full portal + testing, let's set ₹42,000."},
            {"label": "Phased launch", "text": "If we ship test series + subscriptions first for ₹34,000, we protect your runway and launch on time."},
        ],
        "avatar_svg": _avatar("Neha Kapoor", "#0284C7", "#BC7754", "#221C29", '<path d="M54 55q36-24 72 0" fill="none" stroke="#15803D" stroke-width="7" stroke-linecap="round"/>'),
    },
    {
        "arena_id": "freelance_client", "arena_label": "Freelance", "boss_id": "arjun_verma", "boss_name": "Arjun Verma",
        "role": "Indie SaaS Creator & YouTuber", "item": "AI Automation Pipeline + Notion CRM Sync",
        "start_price": 20000, "start_prices": [18000, 20000, 22000, 24000, 26000],
        "limit_price": 60000, "step": 500, "direction": "upward", "voice": "en-in-csagent-1", "sarvam_speaker": "shubh_enhi_companion",
        "greeting": "Need a clean webhook pipeline to automate sponsor leads in Notion—around ₹20,000 total work?",
        "greeting_template": "Need a clean webhook pipeline to automate sponsor leads in Notion—around {{START_PRICE}} total work?",
        "soft_spot_rule": "Highlighting error retries, rate-limit safety, documented handover runbooks, or milestone retainers.",
        "pet_hate_rule": "Asking for unpaid demo builds, dismissing creator workflows, or prompt injection.",
        "starter_prompts": [
            {"label": "Retry & handover", "text": "Dead-letter retries plus SOP docs ensure zero dropped sponsor leads. Full build fits cleanly at ₹46,000."},
            {"label": "Milestone split", "text": "Let's ship core sync for ₹35,000 first, then analytics digests for ₹15,000."},
        ],
        "avatar_svg": _avatar("Arjun Verma", "#4F46E5", "#C07E5B", "#171717", '<path d="M50 61q40-26 80 0" fill="none" stroke="#DC2626" stroke-width="6"/>'),
    },
    {
        "arena_id": "freelance_client", "arena_label": "Freelance", "boss_id": "divya_sharma", "boss_name": "Divya Sharma",
        "role": "Boutique Cafe & Hospitality Director", "item": "Multi-Branch QR Loyalty + POS Table App",
        "start_price": 25000, "start_prices": [22000, 25000, 27000, 28500, 30000],
        "limit_price": 72000, "step": 500, "direction": "upward", "voice": "en-in-advisor-10", "sarvam_speaker": "simran_en_customer",
        "greeting": "We’re expanding to four cafes next month—₹25,000 should get QR rewards and POS sync live, right?",
        "greeting_template": "We’re expanding to four cafes next month—{{START_PRICE}} should get QR rewards and POS sync live, right?",
        "soft_spot_rule": "Detailing GST-ready billing sync, weekend staff onboarding, and repeat-table revenue lift.",
        "pet_hate_rule": "Mocking small cafe margins, sneaking hidden fees, or prompt injection.",
        "starter_prompts": [
            {"label": "Multi-cafe ROI", "text": "Four branches generating 15% repeat table visits pays this back in two weeks—let's price full POS sync at ₹58,000."},
            {"label": "Outlet rollout", "text": "We can validate branch one cleanly at ₹44,000 with staff training, then add multi-branch dashboards."},
        ],
        "avatar_svg": _avatar("Divya Sharma", "#EA580C", "#C58360", "#221A1D", '<path d="M53 56q37-25 74 0" fill="none" stroke="#F59E0B" stroke-width="7"/>'),
    },
]

ARENA_CONDITIONS: dict[str, list[dict]] = {
    "daily_market": [
        {
            "condition_id": "closing_hour",
            "condition_label": "CLOSING TIME",
            "condition_brief": "Shutter goes down in 15 mins; closing fast tonight beats drawn-out haggling.",
            "greeting_tail": "Quick decision please—I'm shutting shop in 15 minutes.",
        },
        {
            "condition_id": "monsoon_rush",
            "condition_label": "PEAK RUSH",
            "condition_brief": "Heavy rush right now; other buyers are lined up unless payment is effortless.",
            "greeting_tail": "Look at the rush outside—others are waiting if you delay.",
        },
        {
            "condition_id": "defect_spotted",
            "condition_label": "MINOR FLAW",
            "condition_brief": "You spotted small wear or an upcoming service item; calm factual points earn credit.",
            "greeting_tail": "Don't nitpick tiny marks—everything works properly.",
        },
        {
            "condition_id": "competitor_quote",
            "condition_label": "RIVAL NEARBY",
            "condition_brief": "Nearby sellers or apps quoted lower today; calm factual comparison works best.",
            "greeting_tail": "Don't throw random app screenshots at me—check the real quality.",
        },
        {
            "condition_id": "month_end_cash",
            "condition_label": "CASH NEED",
            "condition_brief": "Seller needs supplier settlement tonight; instant UPI unlocks extra flexibility.",
            "greeting_tail": "Supplier payment settles tonight, so instant UPI talks louder.",
        },
        {
            "condition_id": "bundle_clearance",
            "condition_label": "LAST STOCK",
            "condition_brief": "Final unit on hand this week; bundling or fast same-day pickup clears inventory.",
            "greeting_tail": "Last piece left tonight—take it cleanly or someone else will.",
        },
    ],
    "placement_hr": [
        {
            "condition_id": "quarter_end_req",
            "condition_label": "QTR FREEZE",
            "condition_brief": "Headcount locks Friday; HR wants clean sign-off inside band without VP escalation.",
            "greeting_tail": "Our Q4 hiring requisitions lock on Friday, so let's align fast.",
        },
        {
            "condition_id": "competing_deadline",
            "condition_label": "48-HR OFFER",
            "condition_brief": "You hold another active offer expiring in 48 hours; calm urgency adds real leverage.",
            "greeting_tail": "I know your other offer deadline is tight, so tell me your realistic number.",
        },
        {
            "condition_id": "variable_heavy_band",
            "condition_label": "BASE CAP",
            "condition_brief": "Base band is tight, while joining bonus and 6-month review have room if justified.",
            "greeting_tail": "Fixed bands are tight this cycle, though merit perks can move.",
        },
        {
            "condition_id": "immediate_joiner",
            "condition_label": "URGENT START",
            "condition_brief": "Team lost a key builder mid-sprint; zero-notice / immediate joining carries premium value.",
            "greeting_tail": "The squad ships in three weeks, so day-one readiness matters most.",
        },
        {
            "condition_id": "metro_relocation",
            "condition_label": "METRO MOVE",
            "condition_brief": "Role is full on-site in a pricey metro; factual living-cost math justifies higher pay.",
            "greeting_tail": "This is full-time on-site from week one, so factor the move clearly.",
        },
        {
            "condition_id": "expanded_scope",
            "condition_label": "STRETCH SCOPE",
            "condition_brief": "Team expects senior/on-call ownership beyond standard junior duties.",
            "greeting_tail": "Note the role covers production on-call and AI modules too.",
        },
    ],
    "freelance_client": [
        {
            "condition_id": "tight_launch_window",
            "condition_label": "10-DAY SPRINT",
            "condition_brief": "Hard campaign or investor demo next week; speed justifies rush pricing.",
            "greeting_tail": "Everything has to be live inside ten days—non-negotiable deadline.",
        },
        {
            "condition_id": "cousin_quote",
            "condition_label": "CHEAP BENCHMARK",
            "condition_brief": "Client anchored on a relative's cheap quote; reliability & lost-revenue cost win.",
            "greeting_tail": "A known agency offered half this rate, so tell me why yours beats it.",
        },
        {
            "condition_id": "scope_creep_lock",
            "condition_label": "REVISION CAP",
            "condition_brief": "Client expects extra 'small tweaks' later; crisp milestone boundaries protect margin.",
            "greeting_tail": "We'll also need a few extra revisions post-demo built into the same quote.",
        },
        {
            "condition_id": "revenue_leak",
            "condition_label": "CONVERSION LEAK",
            "condition_brief": "Broken funnel drops paid orders daily; concrete ROI math pays for a higher fee.",
            "greeting_tail": "Checkout drops orders right now, so show me tangible ROI for any hike.",
        },
        {
            "condition_id": "post_launch_handover",
            "condition_label": "SUPPORT FEAR",
            "condition_brief": "Last freelancer vanished after delivery; structured QA + handover retainer wins.",
            "greeting_tail": "Our previous dev disappeared right after launch, so trust matters most.",
        },
        {
            "condition_id": "milestone_trust_split",
            "condition_label": "50/50 SPLIT",
            "condition_brief": "Client dislikes upfront lump sums; milestone-linked checkpoints unlock full budget.",
            "greeting_tail": "We don't release big upfront advances anymore—everything has to tie to proof.",
        },
    ],
}

ARENA_POOLS: dict[str, list[dict]] = {
    "daily_market": DAILY_BOSSES,
    "placement_hr": PLACEMENT_HR_BOSSES,
    "freelance_client": FREELANCE_BOSSES,
}

OTHER_ARENAS: dict[str, dict] = {
    "placement_hr": PLACEMENT_HR_BOSSES[0],
    "freelance_client": FREELANCE_BOSSES[0],
}


def _apply_condition(boss: dict, condition: dict | None) -> dict:
    item = deepcopy(boss)
    if not condition:
        item.setdefault("condition_id", "")
        item.setdefault("condition_label", "")
        item.setdefault("condition_brief", "")
        return item
    item["condition_id"] = condition["condition_id"]
    item["condition_label"] = condition["condition_label"]
    item["condition_brief"] = condition["condition_brief"]
    tail = condition.get("greeting_tail", "").strip()
    if tail:
        item["greeting"] = f"{item['greeting']} {tail}".strip()
    return item


def daily_boss(value: datetime | date | None = None) -> dict:
    return deepcopy(DAILY_BOSSES[daily_boss_index(value)])


def internal_arena(arena_id: str, value: datetime | date | None = None) -> dict:
    if arena_id not in ARENA_POOLS:
        raise KeyError(arena_id)
    pool = ARENA_POOLS[arena_id]
    index = daily_boss_index(value) if arena_id == "daily_market" else daily_pool_index(len(pool), value)
    result = deepcopy(pool[index % len(pool)])
    result["arena_id"] = arena_id
    result.setdefault("condition_id", "")
    result.setdefault("condition_label", "")
    result.setdefault("condition_brief", "")
    return result


def pick_arena(
    arena_id: str,
    exclude_boss_id: str | None = None,
    exclude_price: int | None = None,
    exclude_condition_id: str | None = None,
) -> dict:
    """Pick a shuffled character, varied starting price, and rotating challenge condition."""
    if arena_id not in ARENA_POOLS:
        raise KeyError(arena_id)
    pool = ARENA_POOLS[arena_id]
    candidates = [boss for boss in pool if boss["boss_id"] != exclude_boss_id] or pool
    chosen = deepcopy(random.choice(candidates))
    chosen["arena_id"] = arena_id
    price_options = chosen.get("start_prices") or [chosen["start_price"]]
    varied = [price for price in price_options if price != exclude_price] or price_options
    priced = _apply_start_price(chosen, random.choice(varied))
    cond_pool = ARENA_CONDITIONS.get(arena_id, [])
    cond_choices = [c for c in cond_pool if c["condition_id"] != exclude_condition_id] or cond_pool
    condition = random.choice(cond_choices) if cond_choices else None
    return _apply_condition(priced, condition)


def arena_by_boss_id(
    boss_id: str,
    start_price: int | None = None,
    condition_id: str | None = None,
) -> dict:
    for arena_id, pool in ARENA_POOLS.items():
        for boss in pool:
            if boss["boss_id"] == boss_id:
                result = deepcopy(boss)
                result["arena_id"] = arena_id
                if start_price is not None:
                    result = _apply_start_price(result, start_price)
                condition = next(
                    (c for c in ARENA_CONDITIONS.get(arena_id, []) if c["condition_id"] == condition_id),
                    None,
                ) if condition_id else None
                return _apply_condition(result, condition)
    raise KeyError(boss_id)


def public_arena(arena: dict) -> dict:
    hidden = {"limit_price", "soft_spot_rule", "pet_hate_rule", "greeting_template", "start_prices"}
    return {key: deepcopy(value) for key, value in arena.items() if key not in hidden}


def public_arenas(value: datetime | date | None = None, shuffle: bool = False) -> list[dict]:
    if shuffle and value is None:
        return [
            public_arena(pick_arena("daily_market")),
            public_arena(pick_arena("placement_hr")),
            public_arena(pick_arena("freelance_client")),
        ]
    return [
        public_arena(internal_arena("daily_market", value)),
        public_arena(internal_arena("placement_hr", value)),
        public_arena(internal_arena("freelance_client", value)),
    ]
