"""
post_from_queue.py — Postet das ÄLTESTE Carousel ODER Reel aus queue/ zu Instagram.

Unterstützt:
  POST_*.json  → Instagram Carousel (8 Slides)
  REEL_*.json  → Instagram Reel (Video)

Workflow:
  1. queue/ wird nach POST_*.json und REEL_*.json durchsucht
  2. Ältestes File wird gewählt (nach mtime)
  3. Typ wird erkannt: POST_ = Carousel, REEL_ = Reel
  4. Bei Erfolg: zu posted/ verschoben
  5. Bei Fehler: File bleibt in queue/, Skript exit 1

Aufruf:
    python post_from_queue.py
    python post_from_queue.py --dry-run
    python post_from_queue.py --pick FILE
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

EXIT_AUTH_BLOCKED = 78


def _detect_auth_block(response_text: str) -> bool:
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
    """Findet das älteste POST_*.json oder REEL_*.json in queue/."""
    files = sorted(
        list(QUEUE_DIR.glob("POST_*.json")) + list(QUEUE_DIR.glob("REEL_*.json")),
        key=lambda p: p.stat().st_mtime,
    )
    return files[0] if files else None


def post_to_facebook(image_urls: list, caption: str) -> str:
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    page_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not page_token:
        return "skipped (FB_PAGE_ID oder FB_PAGE_ACCESS_TOKEN fehlt)"

    BASE = "https://graph.facebook.com/v21.0"
    try:
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
    """Postet Carousel via Instagram Login API."""
    ig_id = os.environ.get("IG_USER_ID", "").strip()
    token = os.environ.get("IG_USER_ACCESS_TOKEN", "").strip()
    if not ig_id or not token:
        return "no_meta_setup (IG_USER_ID oder IG_USER_ACCESS_TOKEN fehlt)"

    BASE = "https://graph.instagram.com/v22.0"
    try:
        def _ensure_jpeg(url: str) -> str:
            import re
            if "res.cloudinary.com" in url and url.endswith(".png"):
                return re.sub(r"/upload/", "/upload/f_jpg,q_auto:good/", url, count=1)
            return url

        container_ids = []
        for i, url in enumerate(image_urls):
            url = _ensure_jpeg(url)
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

        r = requests.post(
            f"{BASE}/{ig_id}/media_publish",
            params={"creation_id": carousel_id, "access_token": token},
            timeout=60,
        )
        if r.status_code != 200:
            return f"error: publish failed: {r.status_code} {r.text[:300]}"
        return f"posted: {r.json().get('id')}"
    except Exception as e:
        return f"error: {e}"


def post_reel_to_instagram(video_url: str, caption: str) -> str:
    """Postet ein Reel via Instagram Login API (media_type: REELS)."""
    ig_id = os.environ.get("IG_USER_ID", "").strip()
    token = os.environ.get("IG_USER_ACCESS_TOKEN", "").strip()
    if not ig_id or not token:
        return "no_meta_setup (IG_USER_ID oder IG_USER_ACCESS_TOKEN fehlt)"

    BASE = "https://graph.instagram.com/v22.0"
    try:
        # Step 1: Reel-Container erstellen
        r = requests.post(
            f"{BASE}/{ig_id}/media",
            params={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": token,
            },
            timeout=60,
        )
        if r.status_code != 200:
            return f"error: reel container failed: {r.status_code} {r.text[:300]}"
        container_id = r.json()["id"]
        print(f"    Reel container: {container_id}")

        # Step 2: Video-Processing abwarten (Videos brauchen länger als Bilder)
        for attempt in range(60):
            time.sleep(5)
            sr = requests.get(
                f"{BASE}/{container_id}",
                params={"fields": "status_code", "access_token": token},
                timeout=20,
            )
            if sr.status_code == 200:
                status = sr.json().get("status_code")
                print(f"    Status [{attempt+1}/60]: {status}")
                if status == "FINISHED":
                    break
                if status == "ERROR":
                    return "error: reel processing failed (status=ERROR)"

        # Step 3: Publishen
        r = requests.post(
            f"{BASE}/{ig_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
            timeout=60,
        )
        if r.status_code != 200:
            return f"error: publish failed: {r.status_code} {r.text[:300]}"
        return f"posted: {r.json().get('id')}"
    except Exception as e:
        return f"error: {e}"


def post_reel_to_facebook(video_url: str, caption: str) -> str:
    """Cross-Post: Reel-Video als FB Reel posten."""
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    page_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not page_token:
        return "skipped (FB_PAGE_ID oder FB_PAGE_ACCESS_TOKEN fehlt)"

    BASE = "https://graph.facebook.com/v21.0"
    try:
        r = requests.post(
            f"{BASE}/{page_id}/video_reels",
            params={
                "upload_phase": "start",
                "access_token": page_token,
            },
            timeout=60,
        )
        if r.status_code != 200:
            return f"fb_reel_error: start failed: {r.status_code} {r.text[:200]}"
        video_id = r.json().get("video_id")

        # Publish via video_url (simpler approach)
        r = requests.post(
            f"{BASE}/{page_id}/videos",
            params={
                "file_url": video_url,
                "description": caption,
                "access_token": page_token,
            },
            timeout=120,
        )
        if r.status_code != 200:
            return f"fb_reel_error: upload failed: {r.status_code} {r.text[:200]}"
        return f"fb_reel_posted: {r.json().get('id')}"
    except Exception as e:
        return f"fb_reel_error: {e}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pick", help="Bestimmtes Queue-File (Pfad oder Name)")
    args = parser.parse_args()

    # 1. Queue-File wählen
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

    # 2. Typ bestimmen
    is_reel = qf.name.startswith("REEL_")
    post_type = "Reel" if is_reel else "Carousel"

    print(f"=== Queue-Posting ({post_type}) ===")
    print(f"File: {qf.name}")

    data = json.loads(qf.read_text(encoding="utf-8"))
    caption = data.get("caption", "")
    topic = data.get("topic", "?")
    print(f"Topic: {topic}")

    if args.dry_run:
        print(f"\n[DRY-RUN] Würde {post_type} posten — nichts geschickt.")
        if is_reel:
            print(f"Video URL: {data.get('video_url', '?')}")
        else:
            print(f"Slides: {len(data.get('image_urls', []))}")
        sys.exit(0)

    # 3. Posten
    if is_reel:
        video_url = data.get("video_url", "")
        if not video_url:
            print("FEHLER: Keine video_url in REEL-File", file=sys.stderr)
            sys.exit(1)
        print(f"Video URL: {video_url}")

        print("\n[Post IG] Sende Reel zu Instagram...")
        status = post_reel_to_instagram(video_url, caption)
        print(f"IG Status: {status}")

        print("\n[Post FB] Cross-Post Reel zu Facebook...")
        fb_status = post_reel_to_facebook(video_url, caption)
        print(f"FB Status: {fb_status}")

    else:
        image_urls = data.get("image_urls", [])
        if not image_urls:
            print("FEHLER: Keine image_urls in Queue-File", file=sys.stderr)
            sys.exit(1)
        print(f"Slides: {len(image_urls)}")

        print("\n[Post IG] Sende Carousel zu Instagram...")
        status = post_to_instagram(image_urls, caption)
        print(f"IG Status: {status}")

        print("\n[Post FB] Cross-Post zu Facebook...")
        fb_status = post_to_facebook(image_urls, caption)
        print(f"FB Status: {fb_status}")

    # AUTH-BLOCK CHECK
    if _detect_auth_block(status) or _detect_auth_block(fb_status):
        print("\n" + "=" * 60, file=sys.stderr)
        print("META AUTH-BLOCK detected (Code 190/200).", file=sys.stderr)
        print("Cron wird auto-disabled durch Workflow.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(EXIT_AUTH_BLOCKED)

    # 4. Bei Erfolg: zu posted/ verschieben
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
