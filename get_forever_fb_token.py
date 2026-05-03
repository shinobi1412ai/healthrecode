"""
get_forever_fb_token.py — Konvertiert Short-Lived FB Token in Forever Page Token.

Workflow:
  1. Du gibst Short-Lived User Token aus Graph API Explorer ein
  2. Script exchangt zu Long-Lived User Token (60 Tage)
  3. Script holt Page Token aus /me/accounts
  4. Page Token derived von Long-Lived User Token = NIE EXPIRES
  5. Output: Page Token + Page ID zum Eintragen in GitHub Secrets

Aufruf:
    python get_forever_fb_token.py
    # → fragt interactive nach Token + zeigt Forever Page Token + Page ID

Voraussetzungen in .env:
    FB_APP_ID=<deine App ID>
    FB_APP_SECRET=<dein App Secret>

Beide kriegst du hier:
    https://developers.facebook.com/apps → deine App → Settings → Basic
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

APP_ID = os.environ.get("FB_APP_ID", "").strip()
APP_SECRET = os.environ.get("FB_APP_SECRET", "").strip()


def exchange_to_long_lived_user_token(short_lived: str) -> str:
    """Tauscht Short-Lived User Token gegen Long-Lived User Token (60 Tage)."""
    r = requests.get(
        "https://graph.facebook.com/v21.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_lived,
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"User-Token-Exchange fail: {r.status_code} {r.text[:300]}")
    return r.json()["access_token"]


def get_pages(long_lived_user_token: str) -> list:
    """Holt alle Pages des Users + deren Forever-Page-Tokens."""
    r = requests.get(
        "https://graph.facebook.com/v21.0/me/accounts",
        params={
            "fields": "id,name,access_token,tasks",
            "access_token": long_lived_user_token,
        },
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Pages-Fetch fail: {r.status_code} {r.text[:300]}")
    return r.json().get("data", [])


def main():
    global APP_ID, APP_SECRET

    print("=== Forever FB Page Token Generator ===\n")

    # App ID interaktiv falls nicht in .env
    if not APP_ID:
        print("FB_APP_ID fehlt in .env.")
        print("Finde sie hier: https://developers.facebook.com/apps -> HealthRecode -> Einstellungen -> Allgemeines\n")
        APP_ID = input("FB_APP_ID einfuegen: ").strip()
        if not APP_ID:
            print("FEHLER: App ID darf nicht leer sein", file=sys.stderr)
            sys.exit(1)

    # App Secret interaktiv falls nicht in .env
    if not APP_SECRET:
        print("\nFB_APP_SECRET fehlt in .env.")
        print("Auf der gleichen Seite -> 'App-Geheimcode anzeigen' -> Passwort eingeben -> kopieren\n")
        APP_SECRET = input("FB_APP_SECRET einfuegen: ").strip()
        if not APP_SECRET:
            print("FEHLER: App Secret darf nicht leer sein", file=sys.stderr)
            sys.exit(1)

    print("\nSchritt: Short-Lived Page-Token (oder User-Token) aus Graph API Explorer einfuegen")
    print("(https://developers.facebook.com/tools/explorer/)")
    print("Permissions die der Token haben muss:")
    print("  - pages_show_list, pages_read_engagement, pages_manage_posts, pages_manage_metadata\n")

    short_lived = input("Token einfuegen (EAA...): ").strip()
    if not short_lived:
        print("FEHLER: Token darf nicht leer sein", file=sys.stderr)
        sys.exit(1)
    if not short_lived.startswith("EAA"):
        print("WARN: Token sollte mit 'EAA' beginnen — pruefe nochmal", file=sys.stderr)

    print("\n[1] Tausche Short-Lived -> Long-Lived User Token...")
    try:
        long_lived = exchange_to_long_lived_user_token(short_lived)
        print(f"    OK ({len(long_lived)} chars)")
    except Exception as e:
        print(f"    FEHLER: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n[2] Hole Pages + Forever Page Tokens...")
    try:
        pages = get_pages(long_lived)
    except Exception as e:
        print(f"    FEHLER: {e}", file=sys.stderr)
        sys.exit(1)

    if not pages:
        print("    KEINE Pages gefunden — pruefe ob du Page-Admin bist", file=sys.stderr)
        sys.exit(1)

    print(f"    OK — {len(pages)} Page(s) gefunden\n")
    print("=" * 70)
    for i, p in enumerate(pages, 1):
        print(f"\nPAGE {i}: {p['name']}")
        print(f"  FB_PAGE_ID           = {p['id']}")
        print(f"  FB_PAGE_ACCESS_TOKEN = {p['access_token'][:20]}...({len(p['access_token'])} chars)")
        print(f"  Permissions: {', '.join(p.get('tasks', []))}")
    print("\n" + "=" * 70)

    # Auto-update GitHub Secrets via gh CLI (falls verfügbar)
    import shutil, subprocess
    if not shutil.which("gh"):
        print("\nWARN: gh CLI nicht installiert — kann Secret nicht automatisch setzen")
        print("Trage beide Werte manuell ein:")
        print("  https://github.com/shinobi1412ai/healthrecode/settings/secrets/actions")
        for p in pages:
            print(f"\nPAGE {p['name']}:")
            print(f"  FB_PAGE_ID           = {p['id']}")
            print(f"  FB_PAGE_ACCESS_TOKEN = {p['access_token']}")
        return

    # Wenn 1 Page → automatisch in Secret schreiben
    if len(pages) == 1:
        page = pages[0]
        print(f"\n[3] Schreibe Secrets via gh CLI...")
        repo = input("Repo (default: shinobi1412ai/healthrecode): ").strip() or "shinobi1412ai/healthrecode"
        try:
            subprocess.run(
                ["gh", "secret", "set", "FB_PAGE_ID", "--repo", repo, "--body", str(page["id"])],
                check=True
            )
            print(f"    OK — FB_PAGE_ID gesetzt")
            subprocess.run(
                ["gh", "secret", "set", "FB_PAGE_ACCESS_TOKEN", "--repo", repo, "--body", page["access_token"]],
                check=True
            )
            print(f"    OK — FB_PAGE_ACCESS_TOKEN gesetzt (Forever)")
            print(f"\n=== FERTIG. Beide Secrets in {repo} aktualisiert. ===")
        except subprocess.CalledProcessError as e:
            print(f"\n    FEHLER beim Schreiben des Secrets: {e}")
            print("    Manuell setzen — siehe oben")
            for p in pages:
                print(f"\nPAGE {p['name']}:")
                print(f"  FB_PAGE_ID           = {p['id']}")
                print(f"  FB_PAGE_ACCESS_TOKEN = {p['access_token']}")
    else:
        # Mehrere Pages → User soll wählen
        print("\n[3] Mehrere Pages gefunden — welche soll in Secrets?")
        for i, p in enumerate(pages, 1):
            print(f"  {i}. {p['name']} ({p['id']})")
        choice = input(f"Nummer 1-{len(pages)} oder 'skip' fuer manuell: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(pages):
            page = pages[int(choice) - 1]
            repo = input("Repo (default: shinobi1412ai/healthrecode): ").strip() or "shinobi1412ai/healthrecode"
            try:
                subprocess.run(
                    ["gh", "secret", "set", "FB_PAGE_ID", "--repo", repo, "--body", str(page["id"])],
                    check=True
                )
                subprocess.run(
                    ["gh", "secret", "set", "FB_PAGE_ACCESS_TOKEN", "--repo", repo, "--body", page["access_token"]],
                    check=True
                )
                print(f"\n=== FERTIG. Secrets fuer Page '{page['name']}' in {repo} gesetzt. ===")
            except subprocess.CalledProcessError as e:
                print(f"FEHLER: {e}")
        else:
            print("\nManuell — Tokens ausgegeben:")
            for p in pages:
                print(f"\n{p['name']}: {p['id']} | {p['access_token']}")


if __name__ == "__main__":
    main()
