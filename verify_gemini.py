"""
verify_gemini.py — Smoke-Test für den Google Gemini API-Key
Prüft ob der Key gültig ist und ob Bildgenerierung freigeschaltet ist.
Generiert ein einzelnes anatomisches Test-Bild.

Aufruf:
    pip install requests python-dotenv
    python verify_gemini.py
"""

import base64
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("FEHLER: 'requests' fehlt. Bitte installieren: pip install requests python-dotenv")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    print("FEHLER: 'python-dotenv' fehlt. Bitte installieren: pip install python-dotenv")
    sys.exit(1)

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
if not API_KEY:
    print("FEHLER: GEMINI_API_KEY nicht in .env gefunden.")
    sys.exit(1)

print(f"OK: Key geladen ({len(API_KEY)} Zeichen, Anfang: {API_KEY[:6]}...{API_KEY[-4:]})")

BASE = "https://generativelanguage.googleapis.com/v1beta"

# === Schritt 1: Welche Modelle sind verfügbar? ===
print("\n=== Schritt 1: Verfügbare Modelle prüfen ===")
try:
    r = requests.get(f"{BASE}/models?key={API_KEY}", timeout=20)
except requests.exceptions.RequestException as e:
    print(f"FEHLER: Kein Netzwerkzugriff zur Gemini API: {e}")
    sys.exit(1)

if r.status_code != 200:
    print(f"FEHLER: Status {r.status_code}")
    print(r.text[:500])
    if r.status_code == 403:
        print("\n→ Key ist ungültig oder Generative Language API nicht aktiviert.")
        print("→ Lösung: https://aistudio.google.com/app/apikey öffnen, Key prüfen.")
    sys.exit(1)

data = r.json()
models = data.get("models", [])
print(f"OK: {len(models)} Modelle verfügbar.")

# Suche nach Bild-fähigen Modellen
image_models = []
for m in models:
    name = m.get("name", "")
    methods = m.get("supportedGenerationMethods", [])
    if "generateContent" in methods and ("image" in name.lower() or "nano-banana" in name.lower()):
        image_models.append(name)

print("\nBild-Modelle gefunden:")
for m in image_models:
    print(f"  - {m}")

if not image_models:
    print("WARNUNG: Keine offensichtlichen Bild-Modelle. Probiere alle Standard-Namen durch.")
    image_models = [
        "models/gemini-3-pro-image-preview",
        "models/gemini-2.5-flash-image",
        "models/gemini-2.5-flash-image-preview",
        "models/imagen-3.0-generate-002",
    ]

# === Schritt 2: Test-Bild generieren ===
print("\n=== Schritt 2: Test-Bild generieren ===")
TEST_PROMPT = (
    "A clean medical illustration of the human heart, anatomically accurate, "
    "labeled chambers, white background, editorial style, deep red accents, "
    "high resolution, suitable for an Instagram educational post."
)

success_model = None
image_bytes = None

for model_name in image_models:
    short = model_name.replace("models/", "")
    print(f"\n→ Probiere {short}...")
    payload = {
        "contents": [{"parts": [{"text": TEST_PROMPT}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    try:
        r = requests.post(
            f"{BASE}/{model_name}:generateContent?key={API_KEY}",
            json=payload,
            timeout=90,
        )
    except requests.exceptions.RequestException as e:
        print(f"  Netzwerkfehler: {e}")
        continue

    if r.status_code != 200:
        msg = r.json().get("error", {}).get("message", r.text[:200]) if r.text else "no body"
        print(f"  Status {r.status_code}: {msg[:200]}")
        continue

    body = r.json()
    candidates = body.get("candidates", [])
    if not candidates:
        print("  Keine candidates in der Antwort.")
        continue

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            image_bytes = base64.b64decode(inline["data"])
            success_model = short
            break
    if image_bytes:
        break
    else:
        print("  Antwort enthielt kein Bild (nur Text).")

if not image_bytes:
    print("\nFEHLER: Konnte mit keinem Modell ein Bild generieren.")
    print("→ Möglicher Grund: Key hat keine Bild-Berechtigung im aktuellen Region/Plan.")
    print("→ Lösung: in https://aistudio.google.com prüfen, ob Bildgenerierung aktiv ist.")
    sys.exit(1)

# === Schritt 3: Speichern ===
out = Path(__file__).parent / "test_image.png"
out.write_bytes(image_bytes)
print(f"\n=== ERFOLG ===")
print(f"Bild generiert mit: {success_model}")
print(f"Gespeichert als: {out}")
print(f"Größe: {len(image_bytes) // 1024} KB")
print("\nÖffne die Datei und prüfe ob das Bild sinnvoll aussieht.")
