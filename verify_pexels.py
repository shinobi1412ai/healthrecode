"""
verify_pexels.py — Smoke-Test für Pexels API
Sucht ein medizinisches Foto + lädt es runter.

Aufruf:
    python verify_pexels.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
if not API_KEY:
    print("FEHLER: PEXELS_API_KEY nicht in .env")
    sys.exit(1)

print(f"OK: Key geladen ({len(API_KEY)} Zeichen, Anfang: {API_KEY[:10]}...)")

HEADERS = {"Authorization": API_KEY}

# === Test 1: Suche nach medizinischem Foto ===
print("\n=== Schritt 1: Suche 'doctor patient consultation' ===")
r = requests.get(
    "https://api.pexels.com/v1/search",
    headers=HEADERS,
    params={
        "query": "doctor patient consultation",
        "per_page": 5,
        "orientation": "portrait",
    },
    timeout=20,
)

if r.status_code != 200:
    print(f"FEHLER: Status {r.status_code}: {r.text[:300]}")
    if r.status_code == 401:
        print("→ API-Key ungültig.")
    sys.exit(1)

data = r.json()
photos = data.get("photos", [])
total = data.get("total_results", 0)

print(f"OK: {total:,} Treffer gefunden, {len(photos)} angezeigt.")
print(f"Rate Limit übrig: {r.headers.get('X-Ratelimit-Remaining', '?')} / {r.headers.get('X-Ratelimit-Limit', '?')}")

if not photos:
    print("WARNUNG: Keine Fotos in der Antwort.")
    sys.exit(1)

# === Test 2: Erstes Foto herunterladen ===
print("\n=== Schritt 2: Erstes Foto herunterladen ===")
photo = photos[0]
print(f"  Fotograf: {photo.get('photographer', '?')}")
print(f"  ID: {photo.get('id')}")
print(f"  Beschreibung (alt): {photo.get('alt', '?')[:80]}")

# Pexels gibt verschiedene Größen — wir nehmen 'large' (~1500px Höhe, perfekt für IG)
img_url = photo["src"]["large"]
print(f"  URL: {img_url[:80]}...")

img_r = requests.get(img_url, timeout=60)
if img_r.status_code != 200:
    print(f"FEHLER: Download-Status {img_r.status_code}")
    sys.exit(1)

out = Path(__file__).parent / "test_image_pexels.jpg"
out.write_bytes(img_r.content)

# === Test 3: Mehrere Beispiel-Suchen ===
print("\n=== Schritt 3: Welche medizinischen Themen sind verfügbar? ===")
test_queries = [
    "anatomy heart",
    "person headache",
    "medical pills",
    "young woman smiling healthy",
    "elderly man worried",
    "stethoscope close up",
]
for q in test_queries:
    rr = requests.get(
        "https://api.pexels.com/v1/search",
        headers=HEADERS,
        params={"query": q, "per_page": 1},
        timeout=15,
    )
    if rr.status_code == 200:
        n = rr.json().get("total_results", 0)
        print(f"  '{q}': {n:,} Treffer")
    else:
        print(f"  '{q}': Status {rr.status_code}")

print(f"\n=== ERFOLG ===")
print(f"Datei: {out}")
print(f"Größe: {len(img_r.content) // 1024} KB")
print(f"\nÖffne {out.name} und prüfe die Qualität.")
print("Pexels hat tausende solche Profi-Fotos kostenlos verfügbar.")
print("→ Pipeline kann diese als Personen-Bilder nutzen + AI nur für Anatomie.")
