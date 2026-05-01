"""
topic_refresher.py — Generiert automatisch neue Topics wenn topics.txt fast leer ist.
Wird von cloud_pipeline.py aufgerufen.

Aufruf direkt:
    python topic_refresher.py

Aufruf programmatisch:
    from topic_refresher import refresh_topics_if_low
    refresh_topics_if_low(threshold=10)
"""

import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TOPICS_FILE = ROOT / "topics.txt"

REFRESH_PROMPT = """You are a medical content strategist for the Health Recode Instagram brand.
Generate 50 NEW Instagram carousel topics for medical/health/anatomy content in the style of @explaining.medicals and @genuinely.healthy.

Each topic must:
- Be specific and concrete (e.g. "Why magnesium deficiency causes anxiety" NOT "Anxiety tips")
- Promise a science-backed angle (specific numbers, studies, mechanisms)
- Use curiosity hooks (what nobody tells you, hidden, surprising, the truth about)
- Stay strictly medical/health/anatomy (no generic lifestyle)
- Be evergreen, not tied to a date or trend

Avoid duplicates with existing topics:
{existing_topics}

Return ONLY the 50 new topics as a plain JSON array of strings:
["topic 1", "topic 2", ..., "topic 50"]
NO markdown fences, NO explanation, just the JSON array.
"""


def count_active_topics() -> int:
    """Zählt nicht-auskommentierte, nicht-leere Zeilen."""
    if not TOPICS_FILE.exists():
        return 0
    lines = TOPICS_FILE.read_text(encoding="utf-8").splitlines()
    return sum(1 for l in lines if l.strip() and not l.startswith("#"))


def fetch_existing_topics(limit: int = 50) -> list[str]:
    """Liest die letzten N existierenden Topics für Dedup-Kontext."""
    if not TOPICS_FILE.exists():
        return []
    lines = TOPICS_FILE.read_text(encoding="utf-8").splitlines()
    actives = [l for l in lines if l.strip() and not l.startswith("#")]
    return actives[-limit:]


def generate_new_topics() -> list[str]:
    """Ruft Gemini auf um 50 neue Topics zu generieren."""
    if not GEMINI_KEY:
        raise RuntimeError("GEMINI_API_KEY fehlt — Auto-Refill nicht möglich")
    existing = fetch_existing_topics(50)
    prompt = REFRESH_PROMPT.format(existing_topics="\n".join(existing))
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.8, "maxOutputTokens": 4000},
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini fail: {r.status_code} {r.text[:200]}")
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    # JSON-Block extrahieren
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise RuntimeError(f"Keine JSON-Liste in Antwort: {text[:200]}")
    topics = json.loads(m.group())
    return [t.strip() for t in topics if t.strip()]


def append_topics(new_topics: list[str]):
    """Fügt neue Topics am Ende von topics.txt an."""
    if not new_topics:
        return
    existing = TOPICS_FILE.read_text(encoding="utf-8") if TOPICS_FILE.exists() else ""
    timestamp = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"\n# === Auto-refilled {timestamp} ({len(new_topics)} Topics) ===\n"
    block += "\n".join(new_topics) + "\n"
    TOPICS_FILE.write_text(existing + block, encoding="utf-8")


def refresh_topics_if_low(threshold: int = 10) -> int:
    """Wenn weniger als `threshold` Topics aktiv sind, generiere neue.
    Returns: Anzahl der generierten neuen Topics (0 wenn nicht nötig)."""
    active = count_active_topics()
    print(f"[topic_refresher] Aktive Topics: {active}, Threshold: {threshold}")
    if active > threshold:
        return 0
    print(f"[topic_refresher] Generiere 50 neue Topics via Gemini...")
    try:
        new_topics = generate_new_topics()
        append_topics(new_topics)
        print(f"[topic_refresher] OK — {len(new_topics)} neue Topics angehängt")
        return len(new_topics)
    except Exception as e:
        print(f"[topic_refresher] FEHLER: {e}")
        return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--threshold", type=int, default=10)
    p.add_argument("--force", action="store_true", help="Generiere auch wenn nicht nötig")
    args = p.parse_args()

    if args.force:
        new = generate_new_topics()
        append_topics(new)
        print(f"Force-generated {len(new)} new topics")
    else:
        refresh_topics_if_low(args.threshold)
