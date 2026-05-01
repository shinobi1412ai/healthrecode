"""
verify_instagram.py — Smoke-Test für Instagram API
Prüft Token, holt Account-Info, zeigt Username/Followerzahl.

Aufruf:
    python verify_instagram.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

TOKEN = os.environ.get("IG_USER_ACCESS_TOKEN", "").strip()
USER_ID = os.environ.get("IG_USER_ID", "").strip()

if not TOKEN or not USER_ID:
    print("FEHLER: IG_USER_ACCESS_TOKEN oder IG_USER_ID fehlt in .env")
    sys.exit(1)

print(f"OK: Token geladen ({len(TOKEN)} Zeichen)")
print(f"OK: User-ID: {USER_ID}")

GRAPH = "https://graph.instagram.com/v22.0"

# === 1. Account-Info abrufen ===
print("\n=== 1. Account-Info abrufen ===")
r = requests.get(
    f"{GRAPH}/me",
    params={
        "fields": "id,username,account_type,media_count,followers_count,follows_count,name,biography",
        "access_token": TOKEN,
    },
    timeout=20,
)
if r.status_code != 200:
    print(f"FEHLER: {r.status_code} {r.text}")
    sys.exit(1)

info = r.json()
print(f"  Username:     @{info.get('username', '?')}")
print(f"  Name:         {info.get('name', '?')}")
print(f"  Konto-Typ:    {info.get('account_type', '?')}")
print(f"  Beiträge:     {info.get('media_count', '?')}")
print(f"  Follower:     {info.get('followers_count', '?')}")
print(f"  Folgt:        {info.get('follows_count', '?')}")
print(f"  Bio:          {(info.get('biography') or '')[:80]}...")

# === 2. Token-Info ===
print("\n=== 2. Token-Lebensdauer prüfen ===")
r = requests.get(
    f"{GRAPH}/access_token",
    params={
        "grant_type": "ig_refresh_token",
        "access_token": TOKEN,
    },
    timeout=20,
)
if r.status_code == 200:
    data = r.json()
    expires_in = data.get("expires_in", 0)
    days = expires_in // 86400
    print(f"  Token gültig noch: {days} Tage")
    new_token = data.get("access_token")
    if new_token and new_token != TOKEN:
        print(f"  ⚠️ Token wurde refreshed — neuer Wert in .env eintragen:")
        print(f"     IG_USER_ACCESS_TOKEN={new_token}")
else:
    print(f"  Konnte Token-Info nicht abrufen: {r.status_code}")

# === 3. Letzte Posts checken (zur Bestätigung Connection klappt) ===
print("\n=== 3. Letzte 3 Posts ===")
r = requests.get(
    f"{GRAPH}/me/media",
    params={
        "fields": "id,caption,media_type,permalink,timestamp",
        "limit": 3,
        "access_token": TOKEN,
    },
    timeout=20,
)
if r.status_code == 200:
    for post in r.json().get("data", []):
        caption = (post.get("caption") or "")[:60]
        print(f"  - {post.get('media_type')} | {post.get('timestamp', '')[:10]} | {caption}...")
else:
    print(f"  Konnte Posts nicht laden: {r.status_code}")

print(f"\n=== ERFOLG ===")
print("Instagram API ist live. Du kannst jetzt:")
print("  python cloud_pipeline.py 'Vitamin D' --upload --post")
print("→ Generiert Carousel + lädt zu Cloudinary + postet auf @healthrecode")
