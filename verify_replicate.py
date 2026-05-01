"""
verify_replicate.py — Smoke-Test für Replicate API
Prüft ob der Token gültig ist, generiert ein Test-Bild mit FLUX 1.1 Pro Ultra.

Aufruf:
    python verify_replicate.py
"""

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()
if not TOKEN:
    print("FEHLER: REPLICATE_API_TOKEN nicht in .env gefunden.")
    print("→ Hol dir einen Token bei https://replicate.com/account/api-tokens")
    sys.exit(1)

print(f"OK: Token geladen ({len(TOKEN)} Zeichen, Anfang: {TOKEN[:8]}...)")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Prefer": "wait",  # synchron warten — keine Polling nötig
}

# === Schritt 1: Account-Check (Account-Endpoint) ===
print("\n=== Schritt 1: Token validieren ===")
r = requests.get("https://api.replicate.com/v1/account", headers=HEADERS, timeout=20)
if r.status_code != 200:
    print(f"FEHLER: Status {r.status_code}: {r.text[:300]}")
    if r.status_code == 401:
        print("→ Token ist ungültig. Auf https://replicate.com/account/api-tokens prüfen.")
    sys.exit(1)
acc = r.json()
print(f"OK: Eingeloggt als {acc.get('username', 'unbekannt')} ({acc.get('type', '?')})")

# === Schritt 2: Test-Bild mit FLUX 1.1 Pro Ultra ===
print("\n=== Schritt 2: Test-Bild mit FLUX 1.1 Pro Ultra ===")
TEST_PROMPT = (
    "A clean medical illustration of the human heart, anatomically accurate, "
    "labeled chambers and vessels, white background, editorial illustration style, "
    "deep crimson red and warm cream tones, high resolution, suitable for an "
    "educational Instagram post. Photorealistic medical textbook style."
)

payload = {
    "input": {
        "prompt": TEST_PROMPT,
        "aspect_ratio": "4:5",
        "output_format": "png",
        "safety_tolerance": 2,
        "raw": False,
    }
}

print("→ Schicke Anfrage (kann 10–30 Sekunden dauern)...")
r = requests.post(
    "https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro-ultra/predictions",
    headers=HEADERS,
    json=payload,
    timeout=120,
)

if r.status_code not in (200, 201):
    print(f"FEHLER: Status {r.status_code}: {r.text[:500]}")
    sys.exit(1)

result = r.json()
status = result.get("status")
print(f"  Prediction Status: {status}")

# Falls Prefer: wait nicht funktioniert hat, manuell pollen
if status not in ("succeeded", "failed", "canceled"):
    print("  → Pollen bis fertig...")
    pred_id = result["id"]
    for _ in range(60):
        time.sleep(2)
        r = requests.get(
            f"https://api.replicate.com/v1/predictions/{pred_id}",
            headers=HEADERS,
            timeout=20,
        )
        result = r.json()
        status = result.get("status")
        if status in ("succeeded", "failed", "canceled"):
            break
    print(f"  Final: {status}")

if status != "succeeded":
    err = result.get("error", "kein error message")
    print(f"FEHLER: Generierung fehlgeschlagen: {err}")
    sys.exit(1)

# Output ist URL (oder Liste)
output = result.get("output")
if isinstance(output, list):
    image_url = output[0]
else:
    image_url = output

if not image_url:
    print("FEHLER: Keine Bild-URL in der Antwort.")
    print(result)
    sys.exit(1)

print(f"OK: Bild generiert: {image_url}")

# === Schritt 3: Bild herunterladen ===
print("\n=== Schritt 3: Bild herunterladen ===")
img_r = requests.get(image_url, timeout=60)
if img_r.status_code != 200:
    print(f"FEHLER: Download fehlgeschlagen, Status {img_r.status_code}")
    sys.exit(1)

out = Path(__file__).parent / "test_image_replicate.png"
out.write_bytes(img_r.content)

# Kosten-Info
metrics = result.get("metrics", {})
cost = result.get("cost", "unbekannt")
predict_time = metrics.get("predict_time", "?")

print(f"\n=== ERFOLG ===")
print(f"Datei: {out}")
print(f"Größe: {len(img_r.content) // 1024} KB")
print(f"Generierungszeit: {predict_time}s")
print(f"Geschätzte Kosten: ~$0.06 (FLUX 1.1 Pro Ultra)")
print(f"\nÖffne {out.name} und prüfe ob das Bild gut aussieht.")
