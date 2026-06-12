"""
cloud_pipeline.py — Master-Orchestrator für volle Auto-Pipeline.

Topic in → fertiges Carousel + Caption + (optional) Posting raus.
Nutzt slide_planner.py + generate_carousel.py.

Aufruf:
    python cloud_pipeline.py "Vitamin D deficiency"
    python cloud_pipeline.py --from-queue topics.txt
"""

import argparse
import asyncio
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

# slide_planner importieren
sys.path.insert(0, str(ROOT))
from slide_planner import plan_slides

# generate_carousel als Modul laden (es exportiert die Slide-Building-Funktionen)
spec = importlib.util.spec_from_file_location("gc", ROOT / "generate_carousel.py")
gc = importlib.util.module_from_spec(spec)
# Wir laden es nur für die Funktionen, NICHT main() ausführen
gc_source = (ROOT / "generate_carousel.py").read_text(encoding="utf-8")


def run_pipeline(topic: str, language: str = "en", backend: str = "auto",
                 do_upload: bool = False, do_post: bool = False,
                 save_to_queue: bool = False) -> dict:
    """Führt die komplette Pipeline für ein Topic aus.

    Returns dict mit Pfaden + Caption + Status.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    print(f"\n=== Pipeline Run: {timestamp} ===")
    print(f"Topic: {topic} ({language})")

    # 1. Slide-Plan generieren via Haiku/Gemini
    print("\n[1] Slide-Plan generieren...")
    plan = plan_slides(topic, language, backend)
    print(f"    OK — {len(plan['slides'])} Slides geplant")

    # Plan in generate_carousel.py SLIDES injizieren via JSON-Datei
    plan_path = ROOT / f"output/plan_{timestamp}.json"
    plan_path.parent.mkdir(exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. Carousel generieren (Pexels + HTML + Playwright)
    print("\n[2] Carousel generieren...")
    # Wir patchen generate_carousel.SLIDES temporär durch monkey-import
    import importlib
    if "generate_carousel" in sys.modules:
        del sys.modules["generate_carousel"]
    import generate_carousel as gc_mod
    # SLIDES = AI-generierte Content-Slides + Outros (OUTRO_COMMENT ist jetzt mit OUTRO_FOLLOW gemerged)
    outros = [o for o in (gc_mod.OUTRO_FOLLOW, gc_mod.OUTRO_COMMENT) if o]
    gc_mod.SLIDES = (
        [_normalize_slide(s) for s in plan["slides"]] + outros
    )

    # Bilder + HTML + Export — defensiv: None-Slides filtern, korrekte Bild-Quelle wählen
    slides_with_imgs = []
    valid_slides = [s for s in gc_mod.SLIDES if s and isinstance(s, dict)]
    print(f"    Verarbeite {len(valid_slides)} Slides (nach None-Filter)")
    for i, slide in enumerate(valid_slides):
        # get_slide_image wählt Quelle: local_bg / google / ai_render / pexels
        path = gc_mod.get_slide_image(slide, i + 1)
        b64 = gc_mod.img_to_base64(path)
        slides_with_imgs.append((slide, b64))

    html = gc_mod.build_html(slides_with_imgs)
    html_path = gc_mod.OUTPUT_DIR / f"carousel_{timestamp}.html"
    html_path.write_text(html, encoding="utf-8")

    asyncio.run(gc_mod.export_slides(html_path, len(slides_with_imgs)))
    print("    OK — 7 PNGs exportiert")

    # 3. (Optional) Cloudinary Upload
    cloudinary_urls = []
    if do_upload:
        print("\n[3] Cloudinary Upload...")
        cloudinary_urls = upload_to_cloudinary(timestamp)
        print(f"    OK — {len(cloudinary_urls)} URLs erhalten")

    # 4a. (Optional) Save to queue für späteres Posten (Generation-only Mode)
    queue_file = None
    if save_to_queue and cloudinary_urls:
        queue_dir = ROOT / "queue"
        queue_dir.mkdir(exist_ok=True)
        queue_file = queue_dir / f"POST_{timestamp}.json"
        queue_data = {
            "timestamp": timestamp,
            "topic": topic,
            "language": language,
            "caption": plan["caption"],
            "image_urls": cloudinary_urls,
            "generated_at": datetime.now().isoformat(),
        }
        queue_file.write_text(json.dumps(queue_data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[4a] Queued für späteres Posten: {queue_file.name}")

    # 4b. (Optional) Instagram Post (sofort)
    ig_status = "skipped"
    fb_status = "skipped"
    if do_post and cloudinary_urls:
        print("\n[4b] Instagram Posting...")
        ig_status = post_to_instagram(cloudinary_urls, plan["caption"])
        print(f"    IG Status: {ig_status}")
        print("\n[4c] Facebook Cross-Post...")
        fb_status = post_to_facebook(cloudinary_urls, plan["caption"])
        print(f"    FB Status: {fb_status}")

    # 5. Summary speichern
    summary = {
        "timestamp": timestamp,
        "topic": topic,
        "language": language,
        "caption": plan["caption"],
        "slide_count": len(plan["slides"]),
        "cloudinary_urls": cloudinary_urls,
        "instagram_status": ig_status,
        "facebook_status": fb_status,
        "queued_file": str(queue_file) if queue_file else None,
        "html_path": str(html_path),
        "plan_path": str(plan_path),
    }
    summary_path = ROOT / f"output/summary_{timestamp}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSummary: {summary_path}")
    return summary


def _fix_parts(raw):
    """Normalisiert AI-generierte headline/subhead_parts zu sauberen (text, modifier) Tupeln.
    Schützt gegen: einzelne Strings, 1-Element-Listen, None-Einträge."""
    if not raw:
        return [("", "regular")]
    result = []
    for p in raw:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            result.append((str(p[0]), str(p[1])))
        elif isinstance(p, (list, tuple)) and len(p) == 1:
            result.append((str(p[0]), "regular"))
        elif isinstance(p, str):
            result.append((p, "regular"))
        else:
            result.append((str(p) if p else "", "regular"))
    return result if result else [("", "regular")]


def _normalize_slide(s: dict) -> dict:
    """Stellt sicher, dass JSON-Plan zu generate_carousel.SLIDES Format passt.
    Defensiv: alle Felder optional, Pass-Through für google_query/ai_render."""
    if not s or not isinstance(s, dict):
        return None
    return {
        "type": s.get("type", "content"),
        "tag": s.get("tag", ""),
        "headline_parts": _fix_parts(s.get("headline_parts", [])),
        "subhead_parts": _fix_parts(s["subhead_parts"]) if s.get("subhead_parts") else None,
        "subline": s.get("subline", ""),
        "pexels_query": s.get("pexels_query", "minimalist health aesthetic"),
        "pexels_color": s.get("pexels_color"),
        "ai_render": s.get("ai_render", False),
        "ai_prompt": s.get("ai_prompt"),
        "google_query": s.get("google_query"),
        "show_logo_block": s.get("show_logo_block", True),
        "show_swipe_cta": s.get("show_swipe_cta", True),
        "engagement_text": s.get("engagement_text", ""),
        "list_items": s.get("list_items"),
        "solid_color": s.get("solid_color"),
    }


def upload_to_cloudinary(timestamp: str) -> list[str]:
    """Lädt slide_1.png ... slide_7.png zu Cloudinary, gibt öffentliche URLs zurück."""
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    output = ROOT / "output"
    # Alle slide_N.png im output Ordner finden, sortiert nach Nummer
    slide_files = sorted(
        output.glob("slide_*.png"),
        key=lambda p: int(p.stem.split("_")[1]),
    )
    urls = []
    for f in slide_files:
        i = int(f.stem.split("_")[1])
        result = cloudinary.uploader.upload(
            str(f),
            public_id=f"medical_{timestamp}_slide_{i}",
            folder="medical-insta",
            overwrite=True,
            format="jpg",          # Instagram Carousel erfordert JPEG, kein PNG
            quality="auto:good",
        )
        urls.append(result["secure_url"])
        print(f"  Uploaded {f.name} → JPEG")
    return urls


def post_to_facebook(image_urls: list, caption: str) -> str:
    """Cross-Post: postet Carousel-Bilder als FB Photo-Album.
    Nutzt FB_PAGE_ACCESS_TOKEN (laeuft NIE ab) + FB_PAGE_ID."""
    page_id = os.environ.get("FB_PAGE_ID", "").strip()
    page_token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not page_token:
        return "skipped (FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN fehlt)"
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
                return f"fb_error: photo {i+1}: {r.status_code} {r.text[:200]}"
            photo_ids.append(r.json()["id"])
        attached = ",".join([f'{{"media_fbid":"{pid}"}}' for pid in photo_ids])
        r = requests.post(
            f"{BASE}/{page_id}/feed",
            params={"message": caption, "attached_media": f"[{attached}]", "access_token": page_token},
            timeout=60,
        )
        if r.status_code != 200:
            return f"fb_error: publish: {r.status_code} {r.text[:200]}"
        return f"fb_posted: {r.json().get('id')}"
    except Exception as e:
        return f"fb_error: {e}"


def post_to_instagram(image_urls: list[str], caption: str) -> str:
    """Postet Carousel via NEUE Instagram Login API (graph.instagram.com).
    Nutzt IG_USER_ID + IG_USER_ACCESS_TOKEN (nicht die alten Meta Graph Vars).

    Returns: 'posted: <id>', 'no_meta_setup', oder 'error: ...'
    """
    import time
    ig_id = os.environ.get("IG_USER_ID", "").strip()
    token = os.environ.get("IG_USER_ACCESS_TOKEN", "").strip()
    if not ig_id or not token:
        return "no_meta_setup (IG_USER_ID oder IG_USER_ACCESS_TOKEN fehlt)"

    BASE = "https://graph.instagram.com/v22.0"
    try:
        # Step 1: Pro Bild einen Carousel-Item-Container erstellen
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
            print(f"    Container {i+1}/{len(image_urls)} created: {container_ids[-1]}")

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

        # Step 3: Warten bis Container ready (IG braucht ~5-30s)
        for attempt in range(30):
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
                    return f"error: container processing failed"

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
    parser.add_argument("topic", nargs="?", help="Topic, z.B. 'Vitamin D deficiency'")
    parser.add_argument("--from-queue", default=None, help="Pfad zu topics.txt (erste Zeile wird genommen, dann entfernt)")
    parser.add_argument("--language", default="en", choices=["en", "de"])
    parser.add_argument("--backend", default="auto", choices=["auto", "gemini", "anthropic"])
    parser.add_argument("--upload", action="store_true", help="Zu Cloudinary hochladen")
    parser.add_argument("--post", action="store_true", help="Auf Instagram posten (braucht Meta-Setup)")
    parser.add_argument("--save-to-queue", action="store_true", help="Statt sofort posten: Queue-File anlegen (für Cron-Posting später)")
    args = parser.parse_args()

    # Topic ermitteln
    if args.from_queue:
        queue_file = Path(args.from_queue)
        lines = [l.strip() for l in queue_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
        if not lines:
            print("Topic-Queue ist leer.", file=sys.stderr)
            sys.exit(1)
        topic = lines[0]
        # Erste Zeile aus Queue entfernen (FIFO)
        rest = "\n".join(["# Auto-removed: " + topic, ""] + lines[1:]) + "\n"
        queue_file.write_text(rest, encoding="utf-8")
        print(f"Aus Queue genommen: {topic}")
    elif args.topic:
        topic = args.topic
    else:
        print("FEHLER: Topic oder --from-queue benötigt.", file=sys.stderr)
        sys.exit(1)

    summary = run_pipeline(topic, args.language, args.backend, args.upload, args.post, args.save_to_queue)
    print(f"\n=== FERTIG ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

