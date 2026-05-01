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
You generate variable-length carousel plans for educational health/anatomy content
in the style of @explaining.medicals, @genuinely.healthy, and @mentality_facts.

Each plan must:
- Pick optimal CONTENT slide count between 3 and 15 based on topic depth:
  - Quick fact / single insight → 3-4 content slides
  - Standard explainer → 5-7 content slides
  - Deep dive (cascading process, multi-step, anatomy system) → 8-15 content slides
- Slide 1 of content: HERO — short H1 hook (3-6 words) + H2 expansion (8-15 words)
- Final content slide: punchy summary or actionable takeaway
- Optional: mid-carousel "💾 SAVE THIS POST" engagement nudge for longer carousels (8+ slides)
- DO NOT generate the 2 outro slides — they are appended automatically by the pipeline
- Use cyan keyword highlighting (mark important words as "primary")
- Use bold/regular weight mix for emphasis (mentality_facts style): mark keywords as "bold", connectors as "regular"
- Pexels query strings: simple, natural (NOT cinematic-overload)
- Source per slide: "pexels_query" for real-life/lifestyle (default), "ai_render": true for anatomy 3D-renders, "google_query" for real public figures
- Topic must stay strictly medical/health/anatomy

Style segment options for headline_parts and subhead_parts:
  - "primary" → cyan brand color, bold
  - "bold"    → white, bold (Keywords)
  - "regular" → white, light weight (connector words)
  - "white"   → white bold (default)

Return ONLY valid JSON in this exact schema (no markdown fences, no commentary).
The "slides" array contains ONLY content slides. Outros are added automatically.

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
