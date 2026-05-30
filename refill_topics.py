"""
refill_topics.py — Auto-refill topics.txt wenn es zu leer ist.

Generiert via Gemini neue Medical/Health Topics, dedupliziert gegen bereits
gepostete Topics (aus posted/POST_*.json), und schreibt sie in topics.txt.

Aufruf:
    python refill_topics.py                     # check + refill auf min 50 wenn < 15
    python refill_topics.py --min 30 --target 60  # Custom Schwellen
    python refill_topics.py --force --target 100  # Force-Refill auf 100

Strategie:
1. Lese topics.txt → aktuelle Topics
2. Lese posted/POST_*.json → bereits gepostete Topics
3. Wenn topics.txt < min_count → AI generiert neue Topics bis target_count
4. Filter: keine Duplikate (aus posted/ + aktuelles topics.txt)
5. Schreibe komplette neue topics.txt
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

TOPICS_FILE = ROOT / "topics.txt"
POSTED_DIR = ROOT / "posted"


SYSTEM_PROMPT = """You generate Instagram carousel topics for a medical/health/anatomy education brand called "HealthRecode".

Your audience: 25-45 year-olds interested in science-backed health optimization, biology, hormones, sleep, fasting, longevity, mental performance.

QUALITY BAR — each topic must be:
- SPECIFIC (not "be healthy" but "Cortisol's 90-minute morning window — what controls your day")
- MECHANISM-DRIVEN (must reveal HOW something works, not just WHAT it does)
- HOOK-WORTHY (contains numbers, percentages, hormones, body systems, specific research findings)
- NICHE: medical, biological, anatomical, physiological — NOT generic lifestyle/wellness fluff

CATEGORIES TO ROTATE — distribute evenly, roughly equal per category:
1. HORMONES (cortisol, insulin, dopamine, testosterone, estrogen, melatonin, leptin, ghrelin)
2. BRAIN & NEURO (brain plasticity, neural pathways, dopamine, ADHD, focus, memory, anxiety)
3. GUT & DIGESTION (microbiome, gut-brain axis, leaky gut, liver detox, IBS, digestion timing)
4. SLEEP & CIRCADIAN (sleep stages, REM, melatonin, jet lag, circadian clock, sleep debt)
5. FASTING & METABOLISM (autophagy, ketosis, insulin sensitivity, mitochondria, glycogen)
6. NUTRITION & VITAMINS (vitamin D, magnesium, omega-3, deficiencies, bioavailability, iron)
7. EXERCISE PHYSIOLOGY (HIIT, muscle synthesis, recovery, VO2max, lactic acid, soreness)
8. AGING & LONGEVITY (telomeres, NAD+, mTOR, senescent cells, mitochondrial decay)
9. STRESS & IMMUNITY (HPA axis, cortisol cascade, inflammation, immune response, lymphatic)
10. WOMEN'S HEALTH (menstrual phases, perimenopause, PCOS, fertility, estrogen dominance)

⚠️ STRICT LIMIT: Maximum 1-2 topics about heart/cardiovascular per batch.
Heart = arteries, heart rate, HRV, cardiac, arrhythmia, blood pressure, coronary.
DO NOT cluster same-category topics together — alternate categories every topic.
WRONG order: heart, heart, heart, brain, brain → BANNED
CORRECT order: brain, gut, hormones, sleep, fasting, nutrition, heart (max 1), exercise → GOOD

FORMAT:
- One topic per line
- 6-12 words per topic
- English only
- NO numbering, NO bullet points, NO commas at line end

EXAMPLE GOOD TOPICS:
72-hour fasting timeline — what science says hour by hour
Cortisol's 90-minute morning window controls your entire day
Why your liver works hardest between 1am and 3am
The gut-brain axis: how 90% of serotonin lives in your stomach
Insulin sensitivity recovery — exact protocol from research
Why magnesium deficiency causes 7 different symptoms
The 4 sleep stages and what each one repairs
Dopamine vs Serotonin — different roles, different fixes
Why women's metabolism shifts every 7 days
Mitochondrial decay starts at 30 — how to reverse it

EXAMPLE BAD TOPICS (do NOT generate):
"Be more healthy"  (too generic)
"Tips for better sleep"  (no mechanism)
"Drink more water"  (not science-backed)
"Eat your veggies"  (vague)

Output: Just the topics, one per line. No commentary, no fences."""


def load_existing_topics() -> set:
    """Aktuelle Topics aus topics.txt + alle bereits geposteten."""
    used = set()
    # Aktuelle topics.txt
    if TOPICS_FILE.exists():
        for line in TOPICS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                used.add(line.lower())

    # Bereits gepostete (aus posted/POST_*.json)
    if POSTED_DIR.exists():
        for f in POSTED_DIR.glob("POST_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                topic = data.get("topic", "").strip()
                if topic:
                    used.add(topic.lower())
            except Exception:
                pass

    return used


def generate_topics_gemini(count: int, exclude: set) -> list:
    """Generiert N neue Topics via Gemini, exkludiert bereits genutzte."""
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY fehlt")

    exclude_text = ""
    if exclude:
        excluded_list = sorted(list(exclude))[:50]  # max 50 zur Klarheit
        exclude_text = f"\n\nDO NOT generate any of these (already used or planned):\n" + "\n".join(f"- {t}" for t in excluded_list)

    user_msg = f"Generate {count} unique medical/health Instagram carousel topics following the rules.{exclude_text}\n\nRemember: ONE topic per line, 6-12 words, English, mechanism-driven, science-backed. No numbering, no fluff."

    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
        json={
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
            "generationConfig": {"temperature": 0.9, "maxOutputTokens": 4000},
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini fail: {r.status_code} {r.text[:300]}")

    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    topics = []
    for line in text.splitlines():
        line = line.strip()
        # Cleanup typische LLM-Artefakte
        if line.startswith(("- ", "* ", "• ", "→ ")):
            line = line[2:].strip()
        if line and line[0].isdigit() and len(line) > 2 and line[1] in (".", ")"):
            line = line[2:].strip()
        # Skip empty, comments, headers
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        if len(line.split()) < 4 or len(line.split()) > 18:
            continue
        topics.append(line)
    return topics


def generate_topics_anthropic(count: int, exclude: set) -> list:
    """Fallback: Anthropic Claude Haiku."""
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY fehlt")

    exclude_text = ""
    if exclude:
        excluded_list = sorted(list(exclude))[:50]
        exclude_text = f"\n\nDO NOT generate any of these:\n" + "\n".join(f"- {t}" for t in excluded_list)

    user_msg = f"Generate {count} unique medical/health Instagram carousel topics. ONE per line, 6-12 words, mechanism-driven.{exclude_text}"

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 3000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic fail: {r.status_code} {r.text[:300]}")

    text = r.json()["content"][0]["text"]
    topics = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ", "• ", "→ ")):
            line = line[2:].strip()
        if line and line[0].isdigit() and len(line) > 2 and line[1] in (".", ")"):
            line = line[2:].strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        if len(line.split()) < 4 or len(line.split()) > 18:
            continue
        topics.append(line)
    return topics


def dedupe_against(new_topics: list, exclude: set) -> list:
    """Entfernt Duplikate (case-insensitive)."""
    seen = set(exclude)  # bereits genutzt
    unique = []
    for t in new_topics:
        norm = t.lower().strip()
        if norm not in seen and len(norm) > 10:
            seen.add(norm)
            unique.append(t)
    return unique


def main():
    parser = argparse.ArgumentParser()
    # AGGRESSIVE DEFAULTS — Marwan will NIE manuell pflegen muessen
    parser.add_argument("--min", type=int, default=50, help="Wenn topics.txt unter dieser Zahl: refill")
    parser.add_argument("--target", type=int, default=100, help="Auf wie viele Topics auffuellen")
    parser.add_argument("--force", action="store_true", help="Refill auch wenn ueber min_count")
    args = parser.parse_args()

    # Aktuelle Topics
    current_topics = []
    if TOPICS_FILE.exists():
        for line in TOPICS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                current_topics.append(line)

    print(f"=== Topic Refill Check ===")
    print(f"Aktuelle Topics in topics.txt: {len(current_topics)}")
    print(f"Schwellen: min={args.min}, target={args.target}")

    if not args.force and len(current_topics) >= args.min:
        print(f"OK — genug Topics ({len(current_topics)} >= {args.min}). Kein Refill noetig.")
        return

    needed = args.target - len(current_topics)
    if needed <= 0:
        print(f"OK — bereits ueber target. Kein Refill.")
        return

    print(f"Refill noetig: +{needed} neue Topics.")

    # Bereits genutzte (current + posted) → AI darf die NICHT generieren
    exclude = load_existing_topics()
    print(f"Exkludiere {len(exclude)} bereits-genutzte Topics (current + posted)")

    # Generieren — Gemini primaer, Anthropic fallback
    print(f"\nGeneriere {needed} neue Topics via Gemini...")
    new_topics = []
    try:
        # Etwas mehr generieren als nötig (Buffer für Duplikate)
        new_topics = generate_topics_gemini(needed + 10, exclude)
    except Exception as e:
        print(f"  Gemini fail ({e}), fallback Anthropic...")
        try:
            new_topics = generate_topics_anthropic(needed + 10, exclude)
        except Exception as e2:
            print(f"  Anthropic auch fail: {e2}", file=sys.stderr)
            sys.exit(1)

    print(f"  {len(new_topics)} Topics generiert")

    # Dedupe + Cap
    unique = dedupe_against(new_topics, exclude)
    unique = unique[:needed]
    print(f"  {len(unique)} unique nach Dedup")

    if not unique:
        print("FEHLER: Keine neuen unique Topics generiert", file=sys.stderr)
        sys.exit(1)

    # Schreibe komplette neue topics.txt
    final = current_topics + unique
    content = "\n".join(final) + "\n"
    TOPICS_FILE.write_text(content, encoding="utf-8")

    print(f"\nOK — topics.txt geupdated:")
    print(f"  Vorher: {len(current_topics)} Topics")
    print(f"  Neue: +{len(unique)}")
    print(f"  Jetzt: {len(final)} Topics total")
    print(f"\nLetzte 5 neue Topics:")
    for t in unique[-5:]:
        print(f"  + {t}")


if __name__ == "__main__":
    main()
