"""
test_pollinations_realistic.py — Qualitäts-Test mit realistischem Prompt
Generiert: Person + Stadt-Hintergrund, um Pollinations für vielfältige Bilder zu prüfen.

Aufruf:
    python test_pollinations_realistic.py
"""

import os
import sys
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("POLLINATIONS_API_KEY", "").strip()

# Drei realistische Test-Prompts mit unterschiedlichen Anforderungen
TESTS = [
    {
        "name": "person_stadt",
        "prompt": (
            "A photorealistic portrait of a young woman walking in a modern European city street, "
            "Berlin Mitte at golden hour, warm sunset light, sharp focus on her face, "
            "shallow depth of field, urban lifestyle photography, natural skin tones, "
            "high detail, 8k quality, professional photo"
        ),
    },
    {
        "name": "arzt_klinik",
        "prompt": (
            "A photorealistic photo of a friendly young doctor in a white coat standing in a "
            "modern bright hospital corridor, holding a tablet, smiling at the camera, "
            "natural daylight, professional medical photography, 8k, sharp focus"
        ),
    },
    {
        "name": "anatomie_render",
        "prompt": (
            "A high quality 3D render of the human heart anatomy, scientifically accurate, "
            "labeled chambers and major vessels, on a dark gradient background, "
            "soft studio lighting, medical textbook quality, ultra detailed, 8k"
        ),
    },
]

print(f"=== Pollinations Realismus-Test (3 Bilder) ===\n")

for test in TESTS:
    encoded = urllib.parse.quote(test["prompt"])
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1024&height=1280&model=flux&nologo=true&enhance=true&seed=42"
    )
    if API_KEY:
        url += f"&token={urllib.parse.quote(API_KEY)}"

    print(f"→ Generiere '{test['name']}'... (kann 30-60s dauern)")
    try:
        r = requests.get(url, timeout=180)
    except requests.exceptions.RequestException as e:
        print(f"  FEHLER: {e}")
        continue

    if r.status_code != 200 or not r.headers.get("Content-Type", "").startswith("image/"):
        print(f"  FEHLER: Status {r.status_code} / {r.headers.get('Content-Type')}")
        print(f"  Body: {r.text[:200]}")
        continue

    out = Path(__file__).parent / f"test_{test['name']}.png"
    out.write_bytes(r.content)
    print(f"  OK: {out.name} ({len(r.content)//1024} KB)\n")

print("=== Fertig ===")
print("Öffne die drei test_*.png Dateien und beurteile die Qualität:")
print("  - test_person_stadt.png  → realistische Person?")
print("  - test_arzt_klinik.png   → glaubwürdiger Arzt?")
print("  - test_anatomie_render.png → akkurate Anatomie?")
