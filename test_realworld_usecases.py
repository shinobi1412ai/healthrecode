"""
test_realworld_usecases.py — Testet die ECHTEN Use-Cases für medizinische Carousels
Generiert 3 Bilder die wir tatsächlich brauchen werden:
  1. Anatomie-3D-Render (Herz)
  2. Single-Person-Portrait (Patient mit Symptom)
  3. Konzept-Bild (medizinische Stillleben)

Aufruf:
    python test_realworld_usecases.py
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
    print("FEHLER: TOGETHER_API_KEY nicht in .env")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

TESTS = [
    {
        "name": "anatomie_herz_3d",
        "model": "black-forest-labs/FLUX.1.1-pro",
        "prompt": (
            "Photorealistic 3D render of an anatomically accurate human heart, "
            "scientifically detailed, showing chambers and major vessels, "
            "deep crimson red and pink tones with subtle highlights, "
            "dramatic studio lighting, dark gradient background, "
            "ultra-detailed surface texture, medical textbook illustration style, "
            "depth of field, 8k resolution, hyperrealistic anatomical visualization"
        ),
    },
    {
        "name": "patient_brustschmerz",
        "model": "black-forest-labs/FLUX.1.1-pro",
        "prompt": (
            "Cinematic close-up portrait of a worried middle-aged man clutching his chest "
            "with his right hand, expression of discomfort and concern, "
            "neutral home interior background slightly blurred, soft window light, "
            "professional editorial photography, sharp focus on his face and hand, "
            "natural skin tones, realistic details, shot on a 50mm lens, "
            "cinematic color grading, 8k, hyperrealistic"
        ),
    },
    {
        "name": "konzept_medikamente",
        "model": "black-forest-labs/FLUX.1.1-pro",
        "prompt": (
            "Minimalist conceptual photograph of pills and a stethoscope arranged on a "
            "clean white marble surface, soft natural light from above, top-down view, "
            "editorial product photography style, sharp detail, subtle shadows, "
            "warm cream and white tones with hints of red, "
            "magazine cover quality, 8k, hyperrealistic medical concept image"
        ),
    },
]

print("=== Real-World Test (3 medizinische Use-Cases) ===\n")
print("Kosten: ~$0.12 für alle drei Bilder (FLUX 1.1 Pro)\n")

success_count = 0
for test in TESTS:
    print(f"→ Generiere '{test['name']}'... (kann 30-60s dauern)")
    payload = {
        "model": test["model"],
        "prompt": test["prompt"],
        "width": 1024,
        "height": 1280,
        "steps": 28,
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
    except Exception as e:
        print(f"  FEHLER: {e}")
        continue

    if r.status_code != 200:
        try:
            err = r.json().get("error", {}).get("message", str(r.text)[:200])
        except Exception:
            err = r.text[:200]
        print(f"  Status {r.status_code}: {err}")
        continue

    data = r.json()
    b64 = data.get("data", [{}])[0].get("b64_json")
    if not b64:
        print(f"  Kein Bild in Antwort")
        continue

    img_bytes = base64.b64decode(b64)
    out = Path(__file__).parent / f"test_{test['name']}.png"
    out.write_bytes(img_bytes)
    print(f"  OK: {out.name} ({len(img_bytes)//1024} KB)\n")
    success_count += 1

print(f"=== Fertig — {success_count}/3 Bilder generiert ===")
print("\nÖffne die drei Dateien und beurteile:")
print("  test_anatomie_herz_3d.png       → Anatomie sauber? Korrekt?")
print("  test_patient_brustschmerz.png   → Person realistisch? Glaubwürdig?")
print("  test_konzept_medikamente.png    → Magazine-Qualität?")
print("\nDas sind die ECHTEN Use-Cases die wir in Carousels brauchen werden.")
print("Wenn diese drei gut aussehen, ist die Bild-Pipeline startklar.")
