"""
verify_together.py — Smoke-Test für Together AI mit hochwertigem realistischen Prompt
Testet beste Modelle zuerst (FLUX 1.1 Pro), fällt zurück auf günstigere.

Aufruf:
    python verify_together.py
"""

import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("TOGETHER_API_KEY", "").strip()
if not API_KEY:
    print("FEHLER: TOGETHER_API_KEY nicht in .env gefunden.")
    sys.exit(1)

print(f"OK: Token geladen ({len(API_KEY)} Zeichen, Anfang: {API_KEY[:10]}...)")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Hyperrealistischer Test-Prompt — Stadt mit Menschen, hochwertig
TEST_PROMPT = (
    "Ultra realistic photograph of a vibrant European city street at golden hour, "
    "Berlin Mitte or Paris Le Marais style, several diverse people walking, "
    "talking and laughing — young professionals, a couple, an elderly man — "
    "warm sunset light filtering between historic buildings, cobblestone street, "
    "outdoor café with patrons in foreground, sharp focus on faces, "
    "shallow depth of field, professional 35mm photography by a Magnum-style "
    "photographer, cinematic color grading, natural skin tones, fine clothing details, "
    "8k resolution, hyperrealistic, award-winning street photography, "
    "shot on Leica Q2, no AI artifacts, photographic"
)

# Modelle in Reihenfolge der Qualität: beste zuerst
MODELS = [
    ("black-forest-labs/FLUX.1.1-pro", "FLUX 1.1 Pro (beste Qualität, ~$0.04/Bild)"),
    ("black-forest-labs/FLUX.1-pro", "FLUX 1 Pro (sehr gut, ~$0.05/Bild)"),
    ("black-forest-labs/FLUX.1-dev", "FLUX 1 Dev (gut, ~$0.025/Bild)"),
    ("black-forest-labs/FLUX.1-schnell", "FLUX Schnell (günstig, ~$0.003/Bild)"),
]

print("\n=== Bildgenerierung mit hyperrealistischem Stadt-Prompt ===\n")
print(f"Prompt: {TEST_PROMPT[:120]}...\n")

success_model = None
image_bytes = None

for model_id, desc in MODELS:
    print(f"→ Probiere {desc}...")
    payload = {
        "model": model_id,
        "prompt": TEST_PROMPT,
        "width": 1024,
        "height": 1280,  # 4:5 Aspect Ratio für Instagram
        "steps": 28 if "pro" in model_id or "dev" in model_id else 4,
        "n": 1,
        "response_format": "b64_json",
    }

    try:
        r = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers=HEADERS,
            json=payload,
            timeout=180,
        )
    except requests.exceptions.RequestException as e:
        print(f"  Netzwerkfehler: {e}")
        continue

    if r.status_code != 200:
        try:
            err = r.json()
            msg = err.get("error", {}).get("message") or err.get("message") or str(err)[:200]
        except Exception:
            msg = r.text[:200]
        print(f"  Status {r.status_code}: {msg[:200]}")
        if r.status_code == 401:
            print("  → Token ungültig.")
            sys.exit(1)
        continue

    data = r.json()
    items = data.get("data", [])
    if not items:
        print(f"  Keine Bilder in Antwort: {data}")
        continue

    b64 = items[0].get("b64_json")
    if b64:
        image_bytes = base64.b64decode(b64)
    else:
        url = items[0].get("url")
        if url:
            img_r = requests.get(url, timeout=60)
            if img_r.status_code == 200:
                image_bytes = img_r.content

    if image_bytes:
        success_model = model_id
        break

if not image_bytes:
    print("\nFEHLER: Konnte mit keinem Modell ein Bild generieren.")
    sys.exit(1)

out = Path(__file__).parent / "test_together_premium.png"
out.write_bytes(image_bytes)

print(f"\n=== ERFOLG ===")
print(f"Modell: {success_model}")
print(f"Datei: {out}")
print(f"Größe: {len(image_bytes) // 1024} KB")
print(f"\nÖffne die Datei und beurteile die Qualität!")
print("Wenn das gut aussieht → wir bauen die Pipeline auf Together AI.")
