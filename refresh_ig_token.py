"""
refresh_ig_token.py — Refresht den IG_USER_ACCESS_TOKEN bevor er abläuft.

Instagram Login API Tokens sind 60 Tage gültig — können aber UNBEGRENZT
verlängert werden, solange man sie alle <60 Tage refresht. So läuft die Pipeline
forever ohne manuellen Eingriff.

Endpoint: GET https://graph.instagram.com/refresh_access_token
  ?grant_type=ig_refresh_token
  &access_token=<old_long_lived_token>

Returns: { access_token: "...", token_type: "bearer", expires_in: 5184000 }  # 60 days

Aufruf:
    python refresh_ig_token.py             # nur refreshen + ausgeben
    python refresh_ig_token.py --update-env  # zusätzlich .env updaten

GitHub Actions: ruft das alle 50 Tage auf, schreibt den neuen Token via
gh CLI in den Repository-Secret IG_USER_ACCESS_TOKEN zurück.
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


def refresh_token(current_token: str) -> dict:
    """Refresht den Long-Lived IG Access Token. Returns dict mit neuem Token + expiry."""
    r = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": current_token},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Refresh fail: {r.status_code} {r.text[:300]}")
    return r.json()


def update_env_file(new_token: str):
    """Tauscht IG_USER_ACCESS_TOKEN in .env aus."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        print(f"WARN: {env_path} existiert nicht — wird neu erstellt")
        env_path.write_text(f"IG_USER_ACCESS_TOKEN={new_token}\n", encoding="utf-8")
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith("IG_USER_ACCESS_TOKEN="):
            lines[i] = f"IG_USER_ACCESS_TOKEN={new_token}"
            found = True
            break
    if not found:
        lines.append(f"IG_USER_ACCESS_TOKEN={new_token}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK — .env aktualisiert mit neuem Token")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-env", action="store_true", help="Schreibt neuen Token in .env")
    parser.add_argument("--quiet", action="store_true", help="Nur Token ausgeben (für gh CLI)")
    args = parser.parse_args()

    current = os.environ.get("IG_USER_ACCESS_TOKEN", "").strip()
    if not current:
        print("FEHLER: IG_USER_ACCESS_TOKEN fehlt in .env / Environment", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"Refreshing IG token (aktuelle Länge: {len(current)} chars)...")

    try:
        result = refresh_token(current)
    except Exception as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        sys.exit(1)

    new_token = result.get("access_token", "")
    expires_in = result.get("expires_in", 0)
    days = expires_in // 86400

    if args.quiet:
        print(new_token)
    else:
        print(f"OK — neuer Token: {new_token[:20]}... ({len(new_token)} chars)")
        print(f"Gültig: {days} Tage ({expires_in} Sekunden)")

    if args.update_env:
        update_env_file(new_token)


if __name__ == "__main__":
    main()
