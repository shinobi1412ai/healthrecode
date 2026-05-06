"""
post_from_queue.py — Postet das ÄLTESTE Carousel aus queue/ zu Instagram.

Workflow:
  1. queue/ wird nach POST_*.json durchsucht
  2. Ältestes File wird gewählt
  3. Bilder werden zu IG gepostet (nutzt vor-uploaded Cloudinary URLs)
  4. Bei Erfolg: File wird zu posted/ verschoben
  5. Bei Fehler: File bleibt in queue/, Skript exit 1

Aufruf:
    python post_from_queue.py
    python post_from_queue.py --dry-run     # zeigt was gepostet würde, postet aber nicht
    python post_from_queue.py --pick FILE   # postet ein bestimmtes File
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

QUEUE_DIR = ROOT / "queue"
POSTED_DIR = ROOT / "posted"
QUEUE_DIR.mkdir(exist_ok=True)
POSTED_DIR.mkdir(exist_ok=True)

# Special exit code: signals Meta-Auth-Block (Code 190/200) to the GitHub workflow.
# When the workflow sees this code, it auto-disables the cron schedule to prevent
# further API hits during a Meta-lock — preventing extension of the lock.
EXIT_AUTH_BLOCKED = 78


def _detect_auth_block(response_text: str) -> bool:
    """Returns True if the Meta API response indicates Auth/Lock issues
    (Code 190 = OAuth invalid/expired/revoked, Code 200 = API access blocked).
    These errors mean human intervention is required — no point retrying."""
    try:
        err = json.loads(response_text).get("error", {})
        code = err.get("code")
        msg = err.get("message", "")
        if code in (190, 200):
            return True
        block_phrases = [
            "API access blocked",
            "permission(s) must be granted",
            "session has been invalidated",
            "user has not authorized",
            "Error validating access token",
        ]
        return any(p in msg for p in block_phrases)
    except Exception:
        return False


def find_oldest_queue_file() -> Path | None:
    """Findet das älteste POST_*.json in queue/ (nach mtime sortiert)."""
    files = sorted(QUEUE_DIR.glob("POST_*.json"), key=lambda p: p.stat().st_mtime)
    return files[0] if files else None


def post_to_facebook(image_urls: list, caption: str) -> str:
    """Cross-Post: postet Carousel-Bilder als FB Photo-Album auf die FB Page.
    Nutzt FB_PAGE_ACCESS_TOKEN (laeuft NIE ab) + FB_PAGE_ID."""
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    page_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not page_token:
        return "skipped (FB_PAGE_ID oder FB_PAGE_ACCESS_TOKEN fehlt)"

    BASE = "https://graph.facebook.com/v21.0"
    try:
        # Bilder als unpublished Photos hochladen
        photo_ids = []
        for i, url in enumerate(image_urls):
            r = requests.post(
                f"{BASE}/{page_id}/photos",
                params={"url": url, "published": "false", "access_token": page_token},
                timeout=60,
            )
            if r.status_code != 200:
                return f"fb_error: photo {i+1} failed: {r.status_code} {r.text[:200]}"
            photo_ids.append(r.json()["id"])

        # Album-Post erstellen (alle Photos in einem Post)
        attached = ",".join([f'{{"media_fbid":"{pid}"}}' for pid in photo_ids])
        r = requests.post(
            f"{BASE}/{page_id}/feed",
            params={
                "message": caption,
                "attached_media": f"[{attached}]",
                "access_token": page_token,
            },
            timeout=60,
        )
        if r.status_code != 200:
            return f"fb_error: feed publish failed: {r.status_code} {r.text[:200]}"
        return f"fb_posted: {r.json().get('id')}"
    except Exception as e:
        return f"fb_error: {e}"


def post_to_instagram(image_urls: list, caption: str) -> str:
    """Postet Carousel via Instagram Login API. Returns status string."""
    ig_id = os.environ.get("IG_USER_ID", "").strip()
    token = os.environ.get("IG_USER_ACCESS_TOKEN", "").strip()
    if not ig_id or not token:
        return "no_meta_setup (IG_USER_ID oder IG_USER_ACCESS_TOKEN fehlt)"

    BASE = "https://graph.instagram.com/v22.0"
    try:
        # Step 1: Carousel-Item-Container erstellen
        container_ids = []
        for i, url in enumerate(image_urls):
            r = requests.post(
                f"{BASE}/{ig_id}/media",
                params={
                    "image_url": url,
                    "is_carousel_item": "true",
                    "access_token": token,
                },
                timeout=60,
            )
            if r.status_code != 200:
                return f"error: container {i+1} failed: {r.status_code} {r.text[:300]}"
            container_ids.append(r.json()["id"])
            print(f"    Container {i+1}/{len(image_urls)}: {container_ids[-1]}")

        # Step 2: Carousel-Container
        r = requests.post(
            f"{BASE}/{ig_id}/media",
            params={
                "media_type": "CAROUSEL",
                "children": ",".join(container_ids),
                "caption": caption,
                "access_token": token,
            },
            timeout=60,
        )
        if r.status_code != 200:
            return f"error: carousel container failed: {r.status_code} {r.text[:300]}"
        carousel_id = r.json()["id"]
        print(f"    Carousel container: {carousel_id}")

        # Step 3: Auf "FINISHED" warten
        for _ in range(30):
            time.sleep(2)
            sr = requests.get(
                f"{BASE}/{carousel_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=20,
            )
            if sr.status_code == 200:
                status = sr.json().get("status_code")
                if status == "FINISHED":
                    break
                if status == "ERROR":
                    return "error: container processing failed"

        # Step 4: Publish
        r = requests.post(
            f"{BASE}/{ig_id}/media_publish",
            params={"creation_id": carousel_id, "access_token": token},
            timeout=60,
        )
        if r.status_code != 200:
            return f"error: publish failed: {r.status_code} {r.text[:300]}"
        post_id = r.json().get("id")
        return f"posted: {post_id}"
    except Exception as e:
        return f"error: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Nur zeigen was gepostet würde")
    parser.add_argument("--pick", help="Bestimmtes Queue-File posten (Pfad oder Name)")
    args = parser.parse_args()

    # 1. Queue-File auswählen
    if args.pick:
        qf = Path(args.pick)
        if not qf.is_absolute():
            qf = QUEUE_DIR / qf
        if not qf.exists():
            print(f"FEHLER: {qf} nicht gefunden", file=sys.stderr)
            sys.exit(1)
    else:
        qf = find_oldest_queue_file()
        if not qf:
            print("Queue ist leer — nichts zu posten.")
            sys.exit(0)

    print(f"=== Queue-Posting ===")
    print(f"File: {qf.name}")

    # 2. Daten laden
    data = json.loads(qf.read_text(encoding="utf-8"))
    image_urls = data.get("image_urls", [])
    caption = data.get("caption", "")
    topic = data.get("topic", "?")
    print(f"Topic: {topic}")
    print(f"Slides: {len(image_urls)}")
    print(f"Caption: {caption[:120]}...")

    if not image_urls:
        print("FEHLER: Keine image_urls in Queue-File", file=sys.stderr)
        sys.exit(1)

    # 3. Dry-Run?
    if args.dry_run:
        print("\n[DRY-RUN] Würde posten — nichts geschickt.")
        sys.exit(0)

    # 4a. IG Posten
    print("\n[Post IG] Sende zu Instagram...")
    status = post_to_instagram(image_urls, caption)
    print(f"IG Status: {status}")

    # 4b. FB Cross-Post (wenn FB_PAGE_ACCESS_TOKEN gesetzt)
    print("\n[Post FB] Cross-Post zu Facebook...")
    fb_status = post_to_facebook(image_urls, caption)
    print(f"FB Status: {fb_status}")

    # AUTH-BLOCK CHECK: if the IG or FB error response contains Meta-Auth-Block
    # patterns (Code 190 = OAuth invalid, Code 200 = API blocked), exit with
    # code 78 so the GitHub workflow auto-disables the cron and stops hitting
    # Meta's API repeatedly during a lock.
    if _detect_auth_block(status) or _detect_auth_block(fb_status):
        print("\n" + "=" * 60, file=sys.stderr)
        print("META AUTH-BLOCK detected (Code 190/200).", file=sys.stderr)
        print("Stopping pipeline. Cron should be auto-disabled by workflow.", file=sys.stderr)
        print("File stays in queue/ — no posting attempt will retry until you fix.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(EXIT_AUTH_BLOCKED)

    # 5. Bei Erfolg: zu posted/ verschieben (mit IG + FB Status)
    if status.startswith("posted:"):
        dest = POSTED_DIR / qf.name
        shutil.move(str(qf), str(dest))
        data["instagram_status"] = status
        data["facebook_status"] = fb_status
        data["posted_at"] = datetime.now().isoformat()
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Verschoben: {dest}")
        sys.exit(0)
    else:
        print("FEHLER: File bleibt in Queue für Retry.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
