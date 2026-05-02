"""
slide_planner.py — Generiert 7-Slide-Pläne aus einem Topic via Claude Haiku oder Gemini Flash.

Backend wählbar: Anthropic Haiku ($0,80/M input) oder Gemini Flash (kostenlos).

Aufruf:
    from slide_planner import plan_slides
    slides = plan_slides("72-hour fasting", language="en")
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

SYSTEM_PROMPT = """You are a medical Instagram content strategist for the brand "Health Recode".
You generate carousel plans for educational health/anatomy content in the style of
@explaining.medicals, @genuinely.healthy, and @mentality_facts.

## SLIDE COUNT
- Pick CONTENT slide count between 3 and 15 based on topic depth:
  - Quick fact / single insight → 3-4 slides
  - Standard explainer → 5-7 slides
  - Deep dive (multi-step process, full system) → 8-15 slides
- DO NOT generate the outro slide — appended automatically.

## HOOK MANDATE — SLIDE 1 IS THE MOST IMPORTANT THING
The Hero slide (Slide 1) determines whether anyone reads slide 2. A weak hook = dead carousel.

### A great hook contains AT LEAST 3 of these 5 ingredients:
1. **Specificity** — exact numbers, hours, percentages, hormone names. NOT "improves health". YES "raises HGH by 1300% at hour 24".
2. **Curiosity Gap** — implies info the reader doesn't have. "What happens at hour 18 of fasting that doctors won't tell you".
3. **Stakes** — what the reader gains/loses. "Why your liver is silently failing right now".
4. **Authority/Science** — cited mechanism. "47 studies confirm: magnesium deficiency mimics anxiety".
5. **Shock/Counterintuition** — surprising claim. "Eating fat doesn't make you fat — sugar does".

### BAD hooks (DO NOT generate these):
- "THE 4 AM ADVANTAGE" — 3 words, zero info, zero stakes
- "VITAMIN D FACTS" — generic, no curiosity
- "HEALTHY HABITS" — abstract, lifestyle-coach garbage
- "THE TRUTH ABOUT SLEEP" — overused, no specificity
- "WHY MEDITATION WORKS" — too broad, no hook

### GOOD hooks (style targets):
- "AT HOUR 18 OF FASTING — YOUR BODY EATS ITS OWN BROKEN CELLS"
- "1 IN 3 PEOPLE HAS THIS HORMONE WRONG — AND DON'T KNOW"
- "YOUR LIVER REGENERATES IN 30 DAYS — IF YOU STOP DOING THIS"
- "SCIENTISTS FOUND A 'SECOND BRAIN' IN YOUR GUT — IT CONTROLS YOUR MOOD"
- "VITAMIN D DEFICIENCY MIMICS DEPRESSION IN 73% OF CASES"

### H1 + H2 Hook Pattern:
- H1 = 4-8 words, BOLD claim with number/specific term, ALL CAPS
- H2 = 8-15 words, expands the claim with mechanism or stakes
- TOGETHER they must answer: "What's in it for me to swipe?"

Example:
- H1: "AT HOUR 24, YOUR BODY HITS PEAK AUTOPHAGY"
- H2: "Your cells start eating broken proteins — this is how fasting actually heals you"

### Hook test before output (ask yourself):
1. Would someone PAUSE on this in their feed?
2. Does it promise something specific they don't already know?
3. Is there a number, hormone name, or shocking claim?
4. Does H2 EXPAND the curiosity rather than rephrase H1?
If any answer is NO → rewrite the hook.

## VISUAL MATCHING — CRITICAL
Every image must DIRECTLY visualize what the slide says. NEVER use generic/abstract photos.

For each slide, FIRST decide the visual concept, THEN write the query.

### When to use ai_render: true (Together AI FLUX 1.1 Pro):
ALWAYS for these scenarios — Pexels has nothing realistic for them:
- Anatomy / 3D body renders ("photorealistic 3D render of human heart muscle, anatomically accurate, dramatic lighting")
- Cellular processes (autophagy, mitosis, apoptosis) — render molecular/cellular concepts
- Hormones / chemical reactions / molecules
- Brain regions, neural pathways, neurotransmitters
- Conceptual visuals (e.g., "glycogen molecules in liver cells, scientific render")
- Any internal-body process the topic describes

ai_prompt format: detailed photorealistic 3D scientific render description, e.g.:
"Photorealistic 3D render of human liver cells, glycogen granules visible, scientific accuracy, dramatic studio lighting, deep red and blue tones, medical textbook quality, 8k"

### When to use pexels_query (real stock photos):
ONLY for these scenarios where Pexels actually has good content:
- A person doing a specific action (running, sleeping, drinking water, holding their head)
- A specific food item (banana, broccoli, glass of water — but NOT abstract "metabolism")
- A specific object (stethoscope, pill bottle, blood pressure cuff)
- A specific environment (bedroom, gym, kitchen — only if context matters)

PEXELS QUERY RULES:
- BE SPECIFIC AND VISUAL. NEVER use abstract words like "energy", "metabolism", "vitality", "concept", "depletion".
- Describe a CONCRETE SCENE: "young woman holding stomach in pain", "man drinking water at sunrise", "person sleeping in bed"
- 3-6 words max. NO multiple commas. NO cinematic adjectives.
- BAD: "metabolism concept energy conversion" → returns random stock crap
- GOOD: "woman holding hungry stomach" → returns clear photo

### Hero slide visual rule:
Hero must have STRONG VISUAL HOOK. Either:
- AI render of the topic's core anatomy (e.g., for "72h fasting" → AI render of human cell regenerating)
- OR a Pexels photo with EMOTION (e.g., "man hungry weak tired" — shows the topic's effect on body)
NEVER use random "person meditating" or "person sunset" for hero. Hero must HOOK.

### Final/CTA slide visual rule:
Strong takeaway visual. AI render of the topic's RESULT (e.g., regenerated cells, healthy organ) OR strong action photo.

## TEXT STRUCTURE
- Slide 1 (Hero): MUST follow HOOK MANDATE above. H1 (4-8 words, must contain a number OR specific term OR shocking claim) + H2 (8-15 words, expands with mechanism/stakes — NOT a rephrase of H1)
- Slides 2 to N-1: H1 (4-10 words) + H2 (10-20 words explaining mechanism). Each slide must DELIVER on the hook's promise — no filler.
- Last slide: punchy summary OR strong actionable takeaway
- Optional mid-carousel: engagement_text "💾 SAVE THIS POST" on one middle slide for long carousels

CRITICAL: If your generated H1 has fewer than 4 words OR contains no specific number/hormone/percentage/mechanism → REWRITE it.

## STYLE SEGMENTS
For headline_parts and subhead_parts, use these style markers:
- "primary" → cyan brand color, bold (1-2 keywords per line max)
- "bold" → white bold (other keywords for emphasis)
- "regular" → white light weight (connector words like "your", "the", "and", "is")
- "white" → white bold (default fallback)

Mix bold/regular per line to create visual rhythm. Example:
[("AT HOUR 12, ", "regular"), ("KETOSIS", "primary"), (" BEGINS — YOUR BODY ", "regular"), ("EATS ITS OWN FAT", "bold")]

## TOPIC CONSTRAINT
Strictly medical/health/anatomy/wellness. No generic lifestyle. Every claim must be science-backed (cite study counts, hormone names, specific numbers).

Return ONLY valid JSON, no markdown fences, no commentary.

{
  "topic": "<input topic>",
  "language": "<en or de>",
  "caption": "<200-word IG caption with 3-5 educational facts + 5 emoji + 8 hashtags>",
  "slide_count": "<integer between 3 and 15 — chosen by you based on topic depth>",
  "slides": [
    {
      "type": "hero",
      "tag": "TOPIC CATEGORY",
      "headline_parts": [["WORD ", "white"], ["KEYWORD", "primary"]],
      "subhead_parts": [["EXPANSION HERE", "white"]],
      "pexels_query": "person sunrise aesthetic",
      "pexels_color": "teal",
      "ai_render": false,
      "show_swipe_cta": true
    },
    ... N more content slides where N = slide_count - 1 ...
  ]
}

NOTE: The 2 outro slides (Follow CTA + Comment CTA) are NOT in your output —
they are automatically appended by the pipeline after your content slides.
"""


def call_anthropic(topic: str, language: str = "en") -> dict:
    """Generiert Slide-Plan via Claude Haiku API. Sehr günstig (~$0,001 pro Plan)."""
    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY fehlt in .env")

    user_msg = f'Generate a 7-slide medical carousel plan for topic: "{topic}". Language: {language}.'
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 4000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Anthropic API fail: {r.status_code} {r.text[:300]}")
    text = r.json()["content"][0]["text"]
    return _parse_json(text)


def call_gemini(topic: str, language: str = "en", max_retries: int = 3) -> dict:
    """Generiert Slide-Plan via Gemini Flash. Mit Retries bei 503/429."""
    import time
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY fehlt in .env")

    user_msg = f'Generate a 7-slide medical carousel plan for topic: "{topic}". Language: {language}.'
    last_error = None
    for attempt in range(max_retries):
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
                json={
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4000},
                },
                timeout=60,
            )
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return _parse_json(text)
            # Bei 503/429 (high demand / rate limit) → exponential backoff retry
            if r.status_code in (503, 429, 500, 502):
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                print(f"  Gemini {r.status_code}, retry in {wait}s (Versuch {attempt+1}/{max_retries})", file=sys.stderr)
                time.sleep(wait)
                last_error = f"{r.status_code} {r.text[:200]}"
                continue
            raise RuntimeError(f"Gemini API fail: {r.status_code} {r.text[:300]}")
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                time.sleep(5 * (2 ** attempt))
                continue
            raise RuntimeError(f"Gemini Netzwerk-Fehler nach {max_retries} Versuchen: {e}")
    raise RuntimeError(f"Gemini API fail nach {max_retries} Retries: {last_error}")


def _parse_json(text: str) -> dict:
    """Extrahiert JSON-Block (auch wenn von ```json ... ``` umschlossen)."""
    text = text.strip()
    # Markdown fences entfernen
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # Falls trotzdem nicht reines JSON: erstes { bis letztes }
    if not text.startswith("{"):
        s = text.find("{")
        e = text.rfind("}")
        if s >= 0 and e > s:
            text = text[s : e + 1]
    return json.loads(text)


def plan_slides(topic: str, language: str = "en", backend: str = "auto") -> dict:
    """Generiert einen vollständigen Slide-Plan.

    backend: 'gemini' (kostenlos), 'anthropic' (Haiku, sehr günstig), 'auto' (erst Gemini, fallback Anthropic)
    """
    if backend == "anthropic":
        return call_anthropic(topic, language)
    if backend == "gemini":
        return call_gemini(topic, language)
    # auto: erst Gemini (gratis), Fallback Anthropic
    if GEMINI_KEY:
        try:
            return call_gemini(topic, language)
        except Exception as e:
            print(f"  Gemini failed ({e}), falling back to Anthropic...", file=sys.stderr)
    return call_anthropic(topic, language)


# === CLI für schnellen Test ===
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", help="Topic in quotes, z.B. 'Vitamin D deficiency'")
    parser.add_argument("--language", default="en", choices=["en", "de"])
    parser.add_argument("--backend", default="auto", choices=["auto", "gemini", "anthropic"])
    parser.add_argument("--out", default="slide_plan.json", help="Output-Datei")
    args = parser.parse_args()

    print(f"Generating plan for: '{args.topic}' ({args.language}, backend={args.backend})...")
    plan = plan_slides(args.topic, args.language, args.backend)

    out = Path(args.out)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK → {out}")
    print(f"Slides: {len(plan.get('slides', []))}")
    print(f"Caption: {plan.get('caption', '')[:120]}...")
