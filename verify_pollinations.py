"""
verify_pollinations.py — Smoke-Test für Pollinations.ai
Komplett kostenlos. Nutzt FLUX im Hintergrund.

Aufruf:
    python verify_pollinations.py
"""

import os
import sys
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("POLLINATIONS_API_KEY", "").strip()
if API_KEY:
    print(f"OK: API-Key geladen ({len(API_KEY)} Zeichen, Anfang: {API_KEY[:6]}...)")
else:
    print("Hinweis: Kein API-Key gesetzt — versuche anonymen Zugriff.")

TEST_PROMPT = (
    "A clean medical illustration of the human heart, anatomically accurate, "
    "labeled chambers and vessels, white background, editorial illustration style, "
    "deep crimson red and warm cream tones, high resolution, suitable for an "
    "educational Instagram post."
)

encoded = urllib.parse.quote(TEST_PROMPT)
url = (
    f"https://image.pollinations.ai/prompt/{encoded}"
    f"?width=1024&height=1280&model=flux&nologo=true&enhance=true"
)

# API-Key als Token-Parameter (Pollinations Format)
if API_KEY:
    url += f"&token={urllib.parse.quote(API_KEY)}"

headers = {}
if API_KEY:
    # Manche Pollinations-Endpunkte akzeptieren auch Authorization-Header
    headers["Authorization"] = f"Bearer {API_KEY}"

print("=== Test mit Pollinations.ai (Modell: flux) ===")
print(f"URL-Länge: {len(url)} Zeichen")
print("→ Anfrage läuft (kann 20–60 Sekunden dauern)...")

try:
    r = requests.get(url, headers=headers, timeout=180)
except requests.exceptions.RequestException as e:
    print(f"FEHLER: Netzwerkfehler: {e}")
    sys.exit(1)

if r.status_code != 200:
    print(f"FEHLER: Status {r.status_code}")
    print(r.text[:500])
    sys.exit(1)

ctype = r.headers.get("Content-Type", "")
if not ctype.startswith("image/"):
    print(f"FEHLER: Antwort ist kein Bild ({ctype})")
    print(r.text[:500])
    sys.exit(1)

out = Path(__file__).parent / "test_image_pollinations.png"
out.write_bytes(r.content)

print(f"\n=== ERFOLG ===")
print(f"Modell: Pollinations FLUX")
print(f"Datei: {out}")
print(f"Größe: {len(r.content) // 1024} KB")
print(f"Content-Type: {ctype}")
print("\nÖffne die Datei und prüfe, ob die Qualität für dich ausreicht.")
print("Falls ja: wir bauen die Pipeline auf Pollinations auf (kostenlos).")
print("Falls nein: $5 bei Together AI aufladen für FLUX Schnell.")
