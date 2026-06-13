"""
reel_pipeline.py — Erstellt einen Instagram Reel aus Carousel-Slides.

Ablauf:
  1. Pexels Intro-Video suchen + downloaden (10s)
  2. Pro Slide: TTS Audio (edge-tts, en-US-AriaNeural)
  3. Pro Slide: Video = JPEG + Ken Burns Zoom + TTS Audio (ffmpeg)
  4. Alle Teile concatenaten → reel.mp4
  5. Cloudinary Upload (video)
  6. REEL_TIMESTAMP.json in queue/ speichern

Aufruf:
    python reel_pipeline.py                     # nimmt neuesten plan aus output/
    python reel_pipeline.py --from-plan output/plan_20260614_0200.json
    python reel_pipeline.py --save-to-queue
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
VOICE = "en-US-AriaNeural"
FPS = 25
SLIDE_PADDING_S = 0.3


# ── Pexels Video ──────────────────────────────────────────────────────────────

def pexels_search_video(query: str) -> str | None:
    if not PEXELS_KEY:
        return None
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": PEXELS_KEY},
        params={"query": query, "per_page": 10, "min_duration": 6, "max_duration": 20},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  Pexels Video: {r.status_code}", file=sys.stderr)
        return None
    videos = r.json().get("videos", [])
    for video in videos:
        files = sorted(video.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
        for vf in files:
            w, h = vf.get("width", 0), vf.get("height", 0)
            if h and w and h / w >= 1.3:  # portrait: 9:16 oder ähnlich
                return vf["link"]
        for vf in files:
            if vf.get("height", 0) >= 720:
                return vf["link"]
    if videos:
        files = sorted(videos[0].get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
        if files:
            return files[0]["link"]
    return None


def _topic_to_video_query(topic: str) -> str:
    t = topic.lower()
    if any(w in t for w in ["brain", "mental", "stress", "anxiety", "sleep", "cognitive"]):
        return "woman meditation peaceful"
    if any(w in t for w in ["gut", "digest", "microbiome", "bloat", "stomach"]):
        return "woman eating healthy food"
    if any(w in t for w in ["hormone", "cortisol", "estrogen", "cycle", "pregnancy", "perimenopause"]):
        return "woman wellness morning routine"
    if any(w in t for w in ["weight", "fat", "metabolism", "belly", "calories"]):
        return "woman fitness workout"
    if any(w in t for w in ["heart", "blood", "pressure", "cholesterol", "cardiovascular"]):
        return "woman running outdoors"
    if any(w in t for w in ["immune", "inflammation", "vitamin", "supplement", "nutrient"]):
        return "healthy food vegetables bright"
    return "woman healthy lifestyle nature"


def download_file(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=90, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  Download fail: {e}", file=sys.stderr)
        return False


# ── TTS ───────────────────────────────────────────────────────────────────────

def slide_to_text(slide: dict) -> str:
    def parts_text(parts):
        if not parts:
            return ""
        return " ".join(
            p[0] if isinstance(p, (list, tuple)) and p else (p if isinstance(p, str) else "")
            for p in parts
        ).strip()

    headline = parts_text(slide.get("headline_parts") or [])
    subhead = parts_text(slide.get("subhead_parts") or [])
    subline = (slide.get("subline") or "").strip()
    engagement = (slide.get("engagement_text") or "").strip()

    pieces = [headline]
    if subhead:
        pieces.append(subhead)
    elif subline:
        pieces.append(subline)
    if engagement and engagement not in pieces:
        pieces.append(engagement)

    return ". ".join(p for p in pieces if p)


async def _tts_async(text: str, path: Path):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(path))


def generate_tts(text: str, path: Path):
    asyncio.run(_tts_async(text, path))


# ── ffmpeg helpers ─────────────────────────────────────────────────────────────

def get_audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    try:
        for s in json.loads(result.stdout).get("streams", []):
            if s.get("codec_type") == "audio":
                return float(s.get("duration", 5.0))
    except Exception:
        pass
    return 5.0


def create_slide_video(image_path: Path, audio_path: Path, out: Path, duration: float):
    """JPEG → 1080x1920 Video mit leichtem Ken-Burns-Zoom + TTS Audio."""
    n_frames = int(duration * FPS)
    # Zoom von 1.0 auf 1.08, zentriert
    zoom_expr = f"min(1+0.08*on/{n_frames},1.08)"
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", (
            f"scale=1200:2133:force_original_aspect_ratio=increase,"
            f"crop=1200:2133,"
            f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={n_frames}:s=1080x1920:fps={FPS}"
        ),
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(out),
    ], check=True, capture_output=True)


def prep_intro_video(src: Path, out: Path, duration: float = 10.0):
    """Intro-Video auf 1080x1920 trimmen + konvertieren."""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(src),
        "-t", str(duration),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=25",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(out),
    ], check=True, capture_output=True)


def concat_videos(paths: list[Path], out: Path):
    filelist = out.parent / f"filelist_{out.stem}.txt"
    filelist.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(filelist),
        "-c", "copy",
        str(out),
    ], check=True, capture_output=True)
    filelist.unlink(missing_ok=True)


# ── Cloudinary ────────────────────────────────────────────────────────────────

def upload_video_to_cloudinary(video_path: Path, timestamp: str) -> str:
    import cloudinary
    import cloudinary.uploader
    cloudinary.config(
        cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
        api_key=os.environ["CLOUDINARY_API_KEY"],
        api_secret=os.environ["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    result = cloudinary.uploader.upload(
        str(video_path),
        resource_type="video",
        public_id=f"medical_reel_{timestamp}",
        folder="medical-reels",
        overwrite=True,
    )
    return result["secure_url"]


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def run_reel_pipeline(plan: dict, timestamp: str, save_to_queue: bool = True) -> dict:
    tmp = ROOT / "output" / f"reel_tmp_{timestamp}"
    tmp.mkdir(parents=True, exist_ok=True)

    topic = plan.get("topic", "health")
    slides = plan.get("slides", [])
    caption = plan.get("caption", "")

    print(f"\n=== Reel Pipeline: {timestamp} ===")
    print(f"Topic: {topic} | Slides: {len(slides)}")

    video_parts: list[Path] = []

    # 1. Pexels Intro-Video
    print("\n[Reel 1] Intro-Video von Pexels...")
    vq = _topic_to_video_query(topic)
    intro_url = pexels_search_video(vq)
    if intro_url:
        raw = tmp / "intro_raw.mp4"
        intro_final = tmp / "intro.mp4"
        if download_file(intro_url, raw):
            try:
                prep_intro_video(raw, intro_final, duration=10.0)
                video_parts.append(intro_final)
                print(f"  OK: '{vq}' ({intro_final.stat().st_size // 1024} KB)")
            except subprocess.CalledProcessError as e:
                print(f"  Intro convert fail: {e.stderr.decode()[:200]}", file=sys.stderr)
    else:
        print("  Kein Pexels Video gefunden — ohne Intro")

    # 2. Pro Slide: TTS + Video
    for i, slide in enumerate(slides):
        print(f"\n[Reel 2.{i+1}] Slide {i+1}/{len(slides)}")

        slide_img = ROOT / "output" / f"slide_{i+1}.png"
        if not slide_img.exists():
            print(f"  Bild fehlt: {slide_img}", file=sys.stderr)
            continue

        tts_text = slide_to_text(slide) or f"Health insight {i+1}"
        print(f"  TTS: {tts_text[:80]}...")

        audio_path = tmp / f"audio_{i+1}.mp3"
        try:
            generate_tts(tts_text, audio_path)
        except Exception as e:
            print(f"  TTS fail: {e}", file=sys.stderr)
            continue

        duration = get_audio_duration(audio_path) + SLIDE_PADDING_S
        slide_video = tmp / f"slide_{i+1}.mp4"
        try:
            create_slide_video(slide_img, audio_path, slide_video, duration)
            video_parts.append(slide_video)
            print(f"  Video OK ({duration:.1f}s, {slide_video.stat().st_size // 1024} KB)")
        except subprocess.CalledProcessError as e:
            print(f"  ffmpeg fail: {e.stderr.decode()[:300]}", file=sys.stderr)
            continue

    if not video_parts:
        raise RuntimeError("Keine Video-Teile erzeugt")

    # 3. Concat
    total_parts = len(video_parts)
    print(f"\n[Reel 3] Concatenate {total_parts} Teile...")
    final_video = ROOT / "output" / f"reel_{timestamp}.mp4"
    concat_videos(video_parts, final_video)
    size_mb = final_video.stat().st_size / 1024 / 1024
    print(f"  Fertig: {size_mb:.1f} MB")

    # 4. Cloudinary Upload
    print("\n[Reel 4] Cloudinary Upload...")
    video_url = upload_video_to_cloudinary(final_video, timestamp)
    print(f"  URL: {video_url}")

    # 5. Queue
    queue_file = None
    if save_to_queue:
        qd = ROOT / "queue"
        qd.mkdir(exist_ok=True)
        queue_file = qd / f"REEL_{timestamp}.json"
        queue_file.write_text(json.dumps({
            "timestamp": timestamp,
            "topic": topic,
            "caption": caption,
            "video_url": video_url,
            "generated_at": datetime.now().isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[Reel 5] Queued: {queue_file.name}")

    return {"video_url": video_url, "queue_file": str(queue_file) if queue_file else None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-plan", help="Pfad zu plan_TIMESTAMP.json")
    parser.add_argument("--save-to-queue", action="store_true")
    args = parser.parse_args()

    if args.from_plan:
        plan_path = Path(args.from_plan)
    else:
        plans = sorted((ROOT / "output").glob("plan_*.json"), key=lambda p: p.stat().st_mtime)
        if not plans:
            print("Kein Plan in output/", file=sys.stderr)
            sys.exit(1)
        plan_path = plans[-1]

    print(f"Plan: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    timestamp = plan_path.stem.replace("plan_", "")

    result = run_reel_pipeline(plan, timestamp, save_to_queue=args.save_to_queue)
    print(json.dumps(result, ensure_ascii=False, indent=2))
