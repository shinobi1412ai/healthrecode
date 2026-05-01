"""
setup_meta_credentials.py — Konvertiert Short-Lived Token in Long-Lived (60 Tage),
holt Facebook-Page-ID und Instagram-Business-Account-ID, schreibt alles in .env.

Aufruf (einmalig):
    python setup_meta_credentials.py
"""

import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH)

APP_ID = os.environ["META_APP_ID"]
APP_SECRET = os.environ["META_APP_SECRET"]
SHORT_TOKEN = os.environ["META_SHORT_LIVED_TOKEN"]

GRAPH = "https://graph.facebook.com/v21.0"


def update_env(key: str, value: str):
    """Ersetzt eine Zeile in .env oder fügt sie hinzu."""
    text = ENV_PATH.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    new_line = f"{key}={value}"
    if pattern.search(text):
        text = pattern.sub(new_line, text)
    else:
        text += f"\n{new_line}"
    ENV_PATH.write_text(text, encoding="utf-8")
    print(f"  → .env updated: {key}={value[:20]}...")


# === Schritt 1: Short-Lived → Long-Lived (60 Tage) ===
print("=== Schritt 1: Long-Lived Token holen (60 Tage gültig) ===")
r = requests.get(
    f"{GRAPH}/oauth/access_token",
    params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": SHORT_TOKEN,
    },
    timeout=20,
)
if r.status_code != 200:
    print(f"FEHLER: {r.status_code} {r.text}"); sys.exit(1)
data = r.json()
long_token = data["access_token"]
expires_in = data.get("expires_in", "unbekannt")
print(f"  OK — gültig {expires_in} Sekunden ({int(expires_in)//86400} Tage)" if isinstance(expires_in, int) else "  OK")
update_env("META_LONG_LIVED_TOKEN", long_token)

# === Schritt 2: Facebook Pages auflisten ===
print("\n=== Schritt 2: Facebook-Pages des Accounts auflisten ===")
r = requests.get(
    f"{GRAPH}/me/accounts",
    params={"access_token": long_token, "fields": "id,name,access_token,instagram_business_account"},
    timeout=20,
)
if r.status_code != 200:
    print(f"FEHLER: {r.status_code} {r.text}"); sys.exit(1)
pages = r.json().get("data", [])
if not pages:
    print("FEHLER: Keine Pages gefunden. Hast du eine FB-Page erstellt + verknüpft?"); sys.exit(1)

print(f"  {len(pages)} Page(s) gefunden:")
for i, p in enumerate(pages):
    has_ig = "✅" if p.get("instagram_business_account") else "❌"
    print(f"    [{i}] {p['name']} (ID: {p['id']}) — IG verknüpft: {has_ig}")

# Auto-pick: erste Page mit IG-Business-Account
target = None
for p in pages:
    if p.get("instagram_business_account"):
        target = p
        break

if not target:
    print("\nFEHLER: Keine Page hat ein verknüpftes Instagram-Business-Konto.")
    print("→ Geh in Meta Business Suite → verknüpfe @healthrecode mit einer Page")
    sys.exit(1)

print(f"\n  Verwende Page: {target['name']}")
update_env("FB_PAGE_ID", target["id"])
update_env("FB_PAGE_ACCESS_TOKEN", target["access_token"])

ig_id = target["instagram_business_account"]["id"]
update_env("IG_BUSINESS_ACCOUNT_ID", ig_id)
print(f"  Instagram Business Account ID: {ig_id}")

# === Schritt 3: IG-Account-Info abrufen (Bestätigung) ===
print("\n=== Schritt 3: Instagram-Account verifizieren ===")
r = requests.get(
    f"{GRAPH}/{ig_id}",
    params={"access_token": long_token, "fields": "username,name,profile_picture_url,followers_count,media_count"},
    timeout=20,
)
if r.status_code == 200:
    info = r.json()
    print(f"  Username:  @{info.get('username', '?')}")
    print(f"  Name:      {info.get('name', '?')}")
    print(f"  Follower:  {info.get('followers_count', '?')}")
    print(f"  Beiträge:  {info.get('media_count', '?')}")
else:
    print(f"  Warnung: konnte IG-Info nicht laden: {r.text[:200]}")

print(f"\n=== ERFOLG ===")
print("Alle Credentials sind in .env gespeichert:")
print("  META_LONG_LIVED_TOKEN, FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN, IG_BUSINESS_ACCOUNT_ID")
print("\nDu kannst jetzt: python cloud_pipeline.py 'Topic' --upload --post")
