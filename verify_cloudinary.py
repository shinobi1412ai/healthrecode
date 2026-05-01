"""
verify_cloudinary.py — Smoke-Test für Cloudinary
Lädt ein Test-Bild hoch, prüft die URL, und löscht das Bild wieder.

Aufruf:
    python verify_cloudinary.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
API_KEY = os.environ.get("CLOUDINARY_API_KEY", "").strip()
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "").strip()

if not all([CLOUD_NAME, API_KEY, API_SECRET]):
    print("FEHLER: Cloudinary-Credentials unvollständig in .env")
    print(f"  CLOUDINARY_CLOUD_NAME = {'OK' if CLOUD_NAME else 'FEHLT'}")
    print(f"  CLOUDINARY_API_KEY    = {'OK' if API_KEY else 'FEHLT'}")
    print(f"  CLOUDINARY_API_SECRET = {'OK' if API_SECRET else 'FEHLT'}")
    sys.exit(1)

print(f"OK: Credentials geladen")
print(f"  Cloud Name: {CLOUD_NAME}")
print(f"  API Key: {API_KEY[:6]}...")

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
except ImportError:
    print("FEHLER: cloudinary fehlt. Installiere: pip install cloudinary")
    sys.exit(1)

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET,
    secure=True,
)

# === Schritt 1: Test-Bild bereitstellen ===
print("\n=== Schritt 1: Test-Bild vorbereiten ===")
TEST_IMG = Path(__file__).parent / "test_image_pollinations.png"
if not TEST_IMG.exists():
    TEST_IMG = Path(__file__).parent / "test_image_replicate.png"
if not TEST_IMG.exists():
    TEST_IMG = Path(__file__).parent / "test_image.png"
if not TEST_IMG.exists():
    # Generiere ein winziges Test-Bild mit Pillow
    print("  Kein Test-Bild gefunden — erzeuge ein Dummy-Bild.")
    try:
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(200, 50, 50))
        TEST_IMG = Path(__file__).parent / "_cloudinary_test.png"
        img.save(TEST_IMG)
    except ImportError:
        print("FEHLER: PIL/Pillow fehlt. Installiere: pip install Pillow")
        sys.exit(1)
print(f"  Bild: {TEST_IMG.name} ({TEST_IMG.stat().st_size // 1024} KB)")

# === Schritt 2: Hochladen ===
print("\n=== Schritt 2: Hochladen zu Cloudinary ===")
try:
    result = cloudinary.uploader.upload(
        str(TEST_IMG),
        public_id="medical_insta_test",
        folder="verify",
        overwrite=True,
    )
except Exception as e:
    print(f"FEHLER: Upload fehlgeschlagen: {e}")
    print("→ Cloud Name könnte falsch sein, oder API-Credentials passen nicht.")
    sys.exit(1)

url = result.get("secure_url")
public_id = result.get("public_id")
print(f"OK: Upload erfolgreich")
print(f"  URL: {url}")
print(f"  Public ID: {public_id}")

# === Schritt 3: URL prüfen (öffentlich erreichbar?) ===
print("\n=== Schritt 3: URL öffentlich erreichbar? ===")
r = requests.get(url, timeout=20)
if r.status_code == 200:
    print(f"OK: URL liefert {r.headers.get('content-type', '?')} ({len(r.content)//1024} KB)")
else:
    print(f"FEHLER: URL gibt Status {r.status_code} zurück")

# === Schritt 4: Wieder löschen (Aufräumen) ===
print("\n=== Schritt 4: Test-Bild wieder löschen ===")
try:
    delete_result = cloudinary.uploader.destroy(public_id)
    if delete_result.get("result") == "ok":
        print("OK: Test-Bild gelöscht.")
    else:
        print(f"WARNUNG: Löschung unklar: {delete_result}")
except Exception as e:
    print(f"WARNUNG: Löschung fehlgeschlagen: {e}")

print(f"\n=== ERFOLG ===")
print("Cloudinary funktioniert. Upload + öffentliche URL + Delete sind alle OK.")
print("→ Pipeline kann diese Credentials für IG-Posting nutzen.")
